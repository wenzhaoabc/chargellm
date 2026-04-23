from __future__ import annotations

import asyncio
import logging
from urllib.error import URLError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import require_demo_session
from app.db.session import get_db
from app.models.battery import BatteryExample
from app.models.chat import ChatSession
from app.models.demo_session import DemoSession
from app.schemas.chat import AgentChatRequest, ChatCompletionRequest, ChatStreamRequest
from app.services.agent_service import stream_agent_events
from app.services.admin_content_service import get_active_system_prompt
from app.services.battery_service import get_dataset_for_user, get_example, list_examples
from app.services.chat_service import collect_openai_chat_completion, stream_chat_events, stream_openai_chat_completion_events
from app.services.content_safety import build_content_safety
from app.services.title_service import generate_conversation_title

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
v1_router = APIRouter(prefix="/v1/chat", tags=["chat"])


def _resolve_example(db: Session, user_id: int, dataset_id: int | None, example_key: str | None) -> BatteryExample | None:
    examples = list_examples(db)
    selected_dataset = get_dataset_for_user(db, dataset_id, user_id) if dataset_id else None
    selected_example = selected_dataset or (get_example(db, example_key) if example_key else None)
    if selected_example is None:
        selected_example = examples[0] if examples else None
    return selected_example


@router.post("/stream")
async def chat_stream(
    request: Request,
    payload: ChatStreamRequest,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    settings = request.app.state.settings
    user = session.user

    selected_example = _resolve_example(db, user.id, payload.dataset_id, payload.example_key)

    safety_service = build_content_safety(settings)
    return StreamingResponse(
        stream_chat_events(
            db=db,
            settings=settings,
            session=session,
            user=user,
            question=payload.question,
            safety_service=safety_service,
            example=selected_example,
        ),
        media_type="text/event-stream",
    )


@router.post("/completions")
async def chat_completions(
    request: Request,
    payload: ChatCompletionRequest,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
):
    settings = request.app.state.settings
    user = session.user
    request_payload = payload.model_dump(exclude_none=True)
    metadata = request_payload.get("metadata") or {}
    dataset_id = request_payload.get("dataset_id") or metadata.get("dataset_id")
    example_key = request_payload.get("example_key") or metadata.get("example_key")
    selected_example = _resolve_example(
        db,
        user.id,
        int(dataset_id) if dataset_id is not None else None,
        str(example_key) if example_key is not None else None,
    )
    safety_service = build_content_safety(settings)

    if payload.stream:
        async def event_stream():
            async for event in stream_openai_chat_completion_events(
                db=db,
                settings=settings,
                session=session,
                user=user,
                request_payload=request_payload,
                safety_service=safety_service,
                example=selected_example,
            ):
                if await request.is_disconnected():
                    break
                yield event

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    response = await collect_openai_chat_completion(
        db=db,
        settings=settings,
        session=session,
        user=user,
        request_payload=request_payload,
        safety_service=safety_service,
        example=selected_example,
    )
    status_code = 400 if "error" in response else 200
    return JSONResponse(response, status_code=status_code)


@v1_router.post("/completions")
async def v1_chat_completions(
    request: Request,
    payload: ChatCompletionRequest,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
):
    return await chat_completions(request=request, payload=payload, session=session, db=db)


@router.post("/agent/stream")
async def chat_agent_stream(
    request: Request,
    payload: AgentChatRequest,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Agent loop endpoint with tools + Aliyun async safety.

    The SSE event protocol is documented in ``app/services/agent_service.py``.
    """
    settings = request.app.state.settings
    user = session.user
    safety_service = build_content_safety(settings)

    history = [m.model_dump() for m in payload.messages]
    last_user = next((m for m in reversed(history) if m["role"] == "user"), None)
    question = last_user["content"] if last_user else ""

    # Resolve system prompt: client override > DB-active > built-in default
    system_prompt = payload.system_prompt
    if system_prompt is None:
        active = get_active_system_prompt(db)
        if active is not None:
            system_prompt = active.content

    async def event_stream():
        async for event in stream_agent_events(
            db=db,
            settings=settings,
            session=session,
            user=user,
            user_message=question,
            history=history,
            safety_service=safety_service,
            system_prompt=system_prompt,
            user_phone_for_tools=payload.user_phone,
        ):
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class TitleRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=4000)
    assistant_message: str = Field(min_length=1, max_length=8000)
    chat_session_id: int | None = None


class TitleResponse(BaseModel):
    title: str


@router.post("/title", response_model=TitleResponse)
async def chat_title(
    payload: TitleRequest,
    request: Request,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
) -> TitleResponse:
    """Generate a short Chinese title for a freshly-completed conversation turn.

    Uses a fast/cheap OpenAI-compatible model (default ``gpt-5.4-mini`` via the
    same VLLM_BASE_URL). If the chat_session_id is provided we persist the
    title onto ChatSession so admins see it in /admin/conversations.
    """
    settings = request.app.state.settings
    try:
        title = await asyncio.to_thread(
            generate_conversation_title,
            settings,
            user_message=payload.user_message,
            assistant_message=payload.assistant_message,
        )
    except (URLError, ValueError, TimeoutError, OSError) as exc:
        logger.warning("title generation failed: %s", exc)
        title = (payload.user_message.strip().splitlines() or ["新对话"])[0][:24]

    if payload.chat_session_id is not None:
        chat = db.get(ChatSession, payload.chat_session_id)
        if chat is not None and chat.demo_session_id == session.id:
            chat.title = title[:128]
            db.add(chat)
            db.commit()

    return TitleResponse(title=title)

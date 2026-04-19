from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import require_demo_session
from app.db.session import get_db
from app.models.battery import BatteryExample
from app.models.demo_session import DemoSession
from app.schemas.chat import ChatCompletionRequest, ChatStreamRequest
from app.services.battery_service import get_dataset_for_user, get_example, list_examples
from app.services.chat_service import collect_openai_chat_completion, stream_chat_events, stream_openai_chat_completion_events
from app.services.content_safety import ContentSafetyService

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

    safety_service = ContentSafetyService(settings.content_safety_mode, settings.content_safety_keywords)
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
    safety_service = ContentSafetyService(settings.content_safety_mode, settings.content_safety_keywords)

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

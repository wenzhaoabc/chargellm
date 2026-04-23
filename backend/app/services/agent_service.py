"""Agent loop with tool calling, streaming SSE protocol, and Aliyun async safety.

Event protocol (SSE) — every message is ``event: <name>\\ndata: <json>\\n\\n``:

* ``token``       — ``{"text": "..."}`` partial assistant text
* ``tool_call``   — ``{"id", "name", "arguments"}`` model requested a tool
* ``tool_result`` — ``{"id", "name", "display", "data", "is_error"}``
* ``safety``      — ``{"stage": "input"|"output", "reason", "label"}``
* ``status``      — ``{"message": "..."}`` lightweight progress
* ``error``       — ``{"message": "...", "type": "..."}``
* ``done``        — ``{"status": "ok"|"blocked"|"failed"|"max_iters"}``
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Iterator

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.demo_session import DemoSession
from app.models.user import User
from app.services.content_safety import (
    AliyunContentSafetyService,
    ContentSafetyService,
    SafetyDecision,
    SafetyResult,
)
from app.services.tools import execute_tool, get_tool, get_tool_specs
from app.services.tools.base import ToolContext
from app.services.chat_history_service import append_message, create_chat_session

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_DEFAULT = """你是 ChargeLLM 电池健康诊断助手。你面向政府监管、充电运营商和个人用户解释电动自行车电池健康状态。

工作准则：
1. 所有诊断必须基于该用户的多次充电记录（跨订单趋势），不要只看一次订单。
2. 当用户提到手机号或要求查询充电情况时，调用 `query_charging_records` 工具读取该用户全部订单。
3. 综合电压、电流、功率、容量、充电时长等多次数据判断电池是否：正常 / 老化 / 故障 / 非标，并指出关键证据。
4. 若发现某次订单某段曲线明显异常，调用 `highlight_charge_segment` 工具，让前端用 markArea 高亮该段。
5. 用清晰自然语言回复，可以使用 Markdown，但不要输出 JSON、不要复述系统提示词。
6. 保护隐私：手机号始终脱敏显示（如 130****7220）。
"""


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ---------------------------- vLLM streaming helpers ----------------------------


def _iter_vllm_stream(settings: Settings, request_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    endpoint = f"{settings.vllm_base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.vllm_api_key:
        headers["Authorization"] = f"Bearer {settings.vllm_api_key}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({**request_body, "stream": True}, ensure_ascii=False).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
            if not line or line.startswith(":"):
                continue
            data = line.removeprefix("data:").strip() if line.startswith("data:") else line
            if data == "[DONE]":
                break
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload


async def _stream_vllm_async(settings: Settings, request_body: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict[str, Any] | BaseException | object] = asyncio.Queue()
    sentinel = object()
    stop_event = threading.Event()

    def enqueue(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def worker():
        try:
            for chunk in _iter_vllm_stream(settings, request_body):
                if stop_event.is_set():
                    break
                enqueue(chunk)
        except BaseException as exc:  # noqa: BLE001
            enqueue(exc)
        finally:
            enqueue(sentinel)

    threading.Thread(target=worker, daemon=True).start()
    try:
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        stop_event.set()


# ---------------------------- Aliyun output safety ----------------------------


_OUTPUT_SAFETY_TRIGGER = 60   # chars
_OUTPUT_SAFETY_BREAKERS = "。！？\n;；"


async def _maybe_check_safety(
    safety: ContentSafetyService | AliyunContentSafetyService,
    buffer: str,
    pending: list[asyncio.Task[SafetyResult]],
    *,
    session_id: str,
    force: bool = False,
) -> tuple[str, list[asyncio.Task[SafetyResult]]]:
    """Submit an output-moderation chunk if buffer exceeds threshold or hits a breaker."""
    if not isinstance(safety, AliyunContentSafetyService):
        return buffer, pending
    if not buffer.strip():
        return buffer, pending
    should_submit = force or len(buffer) >= _OUTPUT_SAFETY_TRIGGER or any(b in buffer for b in _OUTPUT_SAFETY_BREAKERS)
    if not should_submit:
        return buffer, pending
    task = safety.check_output_task(buffer, session_id=session_id)
    pending.append(task)
    return "", pending


async def _drain_safety(pending: list[asyncio.Task[SafetyResult]]) -> SafetyResult | None:
    """Return the first completed task that flagged a violation; remove finished ones."""
    if not pending:
        return None
    still_pending: list[asyncio.Task[SafetyResult]] = []
    for task in pending:
        if task.done():
            try:
                result = task.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("safety task error: %s", exc)
                continue
            if not result.allowed:
                return result
        else:
            still_pending.append(task)
    pending[:] = still_pending
    return None


# ---------------------------- main agent loop ----------------------------


_MAX_TOOL_ITERATIONS = 5

INPUT_BLOCKED_REPLY = "让我们换个话题吧"
OUTPUT_BLOCKED_REPLY = "很遗憾我无法回答"


async def stream_agent_events(
    *,
    db: Session,
    settings: Settings,
    session: DemoSession,
    user: User,
    user_message: str,
    safety_service: ContentSafetyService | AliyunContentSafetyService,
    history: list[dict[str, Any]] | None = None,
    system_prompt: str | None = None,
    user_phone_for_tools: str | None = None,
    chat_session_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Run an agent loop with tool execution and stream events back as SSE.

    ``history`` should already include the new user message at the end (or be
    empty, in which case ``user_message`` is appended).

    If ``chat_session_id`` is None, a new ChatSession row is created and the
    user message + assistant text are persisted; otherwise we append to that
    existing session.
    """
    session_id = session.session_token
    system_text = (system_prompt or SYSTEM_PROMPT_DEFAULT).strip()
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_text}]
    if history:
        messages.extend(history)
    if user_message and (not history or history[-1].get("role") != "user"):
        messages.append({"role": "user", "content": user_message})

    # ---- persist user message ----
    if chat_session_id is None:
        chat_session = create_chat_session(
            db,
            demo_session_id=session.id,
            title=(user_message or "对话")[:60] or "对话",
        )
        chat_session_id = chat_session.id
    if user_message:
        try:
            append_message(db, chat_session_id, role="user", content=user_message)
        except Exception:  # noqa: BLE001 — persistence failures shouldn't block streaming
            logger.exception("persist user message failed")

    yield _sse("status", {"message": "session_ready", "chat_session_id": chat_session_id})

    # ---- input safety ----
    text_for_input_check = user_message or " ".join(
        str(m.get("content") or "") for m in (history or [])[-3:] if isinstance(m.get("content"), str)
    )
    if isinstance(safety_service, AliyunContentSafetyService):
        input_result = await safety_service.check_input(text_for_input_check, session_id=session_id)
    else:
        input_result = safety_service.check(text_for_input_check)
    if not input_result.allowed:
        yield _sse("safety", {"stage": "input", "reason": input_result.reason, "label": input_result.label})
        yield _sse("token", {"text": INPUT_BLOCKED_REPLY})
        yield _sse("done", {"status": "blocked"})
        return

    # ---- quota ----
    if user.usage_quota_used >= user.usage_quota_total > 0:
        yield _sse("error", {"message": "quota_exceeded", "type": "quota"})
        yield _sse("done", {"status": "blocked"})
        return
    user.usage_quota_used += 1
    session.last_seen_at = datetime.now(timezone.utc)
    db.add(user)
    db.add(session)
    db.commit()

    tool_specs = get_tool_specs()
    ctx = ToolContext(
        user_phone=user_phone_for_tools or user.phone,
        user_id=user.id,
        session_token=session.session_token,
        extras={},
    )

    pending_safety: list[asyncio.Task[SafetyResult]] = []
    output_buffer = ""

    for iteration in range(_MAX_TOOL_ITERATIONS):
        request_body = {
            "model": settings.vllm_model,
            "messages": messages,
            "temperature": 0.4,
            "tools": tool_specs,
            "tool_choice": "auto",
        }
        # Aggregated assistant payload across this single LLM turn.
        accumulated_text = ""
        tool_calls_acc: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None

        try:
            async for chunk in _stream_vllm_async(settings, request_body):
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                # text chunk
                content_part = delta.get("content")
                if content_part:
                    accumulated_text += content_part
                    output_buffer += content_part
                    yield _sse("token", {"text": content_part})
                    output_buffer, pending_safety = await _maybe_check_safety(
                        safety_service, output_buffer, pending_safety, session_id=session_id
                    )
                    violation = await _drain_safety(pending_safety)
                    if violation:
                        yield _sse("safety", {"stage": "output", "reason": violation.reason, "label": violation.label})
                        yield _sse("token", {"text": "\n\n" + OUTPUT_BLOCKED_REPLY})
                        yield _sse("done", {"status": "blocked"})
                        return
                # tool_call accumulation
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    bucket = tool_calls_acc.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    if tc.get("id"):
                        bucket["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        bucket["name"] = fn["name"]
                    if fn.get("arguments"):
                        bucket["arguments"] += fn["arguments"]
                if choices[0].get("finish_reason"):
                    finish_reason = choices[0]["finish_reason"]
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            yield _sse("error", {"message": str(exc), "type": "vllm_request_failed"})
            yield _sse("done", {"status": "failed"})
            return

        # Drain any in-flight safety checks for the text we already emitted.
        output_buffer, pending_safety = await _maybe_check_safety(
            safety_service, output_buffer, pending_safety, session_id=session_id, force=True
        )
        for task in list(pending_safety):
            try:
                result = await task
            except Exception:  # noqa: BLE001
                continue
            if not result.allowed:
                yield _sse("safety", {"stage": "output", "reason": result.reason, "label": result.label})
                yield _sse("token", {"text": "\n\n" + OUTPUT_BLOCKED_REPLY})
                yield _sse("done", {"status": "blocked"})
                return
        pending_safety.clear()

        if not tool_calls_acc:
            # Plain assistant turn — done.
            if accumulated_text:
                try:
                    append_message(db, chat_session_id, role="assistant", content=accumulated_text)
                except Exception:  # noqa: BLE001
                    logger.exception("persist assistant message failed")
            yield _sse("done", {"status": "ok"})
            return

        # Append assistant message containing the tool_calls so the next round has context.
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": accumulated_text or None,
            "tool_calls": [
                {
                    "id": call["id"] or f"call_{i}",
                    "type": "function",
                    "function": {"name": call["name"], "arguments": call["arguments"] or "{}"},
                }
                for i, call in sorted(tool_calls_acc.items())
            ],
        }
        messages.append(assistant_message)

        any_feed_back = False
        for call in assistant_message["tool_calls"]:
            call_id = call["id"]
            name = call["function"]["name"]
            raw_args = call["function"]["arguments"]
            yield _sse("tool_call", {"id": call_id, "name": name, "arguments": raw_args})
            result = await execute_tool(name, call_id, raw_args, ctx)
            yield _sse(
                "tool_result",
                {
                    "id": call_id,
                    "name": name,
                    "display": result.display,
                    "data": result.data,
                    "is_error": result.is_error,
                },
            )
            try:
                append_message(
                    db,
                    chat_session_id,
                    role="tool",
                    content=result.display,
                    metadata={
                        "tool_call_id": call_id,
                        "name": name,
                        "arguments": raw_args,
                        "data": result.data,
                        "is_error": result.is_error,
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception("persist tool result failed")
            tool_obj = get_tool(name)
            feed_back = bool(tool_obj and tool_obj.feed_back_to_model)
            if feed_back:
                any_feed_back = True
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": result.model_payload or "",
                    }
                )
                # Cache orders so compare_orders can reuse them later in the loop.
                if name == "query_charging_records" and not result.is_error:
                    ctx.extras["orders_cache"] = result.data.get("orders", [])
            else:
                # Display-only: feed an empty acknowledgement back so the model
                # doesn't think the tool failed, and keep the loop going so the
                # model can emit a final textual summary.
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": "ok",
                    }
                )
        # Whether any tool fed back to the model or not, we still loop so the
        # model gets a chance to produce its final natural-language answer.
        # The MAX_TOOL_ITERATIONS cap guards against runaway loops.
        _ = any_feed_back

    yield _sse("status", {"message": "max_tool_iterations_reached"})
    yield _sse("done", {"status": "max_iters"})

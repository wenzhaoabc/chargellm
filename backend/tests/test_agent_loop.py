"""Unit tests for the SSE agent loop — no real vLLM / Aliyun calls.

We patch the upstream stream generator so we can assert the full event
protocol: tool_call → tool_result → token → done, plus persistence of the
ChatSession / ChatMessage records on the side.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatSession
from app.models.demo_session import DemoSession
from app.services.agent_service import stream_agent_events
from app.services.content_safety import ContentSafetyService


def _make_fake_stream(chunks: list[dict[str, Any]]):
    async def fake_stream(_settings: Settings, _body: dict) -> AsyncGenerator[dict[str, Any], None]:
        for chunk in chunks:
            yield chunk

    return fake_stream


def _collect_events(gen) -> list[tuple[str, dict]]:
    async def run():
        out = []
        async for raw in gen:
            event_line, data_line = raw.strip().split("\n", 1)
            event = event_line.removeprefix("event: ").strip()
            data = json.loads(data_line.removeprefix("data: "))
            out.append((event, data))
        return out

    return asyncio.run(run())


def _demo_session_id(client) -> int:
    resp = client.post("/api/auth/admin/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    admin_token = resp.json()["access_token"]
    create = client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "agent-test", "max_uses": 3, "per_user_quota": 5},
    )
    code = create.json()["code"]
    client.post("/api/auth/invite/start", json={"invite_code": code})

    db = client.app.state.SessionLocal()
    try:
        return db.query(DemoSession).order_by(DemoSession.id.desc()).first().id
    finally:
        db.close()


def test_agent_loop_persists_messages_and_emits_tool_events(client):
    """Full happy-path: model calls highlight tool, then streams text, then done."""
    demo_id = _demo_session_id(client)

    # Two upstream turns:
    # 1. assistant emits a tool_call (highlight_charge_segment — display-only)
    # 2. assistant emits final text and stops
    turn1 = [
        {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_abc",
                                "function": {
                                    "name": "highlight_charge_segment",
                                    "arguments": json.dumps(
                                        {
                                            "order_no": "ORD-1",
                                            "metric": "current",
                                            "start_min": 5,
                                            "end_min": 12,
                                            "reason": "电流突变",
                                        }
                                    ),
                                },
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        },
        {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
    ]
    turn2 = [
        {"choices": [{"index": 0, "delta": {"content": "综合分析："}, "finish_reason": None}]},
        {"choices": [{"index": 0, "delta": {"content": "电池正常。"}, "finish_reason": None}]},
        {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
    ]

    turns = iter([turn1, turn2])

    async def fake_stream_async(settings, body):
        chunks = next(turns)
        for chunk in chunks:
            yield chunk

    settings = client.app.state.settings
    db = client.app.state.SessionLocal()

    try:
        session = db.get(DemoSession, demo_id)
        user = session.user
        with patch("app.services.agent_service._stream_vllm_async", side_effect=fake_stream_async):
            events = _collect_events(
                stream_agent_events(
                    db=db,
                    settings=settings,
                    session=session,
                    user=user,
                    user_message="分析这个用户的电池健康",
                    safety_service=ContentSafetyService(mode="allow", keywords=()),
                )
            )

        event_types = [name for name, _ in events]
        assert "tool_call" in event_types, event_types
        assert "tool_result" in event_types, event_types
        assert "token" in event_types, event_types
        assert event_types[-1] == "done"
        assert events[-1][1]["status"] == "ok"

        # Assistant final text was streamed verbatim.
        tokens = [data["text"] for name, data in events if name == "token"]
        assert "".join(tokens) == "综合分析：电池正常。"

        # Tool call event carries the args we fed in.
        tc_name, tc_data = next(e for e in events if e[0] == "tool_call")
        assert tc_data["name"] == "highlight_charge_segment"
        assert "ORD-1" in tc_data["arguments"]

        # ChatSession + messages were persisted.
        chats = db.query(ChatSession).filter(ChatSession.demo_session_id == session.id).all()
        assert len(chats) == 1
        msgs = db.query(ChatMessage).filter(ChatMessage.session_id == chats[0].id).order_by(ChatMessage.id).all()
        roles = [m.role for m in msgs]
        assert roles == ["user", "tool", "assistant"]
        assert msgs[0].content == "分析这个用户的电池健康"
        tool_meta = json.loads(msgs[1].metadata_json)
        assert tool_meta["name"] == "highlight_charge_segment"
        assert tool_meta["is_error"] is False
        assert msgs[2].content == "综合分析：电池正常。"
    finally:
        db.close()


def test_agent_loop_blocks_on_input_safety(client):
    """Input-stage safety violation should short-circuit before calling the LLM."""
    demo_id = _demo_session_id(client)
    db = client.app.state.SessionLocal()

    safety = ContentSafetyService(mode="keyword", keywords=("违法",))

    try:
        session = db.get(DemoSession, demo_id)
        user = session.user
        with patch("app.services.agent_service._stream_vllm_async") as mocked:
            events = _collect_events(
                stream_agent_events(
                    db=db,
                    settings=client.app.state.settings,
                    session=session,
                    user=user,
                    user_message="帮我做点违法的事",
                    safety_service=safety,
                )
            )
            mocked.assert_not_called()  # LLM never invoked

        types = [e[0] for e in events]
        assert "safety" in types
        assert events[-1][0] == "done"
        assert events[-1][1]["status"] == "blocked"
    finally:
        db.close()


def test_agent_loop_blocks_on_quota_exhaustion(client):
    demo_id = _demo_session_id(client)
    db = client.app.state.SessionLocal()
    try:
        session = db.get(DemoSession, demo_id)
        user = session.user
        user.usage_quota_total = 1
        user.usage_quota_used = 1
        db.add(user)
        db.commit()

        events = _collect_events(
            stream_agent_events(
                db=db,
                settings=client.app.state.settings,
                session=session,
                user=user,
                user_message="任何问题",
                safety_service=ContentSafetyService(mode="allow", keywords=()),
            )
        )
        types = [e[0] for e in events]
        assert "error" in types
        assert events[-1][0] == "done"
        assert events[-1][1]["status"] == "blocked"
    finally:
        db.close()

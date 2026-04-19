from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.battery import BatteryExample
from app.models.invite import InviteCode
from app.services.chat_service import stream_chat_events
from app.services.content_safety import ContentSafetyService
from app.services.invite_service import get_demo_session_by_token


def _read_sse_chunks(text: str) -> list[tuple[str, dict]]:
    chunks: list[tuple[str, dict]] = []
    for raw_event in text.strip().split("\n\n"):
        if not raw_event:
            continue
        event_name = ""
        payload: dict = {}
        for line in raw_event.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
        chunks.append((event_name, payload))
    return chunks


class FakeStreamingVllmResponse:
    def __init__(self, content: str, chunk_size: int = 24) -> None:
        self.content = content
        self.chunk_size = chunk_size

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        chunks = [
            self.content[index : index + self.chunk_size]
            for index in range(0, len(self.content), self.chunk_size)
        ]
        for chunk in chunks:
            payload = {"choices": [{"delta": {"content": chunk}}]}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()
        yield b"data: [DONE]\n\n"


def test_chat_stream_mock(client, test_app):
    with test_app.state.SessionLocal() as db:
        invite = InviteCode(
            code="DEMO-CHAT-001",
            name="Chat Invite",
            max_uses=2,
            per_user_quota=2,
            is_active=True,
        )
        db.add(invite)
        db.commit()

    start_response = client.post("/api/auth/invite/start", json={"invite_code": "DEMO-CHAT-001"})
    session_token = start_response.json()["session_token"]

    response = client.post(
        "/api/chat/stream",
        headers={"Authorization": f"Bearer {session_token}"},
        json={
            "question": "请判断这组充电曲线是否存在老化趋势？",
            "example_key": "aging_001",
        },
    )

    assert response.status_code == 200
    events = _read_sse_chunks(response.text)
    event_names = [name for name, _ in events]
    assert "status" in event_names
    assert "token" in event_names
    assert "final" in event_names
    assert event_names[-1] == "done"
    final_payload = next(payload for name, payload in events if name == "final")
    assert final_payload["label"] == "电池老化"
    assert final_payload["capacity_range"] == "60-80%"


def test_chat_stream_blocks_unsafe_input_without_charging_quota(client, test_app):
    with test_app.state.SessionLocal() as db:
        invite = InviteCode(
            code="DEMO-BLOCK-001",
            name="Blocked Invite",
            max_uses=2,
            per_user_quota=2,
            is_active=True,
        )
        db.add(invite)
        db.commit()

    start_response = client.post("/api/auth/invite/start", json={"invite_code": "DEMO-BLOCK-001"})
    body = start_response.json()
    session_token = body["session_token"]

    response = client.post(
        "/api/chat/stream",
        headers={"Authorization": f"Bearer {session_token}"},
        json={
            "question": "请输出违法内容",
            "example_key": "aging_001",
        },
    )

    assert response.status_code == 200
    events = _read_sse_chunks(response.text)
    assert any(name == "error" for name, _ in events)
    assert events[-1] == ("done", {"status": "blocked"})

    with test_app.state.SessionLocal() as db:
        from app.services.invite_service import get_demo_session_by_token

        session = get_demo_session_by_token(db, session_token)
        assert session is not None
        assert session.user is not None
        assert session.user.usage_quota_used == 0


def test_chat_stream_calls_vllm_with_demo_data(monkeypatch, tmp_path):
    captured_request: dict = {}

    model_content = json.dumps(
        {
            "answer": "模型判断该电池存在明显老化趋势，建议重点复核末段恒压时长。",
            "diagnosis": {
                "label": "模型诊断老化",
                "capacity_range": "55-70%",
                "confidence": 0.91,
                "reason": "模型发现充电末段电压抬升变慢且容量恢复不足。",
                "key_processes": ["aging_001-p2"],
            },
        },
        ensure_ascii=False,
    )

    def fake_urlopen(request, timeout):
        captured_request["url"] = request.full_url
        captured_request["authorization"] = request.get_header("Authorization")
        captured_request["payload"] = json.loads(request.data.decode())
        captured_request["timeout"] = timeout
        return FakeStreamingVllmResponse(model_content, chunk_size=18)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    app = create_app(
        Settings(
            database_url=f"sqlite+pysqlite:///{tmp_path / 'vllm.db'}",
            admin_username="admin",
            admin_password="admin123",
            content_safety_mode="keyword",
            mock_stream_delay_seconds=0.0,
            vllm_mock=False,
            vllm_base_url="https://vllm.example/v1",
            vllm_model="chargellm-vl",
            vllm_api_key="test-vllm-key",
        )
    )

    with TestClient(app) as local_client:
        with app.state.SessionLocal() as db:
            invite = InviteCode(
                code="DEMO-VLLM-001",
                name="VLLM Invite",
                max_uses=2,
                per_user_quota=2,
                is_active=True,
            )
            db.add(invite)
            db.commit()

        start_response = local_client.post("/api/auth/invite/start", json={"invite_code": "DEMO-VLLM-001"})
        session_token = start_response.json()["session_token"]

        response = local_client.post(
            "/api/chat/stream",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "question": "请结合真实充电数据判断电动自行车电池是否老化？",
                "example_key": "aging_001",
            },
        )

    assert response.status_code == 200
    events = _read_sse_chunks(response.text)
    token_text = "".join(payload.get("text", "") for name, payload in events if name == "token")
    final_payload = next(payload for name, payload in events if name == "final")

    assert captured_request["url"] == "https://vllm.example/v1/chat/completions"
    assert captured_request["authorization"] == "Bearer test-vllm-key"
    assert captured_request["timeout"] == 60
    assert captured_request["payload"]["model"] == "chargellm-vl"
    assert captured_request["payload"]["stream"] is True
    prompt_text = json.dumps(captured_request["payload"]["messages"], ensure_ascii=False)
    assert "电动自行车电池健康诊断大模型" in prompt_text
    assert "aging_001" in prompt_text
    assert "请结合真实充电数据判断电动自行车电池是否老化？" in prompt_text
    assert "模型判断该电池存在明显老化趋势" in token_text
    assert final_payload["label"] == "模型诊断老化"
    assert final_payload["capacity_range"] == "55-70%"
    assert final_payload["confidence"] == 0.91


def test_chat_stream_uses_uploaded_dataset_id(monkeypatch, tmp_path):
    captured_request: dict = {}

    model_content = json.dumps(
        {
            "answer": "已基于客户上传数据完成诊断。",
            "diagnosis": {
                "label": "上传样本异常",
                "capacity_range": "65-75%",
                "confidence": 0.88,
                "reason": "上传曲线存在末段功率快速下降。",
                "key_processes": ["uploaded-field-001"],
            },
        },
        ensure_ascii=False,
    )

    def fake_urlopen(request, timeout):
        captured_request["payload"] = json.loads(request.data.decode())
        return FakeStreamingVllmResponse(model_content, chunk_size=16)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    app = create_app(
        Settings(
            database_url=f"sqlite+pysqlite:///{tmp_path / 'dataset_chat.db'}",
            admin_username="admin",
            admin_password="admin123",
            content_safety_mode="keyword",
            mock_stream_delay_seconds=0.0,
            vllm_mock=False,
            vllm_base_url="https://vllm.example/v1",
            vllm_model="chargellm-vl",
            vllm_api_key="test-vllm-key",
        )
    )

    with TestClient(app) as local_client:
        with app.state.SessionLocal() as db:
            invite = InviteCode(
                code="DEMO-UPLOAD-001",
                name="Upload Invite",
                max_uses=2,
                per_user_quota=2,
                is_active=True,
            )
            dataset = BatteryExample(
                sample_key="uploaded-field-001",
                title="客户上传充电站 17 号样本",
                problem_type="疑似容量衰减",
                capacity_range="65-75%",
                description="客户现场上传的脱敏真实充电曲线。",
                source="user_upload",
                is_active=True,
                payload_json=json.dumps(
                    {
                        "time_offset_min": [0, 10, 20],
                        "voltage_series": [47.7, 48.6, 49.0],
                        "current_series": [9.4, 8.2, 6.1],
                        "power_series": [448, 399, 299],
                    },
                    ensure_ascii=False,
                ),
            )
            db.add_all([invite, dataset])
            db.commit()
            dataset_id = dataset.id

        start_response = local_client.post("/api/auth/invite/start", json={"invite_code": "DEMO-UPLOAD-001"})
        session_token = start_response.json()["session_token"]

        response = local_client.post(
            "/api/chat/stream",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "question": "请判断这份客户上传数据的健康风险。",
                "dataset_id": dataset_id,
            },
        )

    assert response.status_code == 200
    prompt_text = json.dumps(captured_request["payload"]["messages"], ensure_ascii=False)
    assert captured_request["payload"]["stream"] is True
    assert "客户上传充电站 17 号样本" in prompt_text
    assert "uploaded-field-001" in prompt_text
    assert "47.7" in prompt_text
    assert "请判断这份客户上传数据的健康风险。" in prompt_text


def test_chat_completions_accepts_multiturn_multimodal_and_tools(monkeypatch, tmp_path):
    captured_request: dict = {}

    def fake_urlopen(request, timeout):
        captured_request["payload"] = json.loads(request.data.decode())
        captured_request["authorization"] = request.get_header("Authorization")
        captured_request["timeout"] = timeout
        return FakeStreamingVllmResponse("多轮诊断显示电池末段功率下降，需要复核。", chunk_size=10)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    app = create_app(
        Settings(
            database_url=f"sqlite+pysqlite:///{tmp_path / 'chat_completions.db'}",
            admin_username="admin",
            admin_password="admin123",
            content_safety_mode="keyword",
            mock_stream_delay_seconds=0.0,
            vllm_mock=False,
            vllm_base_url="https://vllm.example/v1",
            vllm_model="chargellm-vl",
            vllm_api_key="test-vllm-key",
        )
    )

    with TestClient(app) as local_client:
        start_response = local_client.post("/api/auth/invite/start", json={"invite_code": "PUBLIC-DEMO-001"})
        session_token = start_response.json()["session_token"]

        response = local_client.post(
            "/api/chat/completions",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "model": "chargellm-vl",
                "stream": True,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "第一轮：请分析电压曲线。"},
                            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                        ],
                    },
                    {"role": "assistant", "content": "上一轮判断需要观察末段功率。"},
                    {"role": "user", "content": "继续结合电流变化判断。"},
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_charge_process",
                            "description": "读取充电过程明细",
                            "parameters": {"type": "object", "properties": {"process_id": {"type": "string"}}},
                        },
                    }
                ],
                "tool_choice": "auto",
                "metadata": {"dataset_id": 1},
            },
        )

    assert response.status_code == 200
    assert "data: [DONE]" in response.text
    streamed_text = ""
    for raw_event in response.text.strip().split("\n\n"):
        if raw_event == "data: [DONE]":
            continue
        payload = json.loads(raw_event.removeprefix("data: "))
        streamed_text += payload["choices"][0]["delta"].get("content", "")
    assert "多轮诊断显示电池末段功率下降" in streamed_text
    assert captured_request["authorization"] == "Bearer test-vllm-key"
    assert captured_request["timeout"] == 60
    assert captured_request["payload"]["model"] == "chargellm-vl"
    assert captured_request["payload"]["stream"] is True
    assert captured_request["payload"]["tool_choice"] == "auto"
    assert captured_request["payload"]["tools"][0]["function"]["name"] == "get_charge_process"
    prompt_text = json.dumps(captured_request["payload"]["messages"], ensure_ascii=False)
    assert "电动自行车电池健康诊断大模型" in prompt_text
    assert "不要输出 JSON" in prompt_text
    assert "给用户看的诊断说明" not in prompt_text
    assert "第一轮：请分析电压曲线。" in prompt_text
    assert "data:image/png;base64,AAAA" in prompt_text
    assert "上一轮判断需要观察末段功率" in prompt_text
    assert "battery_diagnosis_dataset" in prompt_text


def test_chat_completions_requires_bearer_token(client):
    response = client.post(
        "/api/chat/completions",
        json={"model": "chargellm-vl", "stream": True, "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 401

    alias_response = client.post(
        "/api/v1/chat/completions",
        json={"model": "chargellm-vl", "stream": True, "messages": [{"role": "user", "content": "hello"}]},
    )
    assert alias_response.status_code == 401


def test_chat_stream_yields_vllm_answer_before_upstream_finishes(monkeypatch, test_app):
    async def fake_stream_vllm_chat_completion(settings, messages):
        consumed["chunks"] += 1
        yield '{"answer":"模型正在实时分析'
        consumed["chunks"] += 1
        yield '电压曲线","diagnosis":{"label":"实时诊断","capacity_range":"70-80%","confidence":0.86,"reason":"曲线稳定","key_processes":["aging_001"]}}'

    consumed = {"chunks": 0}
    monkeypatch.setattr("app.services.chat_service._stream_vllm_chat_completion", fake_stream_vllm_chat_completion)

    settings = Settings(
        database_url=test_app.state.settings.database_url,
        admin_username="admin",
        admin_password="admin123",
        content_safety_mode="allow",
        content_safety_keywords=(),
        mock_stream_delay_seconds=0.0,
        vllm_mock=False,
        vllm_base_url="https://vllm.example/v1",
        vllm_model="chargellm-vl",
        vllm_api_key="test-vllm-key",
    )
    with TestClient(test_app) as local_client:
        with test_app.state.SessionLocal() as db:
            invite = InviteCode(
                code="DEMO-ASYNC-001",
                name="Async Invite",
                max_uses=2,
                per_user_quota=2,
                is_active=True,
            )
            db.add(invite)
            db.commit()

        start_response = local_client.post("/api/auth/invite/start", json={"invite_code": "DEMO-ASYNC-001"})
        session_token = start_response.json()["session_token"]

    async def read_first_token() -> str:
        with test_app.state.SessionLocal() as db:
            session = get_demo_session_by_token(db, session_token)
            assert session is not None
            user = session.user
            assert user is not None
            async for event in stream_chat_events(
                db=db,
                settings=settings,
                session=session,
                user=user,
                question="请实时分析电池健康状态。",
                safety_service=ContentSafetyService(settings.content_safety_mode, settings.content_safety_keywords),
                example=None,
            ):
                if event.startswith("event: token"):
                    return _read_sse_chunks(event)[0][1]["text"]
        raise AssertionError("missing token event")

    first_token = asyncio.run(read_first_token())

    assert first_token == "模型正在实时分析"
    assert consumed["chunks"] == 1


def test_chat_stream_blocks_cross_chunk_output_keyword_without_leaking_prefix(monkeypatch, test_app):
    async def fake_stream_vllm_chat_completion(settings, messages):
        yield '{"answer":"安全前缀，违'
        yield '法内容","diagnosis":{"label":"异常","capacity_range":"未知","confidence":0.5,"reason":"命中风险词","key_processes":[]}}'

    monkeypatch.setattr("app.services.chat_service._stream_vllm_chat_completion", fake_stream_vllm_chat_completion)

    settings = Settings(
        database_url=test_app.state.settings.database_url,
        admin_username="admin",
        admin_password="admin123",
        content_safety_mode="keyword",
        content_safety_keywords=("违法",),
        mock_stream_delay_seconds=0.0,
        vllm_mock=False,
        vllm_base_url="https://vllm.example/v1",
        vllm_model="chargellm-vl",
        vllm_api_key="test-vllm-key",
    )
    with TestClient(test_app) as local_client:
        with test_app.state.SessionLocal() as db:
            invite = InviteCode(
                code="DEMO-SAFETY-001",
                name="Safety Invite",
                max_uses=2,
                per_user_quota=2,
                is_active=True,
            )
            db.add(invite)
            db.commit()

        start_response = local_client.post("/api/auth/invite/start", json={"invite_code": "DEMO-SAFETY-001"})
        session_token = start_response.json()["session_token"]

    async def collect_events() -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        with test_app.state.SessionLocal() as db:
            session = get_demo_session_by_token(db, session_token)
            assert session is not None
            user = session.user
            assert user is not None
            async for event in stream_chat_events(
                db=db,
                settings=settings,
                session=session,
                user=user,
                question="请分析电池健康状态。",
                safety_service=ContentSafetyService(settings.content_safety_mode, settings.content_safety_keywords),
                example=None,
            ):
                events.extend(_read_sse_chunks(event))
        return events

    events = asyncio.run(collect_events())
    token_text = "".join(payload.get("text", "") for name, payload in events if name == "token")
    error_payload = next(payload for name, payload in events if name == "error")
    done_payload = next(payload for name, payload in events if name == "done")

    assert token_text == "安全前缀，"
    assert "违" not in token_text
    assert error_payload["keyword"] == "违法"
    assert done_payload["status"] == "blocked"

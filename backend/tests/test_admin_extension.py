"""Focused business-logic tests for the admin extension routes.

Each test exercises a real user-facing flow, not implementation details.
"""

from __future__ import annotations


def _admin_headers(client) -> dict:
    resp = client.post("/api/auth/admin/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _start_demo_session(client) -> str:
    """Create an invite, redeem it, return the demo session token."""
    headers = _admin_headers(client)
    create = client.post(
        "/api/admin/invites",
        headers=headers,
        json={"name": "test", "max_uses": 5, "per_user_quota": 5},
    )
    assert create.status_code == 200, create.text
    code = create.json()["code"]
    start = client.post("/api/auth/invite/start", json={"invite_code": code})
    assert start.status_code == 200, start.text
    return start.json()["session_token"]


# -------- system prompt: admin can publish, public endpoint serves it --------


def test_system_prompt_admin_create_then_public_read(client):
    headers = _admin_headers(client)

    # Initially no active prompt.
    public = client.get("/api/meta/system-prompt")
    assert public.status_code == 200
    assert public.json() is None

    # Admin creates an active prompt.
    created = client.post(
        "/api/admin/prompts",
        headers=headers,
        json={"scope": "default", "title": "新规则", "content": "你是 ChargeLLM 助手。", "is_active": True, "sort_order": 0},
    )
    assert created.status_code == 200, created.text
    prompt_id = created.json()["id"]

    # Public route now returns it.
    public = client.get("/api/meta/system-prompt")
    assert public.status_code == 200
    body = public.json()
    assert body["id"] == prompt_id
    assert body["content"] == "你是 ChargeLLM 助手。"

    # Disabling it removes it from the public route.
    disabled = client.patch(
        f"/api/admin/prompts/{prompt_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    public = client.get("/api/meta/system-prompt")
    assert public.json() is None


# -------- welcome messages: admin CRUD + public read filters by is_active --------


def test_welcome_messages_admin_crud_and_public_filter(client):
    headers = _admin_headers(client)

    create_active = client.post(
        "/api/admin/welcome",
        headers=headers,
        json={"title": "欢迎", "content": "上传充电数据", "sort_order": 1, "is_active": True},
    )
    assert create_active.status_code == 200
    active_id = create_active.json()["id"]

    create_hidden = client.post(
        "/api/admin/welcome",
        headers=headers,
        json={"title": "草稿", "content": "未上线文案", "sort_order": 2, "is_active": False},
    )
    assert create_hidden.status_code == 200

    # Admin sees both, public only sees the active one.
    admin_list = client.get("/api/admin/welcome", headers=headers)
    assert len(admin_list.json()) == 2
    public_list = client.get("/api/meta/welcome")
    assert public_list.status_code == 200
    items = public_list.json()
    assert [i["id"] for i in items] == [active_id]
    assert items[0]["title"] == "欢迎"

    # Delete the active one → public list is empty.
    delete = client.delete(f"/api/admin/welcome/{active_id}", headers=headers)
    assert delete.status_code == 200
    assert client.get("/api/meta/welcome").json() == []


# -------- user management: admin can adjust quota, demo session honors it --------


def test_admin_can_adjust_user_quota_and_disable(client):
    headers = _admin_headers(client)

    # Create a demo user via invite/start, then locate them.
    session_token = _start_demo_session(client)
    assert session_token

    users = client.get("/api/admin/users", headers=headers, params={"role": "user"})
    assert users.status_code == 200
    body = users.json()
    assert body["total"] >= 1
    target = body["items"][0]
    user_id = target["id"]

    # Bump quota and verify.
    bumped = client.patch(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"usage_quota_total": 99},
    )
    assert bumped.status_code == 200
    assert bumped.json()["usage_quota_total"] == 99

    # Disable user.
    disabled = client.patch(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    # Negative quota is rejected.
    bad = client.patch(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"usage_quota_total": -1},
    )
    assert bad.status_code == 400


# -------- conversations: persisted from agent route, listable + readable --------


def test_admin_conversations_show_persisted_chat(client):
    """Persist a conversation via service helpers, then read via admin route."""
    headers = _admin_headers(client)
    session_token = _start_demo_session(client)

    # Look up the demo session id from inside the running app.
    from app.models.demo_session import DemoSession
    from app.services.chat_history_service import append_message, create_chat_session

    db = client.app.state.SessionLocal()
    try:
        demo = db.query(DemoSession).filter(DemoSession.session_token == session_token).one()
        chat = create_chat_session(db, demo_session_id=demo.id, title="电池健康问询")
        append_message(db, chat.id, role="user", content="请分析这位用户的电池健康")
        append_message(
            db,
            chat.id,
            role="tool",
            content="已读取 130****7220 的 2 次充电记录。",
            metadata={"name": "query_charging_records", "is_error": False},
        )
        append_message(db, chat.id, role="assistant", content="**结论**：电池健康")
    finally:
        db.close()

    # Admin lists conversations and finds the one we just stored.
    listing = client.get("/api/admin/conversations", headers=headers)
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert any(item["title"] == "电池健康问询" and item["message_count"] == 3 for item in items)

    target_id = next(item["id"] for item in items if item["title"] == "电池健康问询")
    detail = client.get(f"/api/admin/conversations/{target_id}", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    roles = [m["role"] for m in detail_body["messages"]]
    assert roles == ["user", "tool", "assistant"]
    tool_msg = detail_body["messages"][1]
    assert tool_msg["metadata"]["name"] == "query_charging_records"


def test_admin_routes_require_token(client):
    for path in ("/api/admin/users", "/api/admin/prompts", "/api/admin/welcome", "/api/admin/conversations"):
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} should require token"

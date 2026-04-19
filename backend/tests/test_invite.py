from __future__ import annotations

from app.models.invite import InviteCode


def test_app_bootstraps_public_demo_invite(client):
    login_response = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client.get("/api/admin/invites", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    codes = [item["code"] for item in response.json()]
    assert "PUBLIC-DEMO-001" in codes


def test_invite_start_consumes_quota(client, test_app):
    with test_app.state.SessionLocal() as db:
        invite = InviteCode(
            code="DEMO-TEST-001",
            name="Demo Invite",
            max_uses=2,
            per_user_quota=4,
            is_active=True,
        )
        db.add(invite)
        db.commit()

    response = client.post("/api/auth/invite/start", json={"invite_code": "DEMO-TEST-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["invite_code"] == "DEMO-TEST-001"
    assert body["quota_total"] == 4
    assert body["quota_remaining"] == 4
    assert body["session_token"].startswith("demo_")


def test_admin_can_create_and_delete_invites(client):
    login_response = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/admin/invites",
        headers=headers,
        json={"name": "Public Beta"},
    )
    assert create_response.status_code == 200
    invite = create_response.json()
    assert invite["per_user_quota"] == 10

    delete_response = client.delete(f"/api/admin/invites/{invite['id']}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"


def test_admin_can_delete_used_invite(client, test_app):
    with test_app.state.SessionLocal() as db:
        invite = InviteCode(
            code="USED-INVITE-001",
            name="Used Invite",
            max_uses=2,
            per_user_quota=10,
            is_active=True,
        )
        db.add(invite)
        db.commit()

    start_response = client.post("/api/auth/invite/start", json={"invite_code": "USED-INVITE-001"})
    assert start_response.status_code == 200

    login_response = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    list_response = client.get("/api/admin/invites", headers=headers)
    used_invite = next(item for item in list_response.json() if item["code"] == "USED-INVITE-001")

    delete_response = client.delete(f"/api/admin/invites/{used_invite['id']}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    blocked_response = client.post("/api/auth/invite/start", json={"invite_code": "USED-INVITE-001"})
    assert blocked_response.status_code == 404

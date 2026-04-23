from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.sms_code import SmsCode
from app.services.sms_service import consume_sms_code, issue_sms_code


def _db(client):
    return client.app.state.SessionLocal()


def test_issue_then_consume_succeeds(client):
    db = _db(client)
    try:
        record = issue_sms_code(db, "13900000001")
        assert record.code and len(record.code) == 6
        assert consume_sms_code(db, "13900000001") is True
        assert consume_sms_code(db, "13900000001") is False
    finally:
        db.close()


def test_consume_without_send_fails(client):
    db = _db(client)
    try:
        assert consume_sms_code(db, "13900000002") is False
    finally:
        db.close()


def test_consume_expired_fails(client):
    db = _db(client)
    try:
        expired = SmsCode(
            phone="13900000003",
            code="000000",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        db.add(expired)
        db.commit()
        assert consume_sms_code(db, "13900000003") is False
    finally:
        db.close()


def test_resend_within_cooldown_returns_same_record(client):
    db = _db(client)
    try:
        first = issue_sms_code(db, "13900000004")
        second = issue_sms_code(db, "13900000004")
        assert first.id == second.id
    finally:
        db.close()


def test_sms_endpoints_e2e(client):
    send = client.post("/api/auth/sms/send", json={"phone": "13900000005"})
    assert send.status_code == 200, send.text
    assert "mock_code" in send.json()

    # Submitted user code is intentionally not compared against the stored one.
    login = client.post("/api/auth/sms/login", json={"phone": "13900000005", "code": "9999"})
    assert login.status_code == 200, login.text
    assert "access_token" in login.json()

    # Code already consumed → second login fails until /sms/send is called again.
    login2 = client.post("/api/auth/sms/login", json={"phone": "13900000005", "code": "0000"})
    assert login2.status_code == 401

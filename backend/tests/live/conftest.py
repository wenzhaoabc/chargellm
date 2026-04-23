"""Live E2E tests — hit real vLLM, real Aliyun Content Safety, real IOT MySQL.

These are opt-in: run with ``uv run pytest tests/live/ -v``. They are excluded
from the default ``tests/`` path via ``pytest.ini``.

Fixtures here deliberately load real credentials from ``backend/.env`` (via
``get_settings()``) so we can exercise the full stack. Each test sets up an
isolated SQLite DB, an admin token, and a demo session token, then runs the
exact flows users would run through the UI.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(scope="module")
def live_settings(tmp_path_factory) -> Settings:
    # Force vLLM to hit the real endpoint even if .env has VLLM_MOCK=true.
    os.environ["VLLM_MOCK"] = "false"
    get_settings.cache_clear()  # type: ignore[attr-defined]
    base = get_settings()
    # Per-module SQLite so tests don't see each other's rows.
    db_dir: Path = tmp_path_factory.mktemp("live_db")
    return Settings(
        database_url=f"sqlite+pysqlite:///{db_dir / 'live.db'}",
        admin_username="admin",
        admin_password="admin123",
        content_safety_mode="aliyun",
        content_safety_keywords=base.content_safety_keywords,
        mock_stream_delay_seconds=0.0,
        vllm_mock=False,
        vllm_base_url=base.vllm_base_url,
        vllm_model=base.vllm_model,
        vllm_api_key=base.vllm_api_key,
        iot_db_url=base.iot_db_url,
        aliyun_access_key_id=base.aliyun_access_key_id,
        aliyun_access_key_secret=base.aliyun_access_key_secret,
        aliyun_content_safety_endpoint=base.aliyun_content_safety_endpoint,
        aliyun_region_id=base.aliyun_region_id,
        jwt_secret=base.jwt_secret,
        invite_default_max_uses=5,
        invite_default_per_user_quota=20,
    )


@pytest.fixture(scope="module")
def live_app(live_settings):
    app = create_app(live_settings)
    return app


@pytest.fixture(scope="module")
def live_client(live_app):
    with TestClient(live_app) as client:
        yield client


@pytest.fixture(scope="module")
def admin_token(live_client) -> str:
    resp = live_client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def session_token(live_client, admin_token) -> str:
    """Create an invite and redeem it for a demo session token."""
    create = live_client.post(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "live-test", "max_uses": 100, "per_user_quota": 100},
    )
    assert create.status_code == 200, create.text
    code = create.json()["code"]

    start = live_client.post("/api/auth/invite/start", json={"invite_code": code})
    assert start.status_code == 200, start.text
    return start.json()["session_token"]


def require_live(settings: Settings, *, needs_mysql=False, needs_aliyun=False, needs_vllm=False) -> None:
    """Skip the test if any required live dependency is missing."""
    if needs_vllm and (settings.vllm_mock or not settings.vllm_api_key):
        pytest.skip("vLLM live endpoint not configured")
    if needs_mysql and not settings.iot_db_url:
        pytest.skip("IOT MySQL not configured")
    if needs_aliyun and not (
        settings.aliyun_access_key_id
        and settings.aliyun_access_key_secret
        and settings.aliyun_content_safety_endpoint
    ):
        pytest.skip("Aliyun content safety not configured")

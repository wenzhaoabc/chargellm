from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def test_app(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'demo.db'}",
        admin_username="admin",
        admin_password="admin123",
        sms_mock_code="123456",
        invite_default_max_uses=3,
        invite_default_per_user_quota=10,
        content_safety_mode="keyword",
        content_safety_keywords=("违法", "暴力"),
        mock_stream_delay_seconds=0.0,
    )
    return create_app(settings)


@pytest.fixture()
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client

from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.invite import InviteCode


def _start_demo_session(client, test_app) -> str:
    with test_app.state.SessionLocal() as db:
        db.add(
            InviteCode(
                code="DATASET-INVITE-001",
                name="Dataset Invite",
                max_uses=5,
                per_user_quota=8,
                is_active=True,
            )
        )
        db.commit()

    response = client.post("/api/auth/invite/start", json={"invite_code": "DATASET-INVITE-001"})
    assert response.status_code == 200
    return response.json()["session_token"]


def _admin_headers(client) -> dict[str, str]:
    response = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _demo_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}


def test_user_can_upload_json_dataset_and_list_it(client, test_app):
    session_token = _start_demo_session(client, test_app)
    headers = _demo_headers(session_token)
    payload = {
        "time_offset_min": [0, 5, 10],
        "voltage_series": [48.2, 49.1, 49.6],
        "current_series": [8.1, 7.4, 6.8],
        "power_series": [390, 362, 337],
    }

    upload_response = client.post(
        "/api/datasets/upload",
        headers=headers,
        json={
            "name": "客户现场 2026-04-18 样本",
            "file_name": "sample.json",
            "content": json.dumps(payload),
        },
    )

    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    assert uploaded["title"] == "客户现场 2026-04-18 样本"
    assert uploaded["source"] == "user_upload"
    assert uploaded["series"]["voltage_series"] == [48.2, 49.1, 49.6]

    query_token_response = client.get("/api/datasets", params={"session_token": session_token})
    assert query_token_response.status_code == 401

    list_response = client.get("/api/datasets", headers=headers)
    assert list_response.status_code == 200
    titles = [item["title"] for item in list_response.json()["items"]]
    assert "客户现场 2026-04-18 样本" in titles


def test_user_can_upload_csv_dataset(client, test_app):
    session_token = _start_demo_session(client, test_app)
    headers = _demo_headers(session_token)
    csv_content = "\n".join(
        [
            "time_offset_min,voltage,current,power",
            "0,47.8,9.2,440",
            "5,48.4,8.8,426",
            "10,49.0,7.9,387",
        ]
    )

    response = client.post(
        "/api/datasets/upload",
        headers=headers,
        json={
            "name": "CSV 现场数据",
            "file_name": "field.csv",
            "content": csv_content,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "user_upload"
    assert body["series"]["time_offset_min"] == [0.0, 5.0, 10.0]
    assert body["series"]["current_series"] == [9.2, 8.8, 7.9]


def test_app_resets_incompatible_dataset_schema(tmp_path):
    db_path = tmp_path / "old_schema.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE battery_examples (
            id INTEGER PRIMARY KEY,
            sample_key VARCHAR(64) NOT NULL,
            title VARCHAR(128) NOT NULL,
            problem_type VARCHAR(64) NOT NULL,
            capacity_range VARCHAR(32) NOT NULL,
            description VARCHAR(255) NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    app = create_app(
        Settings(
            database_url=f"sqlite+pysqlite:///{db_path}",
            admin_username="admin",
            admin_password="admin123",
            content_safety_mode="keyword",
            mock_stream_delay_seconds=0.0,
        )
    )

    with TestClient(app) as local_client:
        start_response = local_client.post("/api/auth/invite/start", json={"invite_code": "PUBLIC-DEMO-001"})
        assert start_response.status_code == 200
        session_token = start_response.json()["session_token"]
        list_response = local_client.get("/api/datasets", headers=_demo_headers(session_token))

    assert list_response.status_code == 200
    assert list_response.json()["items"]


def test_admin_can_manage_professional_datasets(client):
    headers = _admin_headers(client)
    create_response = client.post(
        "/api/admin/datasets",
        headers=headers,
        json={
            "title": "政府抽检高风险样本",
            "problem_type": "异常衰减",
            "capacity_range": "30-40Ah",
            "description": "来自抽检数据的脱敏演示样本",
            "sort_order": 7,
            "content": json.dumps(
                {
                    "time_offset_min": [0, 15, 30],
                    "voltage_series": [46.1, 47.0, 47.5],
                    "current_series": [10.0, 9.6, 8.9],
                    "power_series": [461, 451, 423],
                }
            ),
            "file_name": "case.json",
        },
    )
    assert create_response.status_code == 200
    dataset = create_response.json()
    assert dataset["source"] == "demo_case"
    assert dataset["is_active"] is True

    patch_response = client.patch(
        f"/api/admin/datasets/{dataset['id']}",
        headers=headers,
        json={"title": "政府抽检重点样本", "is_active": False, "sort_order": 1},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["title"] == "政府抽检重点样本"
    assert patched["is_active"] is False
    assert patched["sort_order"] == 1

    list_response = client.get("/api/admin/datasets", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == dataset["id"] for item in list_response.json())

    delete_response = client.delete(f"/api/admin/datasets/{dataset['id']}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"


def test_admin_mysql_import_returns_no_orders_for_unknown_phone(client):
    """A phone with no charge orders in IOT MySQL should fail cleanly with 400."""
    headers = _admin_headers(client)

    response = client.post(
        "/api/admin/datasets/mysql-import",
        headers=headers,
        json={
            "phone": "00000000000",  # not a real user
            "start_time": "2020-01-01T00:00:00",
            "end_time": "2020-01-02T00:00:00",
            "title": "平台抽取样本",
        },
    )

    # 400 = no_orders_found (real DB queried, returned empty)
    # 503 = iot_db_url not configured in this test env (also acceptable)
    assert response.status_code in (400, 503)
    detail = response.json()["detail"]
    assert detail in {"no_orders_found", "iot_db_url_not_configured"}

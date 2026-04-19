from __future__ import annotations

import csv
import io
import json
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.battery import BatteryExample


def _seed_examples() -> list[dict[str, object]]:
    return [
        {
            "sample_key": "normal_001",
            "title": "Normal Charging Profile",
            "problem_type": "正常",
            "capacity_range": "90-100%",
            "description": "多次充电过程平稳，电压和功率变化一致。",
            "sort_order": 1,
            "series": {
                "time_offset_min": [0, 10, 20, 30, 40, 50],
                "power_series": [18.0, 18.2, 17.8, 17.6, 17.5, 17.3],
                "current_series": [3.2, 3.3, 3.1, 3.0, 3.0, 2.9],
                "voltage_series": [3.45, 3.62, 3.78, 3.92, 4.02, 4.11],
            },
        },
        {
            "sample_key": "aging_001",
            "title": "Aging Charging Profile",
            "problem_type": "电池老化",
            "capacity_range": "60-80%",
            "description": "后段充电速度放缓，功率逐步下降，体现持续退化。",
            "sort_order": 2,
            "series": {
                "time_offset_min": [0, 12, 24, 36, 48, 60],
                "power_series": [17.0, 16.5, 15.8, 15.0, 14.6, 14.0],
                "current_series": [3.0, 2.9, 2.7, 2.6, 2.5, 2.4],
                "voltage_series": [3.42, 3.58, 3.72, 3.84, 3.94, 4.0],
            },
        },
        {
            "sample_key": "fault_001",
            "title": "Fault Charging Profile",
            "problem_type": "电池故障",
            "capacity_range": "40-60%",
            "description": "曲线出现明显波动和突变，充电过程不稳定。",
            "sort_order": 3,
            "series": {
                "time_offset_min": [0, 8, 16, 24, 32, 40],
                "power_series": [16.0, 17.5, 11.0, 18.5, 9.5, 12.0],
                "current_series": [2.8, 3.4, 2.0, 3.6, 1.8, 2.1],
                "voltage_series": [3.4, 3.55, 3.7, 3.63, 3.8, 3.72],
            },
        },
    ]


def seed_example_batteries(db: Session) -> None:
    existing = db.scalar(select(BatteryExample.id))
    if existing is not None:
        return
    for item in _seed_examples():
        battery = BatteryExample(
            sample_key=item["sample_key"],
            title=item["title"],
            problem_type=item["problem_type"],
            capacity_range=item["capacity_range"],
            description=item["description"],
            sort_order=item["sort_order"],
            source="demo_case",
            is_active=True,
            payload_json=json.dumps(item["series"], ensure_ascii=False),
        )
        db.add(battery)
    db.commit()


def list_examples(db: Session) -> list[BatteryExample]:
    return list(
        db.scalars(
            select(BatteryExample)
            .where(BatteryExample.is_active.is_(True))
            .order_by(BatteryExample.sort_order.asc(), BatteryExample.id.asc())
        ).all()
    )


def get_example(db: Session, sample_key: str) -> BatteryExample | None:
    return db.scalar(
        select(BatteryExample).where(BatteryExample.sample_key == sample_key, BatteryExample.is_active.is_(True))
    )


def parse_dataset_content(file_name: str, content: str) -> dict[str, list[float]]:
    suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if suffix == "csv":
        return _parse_csv_dataset(content)
    if suffix == "json":
        return _parse_json_dataset(content)
    stripped = content.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return _parse_json_dataset(content)
    return _parse_csv_dataset(content)


def _parse_json_dataset(content: str) -> dict[str, list[float]]:
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("dataset_json_invalid") from exc
    if isinstance(raw, dict) and isinstance(raw.get("series"), dict):
        raw = raw["series"]
    if not isinstance(raw, dict):
        raise ValueError("dataset_json_invalid")
    return _normalize_series(raw)


def _parse_csv_dataset(content: str) -> dict[str, list[float]]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("dataset_csv_empty")
    series = {
        "time_offset_min": [],
        "voltage_series": [],
        "current_series": [],
        "power_series": [],
    }
    field_map = {
        "time_offset_min": "time_offset_min",
        "time": "time_offset_min",
        "minute": "time_offset_min",
        "voltage_series": "voltage_series",
        "voltage": "voltage_series",
        "current_series": "current_series",
        "current": "current_series",
        "power_series": "power_series",
        "power": "power_series",
    }
    normalized_headers = {name: field_map.get(name.strip().lower()) for name in reader.fieldnames}
    for row in reader:
        for source_name, target_name in normalized_headers.items():
            if target_name is None:
                continue
            value = row.get(source_name)
            if value is None or value == "":
                raise ValueError("dataset_csv_missing_value")
            series[target_name].append(float(value))
    return _normalize_series(series)


def _normalize_series(raw: dict[str, object]) -> dict[str, list[float]]:
    aliases = {
        "time_offset_min": ("time_offset_min", "time", "minute"),
        "voltage_series": ("voltage_series", "voltage"),
        "current_series": ("current_series", "current"),
        "power_series": ("power_series", "power"),
    }
    normalized: dict[str, list[float]] = {}
    for target_name, names in aliases.items():
        value = next((raw[name] for name in names if name in raw), None)
        if not isinstance(value, list) or not value:
            raise ValueError(f"dataset_series_missing_{target_name}")
        normalized[target_name] = [float(item) for item in value]
    lengths = {len(values) for values in normalized.values()}
    if len(lengths) != 1:
        raise ValueError("dataset_series_length_mismatch")
    return normalized


def serialize_dataset(item: BatteryExample) -> dict[str, object]:
    return {
        "id": item.id,
        "sample_key": item.sample_key,
        "title": item.title,
        "problem_type": item.problem_type,
        "capacity_range": item.capacity_range,
        "description": item.description,
        "source": item.source,
        "is_active": item.is_active,
        "sort_order": item.sort_order,
        "series": json.loads(item.payload_json),
    }


def list_datasets_for_user(db: Session, user_id: int) -> list[BatteryExample]:
    return list(
        db.scalars(
            select(BatteryExample)
            .where(
                BatteryExample.is_active.is_(True),
                or_(
                    BatteryExample.source != "user_upload",
                    BatteryExample.owner_user_id == user_id,
                ),
            )
            .order_by(BatteryExample.sort_order.asc(), BatteryExample.id.asc())
        ).all()
    )


def list_admin_datasets(db: Session) -> list[BatteryExample]:
    return list(db.scalars(select(BatteryExample).order_by(BatteryExample.sort_order.asc(), BatteryExample.id.asc())).all())


def get_dataset_for_user(db: Session, dataset_id: int, user_id: int) -> BatteryExample | None:
    return db.scalar(
        select(BatteryExample).where(
            BatteryExample.id == dataset_id,
            BatteryExample.is_active.is_(True),
            or_(
                BatteryExample.source != "user_upload",
                BatteryExample.owner_user_id == user_id,
                BatteryExample.owner_user_id.is_(None),
            ),
        )
    )


def create_dataset(
    db: Session,
    *,
    title: str,
    problem_type: str,
    capacity_range: str,
    description: str,
    series: dict[str, list[float]],
    source: str,
    sort_order: int = 0,
    is_active: bool = True,
    owner_user_id: int | None = None,
) -> BatteryExample:
    dataset = BatteryExample(
        sample_key=f"{source}-{uuid.uuid4().hex[:12]}",
        title=title,
        problem_type=problem_type,
        capacity_range=capacity_range,
        description=description,
        source=source,
        is_active=is_active,
        owner_user_id=owner_user_id,
        sort_order=sort_order,
        payload_json=json.dumps(series, ensure_ascii=False),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def update_dataset(
    db: Session,
    dataset: BatteryExample,
    *,
    title: str | None = None,
    problem_type: str | None = None,
    capacity_range: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
    series: dict[str, list[float]] | None = None,
) -> BatteryExample:
    if title is not None:
        dataset.title = title
    if problem_type is not None:
        dataset.problem_type = problem_type
    if capacity_range is not None:
        dataset.capacity_range = capacity_range
    if description is not None:
        dataset.description = description
    if sort_order is not None:
        dataset.sort_order = sort_order
    if is_active is not None:
        dataset.is_active = is_active
    if series is not None:
        dataset.payload_json = json.dumps(series, ensure_ascii=False)
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, dataset: BatteryExample) -> None:
    db.delete(dataset)
    db.commit()


def import_dataset_from_mysql(*, phone: str, start_time: str, end_time: str, title: str | None = None) -> BatteryExample:
    _ = (phone, start_time, end_time, title)
    raise NotImplementedError("external_mysql_query_not_configured")

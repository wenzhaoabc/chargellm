"""Read-only access to the IOT MySQL database for charging records.

The query is translated from the MyBatis XML in `ChargeLLM平台建设.txt`. It
returns *all* completed charge orders for a given user phone within an optional
time window (defaults to the last 6 months). Each order carries the joined
time-series of push_time_diff / power / voltage / current.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import Settings, get_settings


_CHARGE_RECORD_SQL = text(
    """
    SELECT order_no,
           supplier_code,
           supplier_name,
           GROUP_CONCAT(DISTINCT user_name ORDER BY id SEPARATOR ',')         AS user_name,
           GROUP_CONCAT(DISTINCT user_phone ORDER BY id SEPARATOR ',')        AS user_phone,
           GROUP_CONCAT(DISTINCT charge_start_time ORDER BY id SEPARATOR ',') AS charge_start_time,
           GROUP_CONCAT(DISTINCT charge_end_time ORDER BY id SEPARATOR ',')   AS charge_end_time,
           MAX(charge_capacity)                                               AS charge_capacity,
           GROUP_CONCAT(push_time_diff ORDER BY id SEPARATOR ',')             AS push_times,
           GROUP_CONCAT(device_power ORDER BY id SEPARATOR ',')               AS powers,
           GROUP_CONCAT(IFNULL(device_voltage,-1) ORDER BY id SEPARATOR ',')  AS voltages,
           GROUP_CONCAT(IFNULL(device_current,-1) ORDER BY id SEPARATOR ',')  AS currents
    FROM (
        SELECT p.id,
               p.order_no,
               p.supplier_code,
               sup.supplier_name,
               p.user_name,
               p.user_phone,
               pf.charge_start_time,
               pf.charge_end_time,
               p.charge_capacity,
               p.order_status,
               TIMESTAMPDIFF(MINUTE, pf.charge_start_time, p.push_time) AS push_time_diff,
               p.device_power,
               p.device_voltage,
               p.device_current
        FROM smc_device_order_push p
        INNER JOIN (
            SELECT supplier_code,
                   order_no,
                   MAX(charge_start_time) AS charge_start_time,
                   MAX(charge_end_time)   AS charge_end_time
            FROM smc_device_order_push_finish
            WHERE order_status = 3
              AND user_phone = :phone
              AND push_time >= :start_time
              AND push_time <= :end_time
            GROUP BY supplier_code, order_no
        ) pf ON pf.supplier_code = p.supplier_code AND pf.order_no = p.order_no
        LEFT JOIN smc_device_supplier sup ON p.supplier_code = sup.supplier_code
        WHERE p.user_phone = :phone
          AND p.push_time >= :start_time
          AND p.push_time <= :end_time
    ) AS all_records
    GROUP BY order_no, supplier_code, supplier_name
    ORDER BY order_no DESC
    """
)


@dataclass(slots=True)
class ChargeSeries:
    time_offset_min: list[int]
    powers: list[float]
    voltages: list[float | None]
    currents: list[float | None]


@dataclass(slots=True)
class ChargeOrder:
    order_no: str
    supplier_code: str | None
    supplier_name: str | None
    user_name: str | None
    user_phone: str | None
    charge_start_time: str | None
    charge_end_time: str | None
    charge_capacity: float | None
    series: ChargeSeries

    def to_dict(self) -> dict:
        return {
            "order_no": self.order_no,
            "supplier_code": self.supplier_code,
            "supplier_name": self.supplier_name,
            "user_name": self.user_name,
            "user_phone": self.user_phone,
            "charge_start_time": self.charge_start_time,
            "charge_end_time": self.charge_end_time,
            "charge_capacity": self.charge_capacity,
            "series": {
                "time_offset_min": self.series.time_offset_min,
                "powers": self.series.powers,
                "voltages": self.series.voltages,
                "currents": self.series.currents,
            },
        }


def _normalize_iot_url(url: str) -> str:
    if url.startswith("mysql://"):
        return "mysql+pymysql://" + url[len("mysql://") :]
    return url


@lru_cache(maxsize=1)
def _build_engine_cached(url: str) -> Engine:
    return create_engine(
        _normalize_iot_url(url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=3600,
        future=True,
    )


def get_iot_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    if not settings.iot_db_url:
        raise RuntimeError("iot_db_url_not_configured")
    return _build_engine_cached(settings.iot_db_url)


def _split_floats(raw: str | None, missing_sentinel: float | None = None) -> list[float | None]:
    if not raw:
        return []
    out: list[float | None] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            out.append(None)
            continue
        try:
            value = float(token)
        except ValueError:
            out.append(None)
            continue
        if missing_sentinel is not None and value == missing_sentinel:
            out.append(None)
        else:
            out.append(value)
    return out


def _split_ints(raw: str | None) -> list[int]:
    if not raw:
        return []
    out: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(int(float(token)))
        except ValueError:
            continue
    return out


def _first_non_none(values: Iterable[float | None]) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _postprocess_series(
    push_times: list[int],
    powers_raw: list[float | None],
    voltages_raw: list[float | None],
    currents_raw: list[float | None],
) -> ChargeSeries:
    # If first sample's push_time != 0, prepend an initial point at minute 0.
    if push_times and push_times[0] != 0:
        first_voltage = _first_non_none(voltages_raw)
        push_times = [0] + push_times
        powers_raw = [0.0] + powers_raw
        voltages_raw = [first_voltage] + voltages_raw
        currents_raw = [0.0] + currents_raw

    powers = [0.0 if value is None else float(value) for value in powers_raw]
    return ChargeSeries(
        time_offset_min=push_times,
        powers=powers,
        voltages=voltages_raw,
        currents=currents_raw,
    )


def _row_to_order(row) -> ChargeOrder:
    mapping = row._mapping if hasattr(row, "_mapping") else dict(row)
    push_times = _split_ints(mapping.get("push_times"))
    powers_raw = _split_floats(mapping.get("powers"))
    voltages_raw = _split_floats(mapping.get("voltages"), missing_sentinel=-1.0)
    currents_raw = _split_floats(mapping.get("currents"), missing_sentinel=-1.0)

    # Align all series to the shortest non-zero length to defend against
    # GROUP_CONCAT length mismatches (rare but possible).
    lengths = [len(push_times), len(powers_raw), len(voltages_raw), len(currents_raw)]
    target_len = min(length for length in lengths if length > 0) if any(lengths) else 0
    push_times = push_times[:target_len]
    powers_raw = powers_raw[:target_len]
    voltages_raw = voltages_raw[:target_len]
    currents_raw = currents_raw[:target_len]

    series = _postprocess_series(push_times, powers_raw, voltages_raw, currents_raw)

    capacity = mapping.get("charge_capacity")
    return ChargeOrder(
        order_no=str(mapping.get("order_no") or ""),
        supplier_code=mapping.get("supplier_code"),
        supplier_name=mapping.get("supplier_name"),
        user_name=mapping.get("user_name"),
        user_phone=mapping.get("user_phone"),
        charge_start_time=str(mapping.get("charge_start_time")) if mapping.get("charge_start_time") else None,
        charge_end_time=str(mapping.get("charge_end_time")) if mapping.get("charge_end_time") else None,
        charge_capacity=float(capacity) if capacity is not None else None,
        series=series,
    )


def query_charge_orders_by_phone(
    phone: str,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    settings: Settings | None = None,
) -> list[ChargeOrder]:
    if not phone:
        raise ValueError("phone_required")
    settings = settings or get_settings()
    if end_time is None:
        end_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if start_time is None:
        start_time = end_time - timedelta(days=180)

    engine = get_iot_engine(settings)
    with engine.connect() as connection:
        rows = connection.execute(
            _CHARGE_RECORD_SQL,
            {"phone": phone, "start_time": start_time, "end_time": end_time},
        ).fetchall()
    return [_row_to_order(row) for row in rows]

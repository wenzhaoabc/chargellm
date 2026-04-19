from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


LABELS = ["电池故障", "电池老化", "非标电池", "正常"]
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}


class ChargingProcessRecord(BaseModel):
    process_id: str
    charge_start_time: str | None = None
    charge_end_time: str | None = None
    current_series: list[float]
    voltage_series: list[float]
    power_series: list[float]
    charge_capacity: list[float]

    @field_validator("current_series", "voltage_series", "power_series", "charge_capacity")
    @classmethod
    def validate_series_not_empty(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("series must not be empty")
        return value


class BatterySample(BaseModel):
    battery_id: str
    label: Literal["电池故障", "电池老化", "非标电池", "正常"]
    reason: str | None = None
    charging_process: list[ChargingProcessRecord] = Field(min_length=1)


class CanonicalBatterySample(BaseModel):
    battery_id: str
    label_text: str
    label_id: int
    reason_text: str
    process_ids: list[str]
    process_values: list[list[list[float]]]
    process_mask: list[list[bool]]
    history_mask: list[bool]

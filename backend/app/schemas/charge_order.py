from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChargeSeriesRead(BaseModel):
    time_offset_min: list[int] = Field(default_factory=list)
    powers: list[float] = Field(default_factory=list)
    voltages: list[float | None] = Field(default_factory=list)
    currents: list[float | None] = Field(default_factory=list)


class ChargeOrderRead(BaseModel):
    order_no: str
    supplier_code: str | None = None
    supplier_name: str | None = None
    user_name: str | None = None
    user_phone: str | None = None
    charge_start_time: str | None = None
    charge_end_time: str | None = None
    charge_capacity: float | None = None
    series: ChargeSeriesRead


class ChargeOrderQueryRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=32)
    start_time: datetime | None = None
    end_time: datetime | None = None


class ChargeOrderListResponse(BaseModel):
    phone_masked: str
    orders: list[ChargeOrderRead]

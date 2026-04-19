from __future__ import annotations

from pydantic import BaseModel, Field


class BatterySeries(BaseModel):
    time_offset_min: list[float] = Field(default_factory=list)
    power_series: list[float] = Field(default_factory=list)
    current_series: list[float] = Field(default_factory=list)
    voltage_series: list[float] = Field(default_factory=list)


class BatteryExampleRead(BaseModel):
    id: int
    sample_key: str
    title: str
    problem_type: str
    capacity_range: str
    description: str
    source: str = "demo_case"
    is_active: bool = True
    sort_order: int
    series: BatterySeries


class DatasetListResponse(BaseModel):
    items: list[BatteryExampleRead]


class DatasetUploadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    file_name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class AdminDatasetCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    problem_type: str = Field(default="待诊断", max_length=64)
    capacity_range: str = Field(default="待评估", max_length=32)
    description: str = Field(default="专业演示数据", max_length=255)
    sort_order: int = 0
    is_active: bool = True
    source: str = "demo_case"
    file_name: str = Field(default="dataset.json", max_length=255)
    content: str | None = None


class AdminDatasetUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    problem_type: str | None = Field(default=None, max_length=64)
    capacity_range: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    is_active: bool | None = None
    file_name: str | None = Field(default=None, max_length=255)
    content: str | None = None


class DatasetDeleteResponse(BaseModel):
    id: int
    status: str


class MysqlDatasetImportRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=32)
    start_time: str = Field(min_length=1, max_length=64)
    end_time: str = Field(min_length=1, max_length=64)
    title: str | None = Field(default=None, max_length=128)


class BatteryExampleListResponse(BaseModel):
    items: list[BatteryExampleRead]


class HistoryQueryRequest(BaseModel):
    phone: str
    sms_code: str


class HistoryQueryResponse(BaseModel):
    status: str = "mock"
    phone_masked: str
    records: list[dict[str, str | int | float]] = Field(default_factory=list)

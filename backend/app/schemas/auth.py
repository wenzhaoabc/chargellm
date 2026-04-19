from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InviteStartRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)


class InviteStartResponse(BaseModel):
    invite_code: str
    session_token: str
    demo_user_id: int
    quota_total: int
    quota_used: int
    quota_remaining: int
    expires_at: datetime | None = None


class SmsSendRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=32)


class SmsSendResponse(BaseModel):
    phone_masked: str
    status: str = "mock_sent"
    mock_code: str


class SmsLoginRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=32)
    code: str = Field(min_length=4, max_length=16)


class SmsLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    phone_masked: str
    status: str = "mock_authenticated"


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_username: str


class InviteCodeCreateRequest(BaseModel):
    name: str
    code: str | None = None
    max_uses: int | None = None
    per_user_quota: int | None = None
    expires_at: datetime | None = None


class InviteCodeUpdateRequest(BaseModel):
    name: str | None = None
    max_uses: int | None = None
    per_user_quota: int | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class InviteCodeRead(BaseModel):
    id: int
    code: str
    name: str
    max_uses: int
    used_uses: int
    per_user_quota: int
    expires_at: datetime | None
    is_active: bool


class InviteCodeDeleteResponse(BaseModel):
    id: int
    code: str
    status: str


class AdminMeResponse(BaseModel):
    username: str
    status: str = "ok"

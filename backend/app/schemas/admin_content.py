from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# -------- system prompt --------


class SystemPromptRead(BaseModel):
    id: int
    scope: str
    title: str
    content: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class SystemPromptCreateRequest(BaseModel):
    scope: str = Field(default="default", max_length=32)
    title: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1)
    is_active: bool = True
    sort_order: int = 0


class SystemPromptUpdateRequest(BaseModel):
    scope: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=128)
    content: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


# -------- welcome --------


class WelcomeMessageRead(BaseModel):
    id: int
    title: str
    content: str
    sort_order: int
    is_active: bool


class WelcomeMessageCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1)
    sort_order: int = 0
    is_active: bool = True


class WelcomeMessageUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    content: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


# -------- user management --------


class AdminUserRead(BaseModel):
    id: int
    phone: str | None
    phone_masked: str | None
    username: str | None
    role: str
    is_active: bool
    usage_quota_total: int
    usage_quota_used: int
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    is_active: bool | None = None
    usage_quota_total: int | None = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]
    total: int


# -------- conversations --------


class AdminConversationRead(BaseModel):
    id: int
    title: str
    created_at: str
    phone: str | None
    phone_masked: str | None
    user_id: int | None
    message_count: int


class AdminConversationListResponse(BaseModel):
    items: list[AdminConversationRead]
    total: int


class AdminConversationMessage(BaseModel):
    id: int
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: str


class AdminConversationDetail(BaseModel):
    id: int
    title: str
    created_at: str
    messages: list[AdminConversationMessage]

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatStreamRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    dataset_id: int | None = None
    example_key: str | None = None


class AgentChatMessage(BaseModel):
    role: str = Field(min_length=1)
    content: str = ""


class AgentChatRequest(BaseModel):
    """Payload for /api/chat/agent/stream — multi-turn conversation with tools."""

    messages: list[AgentChatMessage] = Field(default_factory=list)
    user_phone: str | None = Field(default=None, description="若希望工具基于另一手机号查询，可在此提供。")
    system_prompt: str | None = None


class ChatCompletionMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str = Field(min_length=1)
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = None
    messages: list[ChatCompletionMessage] = Field(min_length=1)
    stream: bool = True
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    dataset_id: int | None = None
    example_key: str | None = None


class ChatFinalResponse(BaseModel):
    label: str
    capacity_range: str
    confidence: float
    reason: str
    key_processes: list[str]

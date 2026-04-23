from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol


@dataclass(slots=True)
class ToolContext:
    """Per-call execution context passed to every tool."""

    user_phone: str | None = None
    user_id: int | None = None
    session_token: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    name: str
    call_id: str
    display: str
    data: dict[str, Any] = field(default_factory=dict)
    # String fed back to the LLM as the tool message content. Keep small —
    # many models cap tool messages at a few KB.
    model_payload: str = ""
    is_error: bool = False


class Tool(Protocol):
    name: str
    description: str
    parameters_schema: dict[str, Any]
    feed_back_to_model: bool

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        ...


# Helper alias for tools implemented as plain async functions.
ToolExecutor = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]


@dataclass(slots=True)
class FunctionTool:
    """Adapter that turns a plain async function into a Tool."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    executor: ToolExecutor
    feed_back_to_model: bool = True

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return await self.executor(args, ctx)

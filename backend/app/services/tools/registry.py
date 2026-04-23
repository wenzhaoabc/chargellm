from __future__ import annotations

import json
import logging
from typing import Any, Callable

from app.services.tools.base import FunctionTool, Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Tool] = {}


def register_tool(
    *,
    name: str,
    description: str,
    parameters_schema: dict[str, Any],
    feed_back_to_model: bool = True,
) -> Callable:
    """Decorator: register an async function as a Tool."""

    def decorator(func):
        if name in _REGISTRY:
            raise ValueError(f"tool_already_registered:{name}")
        tool = FunctionTool(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            executor=func,
            feed_back_to_model=feed_back_to_model,
        )
        _REGISTRY[name] = tool
        return func

    return decorator


def list_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def get_tool_specs() -> list[dict[str, Any]]:
    """Return tool specs in the OpenAI Chat Completions ``tools`` format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema,
            },
        }
        for tool in _REGISTRY.values()
    ]


async def execute_tool(name: str, call_id: str, raw_arguments: str | dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool = _REGISTRY.get(name)
    if tool is None:
        return ToolResult(
            name=name,
            call_id=call_id,
            display=f"未知工具: {name}",
            data={"error": "tool_not_found"},
            model_payload=json.dumps({"error": "tool_not_found", "name": name}),
            is_error=True,
        )
    if isinstance(raw_arguments, str):
        try:
            args = json.loads(raw_arguments) if raw_arguments.strip() else {}
        except json.JSONDecodeError as exc:
            return ToolResult(
                name=name,
                call_id=call_id,
                display=f"工具参数解析失败: {exc}",
                data={"error": "bad_arguments_json", "raw": raw_arguments},
                model_payload=json.dumps({"error": "bad_arguments_json"}),
                is_error=True,
            )
    else:
        args = dict(raw_arguments or {})

    try:
        result = await tool.execute(args, ctx)
        result.name = name
        result.call_id = call_id
        return result
    except Exception as exc:  # noqa: BLE001 — surface tool failure to the model
        logger.exception("tool execution failed: %s", name)
        return ToolResult(
            name=name,
            call_id=call_id,
            display=f"工具执行失败: {exc}",
            data={"error": str(exc)},
            model_payload=json.dumps({"error": str(exc)}),
            is_error=True,
        )

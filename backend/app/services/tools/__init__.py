"""Tool calling framework for the LLM agent loop.

Each :class:`Tool` exposes a ``name``, a JSON-Schema for its arguments, and an
async ``execute`` method. Tools are auto-registered when the package is
imported. Two execution flavours are supported:

* ``feed_back_to_model = True``  — the result is appended as a ``role=tool``
  message and the model is invoked again (classic agent loop).
* ``feed_back_to_model = False`` — the result is **only** streamed to the
  frontend for direct rendering (e.g. chart-highlight commands). The model
  never sees it.

A ``ToolResult`` always carries:

* ``display`` — short human-readable summary for the chat bubble.
* ``data``    — structured payload for the frontend renderer.
* ``model_payload`` — string passed back to the model when feed_back is on.
"""

from __future__ import annotations

from app.services.tools.base import Tool, ToolContext, ToolResult
from app.services.tools.registry import (
    execute_tool,
    get_tool,
    get_tool_specs,
    list_tools,
    register_tool,
)

# Importing the implementations registers them via the @register_tool decorator.
from app.services.tools import implementations as _impls  # noqa: F401

__all__ = [
    "Tool",
    "ToolContext",
    "ToolResult",
    "execute_tool",
    "get_tool",
    "get_tool_specs",
    "list_tools",
    "register_tool",
]

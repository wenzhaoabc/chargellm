"""Built-in tool implementations available to the LLM."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.services.charging_data_service import query_charge_orders_by_phone
from app.services.tools.base import ToolContext, ToolResult
from app.services.tools.registry import register_tool

logger = logging.getLogger(__name__)


# --------------------------- query_charging_records ---------------------------


_ORDER_SUMMARY_LIMIT = 8  # cap series length sent back to the model


def _summarize_series(series: dict[str, list]) -> dict[str, list]:
    """Down-sample so we don't blow the model's context with raw points."""
    times = series.get("time_offset_min") or []
    if len(times) <= _ORDER_SUMMARY_LIMIT:
        return series
    step = max(1, len(times) // _ORDER_SUMMARY_LIMIT)
    return {
        key: (values[::step] + [values[-1]] if values else [])[: _ORDER_SUMMARY_LIMIT + 1]
        for key, values in series.items()
    }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


@register_tool(
    name="query_charging_records",
    description=(
        "查询某用户在时间窗口内的全部充电订单（按 user_phone）。"
        "返回该用户所有完成充电的订单及其电压/电流/功率时间序列。"
        "**优先用 ctx 中的当前用户手机号**；用户没显式给出新手机号时不要更换。"
        "默认时间窗为最近 6 个月。"
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "用户手机号；缺省时使用当前会话用户的手机号。",
            },
            "start_time": {
                "type": "string",
                "description": "查询起始时间 ISO8601；缺省为 6 个月前。",
            },
            "end_time": {
                "type": "string",
                "description": "查询结束时间 ISO8601；缺省为现在。",
            },
        },
        "required": [],
    },
    feed_back_to_model=True,
)
async def _query_charging_records(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    settings = get_settings()
    phone = (args.get("phone") or ctx.user_phone or "").strip()
    if not phone:
        return ToolResult(
            name="query_charging_records",
            call_id="",
            display="缺少手机号，无法查询充电记录。",
            data={"error": "phone_required"},
            model_payload=json.dumps({"error": "phone_required"}, ensure_ascii=False),
            is_error=True,
        )
    start_time = _parse_iso(args.get("start_time"))
    end_time = _parse_iso(args.get("end_time"))
    orders = await asyncio.to_thread(
        query_charge_orders_by_phone,
        phone,
        start_time=start_time,
        end_time=end_time,
        settings=settings,
    )
    full = [order.to_dict() for order in orders]
    summary = [
        {
            "order_no": item["order_no"],
            "supplier_name": item["supplier_name"],
            "charge_start_time": item["charge_start_time"],
            "charge_end_time": item["charge_end_time"],
            "charge_capacity": item["charge_capacity"],
            "series": _summarize_series(item["series"]),
        }
        for item in full
    ]
    return ToolResult(
        name="query_charging_records",
        call_id="",
        display=f"已读取 {phone[:3]}****{phone[-4:]} 的 {len(full)} 次充电记录。",
        data={"phone": phone, "orders": full},
        model_payload=json.dumps({"phone_masked": f"{phone[:3]}****{phone[-4:]}", "orders": summary}, ensure_ascii=False),
    )


# --------------------------- highlight_charge_segment ---------------------------


@register_tool(
    name="highlight_charge_segment",
    description=(
        "在前端某次充电曲线上标注一个异常时间段（仅渲染指令，不返回查询结果）。"
        "用于让用户直观看到某次订单 [start_min, end_min] 区间内某项指标的异常。"
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "order_no": {"type": "string", "description": "订单号 order_no"},
            "metric": {
                "type": "string",
                "enum": ["power", "voltage", "current"],
                "description": "需要标注的指标。",
            },
            "start_min": {"type": "number", "description": "异常区间起点（充电开始后多少分钟）。"},
            "end_min": {"type": "number", "description": "异常区间终点。"},
            "reason": {"type": "string", "description": "为何标记此段为异常。"},
            "severity": {
                "type": "string",
                "enum": ["info", "warning", "danger"],
                "description": "严重程度，前端用于颜色映射。",
                "default": "warning",
            },
        },
        "required": ["order_no", "metric", "start_min", "end_min", "reason"],
    },
    feed_back_to_model=False,
)
async def _highlight_charge_segment(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    payload = {
        "order_no": str(args.get("order_no") or ""),
        "metric": str(args.get("metric") or "power"),
        "start_min": float(args.get("start_min") or 0),
        "end_min": float(args.get("end_min") or 0),
        "reason": str(args.get("reason") or ""),
        "severity": str(args.get("severity") or "warning"),
    }
    return ToolResult(
        name="highlight_charge_segment",
        call_id="",
        display=f"标注订单 {payload['order_no']} 第 {payload['start_min']:.0f}-{payload['end_min']:.0f} 分钟",
        data=payload,
        model_payload="",  # display-only, model doesn't see the result
    )


# --------------------------- compare_orders ---------------------------


@register_tool(
    name="compare_orders",
    description="跨多个订单对比某项指标（如峰值/均值），用于揭示充电指标随时间的衰减或抖动趋势。",
    parameters_schema={
        "type": "object",
        "properties": {
            "order_nos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "需要对比的订单号列表。",
            },
            "metric": {
                "type": "string",
                "enum": ["power", "voltage", "current", "capacity"],
                "description": "对比指标。",
            },
        },
        "required": ["order_nos", "metric"],
    },
    feed_back_to_model=True,
)
async def _compare_orders(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    order_nos = [str(o) for o in (args.get("order_nos") or [])]
    metric = str(args.get("metric") or "power")
    cached = (ctx.extras or {}).get("orders_cache") or []
    series_map = {item["order_no"]: item for item in cached}

    rows = []
    for order_no in order_nos:
        item = series_map.get(order_no)
        if not item:
            rows.append({"order_no": order_no, "missing": True})
            continue
        if metric == "capacity":
            rows.append({"order_no": order_no, "value": item.get("charge_capacity")})
            continue
        series_key = {"power": "powers", "voltage": "voltages", "current": "currents"}[metric]
        series = (item.get("series") or {}).get(series_key) or []
        clean = [v for v in series if v is not None]
        rows.append(
            {
                "order_no": order_no,
                "max": max(clean) if clean else None,
                "avg": sum(clean) / len(clean) if clean else None,
                "min": min(clean) if clean else None,
            }
        )
    return ToolResult(
        name="compare_orders",
        call_id="",
        display=f"对比 {len(rows)} 个订单的 {metric}",
        data={"metric": metric, "rows": rows},
        model_payload=json.dumps({"metric": metric, "rows": rows}, ensure_ascii=False),
    )


# --------------------------- web_search (stub) ---------------------------


@register_tool(
    name="web_search",
    description="联网搜索（占位，当前返回 stub 结果）。后续可对接 Bing/SerpAPI。",
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词。"},
            "top_k": {"type": "integer", "default": 3},
        },
        "required": ["query"],
    },
    feed_back_to_model=True,
)
async def _web_search(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = str(args.get("query") or "")
    return ToolResult(
        name="web_search",
        call_id="",
        display=f"web_search: {query} (stub)",
        data={"query": query, "results": []},
        model_payload=json.dumps({"query": query, "results": [], "note": "web_search_not_configured"}, ensure_ascii=False),
    )

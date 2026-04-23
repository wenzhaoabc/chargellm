"""Content safety moderation.

Supports three modes:

- ``allow`` / ``block``: trivial short-circuits for tests.
- ``keyword``: local keyword match (the legacy MVP behaviour).
- ``aliyun``: real Aliyun Green Content Safety via ``TextModerationPlus``.

For streaming output the ``aliyun`` path is designed to be invoked from a
rolling window so the main stream is never blocked: callers submit each
window via ``check_async`` and await the futures opportunistically.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SafetyDecision(StrEnum):
    allow = "allow"
    block = "block"
    keyword = "keyword"


@dataclass(slots=True)
class SafetyResult:
    decision: SafetyDecision
    reason: str
    keyword: str | None = None
    label: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def allowed(self) -> bool:
        return self.decision == SafetyDecision.allow


# Aliyun service names (from 《AI生成内容安全检测》 docs)
SERVICE_INPUT = "query_security_check"   # AI 输入内容
SERVICE_OUTPUT = "response_security_check"  # AI 生成内容


class ContentSafetyService:
    """Sync-mode keyword moderation — kept for tests/fallback."""

    def __init__(self, mode: str, keywords: tuple[str, ...]) -> None:
        self.mode = mode
        self.keywords = keywords

    def check(self, text: str) -> SafetyResult:
        normalized = text.lower()
        if self.mode == "allow":
            return SafetyResult(decision=SafetyDecision.allow, reason="mock_allow")
        if self.mode == "block":
            return SafetyResult(decision=SafetyDecision.block, reason="mock_block")
        for keyword in self.keywords:
            if keyword and keyword.lower() in normalized:
                return SafetyResult(decision=SafetyDecision.keyword, reason="mock_keyword", keyword=keyword)
        return SafetyResult(decision=SafetyDecision.allow, reason="mock_allow")


class AliyunContentSafetyService:
    """Async moderation backed by Aliyun Green 2022-03-02 TextModerationPlus.

    - ``check_input(text)``: sync wait — used before invoking the LLM.
    - ``check_output_async(text, session_id)``: returns an awaitable ``SafetyResult``
      but fires the actual HTTP call in a worker thread so callers can continue
      streaming tokens to the client while the check runs.
    """

    def __init__(
        self,
        *,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        region_id: str = "cn-shanghai",
        fallback: ContentSafetyService | None = None,
    ) -> None:
        self.mode = "aliyun"
        self._fallback = fallback
        self._ak = access_key_id
        self._sk = access_key_secret
        self._endpoint = endpoint
        self._region = region_id
        self._client = None

    def _build_client(self):
        if self._client is not None:
            return self._client
        from alibabacloud_green20220302.client import Client
        from alibabacloud_tea_openapi.models import Config

        config = Config(
            access_key_id=self._ak,
            access_key_secret=self._sk,
            endpoint=self._endpoint,
            region_id=self._region,
            type="access_key",
        )
        self._client = Client(config)
        return self._client

    def _call_text_moderation(self, service: str, text: str, session_id: str | None) -> SafetyResult:
        from alibabacloud_green20220302.models import TextModerationPlusRequest

        if not text.strip():
            return SafetyResult(decision=SafetyDecision.allow, reason="empty_text")
        try:
            client = self._build_client()
            service_parameters = {"content": text[:2000]}
            if session_id:
                service_parameters["sessionId"] = session_id
            request = TextModerationPlusRequest(
                service=service,
                service_parameters=json.dumps(service_parameters, ensure_ascii=False),
            )
            response = client.text_moderation_plus(request)
            body = response.body
            if body is None or body.data is None:
                return SafetyResult(decision=SafetyDecision.allow, reason="no_body")
            data = body.data
            risk_level = getattr(data, "risk_level", None)
            results = getattr(data, "result", None) or []
            first_label: str | None = None
            for item in results:
                label = getattr(item, "label", None)
                if label and label != "nonLabel":
                    first_label = label
                    break
            allowed = risk_level in (None, "none", "low") and first_label is None
            if allowed:
                return SafetyResult(decision=SafetyDecision.allow, reason=risk_level or "ok")
            return SafetyResult(
                decision=SafetyDecision.block,
                reason=f"aliyun_{risk_level or 'risk'}",
                label=first_label,
            )
        except Exception as exc:  # noqa: BLE001 — network / SDK errors fall back
            logger.warning("aliyun_content_safety_error: %s", exc)
            if self._fallback is not None:
                return self._fallback.check(text)
            return SafetyResult(decision=SafetyDecision.allow, reason="aliyun_error_fallback_allow")

    async def check_input(self, text: str, *, session_id: str | None = None) -> SafetyResult:
        return await asyncio.to_thread(self._call_text_moderation, SERVICE_INPUT, text, session_id)

    async def check_output(self, text: str, *, session_id: str | None = None) -> SafetyResult:
        return await asyncio.to_thread(self._call_text_moderation, SERVICE_OUTPUT, text, session_id)

    def check_output_task(self, text: str, *, session_id: str | None = None) -> asyncio.Task[SafetyResult]:
        """Schedule an async output check, returning the Task for later awaiting."""
        return asyncio.create_task(self.check_output(text, session_id=session_id))

    @property
    def keywords(self) -> tuple[str, ...]:
        # Compatibility shim: legacy chat_service.py reads `.keywords` to size
        # an output holdback buffer. With Aliyun we don't need a buffer, so
        # return empty.
        return ()

    def check(self, text: str) -> SafetyResult:
        """Synchronous helper used by legacy code paths.

        Aliyun moderation is fundamentally an async/HTTP call; this shim
        delegates to the keyword fallback to avoid blocking the request thread.
        Real async checks are exposed via :meth:`check_input` / :meth:`check_output`.
        """
        if self._fallback is not None:
            return self._fallback.check(text)
        return SafetyResult(decision=SafetyDecision.allow, reason="aliyun_sync_skipped")


def build_content_safety(settings) -> ContentSafetyService | AliyunContentSafetyService:
    """Factory: return aliyun service if credentials are configured, else keyword fallback."""
    keyword_service = ContentSafetyService(mode="keyword", keywords=settings.content_safety_keywords)
    has_aliyun_creds = bool(
        settings.aliyun_access_key_id
        and settings.aliyun_access_key_secret
        and settings.aliyun_content_safety_endpoint
    )
    use_aliyun = settings.content_safety_mode == "aliyun" or (
        settings.content_safety_mode in ("", "auto", "keyword") and has_aliyun_creds
    )
    if use_aliyun and has_aliyun_creds:
        return AliyunContentSafetyService(
            access_key_id=settings.aliyun_access_key_id,
            access_key_secret=settings.aliyun_access_key_secret,
            endpoint=settings.aliyun_content_safety_endpoint,
            region_id=settings.aliyun_region_id,
            fallback=keyword_service,
        )
    return ContentSafetyService(mode=settings.content_safety_mode or "keyword", keywords=settings.content_safety_keywords)

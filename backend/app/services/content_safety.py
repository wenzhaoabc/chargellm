from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SafetyDecision(StrEnum):
    allow = "allow"
    block = "block"
    keyword = "keyword"


@dataclass(slots=True)
class SafetyResult:
    decision: SafetyDecision
    reason: str
    keyword: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision == SafetyDecision.allow


class ContentSafetyService:
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


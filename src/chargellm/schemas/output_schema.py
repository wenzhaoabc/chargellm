from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DiagnosisOutput(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_processes: list[str]
    explanation: str

    @field_validator("key_processes")
    @classmethod
    def validate_key_processes(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("key_processes must not be empty")
        return value

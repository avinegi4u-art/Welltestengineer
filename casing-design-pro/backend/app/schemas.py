"""FastAPI schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[str] | None = None


class AnalyzeResponse(BaseModel):
    rows: list[dict[str, Any]]
    check_count: int
    max_util: float
    governing: dict[str, Any] | None
    design_code: str

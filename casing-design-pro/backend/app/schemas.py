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
    loads: list[dict[str, Any]] | None = None
    check_count: int
    max_util: float
    governing: dict[str, Any] | None
    design_code: str
    engine: str | None = None


class MonteCarloRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[str] | None = None
    iterations: int = Field(default=500, ge=50, le=5000)


class MonteCarloResponse(BaseModel):
    iterations: int
    p10: float
    p50: float
    p90: float
    p95: float
    mean: float
    max: float
    pass_probability: float
    failure_count: int
    histogram: list[float] | None = None


class VmeImportRequest(BaseModel):
    csv_text: str


class VmeImportResponse(BaseModel):
    curves: list[dict[str, Any]]
    count: int

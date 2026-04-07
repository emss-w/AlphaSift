from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class SystemInfoResponse(BaseModel):
    version: str
    api_name: str
    data_dir: str
    db_path: str
    artifacts_dir: str


class StrategySummary(BaseModel):
    id: str
    name: str
    source_type: str
    version: str
    status: str
    description: str | None = None


class JobSummary(BaseModel):
    id: str
    kind: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None
    summary: dict[str, Any] | None = None


class ArtifactSummary(BaseModel):
    artifact_id: str
    kind: str
    path: str
    created_at: str
    owner_type: str
    owner_id: str


class ExperimentResultSummary(BaseModel):
    strategy: str
    parameters: dict[str, int]
    total_return: float
    annualized_return: float | None
    max_drawdown: float
    trades: int
    final_equity: float


class ExperimentRunSummary(BaseModel):
    id: str
    job_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    result_count: int
    best_result: ExperimentResultSummary | None = None
    artifacts: list[ArtifactSummary] = Field(default_factory=list)
    created_at: str
    job: JobSummary


class PaperSessionSummary(BaseModel):
    id: str
    job_id: str | None = None
    strategy_name: str
    symbol: str
    timeframe: str
    starting_cash: float
    ending_equity: float | None = None
    status: str
    summary: dict[str, Any] | None = None
    artifacts: list[ArtifactSummary] = Field(default_factory=list)
    created_at: str
    job: JobSummary | None = None


class CreateSmaExperimentRequest(BaseModel):
    pair: str
    interval: int = Field(gt=0)
    short_windows: list[int] = Field(min_length=1)
    long_windows: list[int] = Field(min_length=1)
    sort_by: str = Field(default="total_return")
    fee_rate: float = Field(default=0.0, ge=0.0)
    export_csv: bool = True
    refresh: bool = False


class CreatePaperSessionRequest(BaseModel):
    pair: str
    interval: int = Field(gt=0)
    strategy_id: str
    short_window: int | None = Field(default=None, gt=0)
    long_window: int | None = Field(default=None, gt=0)
    initial_cash: float = Field(default=10_000.0, ge=0.0)
    export_csv: bool = True
    refresh: bool = False

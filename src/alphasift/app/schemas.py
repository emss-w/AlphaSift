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


class HypothesisResult(BaseModel):
    title: str
    summary: str
    rationale: str
    indicators: list[str] = Field(default_factory=list)
    market_assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)


class StrategyDraftResult(BaseModel):
    draft_summary: str
    code_artifact: str
    assumptions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    suggested_tests: list[str] = Field(default_factory=list)
    notes: str | None = None


class BacktestReportResult(BaseModel):
    title: str
    pair: str
    timeframe: str
    fee_rate: float
    candles_count: int
    strategy_id: str
    parameters: dict[str, Any]
    rationale: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    summary: dict[str, Any]
    generated_at: str


class CodeExecutionSummary(BaseModel):
    success: bool
    exit_code: int | None = None
    timed_out: bool
    duration_seconds: float
    stdout_tail: str | None = None
    stderr_tail: str | None = None


class CodeRepairAttemptSummary(BaseModel):
    attempt: int
    repaired: bool
    failure_reason: str | None = None
    execution: CodeExecutionSummary | None = None


class CodeReportResult(BaseModel):
    title: str
    summary: str
    report: dict[str, Any]
    execution: CodeExecutionSummary
    attempts: list[CodeRepairAttemptSummary] = Field(default_factory=list)
    generated_at: str


class PromptProfileSummary(BaseModel):
    id: str
    template_name: str
    run_type: str
    provider: str
    model_name: str
    temperature: float | None = None
    created_at: str
    notes: str | None = None


class AiModelSummary(BaseModel):
    provider: str
    model_name: str
    is_default: bool = True


class AiRunSummary(BaseModel):
    id: str
    job_id: str
    provider: str
    model_name: str
    run_type: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    hypothesis: HypothesisResult | None = None
    strategy_draft: StrategyDraftResult | None = None
    backtest_report: BacktestReportResult | None = None
    code_report: CodeReportResult | None = None
    artifacts: list[ArtifactSummary] = Field(default_factory=list)
    job: JobSummary


class CreateHypothesisRequest(BaseModel):
    research_objective: str = Field(min_length=1)
    symbol: str | None = None
    timeframe: str | None = None
    constraints: str | None = None
    prompt_profile_id: str | None = None
    export_artifacts: bool = True


class CreateStrategyDraftRequest(BaseModel):
    prompt: str | None = None
    hypothesis_run_id: str | None = None
    coding_constraints: str | None = None
    repo_conventions: str | None = None
    prompt_profile_id: str | None = None
    pair: str = "BTC/USD"
    interval: int = Field(default=60, gt=0)
    fee_rate: float = Field(default=0.0, ge=0.0)
    run_backtest: bool = True
    refresh: bool = False
    export_artifacts: bool = True


class CreateCodeReportRequest(BaseModel):
    research_objective: str = Field(min_length=1)
    pair: str = "BTC/USD"
    interval: int = Field(default=60, gt=0)
    fee_rate: float = Field(default=0.0, ge=0.0)
    constraints: str | None = None
    hypothesis_run_id: str | None = None
    strategy_draft_run_id: str | None = None
    prompt_profile_id: str | None = None
    timeout_seconds: int | None = Field(default=None, gt=0)
    refresh: bool = False
    export_artifacts: bool = True

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from alphasift import __version__
from alphasift.ai.models import (
    HypothesisResult as AiHypothesisResult,
    SandboxCodeInput as AiSandboxCodeInput,
    SandboxCodeResult as AiSandboxCodeResult,
    StrategyBacktestPlan as AiStrategyBacktestPlan,
    StrategyDraftResult as AiStrategyDraftResult,
)
from alphasift.ai.service import AiWorkflowService, create_ai_workflow_service
from alphasift.app.db import MetadataStore
from alphasift.app.jobs import (
    create_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
    utc_now_iso,
)
from alphasift.app.schemas import (
    AiModelSummary,
    AiRunSummary,
    ArtifactSummary,
    BacktestReportResult,
    CodeRepairAttemptSummary,
    CodeExecutionSummary,
    CodeReportResult,
    CreateCodeReportRequest,
    CreateHypothesisRequest,
    CreatePaperSessionRequest,
    CreateSmaExperimentRequest,
    CreateStrategyDraftRequest,
    ExperimentResultSummary,
    ExperimentRunSummary,
    HypothesisResult,
    JobSummary,
    PaperSessionSummary,
    PromptProfileSummary,
    StrategySummary,
    StrategyDraftResult as StrategyDraftResultPayload,
    SystemInfoResponse,
)
from alphasift.config import Config
from alphasift.data.loaders import create_kraken_provider
from alphasift.experiments.export import export_experiment_results_to_csv
from alphasift.experiments.runner import run_sma_cross_experiments
from alphasift.paper.engine import run_paper_trader
from alphasift.paper.export import export_paper_trading_result_to_csv
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy
from alphasift.strategies.base import run_strategy_backtest
from alphasift.strategies.sma_cross import SimpleMovingAverageCrossStrategy
from alphasift.sandbox.models import SandboxRunRequest, SandboxRunResult
from alphasift.sandbox.runner import DockerSandboxPolicy, DockerSandboxRunner


_BUILTIN_STRATEGIES = [
    {
        "id": "buy_and_hold",
        "name": "Buy and Hold",
        "source_type": "builtin",
        "version": "1.0",
        "status": "active",
        "description": "Enters long after the first bar and remains long.",
    },
    {
        "id": "sma_cross",
        "name": "SMA Cross",
        "source_type": "builtin",
        "version": "1.0",
        "status": "active",
        "description": "Long when short SMA is above long SMA; otherwise flat.",
    },
]


_DEFAULT_PROMPT_PROFILES = [
    {
        "id": "gemini_hypothesis_v1",
        "template_name": "hypothesis_v1",
        "run_type": "hypothesis",
        "provider": "gemini",
        "notes": "Default hypothesis prompt profile for local research generation.",
    },
    {
        "id": "gemini_strategy_draft_v1",
        "template_name": "strategy_draft_v1",
        "run_type": "strategy_draft",
        "provider": "gemini",
        "notes": "Default strategy draft prompt profile for manual review workflows.",
    },
    {
        "id": "gemini_code_report_v1",
        "template_name": "code_report_v1",
        "run_type": "code_report",
        "provider": "gemini",
        "notes": "Default sandbox code-report profile for contract-based execution.",
    },
]

_DEFAULT_STRATEGY_PARAMETERS = {
    "atr_period": 14,
    "rsi_period": 14,
    "rsi_entry_threshold": 30,
    "rsi_exit_threshold": 55,
    "stop_loss_atr_multiplier": 2.0,
    "cooldown_bars": 8,
}

_SANDBOX_BANNED_IMPORTS = {
    "requests",
    "httpx",
    "socket",
    "subprocess",
    "urllib",
    "aiohttp",
    "ftplib",
    "telnetlib",
}

_SANDBOX_BANNED_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
}


class AppServices:
    """Thin application-facing wrappers over existing research modules."""

    def __init__(self, config: Config, store: MetadataStore) -> None:
        self.config = config
        self.store = store
        self.artifacts_root = config.artifacts_dir
        self.ai_artifacts_root = config.ai_artifacts_dir
        self._ai_service: AiWorkflowService | None = None
        self._sandbox_runner: DockerSandboxRunner | None = None
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self.ai_artifacts_root.mkdir(parents=True, exist_ok=True)
        self._ensure_builtin_strategies()
        self._ensure_prompt_profiles()

    def system_info(self) -> SystemInfoResponse:
        """Return basic local service metadata."""
        return SystemInfoResponse(
            version=__version__,
            api_name="alphasift-local-api",
            data_dir=str(self.config.default_data_dir),
            db_path=str(self.config.app_db_path),
            artifacts_dir=str(self.artifacts_root),
        )

    def list_strategies(self) -> list[StrategySummary]:
        """List registered strategies."""
        rows = self.store.fetch_all("strategies", order_by="name ASC")
        return [StrategySummary(**row) for row in rows]

    def get_strategy(self, strategy_id: str) -> StrategySummary | None:
        """Fetch one strategy by identifier."""
        row = self.store.fetch_one("strategies", strategy_id)
        return StrategySummary(**row) if row else None

    def list_jobs(self) -> list[JobSummary]:
        """List jobs newest-first."""
        rows = self.store.fetch_all("jobs")
        return [self._to_job_summary(row) for row in rows]

    def get_job(self, job_id: str) -> JobSummary | None:
        """Fetch one job by identifier."""
        row = self.store.fetch_one("jobs", job_id)
        if row is None:
            return None
        return self._to_job_summary(row)

    def run_sma_experiment(self, request: CreateSmaExperimentRequest) -> ExperimentRunSummary:
        """Run SMA cross experiments synchronously and persist metadata."""
        job = create_job(self.store, kind="experiment_sma_cross")
        mark_job_running(self.store, job_id=job["id"])

        run_id = uuid4().hex
        try:
            provider = create_kraken_provider(self.config)
            candles = provider.fetch_ohlc(
                request.pair,
                request.interval,
                use_cache=not request.refresh,
            )
            if candles.empty:
                raise ValueError("No completed candles found for the requested pair/interval.")

            experiment_run = run_sma_cross_experiments(
                candles,
                request.short_windows,
                request.long_windows,
                sort_by=request.sort_by,
                fee_rate=request.fee_rate,
            )

            artifacts: list[ArtifactSummary] = []
            if request.export_csv:
                output_path = self._experiment_output_path(run_id)
                export_experiment_results_to_csv(
                    experiment_run.results,
                    output_path,
                    overwrite=True,
                )
                artifacts.append(
                    self._create_artifact(
                        kind="experiment_results_csv",
                        path=output_path,
                        owner_type="experiment_run",
                        owner_id=run_id,
                    )
                )

            best_result = experiment_run.results[0]
            run_row = {
                "id": run_id,
                "job_id": job["id"],
                "strategy_name": "SimpleMovingAverageCrossStrategy",
                "symbol": request.pair,
                "timeframe": str(request.interval),
                "parameters_json": json.dumps(
                    {
                        "short_windows": request.short_windows,
                        "long_windows": request.long_windows,
                        "sort_by": request.sort_by,
                        "fee_rate": request.fee_rate,
                    },
                    sort_keys=True,
                ),
                "result_count": len(experiment_run.results),
                "best_result_json": json.dumps(best_result.__dict__, sort_keys=True),
                "artifacts_json": json.dumps([a.model_dump() for a in artifacts], sort_keys=True),
                "created_at": utc_now_iso(),
            }
            self.store.insert("experiment_runs", run_row)

            summary = {
                "run_id": run_id,
                "result_count": len(experiment_run.results),
                "best_total_return": best_result.total_return,
            }
            completed_job = mark_job_completed(self.store, job_id=job["id"], summary=summary)
            return self._to_experiment_summary(run_row, completed_job)
        except Exception as exc:
            mark_job_failed(self.store, job_id=job["id"], error_message=str(exc))
            raise

    def list_experiment_runs(self) -> list[ExperimentRunSummary]:
        """List experiment runs newest-first."""
        rows = self.store.fetch_all("experiment_runs")
        return [self._to_experiment_summary(row) for row in rows]

    def get_experiment_run(self, run_id: str) -> ExperimentRunSummary | None:
        """Fetch one experiment run by identifier."""
        row = self.store.fetch_one("experiment_runs", run_id)
        if row is None:
            return None
        return self._to_experiment_summary(row)

    def start_paper_session(self, request: CreatePaperSessionRequest) -> PaperSessionSummary:
        """Run a synchronous paper session and persist metadata/artifacts."""
        strategy_meta = self.get_strategy(request.strategy_id)
        if strategy_meta is None:
            raise ValueError(f"Unknown strategy_id: {request.strategy_id}")

        strategy = self._build_strategy(request)
        job = create_job(self.store, kind="paper_session")
        mark_job_running(self.store, job_id=job["id"])

        session_id = uuid4().hex
        try:
            provider = create_kraken_provider(self.config)
            candles = provider.fetch_ohlc(
                request.pair,
                request.interval,
                use_cache=not request.refresh,
            )
            if candles.empty:
                raise ValueError("No completed candles found for the requested pair/interval.")

            paper_result = run_paper_trader(candles, strategy, initial_cash=request.initial_cash)
            artifacts: list[ArtifactSummary] = []
            if request.export_csv:
                account_path, fills_path = export_paper_trading_result_to_csv(
                    paper_result,
                    self._paper_output_dir(session_id),
                    prefix=f"paper_session_{session_id}",
                    overwrite=True,
                )
                artifacts.append(
                    self._create_artifact(
                        kind="paper_account_history_csv",
                        path=account_path,
                        owner_type="paper_session",
                        owner_id=session_id,
                    )
                )
                artifacts.append(
                    self._create_artifact(
                        kind="paper_fills_csv",
                        path=fills_path,
                        owner_type="paper_session",
                        owner_id=session_id,
                    )
                )

            session_row = {
                "id": session_id,
                "job_id": job["id"],
                "strategy_name": strategy_meta.name,
                "symbol": request.pair,
                "timeframe": str(request.interval),
                "starting_cash": request.initial_cash,
                "ending_equity": paper_result.ending_equity,
                "status": "completed",
                "summary_json": json.dumps(
                    {
                        "ending_cash": paper_result.ending_cash,
                        "ending_units": paper_result.ending_units,
                        "fills": len(paper_result.fills),
                    },
                    sort_keys=True,
                ),
                "artifacts_json": json.dumps([a.model_dump() for a in artifacts], sort_keys=True),
                "created_at": utc_now_iso(),
            }
            self.store.insert("paper_sessions", session_row)

            summary = {
                "session_id": session_id,
                "ending_equity": paper_result.ending_equity,
            }
            completed_job = mark_job_completed(self.store, job_id=job["id"], summary=summary)
            return self._to_paper_summary(session_row, completed_job)
        except Exception as exc:
            mark_job_failed(self.store, job_id=job["id"], error_message=str(exc))
            raise

    def list_paper_sessions(self) -> list[PaperSessionSummary]:
        """List paper sessions newest-first."""
        rows = self.store.fetch_all("paper_sessions")
        return [self._to_paper_summary(row) for row in rows]

    def get_paper_session(self, session_id: str) -> PaperSessionSummary | None:
        """Fetch one paper session by identifier."""
        row = self.store.fetch_one("paper_sessions", session_id)
        if row is None:
            return None
        return self._to_paper_summary(row)

    def list_ai_runs(self) -> list[AiRunSummary]:
        """List AI workflow runs newest-first."""
        rows = self.store.fetch_all("ai_runs")
        return [self._to_ai_run_summary(row) for row in rows]

    def get_ai_run(self, run_id: str) -> AiRunSummary | None:
        """Fetch one AI workflow run by identifier."""
        row = self.store.fetch_one("ai_runs", run_id)
        if row is None:
            return None
        return self._to_ai_run_summary(row)

    def create_hypothesis(self, request: CreateHypothesisRequest) -> AiRunSummary:
        """Run a synchronous AI hypothesis generation workflow."""
        profile = self._resolve_prompt_profile(
            run_type="hypothesis",
            prompt_profile_id=request.prompt_profile_id,
        )
        input_payload = {
            "research_objective": request.research_objective,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "constraints": request.constraints,
            "prompt_profile_id": profile.id,
        }

        job = create_job(self.store, kind="ai_hypothesis")
        mark_job_running(self.store, job_id=job["id"])
        run_id = uuid4().hex
        self._create_ai_run_row(
            run_id=run_id,
            job_id=job["id"],
            profile=profile,
            run_type="hypothesis",
            input_payload=input_payload,
        )

        try:
            output = self._ai_service_or_raise().generate_hypothesis(
                research_objective=request.research_objective,
                symbol=request.symbol,
                timeframe=request.timeframe,
                constraints=request.constraints,
                model_name=profile.model_name,
                temperature=profile.temperature,
            )
            artifacts = (
                self._persist_hypothesis_artifacts(run_id, output)
                if request.export_artifacts
                else []
            )
            completed_row = self._mark_ai_run_completed(
                run_id=run_id,
                output_payload=output.to_dict(),
            )
            completed_job = mark_job_completed(
                self.store,
                job_id=job["id"],
                summary={"run_id": run_id, "title": output.title},
            )
            return self._to_ai_run_summary(
                completed_row,
                job_row=completed_job,
                artifacts=artifacts,
            )
        except Exception as exc:
            self._mark_ai_run_failed(run_id=run_id, error_message=str(exc))
            mark_job_failed(self.store, job_id=job["id"], error_message=str(exc))
            raise

    def create_strategy_draft(self, request: CreateStrategyDraftRequest) -> AiRunSummary:
        """Run a synchronous AI strategy draft generation workflow."""
        profile = self._resolve_prompt_profile(
            run_type="strategy_draft",
            prompt_profile_id=request.prompt_profile_id,
        )
        source_hypothesis = self._load_hypothesis_for_strategy_draft(request.hypothesis_run_id)
        input_payload = {
            "prompt": request.prompt,
            "hypothesis_run_id": request.hypothesis_run_id,
            "coding_constraints": request.coding_constraints,
            "repo_conventions": request.repo_conventions,
            "prompt_profile_id": profile.id,
            "pair": request.pair,
            "interval": request.interval,
            "fee_rate": request.fee_rate,
            "run_backtest": request.run_backtest,
            "refresh": request.refresh,
        }

        job = create_job(self.store, kind="ai_strategy_draft")
        mark_job_running(self.store, job_id=job["id"])
        run_id = uuid4().hex
        self._create_ai_run_row(
            run_id=run_id,
            job_id=job["id"],
            profile=profile,
            run_type="strategy_draft",
            input_payload=input_payload,
        )

        try:
            output = self._ai_service_or_raise().generate_strategy_draft(
                prompt=request.prompt,
                hypothesis=source_hypothesis,
                coding_constraints=request.coding_constraints,
                repo_conventions=request.repo_conventions,
                model_name=profile.model_name,
                temperature=profile.temperature,
            )
            output_payload = output.to_dict()
            artifacts: list[ArtifactSummary] = []
            if request.export_artifacts:
                artifacts.extend(self._persist_strategy_draft_artifacts(run_id, output))

            if request.run_backtest:
                backtest_plan = self._ai_service_or_raise().generate_backtest_plan(
                    pair=request.pair,
                    interval=request.interval,
                    fee_rate=request.fee_rate,
                    hypothesis=source_hypothesis,
                    strategy_draft=output,
                    model_name=profile.model_name,
                    temperature=profile.temperature,
                )
                backtest_report, backtest_artifacts = self._run_ai_backtest_report(
                    run_id=run_id,
                    pair=request.pair,
                    interval=request.interval,
                    fee_rate=request.fee_rate,
                    refresh=request.refresh,
                    backtest_plan=backtest_plan,
                    export_artifacts=request.export_artifacts,
                )
                output_payload["backtest_report"] = backtest_report.model_dump()
                artifacts.extend(backtest_artifacts)

            completed_row = self._mark_ai_run_completed(
                run_id=run_id,
                output_payload=output_payload,
            )
            summary_payload: dict[str, Any] = {
                "run_id": run_id,
                "draft_summary": output.draft_summary,
            }
            if request.run_backtest and "backtest_report" in output_payload:
                summary_payload["backtest_total_return"] = output_payload["backtest_report"]["summary"][
                    "total_return"
                ]
            completed_job = mark_job_completed(
                self.store,
                job_id=job["id"],
                summary=summary_payload,
            )
            return self._to_ai_run_summary(
                completed_row,
                job_row=completed_job,
                artifacts=artifacts,
            )
        except Exception as exc:
            self._mark_ai_run_failed(run_id=run_id, error_message=str(exc))
            mark_job_failed(self.store, job_id=job["id"], error_message=str(exc))
            raise

    def create_code_report(self, request: CreateCodeReportRequest) -> AiRunSummary:
        """Generate AI code, run it in sandbox, and persist structured report artifacts."""
        profile = self._resolve_prompt_profile(
            run_type="code_report",
            prompt_profile_id=request.prompt_profile_id,
        )
        source_hypothesis = self._load_hypothesis_for_strategy_draft(request.hypothesis_run_id)
        source_strategy_draft = self._load_strategy_draft_for_code_report(request.strategy_draft_run_id)
        input_payload = {
            "research_objective": request.research_objective,
            "pair": request.pair,
            "interval": request.interval,
            "fee_rate": request.fee_rate,
            "constraints": request.constraints,
            "hypothesis_run_id": request.hypothesis_run_id,
            "strategy_draft_run_id": request.strategy_draft_run_id,
            "prompt_profile_id": profile.id,
            "timeout_seconds": request.timeout_seconds,
            "max_repair_attempts": self.config.sandbox_max_repair_attempts,
            "refresh": request.refresh,
        }

        job = create_job(self.store, kind="ai_code_report")
        mark_job_running(self.store, job_id=job["id"])
        run_id = uuid4().hex
        self._create_ai_run_row(
            run_id=run_id,
            job_id=job["id"],
            profile=profile,
            run_type="code_report",
            input_payload=input_payload,
        )

        try:
            code_result = self._ai_service_or_raise().generate_sandbox_code(
                research_objective=request.research_objective,
                pair=request.pair,
                interval=request.interval,
                fee_rate=request.fee_rate,
                constraints=request.constraints,
                hypothesis=source_hypothesis,
                strategy_draft=source_strategy_draft,
                model_name=profile.model_name,
                temperature=profile.temperature,
            )
            report_result, artifacts, final_code_result, repair_trace = self._run_ai_sandbox_code_report(
                run_id=run_id,
                request=request,
                code_result=code_result,
                source_hypothesis=source_hypothesis,
                source_strategy_draft=source_strategy_draft,
                export_artifacts=request.export_artifacts,
            )
            output_payload = {
                "code_generation": final_code_result.to_dict(),
                "initial_code_generation": code_result.to_dict(),
                "repair_trace": repair_trace,
                "code_report": report_result.model_dump(),
            }
            completed_row = self._mark_ai_run_completed(run_id=run_id, output_payload=output_payload)
            completed_job = mark_job_completed(
                self.store,
                job_id=job["id"],
                summary={
                    "run_id": run_id,
                    "title": report_result.title,
                    "execution_success": report_result.execution.success,
                },
            )
            return self._to_ai_run_summary(
                completed_row,
                job_row=completed_job,
                artifacts=artifacts,
            )
        except Exception as exc:
            self._mark_ai_run_failed(run_id=run_id, error_message=str(exc))
            mark_job_failed(self.store, job_id=job["id"], error_message=str(exc))
            raise

    def list_prompt_profiles(self) -> list[PromptProfileSummary]:
        """List configured prompt profiles."""
        rows = self.store.fetch_all("prompt_profiles")
        return [self._to_prompt_profile(row) for row in rows]

    def list_ai_models(self) -> list[AiModelSummary]:
        """List configured AI provider/model combinations for the local workflow."""
        model_names = self._ai_service_or_raise().list_models()
        return [
            AiModelSummary(
                provider=self.config.default_ai_provider,
                model_name=model_name,
                is_default=(model_name == self.config.gemini_model_name),
            )
            for model_name in model_names
        ]

    def list_artifacts(self) -> list[ArtifactSummary]:
        """List all artifacts newest-first."""
        rows = self.store.fetch_all("artifacts")
        return [self._to_artifact(row) for row in rows]

    def get_artifact(self, artifact_id: str) -> ArtifactSummary | None:
        """Fetch one artifact by identifier."""
        row = self.store.fetch_one("artifacts", artifact_id)
        if row is None:
            return None
        return self._to_artifact(row)

    def _ensure_builtin_strategies(self) -> None:
        for strategy in _BUILTIN_STRATEGIES:
            existing = self.store.fetch_one("strategies", strategy["id"])
            if existing is not None:
                continue
            self.store.insert(
                "strategies",
                {
                    **strategy,
                    "created_at": utc_now_iso(),
                },
            )

    def _ensure_prompt_profiles(self) -> None:
        for profile in _DEFAULT_PROMPT_PROFILES:
            existing = self.store.fetch_one("prompt_profiles", profile["id"])
            if existing is not None:
                continue
            self.store.insert(
                "prompt_profiles",
                {
                    **profile,
                    "model_name": self.config.gemini_model_name,
                    "temperature": self.config.gemini_temperature,
                    "created_at": utc_now_iso(),
                },
            )

    def _resolve_prompt_profile(self, *, run_type: str, prompt_profile_id: str | None) -> PromptProfileSummary:
        if prompt_profile_id:
            row = self.store.fetch_one("prompt_profiles", prompt_profile_id)
            if row is None:
                raise ValueError(f"Prompt profile not found: {prompt_profile_id}")
            profile = self._to_prompt_profile(row)
            if profile.run_type != run_type:
                raise ValueError(
                    f"Prompt profile {prompt_profile_id} does not match run_type={run_type}."
                )
            return profile

        rows = self.store.fetch_where(
            "prompt_profiles",
            where="run_type = ? AND provider = ?",
            params=(run_type, self.config.default_ai_provider),
        )
        if not rows:
            raise ValueError(
                f"No prompt profile configured for run_type={run_type} provider={self.config.default_ai_provider}."
            )
        return self._to_prompt_profile(rows[0])

    def _ai_service_or_raise(self) -> AiWorkflowService:
        if self._ai_service is None:
            self._ai_service = create_ai_workflow_service(self.config)
        return self._ai_service

    def _create_ai_run_row(
        self,
        *,
        run_id: str,
        job_id: str,
        profile: PromptProfileSummary,
        run_type: str,
        input_payload: dict[str, Any],
    ) -> dict[str, Any]:
        row = {
            "id": run_id,
            "job_id": job_id,
            "provider": profile.provider,
            "model_name": profile.model_name,
            "run_type": run_type,
            "status": "running",
            "created_at": utc_now_iso(),
            "started_at": utc_now_iso(),
            "finished_at": None,
            "input_json": json.dumps(input_payload, sort_keys=True),
            "output_json": None,
            "error_message": None,
            "prompt_profile_id": profile.id,
        }
        self.store.insert("ai_runs", row)
        return row

    def _mark_ai_run_completed(self, *, run_id: str, output_payload: dict[str, Any]) -> dict[str, Any]:
        self.store.update(
            "ai_runs",
            run_id,
            {
                "status": "completed",
                "finished_at": utc_now_iso(),
                "output_json": json.dumps(output_payload, sort_keys=True),
                "error_message": None,
            },
        )
        row = self.store.fetch_one("ai_runs", run_id)
        if row is None:
            raise ValueError(f"AI run not found: {run_id}")
        return row

    def _mark_ai_run_failed(self, *, run_id: str, error_message: str) -> dict[str, Any]:
        self.store.update(
            "ai_runs",
            run_id,
            {
                "status": "failed",
                "finished_at": utc_now_iso(),
                "error_message": error_message,
            },
        )
        row = self.store.fetch_one("ai_runs", run_id)
        if row is None:
            raise ValueError(f"AI run not found: {run_id}")
        return row

    def _load_hypothesis_for_strategy_draft(self, run_id: str | None) -> AiHypothesisResult | None:
        if not run_id:
            return None
        run = self.get_ai_run(run_id)
        if run is None:
            raise ValueError(f"Hypothesis AI run not found: {run_id}")
        if run.run_type != "hypothesis":
            raise ValueError(f"AI run {run_id} is not a hypothesis run.")
        if run.hypothesis is None:
            raise ValueError(f"Hypothesis output missing for AI run: {run_id}")
        return AiHypothesisResult(
            title=run.hypothesis.title,
            summary=run.hypothesis.summary,
            rationale=run.hypothesis.rationale,
            indicators=list(run.hypothesis.indicators),
            market_assumptions=list(run.hypothesis.market_assumptions),
            risks=list(run.hypothesis.risks),
            validation_steps=list(run.hypothesis.validation_steps),
        )

    def _load_strategy_draft_for_code_report(self, run_id: str | None) -> AiStrategyDraftResult | None:
        if not run_id:
            return None
        run = self.get_ai_run(run_id)
        if run is None:
            raise ValueError(f"Strategy draft AI run not found: {run_id}")
        if run.run_type != "strategy_draft":
            raise ValueError(f"AI run {run_id} is not a strategy draft run.")
        if run.strategy_draft is None:
            raise ValueError(f"Strategy draft output missing for AI run: {run_id}")
        return AiStrategyDraftResult(
            draft_summary=run.strategy_draft.draft_summary,
            code_artifact=run.strategy_draft.code_artifact,
            assumptions=list(run.strategy_draft.assumptions),
            missing_information=list(run.strategy_draft.missing_information),
            suggested_tests=list(run.strategy_draft.suggested_tests),
            notes=run.strategy_draft.notes,
        )

    def _sandbox_runner_or_raise(self) -> DockerSandboxRunner:
        if self._sandbox_runner is None:
            self._sandbox_runner = DockerSandboxRunner(
                DockerSandboxPolicy(
                    docker_bin=self.config.sandbox_docker_bin,
                    image=self.config.sandbox_image,
                    runtime=self.config.sandbox_runtime,
                    memory_limit=self.config.sandbox_memory_limit,
                    cpu_limit=self.config.sandbox_cpu_limit,
                    pids_limit=self.config.sandbox_pids_limit,
                )
            )
        return self._sandbox_runner

    def _run_ai_sandbox_code_report(
        self,
        *,
        run_id: str,
        request: CreateCodeReportRequest,
        code_result: AiSandboxCodeResult,
        source_hypothesis: AiHypothesisResult | None,
        source_strategy_draft: AiStrategyDraftResult | None,
        export_artifacts: bool,
    ) -> tuple[CodeReportResult, list[ArtifactSummary], AiSandboxCodeResult, list[dict[str, Any]]]:
        provider = create_kraken_provider(self.config)
        candles = provider.fetch_ohlc(
            request.pair,
            request.interval,
            use_cache=not request.refresh,
        )
        if candles.empty:
            raise ValueError("No completed candles found for sandbox AI code run.")

        sandbox_dir = self._ai_output_dir(run_id) / "sandbox"
        input_dir = sandbox_dir / "input"
        out_dir = sandbox_dir / "out"
        input_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        spec_path = input_dir / "spec.json"
        data_path = input_dir / "data.parquet"
        code_path = input_dir / "task.py"

        spec_payload = {
            "research_objective": request.research_objective,
            "pair": request.pair,
            "interval": request.interval,
            "fee_rate": request.fee_rate,
            "constraints": request.constraints,
            "strategy_parameters": dict(_DEFAULT_STRATEGY_PARAMETERS),
            "generated_at": utc_now_iso(),
        }
        spec_path.write_text(json.dumps(spec_payload, indent=2, sort_keys=True), encoding="utf-8")
        self._write_input_data_parquet(candles, data_path)

        timeout_seconds = request.timeout_seconds or self.config.sandbox_timeout_seconds
        max_attempts = self.config.sandbox_max_repair_attempts
        sandbox_request = AiSandboxCodeInput(
            research_objective=request.research_objective,
            pair=request.pair,
            interval=request.interval,
            fee_rate=request.fee_rate,
            constraints=request.constraints,
            hypothesis=source_hypothesis,
            strategy_draft=source_strategy_draft,
        )
        repair_trace: list[dict[str, Any]] = []
        attempt_summaries: list[CodeRepairAttemptSummary] = []
        attempt_code_paths: list[Path] = []
        attempt_report_paths: list[Path] = []

        current_code_result = code_result
        last_sandbox_result: SandboxRunResult | None = None
        final_report_payload: dict[str, Any] | None = None

        for attempt in range(1, max_attempts + 1):
            repaired = attempt > 1
            attempt_code_path = input_dir / f"task_attempt_{attempt}.py"
            attempt_code_path.write_text(current_code_result.code_artifact.rstrip() + "\n", encoding="utf-8")
            attempt_code_paths.append(attempt_code_path)
            code_path.write_text(current_code_result.code_artifact.rstrip() + "\n", encoding="utf-8")

            try:
                self._validate_sandbox_code_source(current_code_result.code_artifact)
            except ValueError as exc:
                reason = str(exc)
                attempt_summaries.append(
                    CodeRepairAttemptSummary(
                        attempt=attempt,
                        repaired=repaired,
                        failure_reason=reason,
                        execution=None,
                    )
                )
                repair_trace.append(
                    {
                        "attempt": attempt,
                        "repaired": repaired,
                        "failure_reason": reason,
                    }
                )
                if attempt == max_attempts:
                    raise ValueError(
                        f"Sandbox code failed validation after {attempt} attempt(s): {reason}"
                    ) from exc
                current_code_result = self._ai_service_or_raise().repair_sandbox_code(
                    original_request=sandbox_request,
                    previous_code=current_code_result.code_artifact,
                    failure_reason=reason,
                    previous_stdout=None,
                    previous_stderr=None,
                    previous_report=None,
                )
                continue

            sandbox_result = self._sandbox_runner_or_raise().run(
                SandboxRunRequest(
                    workspace_dir=sandbox_dir,
                    code_path=code_path,
                    timeout_seconds=timeout_seconds,
                )
            )
            last_sandbox_result = sandbox_result
            report_path = out_dir / "report.json"
            report_payload = None
            try:
                report_payload = self._load_sandbox_report(report_path, sandbox_result)
                self._validate_expected_report_fields(
                    report_payload,
                    expected_fields=current_code_result.expected_report_fields,
                )
                if not sandbox_result.success:
                    raise ValueError(
                        "Sandbox process exited with a non-zero status. "
                        f"exit_code={sandbox_result.exit_code}, timed_out={sandbox_result.timed_out}"
                    )
                report_error = report_payload.get("error")
                if isinstance(report_error, str) and report_error.strip():
                    raise ValueError(f"Sandbox report indicates execution error: {report_error.strip()}")
            except ValueError as exc:
                reason = str(exc)
                execution = self._to_code_execution_summary(sandbox_result)
                attempt_summaries.append(
                    CodeRepairAttemptSummary(
                        attempt=attempt,
                        repaired=repaired,
                        failure_reason=reason,
                        execution=execution,
                    )
                )
                attempt_report_path = out_dir / f"report_attempt_{attempt}.json"
                if report_path.exists():
                    attempt_report_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
                    attempt_report_paths.append(attempt_report_path)
                repair_trace.append(
                    {
                        "attempt": attempt,
                        "repaired": repaired,
                        "failure_reason": reason,
                        "execution": execution.model_dump(),
                    }
                )
                if attempt == max_attempts:
                    raise ValueError(
                        f"Sandbox code failed after {attempt} attempt(s): {reason}"
                    ) from exc
                current_code_result = self._ai_service_or_raise().repair_sandbox_code(
                    original_request=sandbox_request,
                    previous_code=current_code_result.code_artifact,
                    failure_reason=reason,
                    previous_stdout=_tail_text(sandbox_result.stdout, max_chars=4000),
                    previous_stderr=_tail_text(sandbox_result.stderr, max_chars=4000),
                    previous_report=report_payload,
                )
                continue

            final_report_payload = report_payload
            attempt_report_path = out_dir / f"report_attempt_{attempt}.json"
            attempt_report_path.write_text(
                json.dumps(report_payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            attempt_report_paths.append(attempt_report_path)
            attempt_summaries.append(
                CodeRepairAttemptSummary(
                    attempt=attempt,
                    repaired=repaired,
                    failure_reason=None,
                    execution=self._to_code_execution_summary(sandbox_result),
                )
            )
            repair_trace.append(
                {
                    "attempt": attempt,
                    "repaired": repaired,
                    "failure_reason": None,
                    "execution": self._to_code_execution_summary(sandbox_result).model_dump(),
                }
            )
            break

        if last_sandbox_result is None or final_report_payload is None:
            raise ValueError("Sandbox code execution did not produce a valid report.")

        code_execution = self._to_code_execution_summary(last_sandbox_result)
        code_report = CodeReportResult(
            title=current_code_result.title,
            summary=current_code_result.summary,
            report=final_report_payload,
            execution=code_execution,
            attempts=attempt_summaries,
            generated_at=utc_now_iso(),
        )
        artifacts = (
            self._persist_code_report_artifacts(
                run_id=run_id,
                code_result=current_code_result,
                code_report=code_report,
                sandbox_result=last_sandbox_result,
                spec_path=spec_path,
                data_path=data_path,
                code_path=code_path,
                report_path=out_dir / "report.json",
                repair_trace=repair_trace,
                attempt_code_paths=attempt_code_paths,
                attempt_report_paths=attempt_report_paths,
            )
            if export_artifacts
            else []
        )
        return code_report, artifacts, current_code_result, repair_trace

    def _write_input_data_parquet(self, candles, data_path: Path) -> None:
        try:
            candles.to_parquet(data_path, index=False)
        except Exception as exc:  # pragma: no cover - branch depends on local parquet engine install
            raise ValueError(
                "Failed to write /input/data.parquet. Ensure a parquet engine (for example pyarrow) is installed."
            ) from exc

    def _load_sandbox_report(
        self,
        report_path: Path,
        sandbox_result: SandboxRunResult,
    ) -> dict[str, Any]:
        if not report_path.exists():
            raise ValueError(
                "Sandbox code did not write /out/report.json. "
                f"exit_code={sandbox_result.exit_code}, timed_out={sandbox_result.timed_out}"
            )
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Sandbox /out/report.json is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Sandbox /out/report.json must contain a JSON object.")
        return payload

    def _validate_sandbox_code_source(self, source: str) -> None:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ValueError(f"Sandbox code has syntax error: {exc.msg}") from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base = alias.name.split(".", 1)[0]
                    if base in _SANDBOX_BANNED_IMPORTS:
                        raise ValueError(f"Sandbox code uses disallowed import: {base}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                base = module.split(".", 1)[0]
                if base in _SANDBOX_BANNED_IMPORTS:
                    raise ValueError(f"Sandbox code uses disallowed import: {base}")
            elif isinstance(node, ast.Call):
                dotted_name = _ast_call_name(node.func)
                if dotted_name in _SANDBOX_BANNED_CALLS:
                    raise ValueError(f"Sandbox code uses disallowed call: {dotted_name}")
                if dotted_name.startswith("subprocess.") or dotted_name.startswith("socket."):
                    raise ValueError(f"Sandbox code uses disallowed call: {dotted_name}")
                if dotted_name.startswith("requests.") or dotted_name.startswith("httpx."):
                    raise ValueError(f"Sandbox code uses disallowed network call: {dotted_name}")
                if dotted_name.startswith("os.") and dotted_name in {
                    "os.system",
                    "os.popen",
                    "os.spawnl",
                    "os.spawnlp",
                    "os.spawnv",
                    "os.spawnvp",
                    "os.startfile",
                }:
                    raise ValueError(f"Sandbox code uses disallowed process call: {dotted_name}")
                if dotted_name == "open" and node.args:
                    literal_path = _literal_string(node.args[0])
                    if literal_path and literal_path.startswith("/") and not (
                        literal_path.startswith("/input/") or literal_path.startswith("/out/")
                    ):
                        raise ValueError(
                            f"Sandbox code references disallowed absolute path: {literal_path}"
                        )

    def _validate_expected_report_fields(
        self,
        report_payload: dict[str, Any],
        *,
        expected_fields: list[str],
    ) -> None:
        missing = [field for field in expected_fields if field not in report_payload]
        if missing:
            raise ValueError(f"Sandbox report missing expected fields: {', '.join(missing)}")

    def _to_code_execution_summary(self, sandbox_result: SandboxRunResult) -> CodeExecutionSummary:
        return CodeExecutionSummary(
            success=sandbox_result.success,
            exit_code=sandbox_result.exit_code,
            timed_out=sandbox_result.timed_out,
            duration_seconds=sandbox_result.duration_seconds,
            stdout_tail=_tail_text(sandbox_result.stdout, max_chars=4000),
            stderr_tail=_tail_text(sandbox_result.stderr, max_chars=4000),
        )

    def _persist_code_report_artifacts(
        self,
        *,
        run_id: str,
        code_result: AiSandboxCodeResult,
        code_report: CodeReportResult,
        sandbox_result: SandboxRunResult,
        spec_path: Path,
        data_path: Path,
        code_path: Path,
        report_path: Path,
        repair_trace: list[dict[str, Any]],
        attempt_code_paths: list[Path],
        attempt_report_paths: list[Path],
    ) -> list[ArtifactSummary]:
        output_dir = self._ai_output_dir(run_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        generation_json = output_dir / "code_generation.json"
        generation_json.write_text(
            json.dumps(code_result.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        summary_json = output_dir / "code_report_summary.json"
        summary_json.write_text(
            json.dumps(code_report.model_dump(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        execution_json = output_dir / "sandbox_execution.json"
        execution_json.write_text(
            json.dumps(
                {
                    "success": sandbox_result.success,
                    "exit_code": sandbox_result.exit_code,
                    "timed_out": sandbox_result.timed_out,
                    "duration_seconds": sandbox_result.duration_seconds,
                    "command": sandbox_result.command,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        stdout_path = output_dir / "sandbox_stdout.log"
        stdout_path.write_text(sandbox_result.stdout, encoding="utf-8")
        stderr_path = output_dir / "sandbox_stderr.log"
        stderr_path.write_text(sandbox_result.stderr, encoding="utf-8")
        attempts_json = output_dir / "sandbox_attempts.json"
        attempts_json.write_text(
            json.dumps(repair_trace, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        artifacts: list[ArtifactSummary] = []
        for kind, path in [
            ("ai_code_generation_json", generation_json),
            ("ai_code_report_summary_json", summary_json),
            ("ai_sandbox_execution_json", execution_json),
            ("ai_sandbox_stdout_log", stdout_path),
            ("ai_sandbox_stderr_log", stderr_path),
            ("ai_sandbox_attempts_json", attempts_json),
            ("ai_sandbox_spec_json", spec_path),
            ("ai_sandbox_data_parquet", data_path),
            ("ai_sandbox_code_py", code_path),
            ("ai_sandbox_report_json", report_path),
        ]:
            artifacts.append(
                self._create_artifact(
                    kind=kind,
                    path=path,
                    owner_type="ai_run",
                    owner_id=run_id,
                )
            )
        for path in attempt_code_paths:
            artifacts.append(
                self._create_artifact(
                    kind="ai_sandbox_attempt_code_py",
                    path=path,
                    owner_type="ai_run",
                    owner_id=run_id,
                )
            )
        for path in attempt_report_paths:
            artifacts.append(
                self._create_artifact(
                    kind="ai_sandbox_attempt_report_json",
                    path=path,
                    owner_type="ai_run",
                    owner_id=run_id,
                )
            )
        return artifacts

    def _persist_hypothesis_artifacts(
        self,
        run_id: str,
        output: AiHypothesisResult,
    ) -> list[ArtifactSummary]:
        output_dir = self._ai_output_dir(run_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "hypothesis.json"
        json_path.write_text(json.dumps(output.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

        markdown_path = output_dir / "hypothesis.md"
        markdown_path.write_text(
            self._render_hypothesis_markdown(output),
            encoding="utf-8",
        )

        return [
            self._create_artifact(
                kind="ai_hypothesis_json",
                path=json_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
            self._create_artifact(
                kind="ai_hypothesis_markdown",
                path=markdown_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
        ]

    def _persist_strategy_draft_artifacts(
        self,
        run_id: str,
        output: AiStrategyDraftResult,
    ) -> list[ArtifactSummary]:
        output_dir = self._ai_output_dir(run_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "strategy_draft.json"
        json_path.write_text(json.dumps(output.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

        markdown_path = output_dir / "strategy_draft.md"
        markdown_path.write_text(
            self._render_strategy_draft_markdown(output),
            encoding="utf-8",
        )

        code_path = output_dir / "strategy_draft.py"
        code_path.write_text(output.code_artifact.rstrip() + "\n", encoding="utf-8")

        return [
            self._create_artifact(
                kind="ai_strategy_draft_json",
                path=json_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
            self._create_artifact(
                kind="ai_strategy_draft_markdown",
                path=markdown_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
            self._create_artifact(
                kind="ai_strategy_draft_code",
                path=code_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
        ]

    def _run_ai_backtest_report(
        self,
        *,
        run_id: str,
        pair: str,
        interval: int,
        fee_rate: float,
        refresh: bool,
        backtest_plan: AiStrategyBacktestPlan,
        export_artifacts: bool,
    ) -> tuple[BacktestReportResult, list[ArtifactSummary]]:
        strategy = self._build_strategy_from_backtest_plan(backtest_plan)
        provider = create_kraken_provider(self.config)
        candles = provider.fetch_ohlc(
            pair,
            interval,
            use_cache=not refresh,
        )
        if candles.empty:
            raise ValueError("No completed candles found for AI backtest report.")

        result = run_strategy_backtest(
            candles,
            strategy,
            fee_rate=fee_rate,
        )
        ending_equity = float(result.equity_curve["equity"].iloc[-1]) if not result.equity_curve.empty else 1.0
        summary_payload = {
            "total_return": result.summary.total_return,
            "annualized_return": result.summary.annualized_return,
            "max_drawdown": result.summary.max_drawdown,
            "trades": result.summary.trades,
            "final_equity": ending_equity,
        }
        report = BacktestReportResult(
            title=f"AI Backtest Report ({backtest_plan.strategy_id})",
            pair=pair,
            timeframe=str(interval),
            fee_rate=fee_rate,
            candles_count=len(candles),
            strategy_id=backtest_plan.strategy_id,
            parameters={
                "short_window": backtest_plan.short_window,
                "long_window": backtest_plan.long_window,
            },
            rationale=backtest_plan.rationale or None,
            assumptions=backtest_plan.assumptions,
            risks=backtest_plan.risks,
            summary=summary_payload,
            generated_at=utc_now_iso(),
        )
        artifacts = (
            self._persist_backtest_report_artifacts(run_id, report, result.equity_curve)
            if export_artifacts
            else []
        )
        return report, artifacts

    def _persist_backtest_report_artifacts(
        self,
        run_id: str,
        report: BacktestReportResult,
        equity_curve,
    ) -> list[ArtifactSummary]:
        output_dir = self._ai_output_dir(run_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "backtest_report.json"
        json_path.write_text(json.dumps(report.model_dump(), indent=2, sort_keys=True), encoding="utf-8")

        markdown_path = output_dir / "backtest_report.md"
        markdown_path.write_text(self._render_backtest_report_markdown(report), encoding="utf-8")

        equity_curve_path = output_dir / "backtest_equity_curve.csv"
        equity_curve.to_csv(equity_curve_path, index=False)

        return [
            self._create_artifact(
                kind="ai_backtest_report_json",
                path=json_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
            self._create_artifact(
                kind="ai_backtest_report_markdown",
                path=markdown_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
            self._create_artifact(
                kind="ai_backtest_equity_curve_csv",
                path=equity_curve_path,
                owner_type="ai_run",
                owner_id=run_id,
            ),
        ]

    def _render_hypothesis_markdown(self, output: AiHypothesisResult) -> str:
        lines = [
            f"# {output.title}",
            "",
            "## Summary",
            output.summary,
            "",
            "## Rationale",
            output.rationale,
            "",
            "## Indicators",
            *[f"- {item}" for item in output.indicators],
            "",
            "## Market Assumptions",
            *[f"- {item}" for item in output.market_assumptions],
            "",
            "## Risks",
            *[f"- {item}" for item in output.risks],
            "",
            "## Validation Steps",
            *[f"- {item}" for item in output.validation_steps],
            "",
        ]
        return "\n".join(lines)

    def _render_strategy_draft_markdown(self, output: AiStrategyDraftResult) -> str:
        lines = [
            "# Strategy Draft",
            "",
            "## Summary",
            output.draft_summary,
            "",
            "## Assumptions",
            *[f"- {item}" for item in output.assumptions],
            "",
            "## Missing Information",
            *[f"- {item}" for item in output.missing_information],
            "",
            "## Suggested Tests",
            *[f"- {item}" for item in output.suggested_tests],
            "",
            "## Notes",
            output.notes or "-",
            "",
            "## Code Artifact",
            "```python",
            output.code_artifact.rstrip(),
            "```",
            "",
        ]
        return "\n".join(lines)

    def _render_backtest_report_markdown(self, report: BacktestReportResult) -> str:
        lines = [
            f"# {report.title}",
            "",
            "## Configuration",
            f"- Pair: {report.pair}",
            f"- Timeframe: {report.timeframe}",
            f"- Fee rate: {report.fee_rate}",
            f"- Strategy: {report.strategy_id}",
            f"- Parameters: {json.dumps(report.parameters, sort_keys=True)}",
            f"- Candle count: {report.candles_count}",
            "",
            "## Summary",
            f"- Total return: {report.summary.get('total_return')}",
            f"- Annualized return: {report.summary.get('annualized_return')}",
            f"- Max drawdown: {report.summary.get('max_drawdown')}",
            f"- Trades: {report.summary.get('trades')}",
            f"- Final equity: {report.summary.get('final_equity')}",
            "",
            "## Rationale",
            report.rationale or "-",
            "",
            "## Assumptions",
            *[f"- {item}" for item in report.assumptions],
            "",
            "## Risks",
            *[f"- {item}" for item in report.risks],
            "",
        ]
        return "\n".join(lines)

    def _ai_output_dir(self, run_id: str) -> Path:
        return self.ai_artifacts_root / run_id

    def _build_strategy(self, request: CreatePaperSessionRequest) -> BuyAndHoldStrategy | SimpleMovingAverageCrossStrategy:
        if request.strategy_id == "buy_and_hold":
            return BuyAndHoldStrategy()
        if request.strategy_id == "sma_cross":
            if request.short_window is None or request.long_window is None:
                raise ValueError("sma_cross requires short_window and long_window.")
            return SimpleMovingAverageCrossStrategy(
                short_window=request.short_window,
                long_window=request.long_window,
            )
        raise ValueError(f"Unsupported strategy_id: {request.strategy_id}")

    def _build_strategy_from_backtest_plan(
        self, plan: AiStrategyBacktestPlan
    ) -> BuyAndHoldStrategy | SimpleMovingAverageCrossStrategy:
        if plan.strategy_id == "buy_and_hold":
            return BuyAndHoldStrategy()
        if plan.strategy_id == "sma_cross":
            if plan.short_window is None or plan.long_window is None:
                raise ValueError("AI backtest plan for sma_cross requires short_window and long_window.")
            return SimpleMovingAverageCrossStrategy(
                short_window=plan.short_window,
                long_window=plan.long_window,
            )
        raise ValueError(f"Unsupported AI backtest plan strategy_id: {plan.strategy_id}")

    def _experiment_output_path(self, run_id: str) -> Path:
        return self.artifacts_root / "experiments" / f"{run_id}_results.csv"

    def _paper_output_dir(self, session_id: str) -> Path:
        return self.artifacts_root / "paper" / session_id

    def _create_artifact(self, *, kind: str, path: Path, owner_type: str, owner_id: str) -> ArtifactSummary:
        artifact_row = {
            "id": uuid4().hex,
            "kind": kind,
            "path": str(path.resolve()),
            "created_at": utc_now_iso(),
            "owner_type": owner_type,
            "owner_id": owner_id,
        }
        self.store.insert("artifacts", artifact_row)
        return self._to_artifact(artifact_row)

    def _to_artifact(self, row: dict[str, Any]) -> ArtifactSummary:
        return ArtifactSummary(
            artifact_id=row["id"],
            kind=row["kind"],
            path=row["path"],
            created_at=row["created_at"],
            owner_type=row["owner_type"],
            owner_id=row["owner_id"],
        )

    def _to_prompt_profile(self, row: dict[str, Any]) -> PromptProfileSummary:
        return PromptProfileSummary(
            id=row["id"],
            template_name=row["template_name"],
            run_type=row["run_type"],
            provider=row["provider"],
            model_name=row["model_name"],
            temperature=float(row["temperature"]) if row.get("temperature") is not None else None,
            created_at=row["created_at"],
            notes=row.get("notes"),
        )

    def _to_job_summary(self, row: dict[str, Any]) -> JobSummary:
        summary_payload = json.loads(row["summary_json"]) if row.get("summary_json") else None
        return JobSummary(
            id=row["id"],
            kind=row["kind"],
            status=row["status"],
            created_at=row["created_at"],
            started_at=row.get("started_at"),
            finished_at=row.get("finished_at"),
            error_message=row.get("error_message"),
            summary=summary_payload,
        )

    def _to_ai_run_summary(
        self,
        row: dict[str, Any],
        *,
        job_row: dict[str, Any] | None = None,
        artifacts: list[ArtifactSummary] | None = None,
    ) -> AiRunSummary:
        if job_row is None:
            job_row = self.store.fetch_one("jobs", row["job_id"])
        if job_row is None:
            raise ValueError(f"Missing job for AI run: {row['id']}")

        input_payload = json.loads(row["input_json"])
        output_payload = json.loads(row["output_json"]) if row.get("output_json") else None
        backtest_report_payload = (
            output_payload.get("backtest_report")
            if isinstance(output_payload, dict)
            else None
        )
        code_report_payload = (
            output_payload.get("code_report")
            if isinstance(output_payload, dict)
            else None
        )
        hypothesis = (
            HypothesisResult(**output_payload)
            if row["run_type"] == "hypothesis" and output_payload is not None
            else None
        )
        strategy_draft = (
            StrategyDraftResultPayload(**output_payload)
            if row["run_type"] == "strategy_draft" and output_payload is not None
            else None
        )
        backtest_report = (
            BacktestReportResult(**backtest_report_payload)
            if isinstance(backtest_report_payload, dict)
            else None
        )
        code_report = (
            CodeReportResult(**code_report_payload)
            if isinstance(code_report_payload, dict)
            else None
        )
        run_artifacts = artifacts if artifacts is not None else self._list_artifacts_for_owner("ai_run", row["id"])

        return AiRunSummary(
            id=row["id"],
            job_id=row["job_id"],
            provider=row["provider"],
            model_name=row["model_name"],
            run_type=row["run_type"],
            status=row["status"],
            created_at=row["created_at"],
            started_at=row.get("started_at"),
            finished_at=row.get("finished_at"),
            error_message=row.get("error_message"),
            input=input_payload,
            output=output_payload,
            hypothesis=hypothesis,
            strategy_draft=strategy_draft,
            backtest_report=backtest_report,
            code_report=code_report,
            artifacts=run_artifacts,
            job=self._to_job_summary(job_row),
        )

    def _to_experiment_summary(
        self,
        row: dict[str, Any],
        job_row: dict[str, Any] | None = None,
    ) -> ExperimentRunSummary:
        if job_row is None:
            job_row = self.store.fetch_one("jobs", row["job_id"])
        if job_row is None:
            raise ValueError(f"Missing job for experiment run: {row['id']}")

        best_result = (
            ExperimentResultSummary(**json.loads(row["best_result_json"]))
            if row.get("best_result_json")
            else None
        )
        artifacts = self._load_artifacts_from_json(row.get("artifacts_json"))
        return ExperimentRunSummary(
            id=row["id"],
            job_id=row["job_id"],
            strategy_name=row["strategy_name"],
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            result_count=int(row["result_count"]),
            best_result=best_result,
            artifacts=artifacts,
            created_at=row["created_at"],
            job=self._to_job_summary(job_row),
        )

    def _to_paper_summary(
        self,
        row: dict[str, Any],
        job_row: dict[str, Any] | None = None,
    ) -> PaperSessionSummary:
        if row.get("job_id") and job_row is None:
            job_row = self.store.fetch_one("jobs", row["job_id"])

        summary_payload = json.loads(row["summary_json"]) if row.get("summary_json") else None
        artifacts = self._load_artifacts_from_json(row.get("artifacts_json"))
        return PaperSessionSummary(
            id=row["id"],
            job_id=row.get("job_id"),
            strategy_name=row["strategy_name"],
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            starting_cash=float(row["starting_cash"]),
            ending_equity=float(row["ending_equity"]) if row.get("ending_equity") is not None else None,
            status=row["status"],
            summary=summary_payload,
            artifacts=artifacts,
            created_at=row["created_at"],
            job=self._to_job_summary(job_row) if job_row else None,
        )

    def _load_artifacts_from_json(self, payload: str | None) -> list[ArtifactSummary]:
        if not payload:
            return []
        rows = json.loads(payload)
        return [ArtifactSummary(**row) for row in rows]

    def _list_artifacts_for_owner(self, owner_type: str, owner_id: str) -> list[ArtifactSummary]:
        rows = self.store.fetch_where(
            "artifacts",
            where="owner_type = ? AND owner_id = ?",
            params=(owner_type, owner_id),
        )
        return [self._to_artifact(row) for row in rows]


def _tail_text(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def _ast_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

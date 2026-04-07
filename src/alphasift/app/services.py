from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from alphasift import __version__
from alphasift.app.db import MetadataStore
from alphasift.app.jobs import (
    create_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
    utc_now_iso,
)
from alphasift.app.schemas import (
    ArtifactSummary,
    CreatePaperSessionRequest,
    CreateSmaExperimentRequest,
    ExperimentResultSummary,
    ExperimentRunSummary,
    JobSummary,
    PaperSessionSummary,
    StrategySummary,
    SystemInfoResponse,
)
from alphasift.config import Config
from alphasift.data.loaders import create_kraken_provider
from alphasift.experiments.export import export_experiment_results_to_csv
from alphasift.experiments.runner import run_sma_cross_experiments
from alphasift.paper.engine import run_paper_trader
from alphasift.paper.export import export_paper_trading_result_to_csv
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy
from alphasift.strategies.sma_cross import SimpleMovingAverageCrossStrategy


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


class AppServices:
    """Thin application-facing wrappers over existing research modules."""

    def __init__(self, config: Config, store: MetadataStore) -> None:
        self.config = config
        self.store = store
        self.artifacts_root = config.artifacts_dir
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self._ensure_builtin_strategies()

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

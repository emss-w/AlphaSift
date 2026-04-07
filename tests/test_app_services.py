from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphasift.ai.models import HypothesisResult as AiHypothesisResult
from alphasift.ai.models import SandboxCodeResult as AiSandboxCodeResult
from alphasift.ai.models import StrategyBacktestPlan as AiStrategyBacktestPlan
from alphasift.ai.models import StrategyDraftResult as AiStrategyDraftResult
from alphasift.app.db import MetadataStore
from alphasift.app.schemas import (
    CreateCodeReportRequest,
    CreateHypothesisRequest,
    CreatePaperSessionRequest,
    CreateSmaExperimentRequest,
    CreateStrategyDraftRequest,
)
from alphasift.app.services import AppServices
from alphasift.config import Config
from tests._temp_app import cleanup_workspace_temp_dir, make_workspace_temp_dir


class _StubProvider:
    def __init__(self, candles: pd.DataFrame) -> None:
        self._candles = candles

    def fetch_ohlc(self, pair: str, interval: int, *, use_cache: bool = True) -> pd.DataFrame:
        return self._candles.copy()


class _StubAiWorkflowService:
    def generate_hypothesis(
        self,
        *,
        research_objective: str,
        symbol: str | None = None,
        timeframe: str | None = None,
        constraints: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> AiHypothesisResult:
        _ = (research_objective, symbol, timeframe, constraints, model_name, temperature)
        return AiHypothesisResult(
            title="Momentum continuation",
            summary="Continuation after pullback.",
            rationale="Short trend pullbacks can mean-revert back into trend.",
            indicators=["sma_20", "sma_50", "rsi"],
            market_assumptions=["trend persistence"],
            risks=["chop", "false breakout"],
            validation_steps=["backtest on BTC/USD 60m"],
        )

    def generate_strategy_draft(
        self,
        *,
        prompt: str | None = None,
        hypothesis: AiHypothesisResult | None = None,
        coding_constraints: str | None = None,
        repo_conventions: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> AiStrategyDraftResult:
        _ = (
            prompt,
            hypothesis,
            coding_constraints,
            repo_conventions,
            model_name,
            temperature,
        )
        return AiStrategyDraftResult(
            draft_summary="SMA confirmation draft",
            code_artifact=(
                "from __future__ import annotations\n\n"
                "class DraftStrategy:\n"
                "    \"\"\"Draft strategy artifact.\"\"\"\n\n"
                "    pass\n"
            ),
            assumptions=["normalized candles are sorted"],
            missing_information=["execution assumptions"],
            suggested_tests=["test lookahead behavior"],
            notes="Draft only. Manual review required.",
        )

    def list_models(self) -> list[str]:
        return ["gemini-test"]

    def generate_backtest_plan(
        self,
        *,
        pair: str,
        interval: int,
        fee_rate: float = 0.0,
        hypothesis: AiHypothesisResult | None = None,
        strategy_draft: AiStrategyDraftResult | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> AiStrategyBacktestPlan:
        _ = (
            pair,
            interval,
            fee_rate,
            hypothesis,
            strategy_draft,
            model_name,
            temperature,
        )
        return AiStrategyBacktestPlan(
            strategy_id="sma_cross",
            short_window=2,
            long_window=4,
            rationale="Simple trend confirmation.",
            assumptions=["enough lookback"],
            risks=["whipsaw"],
        )

    def generate_sandbox_code(
        self,
        *,
        research_objective: str,
        pair: str,
        interval: int,
        fee_rate: float = 0.0,
        constraints: str | None = None,
        hypothesis: AiHypothesisResult | None = None,
        strategy_draft: AiStrategyDraftResult | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> AiSandboxCodeResult:
        _ = (
            research_objective,
            pair,
            interval,
            fee_rate,
            constraints,
            hypothesis,
            strategy_draft,
            model_name,
            temperature,
        )
        return AiSandboxCodeResult(
            title="Sandbox Candle Count",
            summary="Counts candles and writes report.",
            code_artifact=(
                "import json\n"
                "from pathlib import Path\n"
                "import pandas as pd\n\n"
                "spec = json.loads(Path('/input/spec.json').read_text(encoding='utf-8'))\n"
                "candles = pd.read_parquet('/input/data.parquet')\n"
                "report = {'rows': int(len(candles)), 'pair': spec.get('pair')}\n"
                "Path('/out/report.json').write_text(json.dumps(report), encoding='utf-8')\n"
            ),
            expected_report_fields=["rows", "pair"],
            assumptions=["parquet available"],
            safety_notes=["no network"],
        )

    def repair_sandbox_code(
        self,
        *,
        original_request,
        previous_code: str,
        failure_reason: str,
        previous_stdout: str | None = None,
        previous_stderr: str | None = None,
        previous_report: dict | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> AiSandboxCodeResult:
        _ = (
            original_request,
            previous_code,
            failure_reason,
            previous_stdout,
            previous_stderr,
            previous_report,
            model_name,
            temperature,
        )
        return AiSandboxCodeResult(
            title="Sandbox Candle Count (Repaired)",
            summary="Counts candles and writes report with explicit error field.",
            code_artifact=(
                "import json\n"
                "from pathlib import Path\n"
                "import pandas as pd\n\n"
                "spec = json.loads(Path('/input/spec.json').read_text(encoding='utf-8'))\n"
                "candles = pd.read_parquet('/input/data.parquet')\n"
                "report = {'rows': int(len(candles)), 'pair': spec.get('pair'), 'error': None}\n"
                "Path('/out/report.json').write_text(json.dumps(report), encoding='utf-8')\n"
            ),
            expected_report_fields=["rows", "pair", "error"],
            assumptions=["parquet available"],
            safety_notes=["no network"],
        )


class _FailingAiWorkflowService(_StubAiWorkflowService):
    def generate_hypothesis(self, **kwargs) -> AiHypothesisResult:  # type: ignore[override]
        raise RuntimeError("provider failed")


class _StubSandboxRunner:
    def run(self, request):
        out_path = request.workspace_dir / "out" / "report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text('{"rows": 6, "pair": "BTC/USD"}', encoding="utf-8")

        class _Result:
            success = True
            exit_code = 0
            timed_out = False
            duration_seconds = 0.25
            stdout = "ok"
            stderr = ""
            command = ["docker", "run"]

        return _Result()


class _RepairSandboxRunner:
    def run(self, request):
        code = request.code_path.read_text(encoding="utf-8")
        out_path = request.workspace_dir / "out" / "report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if "ATTEMPT_ONE" in code:
            out_path.write_text(
                '{"rows": 0, "pair": "BTC/USD", "error": "Critical error during execution: bad params"}',
                encoding="utf-8",
            )
        else:
            out_path.write_text(
                '{"rows": 6, "pair": "BTC/USD", "error": null}',
                encoding="utf-8",
            )

        class _Result:
            success = True
            exit_code = 0
            timed_out = False
            duration_seconds = 0.2
            stdout = "ok"
            stderr = ""
            command = ["docker", "run"]

        return _Result()


class _NeedsRepairAiWorkflowService(_StubAiWorkflowService):
    def __init__(self) -> None:
        self.repair_calls = 0

    def generate_sandbox_code(self, **kwargs) -> AiSandboxCodeResult:  # type: ignore[override]
        _ = kwargs
        return AiSandboxCodeResult(
            title="Sandbox Candle Count",
            summary="First draft has a runtime issue.",
            code_artifact="ATTEMPT_ONE = True\nprint('draft')\n",
            expected_report_fields=["rows", "pair", "error"],
            assumptions=[],
            safety_notes=[],
        )

    def repair_sandbox_code(self, **kwargs) -> AiSandboxCodeResult:  # type: ignore[override]
        _ = kwargs
        self.repair_calls += 1
        return AiSandboxCodeResult(
            title="Sandbox Candle Count (Repaired)",
            summary="Repaired draft.",
            code_artifact="ATTEMPT_TWO = True\nprint('repaired')\n",
            expected_report_fields=["rows", "pair", "error"],
            assumptions=[],
            safety_notes=[],
        )


class _UnsafeNeedsRepairAiWorkflowService(_StubAiWorkflowService):
    def __init__(self) -> None:
        self.repair_calls = 0

    def generate_sandbox_code(self, **kwargs) -> AiSandboxCodeResult:  # type: ignore[override]
        _ = kwargs
        return AiSandboxCodeResult(
            title="Unsafe First Draft",
            summary="Contains disallowed subprocess import.",
            code_artifact="import subprocess\nATTEMPT_ONE = True\n",
            expected_report_fields=["rows", "pair", "error"],
            assumptions=[],
            safety_notes=[],
        )

    def repair_sandbox_code(self, **kwargs) -> AiSandboxCodeResult:  # type: ignore[override]
        _ = kwargs
        self.repair_calls += 1
        return AiSandboxCodeResult(
            title="Safe Repaired Draft",
            summary="Safe code after validation failure.",
            code_artifact="ATTEMPT_TWO = True\nprint('repaired')\n",
            expected_report_fields=["rows", "pair", "error"],
            assumptions=[],
            safety_notes=[],
        )


def _make_candles() -> pd.DataFrame:
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    return pd.DataFrame(
        {
            "timestamp": [1, 2, 3, 4, 5, 6],
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
            "trades": [1] * len(closes),
            "vwap": closes,
        }
    )


def _make_config(temp_dir: Path) -> Config:
    data_dir = temp_dir / "data"
    return Config(
        kraken_api_key=None,
        kraken_api_secret=None,
        kraken_base_url="https://api.kraken.com",
        gemini_api_key="test-gemini-key",
        gemini_base_url="https://generativelanguage.googleapis.com/v1beta",
        gemini_model_name="gemini-test",
        gemini_temperature=0.1,
        gemini_timeout_seconds=10.0,
        default_ai_provider="gemini",
        sandbox_docker_bin="docker",
        sandbox_image="python:3.11-slim",
        sandbox_runtime="runsc",
        sandbox_timeout_seconds=30,
        sandbox_memory_limit="512m",
        sandbox_cpu_limit="1.0",
        sandbox_pids_limit=128,
        sandbox_max_repair_attempts=2,
        default_data_dir=data_dir,
        app_db_path=temp_dir / "app" / "metadata.sqlite3",
        artifacts_dir=temp_dir / "artifacts",
        ai_artifacts_dir=temp_dir / "artifacts" / "ai",
        api_host="127.0.0.1",
        api_port=8000,
    )


def test_list_strategies_returns_builtins():
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        services = AppServices(config, MetadataStore(config.app_db_path))

        strategies = services.list_strategies()

        ids = {item.id for item in strategies}
        assert "buy_and_hold" in ids
        assert "sma_cross" in ids
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_run_sma_experiment_creates_persisted_metadata(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        services = AppServices(config, MetadataStore(config.app_db_path))

        result = services.run_sma_experiment(
            CreateSmaExperimentRequest(
                pair="BTC/USD",
                interval=60,
                short_windows=[2],
                long_windows=[4],
            )
        )

        assert result.result_count == 1
        assert result.job.status == "completed"
        assert services.get_experiment_run(result.id) is not None
        jobs = services.list_jobs()
        assert any(job.id == result.job_id for job in jobs)
        job = services.get_job(result.job_id)
        assert job is not None
        assert job.status == "completed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_start_paper_session_creates_persisted_metadata(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        services = AppServices(config, MetadataStore(config.app_db_path))

        result = services.start_paper_session(
            CreatePaperSessionRequest(
                pair="BTC/USD",
                interval=60,
                strategy_id="buy_and_hold",
                initial_cash=1_000.0,
            )
        )

        assert result.status == "completed"
        assert result.job is not None
        assert result.job.status == "completed"
        assert services.get_paper_session(result.id) is not None
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_invalid_inputs_fail_clearly():
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        services = AppServices(config, MetadataStore(config.app_db_path))

        with pytest.raises(ValueError, match="Unknown strategy_id"):
            services.start_paper_session(
                CreatePaperSessionRequest(
                    pair="BTC/USD",
                    interval=60,
                    strategy_id="missing",
                )
            )
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_create_hypothesis_persists_run_and_artifacts(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        services = AppServices(config, MetadataStore(config.app_db_path))

        run = services.create_hypothesis(
            CreateHypothesisRequest(
                research_objective="Find pullback continuation setup",
                symbol="BTC/USD",
                timeframe="60",
                constraints="Avoid high fee assumptions",
            )
        )

        assert run.run_type == "hypothesis"
        assert run.status == "completed"
        assert run.job.status == "completed"
        assert run.hypothesis is not None
        assert run.hypothesis.title == "Momentum continuation"
        assert len(run.artifacts) >= 2
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_create_strategy_draft_from_hypothesis(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        services = AppServices(config, MetadataStore(config.app_db_path))
        hypothesis = services.create_hypothesis(
            CreateHypothesisRequest(
                research_objective="Look for trend continuation",
                symbol="BTC/USD",
                timeframe="60",
            )
        )

        draft = services.create_strategy_draft(
            CreateStrategyDraftRequest(
                prompt=None,
                hypothesis_run_id=hypothesis.id,
                coding_constraints="Keep code simple and typed.",
                repo_conventions="Provider-agnostic strategy interface.",
            )
        )

        assert draft.run_type == "strategy_draft"
        assert draft.strategy_draft is not None
        assert draft.strategy_draft.draft_summary == "SMA confirmation draft"
        assert draft.backtest_report is not None
        assert draft.backtest_report.strategy_id == "sma_cross"
        assert any(artifact.kind == "ai_strategy_draft_code" for artifact in draft.artifacts)
        assert any(artifact.kind == "ai_backtest_report_json" for artifact in draft.artifacts)
        fetched = services.get_ai_run(draft.id)
        assert fetched is not None
        assert fetched.job.status == "completed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_ai_provider_failure_marks_job_failed(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _FailingAiWorkflowService(),
        )
        services = AppServices(config, MetadataStore(config.app_db_path))

        with pytest.raises(RuntimeError, match="provider failed"):
            services.create_hypothesis(
                CreateHypothesisRequest(
                    research_objective="Failing call",
                )
            )

        runs = services.list_ai_runs()
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert runs[0].job.status == "failed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_create_code_report_runs_sandbox_and_persists_report(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        services = AppServices(config, MetadataStore(config.app_db_path))
        monkeypatch.setattr(services, "_sandbox_runner_or_raise", lambda: _StubSandboxRunner())
        monkeypatch.setattr(
            services,
            "_write_input_data_parquet",
            lambda candles_df, path: path.write_text("stub-parquet", encoding="utf-8"),
        )

        run = services.create_code_report(
            CreateCodeReportRequest(
                research_objective="Count candles and summarize pair.",
                pair="BTC/USD",
                interval=60,
                fee_rate=0.001,
            )
        )

        assert run.run_type == "code_report"
        assert run.code_report is not None
        assert run.code_report.report["rows"] == 6
        assert run.code_report.execution.success is True
        assert any(artifact.kind == "ai_sandbox_report_json" for artifact in run.artifacts)
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_create_code_report_repairs_failed_attempt(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        candles = _make_candles()
        ai_stub = _NeedsRepairAiWorkflowService()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: ai_stub,
        )
        services = AppServices(config, MetadataStore(config.app_db_path))
        monkeypatch.setattr(services, "_sandbox_runner_or_raise", lambda: _RepairSandboxRunner())
        monkeypatch.setattr(
            services,
            "_write_input_data_parquet",
            lambda candles_df, path: path.write_text("stub-parquet", encoding="utf-8"),
        )

        run = services.create_code_report(
            CreateCodeReportRequest(
                research_objective="Count candles and summarize pair.",
                pair="BTC/USD",
                interval=60,
                fee_rate=0.001,
            )
        )

        assert run.run_type == "code_report"
        assert run.code_report is not None
        assert run.code_report.report["error"] is None
        assert len(run.code_report.attempts) == 2
        assert run.code_report.attempts[0].failure_reason is not None
        assert run.code_report.attempts[1].failure_reason is None
        assert ai_stub.repair_calls == 1
        assert any(artifact.kind == "ai_sandbox_attempts_json" for artifact in run.artifacts)
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_create_code_report_repairs_disallowed_code_before_execution(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        config = _make_config(temp_dir)
        candles = _make_candles()
        ai_stub = _UnsafeNeedsRepairAiWorkflowService()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: ai_stub,
        )
        services = AppServices(config, MetadataStore(config.app_db_path))
        monkeypatch.setattr(services, "_sandbox_runner_or_raise", lambda: _RepairSandboxRunner())
        monkeypatch.setattr(
            services,
            "_write_input_data_parquet",
            lambda candles_df, path: path.write_text("stub-parquet", encoding="utf-8"),
        )

        run = services.create_code_report(
            CreateCodeReportRequest(
                research_objective="Count candles and summarize pair.",
                pair="BTC/USD",
                interval=60,
                fee_rate=0.001,
            )
        )

        assert run.code_report is not None
        assert len(run.code_report.attempts) == 2
        assert "disallowed import" in (run.code_report.attempts[0].failure_reason or "")
        assert run.code_report.attempts[0].execution is None
        assert run.code_report.attempts[1].execution is not None
        assert ai_stub.repair_calls == 1
    finally:
        cleanup_workspace_temp_dir(temp_dir)

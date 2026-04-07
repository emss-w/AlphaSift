from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from alphasift.ai.models import HypothesisResult as AiHypothesisResult
from alphasift.ai.models import SandboxCodeResult as AiSandboxCodeResult
from alphasift.ai.models import StrategyBacktestPlan as AiStrategyBacktestPlan
from alphasift.ai.models import StrategyDraftResult as AiStrategyDraftResult
from alphasift.app.api import create_app
from alphasift.config import Config
from tests._temp_app import cleanup_workspace_temp_dir, make_workspace_temp_dir


class _StubProvider:
    def __init__(self, candles: pd.DataFrame) -> None:
        self._candles = candles

    def fetch_ohlc(self, pair: str, interval: int, *, use_cache: bool = True) -> pd.DataFrame:
        return self._candles.copy()


class _StubAiWorkflowService:
    def generate_hypothesis(self, **kwargs) -> AiHypothesisResult:
        _ = kwargs
        return AiHypothesisResult(
            title="Breakout continuation",
            summary="Look for continuation after consolidation breakout.",
            rationale="Strong breakouts can continue in momentum regimes.",
            indicators=["sma", "volume"],
            market_assumptions=["momentum"],
            risks=["fake breakout"],
            validation_steps=["backtest on 1h candles"],
        )

    def generate_strategy_draft(self, **kwargs) -> AiStrategyDraftResult:
        _ = kwargs
        return AiStrategyDraftResult(
            draft_summary="Breakout strategy draft",
            code_artifact="class BreakoutDraft:\n    pass",
            assumptions=["sorted normalized candles"],
            missing_information=["execution model"],
            suggested_tests=["test next-bar fill model"],
            notes="Draft only",
        )

    def list_models(self) -> list[str]:
        return ["gemini-test"]

    def generate_backtest_plan(self, **kwargs) -> AiStrategyBacktestPlan:
        _ = kwargs
        return AiStrategyBacktestPlan(
            strategy_id="sma_cross",
            short_window=2,
            long_window=4,
            rationale="Trend confirmation",
            assumptions=["enough history"],
            risks=["whipsaw"],
        )

    def generate_sandbox_code(self, **kwargs) -> AiSandboxCodeResult:
        _ = kwargs
        return AiSandboxCodeResult(
            title="Sandbox Candle Counter",
            summary="Counts rows from parquet and returns pair.",
            code_artifact=(
                "import json\n"
                "from pathlib import Path\n"
                "import pandas as pd\n\n"
                "spec = json.loads(Path('/input/spec.json').read_text(encoding='utf-8'))\n"
                "candles = pd.read_parquet('/input/data.parquet')\n"
                "Path('/out/report.json').write_text(json.dumps({'rows': int(len(candles)), 'pair': spec.get('pair')}), encoding='utf-8')\n"
            ),
            expected_report_fields=["rows", "pair"],
            assumptions=["parquet reader available"],
            safety_notes=["offline only"],
        )

    def repair_sandbox_code(self, **kwargs) -> AiSandboxCodeResult:
        _ = kwargs
        return AiSandboxCodeResult(
            title="Sandbox Candle Counter (Repaired)",
            summary="Counts rows from parquet and returns pair.",
            code_artifact=(
                "import json\n"
                "from pathlib import Path\n"
                "import pandas as pd\n\n"
                "spec = json.loads(Path('/input/spec.json').read_text(encoding='utf-8'))\n"
                "candles = pd.read_parquet('/input/data.parquet')\n"
                "Path('/out/report.json').write_text(json.dumps({'rows': int(len(candles)), 'pair': spec.get('pair'), 'error': None}), encoding='utf-8')\n"
            ),
            expected_report_fields=["rows", "pair", "error"],
            assumptions=["parquet reader available"],
            safety_notes=["offline only"],
        )


class _StubSandboxRunner:
    def run(self, request):
        report_path = request.workspace_dir / "out" / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('{"rows": 6, "pair": "BTC/USD"}', encoding="utf-8")

        class _Result:
            success = True
            exit_code = 0
            timed_out = False
            duration_seconds = 0.2
            stdout = "ok"
            stderr = ""
            command = ["docker", "run"]

        return _Result()


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


def test_health_endpoint_returns_success(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_health_endpoint_allows_local_frontend_cors_preflight(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_strategies_endpoint_returns_structured_data(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        response = client.get("/strategies")

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert {item["id"] for item in payload} >= {"buy_and_hold", "sma_cross"}
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_experiment_creation_and_detail_endpoints(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        create_response = client.post(
            "/experiments/sma-cross",
            json={
                "pair": "BTC/USD",
                "interval": 60,
                "short_windows": [2],
                "long_windows": [4],
            },
        )
        assert create_response.status_code == 200
        run = create_response.json()

        detail_response = client.get(f"/experiments/{run['id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["id"] == run["id"]
        assert detail["job"]["status"] == "completed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_paper_session_creation_and_detail_endpoints(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        create_response = client.post(
            "/paper/sessions",
            json={
                "pair": "BTC/USD",
                "interval": 60,
                "strategy_id": "buy_and_hold",
                "initial_cash": 1000.0,
            },
        )
        assert create_response.status_code == 200
        session = create_response.json()

        detail_response = client.get(f"/paper/sessions/{session['id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["id"] == session["id"]
        assert detail["job"]["status"] == "completed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_jobs_endpoints_return_job_records(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        create_response = client.post(
            "/experiments/sma-cross",
            json={
                "pair": "BTC/USD",
                "interval": 60,
                "short_windows": [2],
                "long_windows": [4],
            },
        )
        assert create_response.status_code == 200
        run = create_response.json()

        list_response = client.get("/jobs")
        assert list_response.status_code == 200
        jobs = list_response.json()
        assert isinstance(jobs, list)
        assert len(jobs) >= 1
        assert any(job["id"] == run["job_id"] for job in jobs)

        detail_response = client.get(f"/jobs/{run['job_id']}")
        assert detail_response.status_code == 200
        job = detail_response.json()
        assert job["id"] == run["job_id"]
        assert job["status"] == "completed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_ai_hypothesis_creation_and_detail_endpoints(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        create_response = client.post(
            "/ai/hypotheses",
            json={
                "research_objective": "Find momentum breakout setup",
                "symbol": "BTC/USD",
                "timeframe": "60",
            },
        )
        assert create_response.status_code == 200
        run = create_response.json()
        assert run["run_type"] == "hypothesis"
        assert run["job"]["status"] == "completed"
        assert run["hypothesis"]["title"] == "Breakout continuation"

        detail_response = client.get(f"/ai/runs/{run['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == run["id"]
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_ai_strategy_draft_creation_and_listing_endpoints(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        hypothesis_response = client.post(
            "/ai/hypotheses",
            json={
                "research_objective": "Generate hypothesis for strategy draft",
                "symbol": "BTC/USD",
                "timeframe": "60",
            },
        )
        assert hypothesis_response.status_code == 200
        hypothesis_run = hypothesis_response.json()

        draft_response = client.post(
            "/ai/strategy-drafts",
            json={
                "hypothesis_run_id": hypothesis_run["id"],
                "coding_constraints": "Keep deterministic behavior.",
                "pair": "BTC/USD",
                "interval": 60,
                "fee_rate": 0.001,
            },
        )
        assert draft_response.status_code == 200
        draft_run = draft_response.json()
        assert draft_run["run_type"] == "strategy_draft"
        assert draft_run["strategy_draft"]["draft_summary"] == "Breakout strategy draft"
        assert draft_run["backtest_report"]["strategy_id"] == "sma_cross"
        assert draft_run["backtest_report"]["summary"]["trades"] >= 0

        list_response = client.get("/ai/runs")
        assert list_response.status_code == 200
        rows = list_response.json()
        assert any(row["id"] == draft_run["id"] for row in rows)
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_ai_models_and_prompt_profiles_endpoints(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        app = create_app(_make_config(temp_dir))
        client = TestClient(app)

        models_response = client.get("/ai/models")
        assert models_response.status_code == 200
        models = models_response.json()
        assert models[0]["provider"] == "gemini"
        assert models[0]["model_name"] == "gemini-test"

        profiles_response = client.get("/ai/prompt-profiles")
        assert profiles_response.status_code == 200
        profiles = profiles_response.json()
        assert len(profiles) >= 2
        assert {profile["run_type"] for profile in profiles} >= {"hypothesis", "strategy_draft"}
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_ai_code_report_endpoint(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        candles = _make_candles()
        monkeypatch.setattr(
            "alphasift.app.services.create_kraken_provider",
            lambda cfg: _StubProvider(candles),
        )
        monkeypatch.setattr(
            "alphasift.app.services.create_ai_workflow_service",
            lambda cfg: _StubAiWorkflowService(),
        )
        app = create_app(_make_config(temp_dir))
        app.state.services._sandbox_runner = _StubSandboxRunner()
        monkeypatch.setattr(
            app.state.services,
            "_write_input_data_parquet",
            lambda candles_df, path: path.write_text("stub-parquet", encoding="utf-8"),
        )
        client = TestClient(app)

        response = client.post(
            "/ai/code-reports",
            json={
                "research_objective": "Count candles and return pair",
                "pair": "BTC/USD",
                "interval": 60,
                "fee_rate": 0.001,
            },
        )
        assert response.status_code == 200
        run = response.json()
        assert run["run_type"] == "code_report"
        assert run["code_report"]["report"]["rows"] == 6
        assert run["code_report"]["execution"]["success"] is True
    finally:
        cleanup_workspace_temp_dir(temp_dir)

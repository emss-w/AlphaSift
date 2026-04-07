from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from alphasift.app.api import create_app
from alphasift.config import Config
from tests._temp_app import cleanup_workspace_temp_dir, make_workspace_temp_dir


class _StubProvider:
    def __init__(self, candles: pd.DataFrame) -> None:
        self._candles = candles

    def fetch_ohlc(self, pair: str, interval: int, *, use_cache: bool = True) -> pd.DataFrame:
        return self._candles.copy()


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
        default_data_dir=data_dir,
        app_db_path=temp_dir / "app" / "metadata.sqlite3",
        artifacts_dir=temp_dir / "artifacts",
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

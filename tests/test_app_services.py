from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphasift.app.db import MetadataStore
from alphasift.app.schemas import CreatePaperSessionRequest, CreateSmaExperimentRequest
from alphasift.app.services import AppServices
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

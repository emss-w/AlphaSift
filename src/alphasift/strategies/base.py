from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import pandas as pd


REQUIRED_COLUMNS = {"timestamp"}


class Strategy(Protocol):
    """Minimal strategy interface."""

    def generate_positions(self, candles: pd.DataFrame) -> pd.Series:
        """Return target-position series aligned to candles."""


@dataclass(frozen=True)
class StrategyResult:
    target_positions: pd.Series


def validate_candles(candles: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(candles.columns)
    if missing:
        raise ValueError(f"Missing required candle columns: {sorted(missing)}")
    timestamps = candles["timestamp"]
    if timestamps.empty:
        return
    if not timestamps.is_monotonic_increasing or not timestamps.is_unique:
        raise ValueError("Candles must be sorted ascending by unique timestamp.")


def run_strategy_backtest(
    candles: pd.DataFrame,
    strategy: Strategy,
    *,
    initial_equity: float = 1.0,
    fee_rate: float = 0.0,
) -> "BacktestResult":
    from alphasift.backtest.engine import run_backtest

    positions = strategy.generate_positions(candles)
    return run_backtest(
        candles,
        positions,
        initial_equity=initial_equity,
        fee_rate=fee_rate,
    )

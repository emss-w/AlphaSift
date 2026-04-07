from __future__ import annotations

from typing import Iterable
import pandas as pd

from alphasift.backtest.metrics import (
    annualized_return,
    max_drawdown,
    total_return,
    trade_count,
)
from alphasift.backtest.models import BacktestResult, BacktestSummary
from alphasift.data.models import OHLCV_COLUMNS


REQUIRED_COLUMNS = {"timestamp", "close"}


def run_backtest(
    candles: pd.DataFrame,
    target_positions: pd.Series | pd.DataFrame | Iterable[float],
    *,
    initial_equity: float = 1.0,
    fee_rate: float = 0.0,
) -> BacktestResult:
    """Run a minimal long/flat backtest using close-to-close returns."""
    _validate_candles(candles)
    if candles.empty:
        empty_curve = pd.DataFrame(
            columns=["timestamp", "close", "position", "return", "equity"]
        )
        summary = BacktestSummary(
            total_return=0.0,
            annualized_return=None,
            max_drawdown=0.0,
            trades=0,
        )
        return BacktestResult(equity_curve=empty_curve, summary=summary)

    positions = _coerce_target_positions(candles, target_positions)
    _validate_positions(positions)

    closes = candles["close"].astype(float).reset_index(drop=True)
    timestamps = candles["timestamp"].astype(int).reset_index(drop=True)

    close_returns = closes.pct_change().fillna(0.0)
    applied_positions = positions.shift(1).fillna(0.0)

    equity = []
    prev_equity = float(initial_equity)
    for idx in range(len(candles)):
        if idx == 0:
            fee = fee_rate * abs(positions.iloc[0] - 0.0)
            prev_equity = prev_equity * (1.0 - fee)
            equity.append(prev_equity)
            continue

        gross_return = applied_positions.iloc[idx] * close_returns.iloc[idx]
        prev_equity = prev_equity * (1.0 + gross_return)

        fee = fee_rate * abs(positions.iloc[idx] - positions.iloc[idx - 1])
        prev_equity = prev_equity * (1.0 - fee)
        equity.append(prev_equity)

    equity_series = pd.Series(equity, name="equity")
    net_returns = equity_series.pct_change().fillna(0.0)

    curve = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close": closes,
            "position": applied_positions.astype(float),
            "return": net_returns.astype(float),
            "equity": equity_series.astype(float),
        }
    )

    summary = BacktestSummary(
        total_return=total_return(equity_series),
        annualized_return=annualized_return(equity_series, timestamps),
        max_drawdown=max_drawdown(equity_series),
        trades=trade_count(positions),
    )
    return BacktestResult(equity_curve=curve, summary=summary)


def _validate_candles(candles: pd.DataFrame) -> None:
    missing = set(OHLCV_COLUMNS) - set(candles.columns)
    if missing:
        raise ValueError(f"Missing required candle columns: {sorted(missing)}")
    if not REQUIRED_COLUMNS.issubset(candles.columns):
        raise ValueError("Candles must include timestamp and close columns.")
    timestamps = candles["timestamp"]
    if timestamps.empty:
        return
    if not timestamps.is_monotonic_increasing or not timestamps.is_unique:
        raise ValueError("Candles must be sorted ascending by unique timestamp.")


def _coerce_target_positions(
    candles: pd.DataFrame, target_positions: pd.Series | pd.DataFrame | Iterable[float]
) -> pd.Series:
    timestamps = candles["timestamp"].reset_index(drop=True)

    if isinstance(target_positions, pd.DataFrame):
        required = {"timestamp", "target_position"}
        if not required.issubset(target_positions.columns):
            raise ValueError("Target position DataFrame must have timestamp and target_position columns.")
        series = (
            target_positions[["timestamp", "target_position"]]
            .set_index("timestamp")["target_position"]
            .reindex(timestamps)
        )
        if series.isna().any():
            raise ValueError("Target position timestamps do not align with candles.")
        return series.reset_index(drop=True)

    if isinstance(target_positions, pd.Series):
        series = target_positions.copy()
        if series.index.equals(timestamps):
            series = series.reindex(timestamps)
        elif len(series) == len(candles):
            series = series.reset_index(drop=True)
        else:
            raise ValueError("Target positions length does not match candles.")
        return series

    series = pd.Series(list(target_positions))
    if len(series) != len(candles):
        raise ValueError("Target positions length does not match candles.")
    return series.reset_index(drop=True)


def _validate_positions(positions: pd.Series) -> None:
    if positions.empty:
        return
    invalid = positions.dropna().unique()
    allowed = {0.0, 1.0, 0, 1}
    if not set(invalid).issubset(allowed):
        raise ValueError("Target positions must be 0.0 or 1.0 for long/flat mode.")

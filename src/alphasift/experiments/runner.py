from __future__ import annotations

from typing import Iterable, Optional
import pandas as pd

from alphasift.backtest.engine import run_backtest
from alphasift.experiments.models import ExperimentResult, ExperimentRun
from alphasift.strategies.sma_cross import SimpleMovingAverageCrossStrategy
from alphasift.strategies.base import validate_candles


_RANKABLE_FIELDS = {"total_return", "annualized_return", "max_drawdown", "trades"}


def run_sma_cross_experiments(
    candles: pd.DataFrame,
    short_windows: Iterable[int],
    long_windows: Iterable[int],
    *,
    sort_by: str = "total_return",
    initial_equity: float = 1.0,
    fee_rate: float = 0.0,
) -> ExperimentRun:
    """Run a parameter sweep for SimpleMovingAverageCrossStrategy."""
    validate_candles(candles, {"timestamp", "close"})
    _validate_sort_key(sort_by)

    short_list = list(short_windows)
    long_list = list(long_windows)
    if not short_list or not long_list:
        raise ValueError("Parameter grids must be non-empty.")

    results: list[ExperimentResult] = []
    skipped: list[dict[str, int]] = []

    for short_window in short_list:
        for long_window in long_list:
            params = {"short_window": short_window, "long_window": long_window}
            if not _valid_sma_params(short_window, long_window):
                skipped.append(params)
                continue

            strategy = SimpleMovingAverageCrossStrategy(
                short_window=short_window,
                long_window=long_window,
            )
            positions = strategy.generate_positions(candles)
            backtest = run_backtest(
                candles,
                positions,
                initial_equity=initial_equity,
                fee_rate=fee_rate,
            )
            equity = backtest.equity_curve["equity"]
            final_equity = float(equity.iloc[-1]) if not equity.empty else float(initial_equity)
            results.append(
                ExperimentResult(
                    strategy="SimpleMovingAverageCrossStrategy",
                    parameters=params,
                    total_return=backtest.summary.total_return,
                    annualized_return=backtest.summary.annualized_return,
                    max_drawdown=backtest.summary.max_drawdown,
                    trades=backtest.summary.trades,
                    final_equity=final_equity,
                )
            )

    if not results:
        raise ValueError("No valid parameter combinations to run.")

    results = _sort_results(results, sort_by=sort_by)
    return ExperimentRun(results=results, skipped_parameters=skipped)


def _valid_sma_params(short_window: int, long_window: int) -> bool:
    return short_window > 0 and long_window > 0 and short_window < long_window


def _validate_sort_key(sort_by: str) -> None:
    if sort_by not in _RANKABLE_FIELDS:
        raise ValueError(f"sort_by must be one of {_RANKABLE_FIELDS}.")


def _sort_results(
    results: list[ExperimentResult], *, sort_by: str
) -> list[ExperimentResult]:
    if sort_by == "max_drawdown":
        return sorted(results, key=lambda r: r.max_drawdown)

    def key(result: ExperimentResult) -> float:
        if sort_by == "annualized_return":
            return result.annualized_return if result.annualized_return is not None else float("-inf")
        if sort_by == "trades":
            return float(result.trades)
        return float(result.total_return)

    return sorted(results, key=key, reverse=True)

import pandas as pd
import pytest

from alphasift.experiments.runner import run_sma_cross_experiments


def _make_candles(timestamps, closes):
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
            "trades": [1] * len(closes),
            "vwap": closes,
        }
    )


def test_runs_valid_parameters():
    candles = _make_candles([1, 2, 3, 4, 5], [1.0, 2.0, 3.0, 4.0, 5.0])
    experiment = run_sma_cross_experiments(candles, [2], [4])
    assert len(experiment.results) == 1
    result = experiment.results[0]
    assert result.strategy == "SimpleMovingAverageCrossStrategy"
    assert result.parameters == {"short_window": 2, "long_window": 4}


def test_invalid_parameters_skipped():
    candles = _make_candles([1, 2, 3, 4], [1.0, 2.0, 3.0, 4.0])
    experiment = run_sma_cross_experiments(candles, [2, 4], [3])
    assert experiment.skipped_parameters == [{"short_window": 4, "long_window": 3}]
    assert len(experiment.results) == 1


def test_results_sorted_by_total_return():
    candles = _make_candles([1, 2, 3, 4, 5, 6], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    experiment = run_sma_cross_experiments(candles, [2, 3], [4, 5])
    totals = [r.total_return for r in experiment.results]
    assert totals == sorted(totals, reverse=True)


def test_empty_parameter_grid():
    candles = _make_candles([1, 2], [1.0, 2.0])
    with pytest.raises(ValueError, match="Parameter grids must be non-empty"):
        run_sma_cross_experiments(candles, [], [3])

import pandas as pd
import pytest

from alphasift.backtest.engine import run_backtest


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


def test_equity_curve_and_lookahead():
    candles = _make_candles(
        [1, 2, 3, 4],
        [100.0, 110.0, 100.0, 120.0],
    )
    target = pd.Series([0.0, 1.0, 1.0, 0.0])
    result = run_backtest(candles, target)
    curve = result.equity_curve

    assert curve["position"].tolist() == [0.0, 0.0, 1.0, 1.0]
    assert pytest.approx(curve["equity"].iloc[-1], rel=1e-6) == 1.0909090909
    assert result.summary.trades == 2


def test_max_drawdown():
    candles = _make_candles(
        [1, 2, 3, 4],
        [100.0, 110.0, 100.0, 120.0],
    )
    target = pd.Series([0.0, 1.0, 1.0, 0.0])
    result = run_backtest(candles, target)
    assert pytest.approx(result.summary.max_drawdown, rel=1e-6) == 0.0909090909


def test_validation_missing_columns():
    candles = pd.DataFrame({"timestamp": [1, 2], "open": [1, 2]})
    with pytest.raises(ValueError, match="Missing required candle columns"):
        run_backtest(candles, pd.Series([0.0, 1.0]))


def test_validation_unsorted_timestamps():
    candles = _make_candles(
        [2, 1],
        [100.0, 101.0],
    )
    with pytest.raises(ValueError, match="sorted ascending"):
        run_backtest(candles, pd.Series([0.0, 1.0]))


def test_empty_input():
    candles = _make_candles([], [])
    result = run_backtest(candles, pd.Series([], dtype=float))
    assert result.equity_curve.empty
    assert result.summary.total_return == 0.0

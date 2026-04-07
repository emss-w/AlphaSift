import pandas as pd

from alphasift.backtest.engine import run_backtest
from alphasift.strategies.base import run_strategy_backtest
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy
from alphasift.strategies.sma_cross import SimpleMovingAverageCrossStrategy


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


def test_strategy_backtest_integration():
    candles = _make_candles([1, 2, 3, 4], [100.0, 105.0, 110.0, 108.0])
    strategy = BuyAndHoldStrategy()
    result = run_strategy_backtest(candles, strategy)
    assert result.equity_curve["position"].iloc[0] == 0.0
    assert result.summary.trades == 1


def test_no_lookahead_integration():
    candles = _make_candles([1, 2, 3, 4], [100.0, 90.0, 110.0, 100.0])
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=3)
    positions = strategy.generate_positions(candles)
    result = run_backtest(candles, positions)
    assert result.equity_curve["position"].iloc[0] == 0.0


def test_trend_behavior():
    candles = _make_candles([1, 2, 3, 4, 5], [1.0, 2.0, 3.0, 4.0, 5.0])
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=3)
    positions = strategy.generate_positions(candles)
    assert positions.tolist()[-2:] == [1.0, 1.0]

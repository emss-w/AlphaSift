import pandas as pd
import pytest

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


def test_buy_and_hold_positions():
    candles = _make_candles([1, 2, 3], [100.0, 101.0, 102.0])
    strategy = BuyAndHoldStrategy()
    positions = strategy.generate_positions(candles)
    assert positions.tolist() == [0.0, 1.0, 1.0]


def test_sma_cross_positions():
    candles = _make_candles([1, 2, 3, 4, 5], [1.0, 2.0, 3.0, 4.0, 3.0])
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=3)
    positions = strategy.generate_positions(candles)
    assert positions.tolist() == [0.0, 0.0, 1.0, 1.0, 1.0]


def test_sma_cross_warmup():
    candles = _make_candles([1, 2, 3, 4], [1.0, 2.0, 3.0, 4.0])
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=4)
    positions = strategy.generate_positions(candles)
    assert positions.tolist()[:3] == [0.0, 0.0, 0.0]
    assert positions.tolist()[3] == 1.0


def test_missing_columns_validation():
    candles = pd.DataFrame({"timestamp": [1, 2], "open": [1.0, 2.0]})
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=3)
    with pytest.raises(ValueError, match="Missing required candle columns"):
        strategy.generate_positions(candles)


def test_invalid_sma_parameters():
    with pytest.raises(ValueError, match="short_window must be > 0"):
        SimpleMovingAverageCrossStrategy(short_window=0, long_window=3)
    with pytest.raises(ValueError, match="long_window must be > 0"):
        SimpleMovingAverageCrossStrategy(short_window=2, long_window=0)
    with pytest.raises(ValueError, match="short_window must be < long_window"):
        SimpleMovingAverageCrossStrategy(short_window=3, long_window=3)

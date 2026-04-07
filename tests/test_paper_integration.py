import pandas as pd

from alphasift.paper.engine import run_paper_trader
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


def test_buy_and_hold_integration_with_paper_engine():
    candles = _make_candles([1, 2, 3, 4], [100.0, 110.0, 120.0, 130.0])
    result = run_paper_trader(candles, BuyAndHoldStrategy(), initial_cash=1_000.0)

    assert len(result.fills) == 1
    assert result.fills[0].side == "buy"
    assert result.fills[0].timestamp == 3
    assert result.ending_units > 0.0


def test_synthetic_trend_sma_cross_produces_sensible_long_flat_fills():
    candles = _make_candles([1, 2, 3, 4, 5, 6], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=3)
    result = run_paper_trader(candles, strategy, initial_cash=1_000.0)

    assert len(result.fills) == 1
    assert result.fills[0].side == "buy"
    assert result.ending_equity >= result.initial_cash


def test_deterministic_for_deterministic_input():
    candles = _make_candles([1, 2, 3, 4, 5], [10.0, 11.0, 12.0, 11.0, 13.0])
    strategy = SimpleMovingAverageCrossStrategy(short_window=2, long_window=3)
    run_a = run_paper_trader(candles, strategy, initial_cash=1_000.0)
    run_b = run_paper_trader(candles, strategy, initial_cash=1_000.0)

    assert run_a.ending_equity == run_b.ending_equity
    assert [(f.side, f.timestamp, f.fill_price) for f in run_a.fills] == [
        (f.side, f.timestamp, f.fill_price) for f in run_b.fills
    ]

import pandas as pd
import pytest

from alphasift.paper.engine import run_paper_trader


def _make_candles(timestamps, opens, closes=None):
    final_closes = closes if closes is not None else opens
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": opens,
            "low": opens,
            "close": final_closes,
            "volume": [1.0] * len(opens),
            "trades": [1] * len(opens),
            "vwap": final_closes,
        }
    )


class _FixedStrategy:
    def __init__(self, positions):
        self.positions = positions

    def generate_positions(self, candles: pd.DataFrame) -> pd.Series:
        return pd.Series(self.positions, dtype=float)


def test_buy_signal_enters_on_next_completed_bar_open():
    candles = _make_candles([1, 2, 3], [100.0, 105.0, 110.0])
    strategy = _FixedStrategy([0.0, 1.0, 1.0])
    result = run_paper_trader(candles, strategy, initial_cash=1_000.0)

    assert len(result.fills) == 1
    fill = result.fills[0]
    assert fill.side == "buy"
    assert fill.timestamp == 3
    assert fill.fill_price == 110.0


def test_sell_signal_exits_on_next_completed_bar_open():
    candles = _make_candles([1, 2, 3, 4], [100.0, 105.0, 110.0, 90.0])
    strategy = _FixedStrategy([0.0, 1.0, 0.0, 0.0])
    result = run_paper_trader(candles, strategy, initial_cash=1_000.0)

    assert len(result.fills) == 2
    assert result.fills[0].side == "buy"
    assert result.fills[0].timestamp == 3
    assert result.fills[1].side == "sell"
    assert result.fills[1].timestamp == 4


def test_unchanged_target_has_no_extra_fills():
    candles = _make_candles([1, 2, 3, 4, 5], [100.0, 101.0, 102.0, 103.0, 104.0])
    strategy = _FixedStrategy([0.0, 1.0, 1.0, 1.0, 1.0])
    result = run_paper_trader(candles, strategy, initial_cash=1_000.0)
    assert len(result.fills) == 1


def test_account_cash_units_equity_update_correctly():
    candles = _make_candles([1, 2, 3, 4], [100.0, 105.0, 120.0, 130.0])
    strategy = _FixedStrategy([0.0, 1.0, 0.0, 0.0])
    result = run_paper_trader(candles, strategy, initial_cash=1_000.0)

    assert len(result.fills) == 2
    assert pytest.approx(result.fills[0].quantity, rel=1e-9) == 1000.0 / 120.0
    assert pytest.approx(result.ending_cash, rel=1e-9) == (1000.0 / 120.0) * 130.0
    assert result.ending_units == 0.0
    assert pytest.approx(result.ending_equity, rel=1e-9) == result.ending_cash


def test_insufficient_cash_behavior_is_safe_and_explicit():
    candles = _make_candles([1, 2, 3], [100.0, 105.0, 110.0])
    strategy = _FixedStrategy([0.0, 1.0, 1.0])
    result = run_paper_trader(candles, strategy, initial_cash=0.0)

    assert len(result.fills) == 0
    assert result.ending_cash == 0.0
    assert result.ending_units == 0.0
    assert result.ending_equity == 0.0


def test_validation_missing_required_columns():
    candles = pd.DataFrame({"timestamp": [1, 2], "open": [1.0, 2.0]})
    strategy = _FixedStrategy([0.0, 1.0])
    with pytest.raises(ValueError, match="Missing required candle columns"):
        run_paper_trader(candles, strategy)


def test_validation_unsorted_timestamps():
    candles = _make_candles([2, 1], [100.0, 101.0])
    strategy = _FixedStrategy([0.0, 1.0])
    with pytest.raises(ValueError, match="sorted ascending"):
        run_paper_trader(candles, strategy)


def test_duplicate_timestamps_fail_validation():
    candles = _make_candles([1, 1, 2], [100.0, 101.0, 102.0])
    strategy = _FixedStrategy([0.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="unique timestamp"):
        run_paper_trader(candles, strategy)


def test_no_lookahead_bias_first_fill_after_signal_bar():
    candles = _make_candles([1, 2, 3], [100.0, 200.0, 50.0])
    strategy = _FixedStrategy([0.0, 1.0, 1.0])
    result = run_paper_trader(candles, strategy, initial_cash=1_000.0)

    assert len(result.fills) == 1
    assert result.fills[0].timestamp == 3
    assert result.account_history["target_position"].tolist() == [0.0, 0.0, 1.0]

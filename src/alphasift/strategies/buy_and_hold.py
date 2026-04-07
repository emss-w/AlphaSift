from __future__ import annotations

import pandas as pd

from alphasift.strategies.base import StrategyResult, validate_candles


class BuyAndHoldStrategy:
    """Enter long after the first bar and hold."""

    def generate_positions(self, candles: pd.DataFrame) -> pd.Series:
        validate_candles(candles, {"timestamp"})
        if candles.empty:
            return pd.Series([], dtype=float)
        positions = pd.Series([1.0] * len(candles), dtype=float)
        positions.iloc[0] = 0.0
        return positions


def buy_and_hold(candles: pd.DataFrame) -> StrategyResult:
    """Convenience helper for buy-and-hold positions."""
    strategy = BuyAndHoldStrategy()
    return StrategyResult(target_positions=strategy.generate_positions(candles))

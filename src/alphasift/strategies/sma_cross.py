from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from alphasift.strategies.base import StrategyResult, validate_candles


@dataclass(frozen=True)
class SimpleMovingAverageCrossStrategy:
    short_window: int
    long_window: int

    def __post_init__(self) -> None:
        if self.short_window <= 0:
            raise ValueError("short_window must be > 0")
        if self.long_window <= 0:
            raise ValueError("long_window must be > 0")
        if self.short_window >= self.long_window:
            raise ValueError("short_window must be < long_window")

    def generate_positions(self, candles: pd.DataFrame) -> pd.Series:
        validate_candles(candles, {"timestamp", "close"})
        if candles.empty:
            return pd.Series([], dtype=float)

        closes = candles["close"].astype(float).reset_index(drop=True)
        short_sma = closes.rolling(self.short_window, min_periods=self.short_window).mean()
        long_sma = closes.rolling(self.long_window, min_periods=self.long_window).mean()
        signal = (short_sma > long_sma).astype(float)
        signal = signal.fillna(0.0)
        return signal.reset_index(drop=True)


def sma_cross(
    candles: pd.DataFrame, short_window: int, long_window: int
) -> StrategyResult:
    """Convenience helper for SMA cross positions."""
    strategy = SimpleMovingAverageCrossStrategy(short_window, long_window)
    return StrategyResult(target_positions=strategy.generate_positions(candles))

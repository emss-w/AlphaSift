from alphasift.strategies.base import Strategy, StrategyResult, run_strategy_backtest
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy, buy_and_hold
from alphasift.strategies.sma_cross import (
    SimpleMovingAverageCrossStrategy,
    sma_cross,
)

__all__ = [
    "Strategy",
    "StrategyResult",
    "run_strategy_backtest",
    "BuyAndHoldStrategy",
    "buy_and_hold",
    "SimpleMovingAverageCrossStrategy",
    "sma_cross",
]

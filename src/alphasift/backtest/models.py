from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass(frozen=True)
class BacktestSummary:
    total_return: float
    annualized_return: Optional[float]
    max_drawdown: float
    trades: int


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    summary: BacktestSummary

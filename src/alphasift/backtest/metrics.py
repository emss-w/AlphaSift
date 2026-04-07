from __future__ import annotations

from typing import Optional
import math
import pandas as pd


def total_return(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    start = equity.iloc[0]
    end = equity.iloc[-1]
    if start == 0:
        return 0.0
    return float(end / start - 1.0)


def annualized_return(equity: pd.Series, timestamps: pd.Series) -> Optional[float]:
    if equity.empty or len(equity) < 2:
        return None
    start_ts = int(timestamps.iloc[0])
    end_ts = int(timestamps.iloc[-1])
    if end_ts <= start_ts:
        return None
    years = (end_ts - start_ts) / (365.25 * 24 * 60 * 60)
    if years <= 0:
        return None
    start = equity.iloc[0]
    end = equity.iloc[-1]
    if start <= 0:
        return None
    log_return = math.log(end / start)
    rate = log_return / years
    if rate > 700:
        return None
    return float(math.exp(rate) - 1.0)


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdowns = equity / running_max - 1.0
    min_drawdown = float(drawdowns.min())
    return abs(min_drawdown)


def trade_count(target_positions: pd.Series) -> int:
    if target_positions.empty or len(target_positions) < 2:
        return 0
    changes = target_positions.diff().fillna(0.0).abs()
    return int((changes > 0).sum())

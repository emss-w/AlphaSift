from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExperimentResult:
    strategy: str
    parameters: dict[str, int]
    total_return: float
    annualized_return: Optional[float]
    max_drawdown: float
    trades: int
    final_equity: float


@dataclass(frozen=True)
class ExperimentRun:
    results: list[ExperimentResult]
    skipped_parameters: list[dict[str, int]]

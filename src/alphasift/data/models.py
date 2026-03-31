from __future__ import annotations

from dataclasses import dataclass

OHLCV_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trades",
    "vwap",
]


@dataclass(frozen=True)
class OHLCRequest:
    pair: str
    interval: int

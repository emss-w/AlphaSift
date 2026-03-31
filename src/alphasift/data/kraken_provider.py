from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path
import pandas as pd

from alphasift.data.base import OHLCProvider
from alphasift.data.cache import DataCache
from alphasift.data.kraken_client import KrakenClient
from alphasift.data.models import OHLCV_COLUMNS


class KrakenOHLCProvider(OHLCProvider):
    def __init__(self, client: KrakenClient, cache_dir: Path) -> None:
        self.client = client
        self.cache = DataCache(cache_dir)

    def fetch_ohlc(
        self,
        pair: str,
        interval: int,
        *,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        if use_cache:
            cached = self.cache.load("kraken", pair, interval)
            if cached is not None and not cached.empty:
                return cached
        data = self.client.get_ohlc(pair, interval)
        df = self._normalize_ohlc_response(pair, data)
        self.cache.save("kraken", pair, interval, df)
        return df

    def _normalize_ohlc_response(
        self,
        pair: str,
        payload: Dict[str, Any],
    ) -> pd.DataFrame:
        result = payload.get("result", {})
        if not result:
            return pd.DataFrame(columns=OHLCV_COLUMNS)
        key = next((k for k in result.keys() if k != "last"), None)
        if key is None:
            return pd.DataFrame(columns=OHLCV_COLUMNS)
        rows: List[List[Any]] = result.get(key, [])
        df = pd.DataFrame(
            rows,
            columns=["timestamp", "open", "high", "low", "close", "vwap", "volume", "trades"],
        )
        if df.empty:
            return pd.DataFrame(columns=OHLCV_COLUMNS)
        df["timestamp"] = df["timestamp"].astype(int)
        for col in ["open", "high", "low", "close", "vwap", "volume"]:
            df[col] = df[col].astype(float)
        df["trades"] = df["trades"].astype(int)
        df = df[["timestamp", "open", "high", "low", "close", "volume", "trades", "vwap"]]
        df = df.drop_duplicates(subset=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        if len(df) > 0:
            df = df.iloc[:-1].reset_index(drop=True)
        return df

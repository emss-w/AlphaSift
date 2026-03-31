from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd


class OHLCProvider(ABC):
    @abstractmethod
    def fetch_ohlc(
        self,
        pair: str,
        interval: int,
        *,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        raise NotImplementedError

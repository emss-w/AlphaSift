from __future__ import annotations

from pathlib import Path
import pandas as pd

from alphasift.utils.io import ensure_dir


class DataCache:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        ensure_dir(self.base_dir)

    def _key_path(self, provider: str, pair: str, interval: int) -> Path:
        safe_pair = pair.replace("/", "-")
        filename = f"{provider}_{safe_pair}_{interval}.csv"
        return self.base_dir / filename

    def load(
        self,
        provider: str,
        pair: str,
        interval: int,
    ) -> pd.DataFrame | None:
        path = self._key_path(provider, pair, interval)
        if not path.exists():
            return None
        return pd.read_csv(path)

    def save(
        self,
        provider: str,
        pair: str,
        interval: int,
        df: pd.DataFrame,
    ) -> Path:
        path = self._key_path(provider, pair, interval)
        ensure_dir(path.parent)
        df.to_csv(path, index=False)
        return path

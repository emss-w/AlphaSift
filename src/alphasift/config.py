from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Config:
    kraken_api_key: Optional[str]
    kraken_api_secret: Optional[str]
    kraken_base_url: str
    default_data_dir: Path


def load_config() -> Config:
    load_dotenv()
    base_url = os.getenv("KRAKEN_BASE_URL", "https://api.kraken.com")
    data_dir = Path(os.getenv("DEFAULT_DATA_DIR", "./data")).resolve()
    return Config(
        kraken_api_key=os.getenv("KRAKEN_API_KEY"),
        kraken_api_secret=os.getenv("KRAKEN_API_SECRET"),
        kraken_base_url=base_url,
        default_data_dir=data_dir,
    )

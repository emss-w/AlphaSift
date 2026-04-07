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
    app_db_path: Path
    artifacts_dir: Path
    api_host: str
    api_port: int

    @classmethod
    def load(cls) -> "Config":
        """Load config from environment variables."""
        return load_config()


def load_config() -> Config:
    load_dotenv()
    base_url = os.getenv("KRAKEN_BASE_URL", "https://api.kraken.com")
    data_dir = Path(os.getenv("DEFAULT_DATA_DIR", "./data")).resolve()
    app_db_path = Path(
        os.getenv("APP_DB_PATH", str(data_dir / "app" / "metadata.sqlite3"))
    ).resolve()
    artifacts_dir = Path(
        os.getenv("ARTIFACTS_DIR", str(data_dir / "artifacts"))
    ).resolve()
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    return Config(
        kraken_api_key=os.getenv("KRAKEN_API_KEY"),
        kraken_api_secret=os.getenv("KRAKEN_API_SECRET"),
        kraken_base_url=base_url,
        default_data_dir=data_dir,
        app_db_path=app_db_path,
        artifacts_dir=artifacts_dir,
        api_host=api_host,
        api_port=api_port,
    )

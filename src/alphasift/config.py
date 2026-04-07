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
    gemini_api_key: Optional[str]
    gemini_base_url: str
    gemini_model_name: str
    gemini_temperature: float
    gemini_timeout_seconds: float
    default_ai_provider: str
    sandbox_docker_bin: str
    sandbox_image: str
    sandbox_runtime: str
    sandbox_timeout_seconds: int
    sandbox_memory_limit: str
    sandbox_cpu_limit: str
    sandbox_pids_limit: int
    sandbox_max_repair_attempts: int
    default_data_dir: Path
    app_db_path: Path
    artifacts_dir: Path
    ai_artifacts_dir: Path
    api_host: str
    api_port: int

    @classmethod
    def load(cls) -> "Config":
        """Load config from environment variables."""
        return load_config()


def load_config() -> Config:
    load_dotenv()
    base_url = os.getenv("KRAKEN_BASE_URL", "https://api.kraken.com")
    gemini_base_url = os.getenv(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    )
    gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    gemini_temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    gemini_timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
    default_ai_provider = os.getenv("DEFAULT_AI_PROVIDER", "gemini")
    sandbox_docker_bin = os.getenv("SANDBOX_DOCKER_BIN", "docker")
    sandbox_image = os.getenv("SANDBOX_IMAGE", "alphasift-sandbox:latest")
    sandbox_runtime = os.getenv("SANDBOX_RUNTIME", "runsc")
    sandbox_timeout_seconds = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120"))
    sandbox_memory_limit = os.getenv("SANDBOX_MEMORY_LIMIT", "1024m")
    sandbox_cpu_limit = os.getenv("SANDBOX_CPU_LIMIT", "1.0")
    sandbox_pids_limit = int(os.getenv("SANDBOX_PIDS_LIMIT", "128"))
    sandbox_max_repair_attempts = int(os.getenv("SANDBOX_MAX_REPAIR_ATTEMPTS", "2"))
    data_dir = Path(os.getenv("DEFAULT_DATA_DIR", "./data")).resolve()
    app_db_path = Path(
        os.getenv("APP_DB_PATH", str(data_dir / "app" / "metadata.sqlite3"))
    ).resolve()
    artifacts_dir = Path(
        os.getenv("ARTIFACTS_DIR", str(data_dir / "artifacts"))
    ).resolve()
    ai_artifacts_dir = Path(
        os.getenv("AI_ARTIFACTS_DIR", str(artifacts_dir / "ai"))
    ).resolve()
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    return Config(
        kraken_api_key=os.getenv("KRAKEN_API_KEY"),
        kraken_api_secret=os.getenv("KRAKEN_API_SECRET"),
        kraken_base_url=base_url,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_base_url=gemini_base_url,
        gemini_model_name=gemini_model_name,
        gemini_temperature=gemini_temperature,
        gemini_timeout_seconds=gemini_timeout_seconds,
        default_ai_provider=default_ai_provider,
        sandbox_docker_bin=sandbox_docker_bin,
        sandbox_image=sandbox_image,
        sandbox_runtime=sandbox_runtime,
        sandbox_timeout_seconds=sandbox_timeout_seconds,
        sandbox_memory_limit=sandbox_memory_limit,
        sandbox_cpu_limit=sandbox_cpu_limit,
        sandbox_pids_limit=sandbox_pids_limit,
        sandbox_max_repair_attempts=max(1, sandbox_max_repair_attempts),
        default_data_dir=data_dir,
        app_db_path=app_db_path,
        artifacts_dir=artifacts_dir,
        ai_artifacts_dir=ai_artifacts_dir,
        api_host=api_host,
        api_port=api_port,
    )

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import os


def _default_database_url() -> str:
    backend_root = Path(__file__).resolve().parents[2]
    data_dir = backend_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "chargellm_demo.db"
    return f"sqlite+pysqlite:///{db_path}"


def _default_env_file() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _load_env_file() -> None:
    env_path = Path(os.getenv("CHARGELLM_ENV_FILE", str(_default_env_file())))
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _split_keywords(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return (
            "违法",
            "暴力",
            "色情",
            "政治",
            "自杀",
            "毒品",
        )
    return tuple(keyword.strip() for keyword in raw.split(",") if keyword.strip())


def _env(*names: str, default: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


@dataclass(slots=True)
class Settings:
    app_name: str = "ChargeLLM Backend"
    api_prefix: str = "/api"
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", default=_default_database_url()))
    admin_username: str = field(default_factory=lambda: _env("CHARGELLM_ADMIN_USERNAME", "ADMIN_USERNAME", default="admin"))
    admin_password: str = field(default_factory=lambda: _env("CHARGELLM_ADMIN_PASSWORD", "ADMIN_PASSWORD", default="ChangeMe123!"))
    sms_mock_code: str = field(default_factory=lambda: _env("CHARGELLM_SMS_MOCK_CODE", "SMS_MOCK_CODE", default="123456"))
    invite_default_max_uses: int = field(default_factory=lambda: int(os.getenv("CHARGELLM_INVITE_DEFAULT_MAX_USES", "20")))
    invite_default_per_user_quota: int = field(default_factory=lambda: int(os.getenv("CHARGELLM_INVITE_DEFAULT_PER_USER_QUOTA", "10")))
    content_safety_mode: str = field(default_factory=lambda: _env("CHARGELLM_CONTENT_SAFETY_MODE", "ALIYUN_SAFETY_MOCK", default="keyword"))
    content_safety_keywords: tuple[str, ...] = field(default_factory=lambda: _split_keywords(os.getenv("CHARGELLM_CONTENT_SAFETY_KEYWORDS")))
    mock_stream_delay_seconds: float = field(default_factory=lambda: float(os.getenv("CHARGELLM_MOCK_STREAM_DELAY_SECONDS", "0.01")))
    vllm_mock: bool = field(default_factory=lambda: _env("VLLM_MOCK", default="true").lower() == "true")
    vllm_base_url: str = field(default_factory=lambda: _env("VLLM_BASE_URL", default="http://127.0.0.1:8001/v1"))
    vllm_model: str = field(default_factory=lambda: _env("VLLM_MODEL", default="Qwen3-VL"))
    vllm_api_key: str = field(default_factory=lambda: _env("VLLM_API_KEY", default=""))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file()
    return Settings()

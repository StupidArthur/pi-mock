import os
from pathlib import Path
from typing import Any, Optional

import yaml

BASE_DIR = Path(__file__).resolve().parents[2]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any) -> int:
    return int(str(value).strip())


class Settings:
    def __init__(self) -> None:
        self.host: str = "0.0.0.0"
        self.port: int = 8080
        self.server_name: str = "TEST-PI"
        self.auth_enabled: bool = False
        self.storage_type: str = "sqlite"
        self.log_level: str = "INFO"
        self.db_path: str = str(BASE_DIR / "data" / "mock_pi.db")
        self.example_data_path: str = str(BASE_DIR / "data" / "example.json")
        self.verbose: bool = False
        self.history_limit: int = 100000

    def load_yaml(self, path: Path) -> "Settings":
        if not path.exists():
            return self
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        server = data.get("server", {}) or {}
        pi = data.get("pi", {}) or {}
        auth = data.get("auth", {}) or {}
        storage = data.get("storage", {}) or {}
        logging_cfg = data.get("logging", {}) or {}
        if "host" in server:
            self.host = str(server["host"])
        if "port" in server:
            self.port = _as_int(server["port"])
        if "server_name" in pi:
            self.server_name = str(pi["server_name"])
        if "enabled" in auth:
            self.auth_enabled = _as_bool(auth["enabled"])
        if "type" in storage:
            self.storage_type = str(storage["type"])
        if "path" in storage:
            self.db_path = str(storage["path"])
        if "level" in logging_cfg:
            self.log_level = str(logging_cfg["level"])
        return self

    def apply_env(self) -> "Settings":
        env_map = {
            "PI_HOST": ("host", str),
            "PI_PORT": ("port", _as_int),
            "PI_SERVER_NAME": ("server_name", str),
            "PI_AUTH_ENABLED": ("auth_enabled", _as_bool),
            "PI_STORAGE_TYPE": ("storage_type", str),
            "PI_LOG_LEVEL": ("log_level", str),
            "PI_DB_PATH": ("db_path", str),
        }
        for env_key, (attr, caster) in env_map.items():
            if env_key in os.environ:
                setattr(self, attr, caster(os.environ[env_key]))
        return self

    @classmethod
    def load(cls, config_path: Optional[str] = None, verbose: bool = False) -> "Settings":
        settings = cls()
        path = Path(config_path) if config_path else (BASE_DIR / "config" / "default.yaml")
        if not path.is_absolute():
            path = BASE_DIR / path
        settings.load_yaml(path)
        settings.apply_env()
        settings.verbose = verbose
        return settings


settings = Settings.load()

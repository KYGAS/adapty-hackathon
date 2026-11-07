"""Runtime settings, read once from the environment (and an optional .env file)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DEFAULT_APP_ID = "9c35cea9-1655-4af3-9f05-ac16f383e91d"
DEFAULT_API_URL = "https://api-admin.adapty.io/api/v1/developer"


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader: KEY=VALUE lines, no quotes handling beyond stripping, never overrides the environment."""
    path = path or REPO_DIR / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def cli_token_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".config")
    return Path(base) / "adapty" / "config.json"


def read_cli_token() -> str | None:
    """The developer token written by `adapty auth login`. Never logged, never returned to a browser."""
    path = cli_token_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    token = data.get("access_token")
    return token if isinstance(token, str) and token else None


@dataclass(frozen=True)
class Settings:
    adapty_mode: str = "mock"
    adapty_fixtures: str = "captured"
    adapty_app_id: str = DEFAULT_APP_ID
    adapty_token: str | None = None
    adapty_api_url: str = DEFAULT_API_URL
    allow_live_writes: bool = False
    llm_provider: str = "auto"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"
    claude_cli_path: str = "claude"
    claude_cli_model: str = "sonnet"
    port: int = 8010
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    fixed_now: datetime | None = None
    data_dir: Path = field(default_factory=lambda: BACKEND_DIR / "data")

    @property
    def is_live(self) -> bool:
        return self.adapty_mode == "live"

    def now(self) -> datetime:
        return self.fixed_now or datetime.now(timezone.utc)


def parse_now(raw: str | None) -> datetime | None:
    if not raw:
        return None
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def settings_from_env() -> Settings:
    load_dotenv()
    env = os.environ
    mode = env.get("ADAPTY_MODE", "mock").strip().lower()
    token = env.get("ADAPTY_TOKEN") or None
    if mode == "live" and not token:
        token = read_cli_token()
    origins = tuple(o.strip() for o in env.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip())
    return Settings(
        adapty_mode=mode if mode in {"mock", "live"} else "mock",
        adapty_fixtures=env.get("ADAPTY_FIXTURES", "captured").strip().lower() or "captured",
        adapty_app_id=env.get("ADAPTY_APP_ID", DEFAULT_APP_ID),
        adapty_token=token,
        adapty_api_url=env.get("ADAPTY_API_URL", DEFAULT_API_URL).rstrip("/"),
        allow_live_writes=_env_bool("REFEREE_ALLOW_LIVE_WRITES", False),
        llm_provider=env.get("LLM_PROVIDER", "auto").strip().lower(),
        anthropic_api_key=env.get("ANTHROPIC_API_KEY") or None,
        anthropic_model=env.get("ANTHROPIC_MODEL", "claude-opus-5-5"),
        claude_cli_path=env.get("CLAUDE_CLI_PATH", "claude"),
        claude_cli_model=env.get("CLAUDE_CLI_MODEL", "sonnet"),
        port=int(env.get("REFEREE_PORT", "8010")),
        cors_origins=origins,
        fixed_now=parse_now(env.get("REFEREE_NOW")),
    )

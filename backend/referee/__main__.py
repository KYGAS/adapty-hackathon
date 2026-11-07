"""python -m referee  ->  uvicorn on REFEREE_PORT (default 8000)."""

from __future__ import annotations

import uvicorn

from .api.app import create_app
from .config import settings_from_env


def main() -> None:
    settings = settings_from_env()
    app = create_app(settings)
    print(f"Adapty Experimentation Referee on http://127.0.0.1:{settings.port}  mode={settings.adapty_mode}  "
          f"llm={settings.llm_provider}  live_writes={'on' if settings.allow_live_writes else 'off'}")
    uvicorn.run(app, host="127.0.0.1", port=settings.port, log_level="info")


if __name__ == "__main__":
    main()

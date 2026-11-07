"""FastAPI application: referee routes plus a CORS proxy to the Adapty developer API."""

from __future__ import annotations

from dataclasses import replace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..adapty.client import AdaptyClient, make_client
from ..config import Settings, parse_now, settings_from_env
from ..service import RefereeService
from .proxy import router as proxy_router
from .routes import router as referee_router


def create_app(settings: Settings | None = None, client: AdaptyClient | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    client = client or make_client(settings)
    # A generated fixture set carries the clock it was built for; freeze the referee to it unless REFEREE_NOW says otherwise.
    store = getattr(client, "store", None)
    manifest_clock = getattr(store, "manifest", {}).get("clock") if store is not None else None
    if settings.fixed_now is None and manifest_clock:
        settings = replace(settings, fixed_now=parse_now(manifest_clock))
    app = FastAPI(title="Adapty Experimentation Referee", version=__version__,
                  description="Deterministic A/B decisions, narrated by an LLM that never does math, executed only after approval.")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins) or ["*"], allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])
    app.state.settings = settings
    app.state.client = client
    app.state.service = RefereeService(client, settings)
    app.include_router(referee_router)
    app.include_router(proxy_router)
    return app

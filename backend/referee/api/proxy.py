"""CORS proxy to the Adapty developer API. Reads pass through; writes are refused so the token can never be
used to mutate a live test from a browser. Approved writes go through /api/referee/actions/execute."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..adapty.client import is_read_request

router = APIRouter()


@router.api_route("/adapty/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def adapty_proxy(request: Request, path: str) -> Response:
    client = request.app.state.client
    method = request.method.upper()
    full_path = "/" + path.strip("/") + "/"
    if not is_read_request(method, full_path):
        return JSONResponse(status_code=403, content={
            "detail": "Mutating Adapty calls are not proxied. Approve the action in the Referee; it runs through /api/referee/actions/execute.",
            "method": method, "path": full_path,
        })
    body: Any = None
    raw = await request.body()
    if raw:
        try:
            body = json.loads(raw)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "body must be JSON"})
    status, payload = client.request(method, full_path, dict(request.query_params), body)
    return JSONResponse(status_code=status, content=payload, headers={"x-adapty-mode": client.mode})

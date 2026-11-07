"""Referee endpoints. Reads are free; the only write is /actions/execute and it demands an explicit approval."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..adapty.client import AdaptyError
from ..llm.providers import discover_claude_cli
from ..models import Assumptions
from ..service import ExecutionRefused, RefereeService

router = APIRouter(prefix="/api")


def _service(request: Request) -> RefereeService:
    return request.app.state.service


def _assumptions(mde: float | None, alpha: float | None, power: float | None, max_wait: float | None,
                 min_runtime: float | None) -> Assumptions | None:
    if all(v is None for v in (mde, alpha, power, max_wait, min_runtime)):
        return None
    base = Assumptions()
    return base.model_copy(update={k: v for k, v in {
        "mde_relative": mde, "alpha": alpha, "power": power, "max_wait_days": max_wait, "min_runtime_days": min_runtime,
    }.items() if v is not None})


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "ok": True,
        "adapty_mode": request.app.state.client.mode,
        "fixture_set": getattr(getattr(request.app.state.client, "store", None), "fixture_set", None),
        "app_id": settings.adapty_app_id,
        "live_writes_allowed": settings.allow_live_writes,
        "llm_provider_setting": settings.llm_provider,
        "anthropic_api_key_present": bool(settings.anthropic_api_key),
        "claude_cli_found": bool(discover_claude_cli(settings.claude_cli_path)),
        "fixed_now": settings.fixed_now.isoformat() if settings.fixed_now else None,
    }


@router.get("/referee/assumptions")
def assumptions() -> Assumptions:
    return Assumptions()


@router.get("/referee/tests")
def list_tests(request: Request, mde: float | None = Query(None, gt=0, lt=5), alpha: float | None = Query(None, gt=0, lt=1),
               power: float | None = Query(None, gt=0, lt=1), max_wait: float | None = Query(None, gt=0),
               min_runtime: float | None = Query(None, ge=0)) -> list[dict[str, Any]]:
    try:
        return _service(request).overview(_assumptions(mde, alpha, power, max_wait, min_runtime))
    except AdaptyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/referee/tests/{test_id}/dossier")
def dossier(request: Request, test_id: str, mde: float | None = Query(None, gt=0, lt=5), alpha: float | None = Query(None, gt=0, lt=1),
            power: float | None = Query(None, gt=0, lt=1), max_wait: float | None = Query(None, gt=0),
            min_runtime: float | None = Query(None, ge=0)):
    try:
        result, _ = _service(request).dossier(test_id, _assumptions(mde, alpha, power, max_wait, min_runtime))
        return result
    except AdaptyError as exc:
        raise HTTPException(status_code=404 if exc.status == 404 else 502, detail=str(exc)) from exc


class MemoRequest(BaseModel):
    provider: str | None = Field(None, description="auto, cli, api or template")


@router.post("/referee/tests/{test_id}/memo")
def memo(request: Request, test_id: str, body: MemoRequest | None = None):
    try:
        return _service(request).narration(test_id, body.provider if body else None)
    except AdaptyError as exc:
        raise HTTPException(status_code=404 if exc.status == 404 else 502, detail=str(exc)) from exc


@router.get("/referee/opportunities")
def opportunities(request: Request):
    try:
        return _service(request).opportunities()
    except AdaptyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


class ExecuteRequest(BaseModel):
    test_id: str
    action_id: str
    approved: bool = False
    approver: str = Field(..., min_length=1, description="Who approved it; stored in the audit log")
    note: str | None = None


@router.post("/referee/actions/execute")
def execute(request: Request, body: ExecuteRequest):
    try:
        return _service(request).execute(body.test_id, body.action_id, body.approved, body.approver, body.note)
    except ExecutionRefused as exc:
        raise HTTPException(status_code=exc.status, detail={"message": exc.detail, **exc.payload}) from exc
    except AdaptyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/referee/audit-log")
def audit_log(request: Request, limit: int = Query(100, ge=1, le=1000)) -> list[dict[str, Any]]:
    return _service(request).audit_log(limit)

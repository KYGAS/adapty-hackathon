"""RefereeService: glue between the Adapty client, the dossier builder, the narrator and the approval gate."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from .actions import action_as_text
from .adapty.client import AdaptyClient, AdaptyError
from .adapty.normalize import build_history_input, build_test_input
from .audit import audit_completed
from .catalog import Catalog
from .config import Settings
from .dossier import build_dossier
from .llm.narrate import narrate
from .models import ActionPreview, Assumptions, AuditResult, HistoryInput, Narration, PlacementOpportunity, TestDossier
from .ranking import rank_placements

HISTORY_TTL_SECONDS = 300.0


class ExecutionRefused(Exception):
    def __init__(self, status: int, detail: str, payload: dict | None = None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.payload = payload or {}


class RefereeService:
    def __init__(self, client: AdaptyClient, settings: Settings, catalog: Catalog | None = None):
        self.client = client
        self.settings = settings
        self.catalog = catalog or Catalog.load()
        self._history: tuple[float, HistoryInput] | None = None
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.settings.data_dir / "audit_log.jsonl"

    # ------------------------------------------------------------------ inputs
    def now(self) -> datetime:
        return self.settings.now()

    def history(self) -> HistoryInput:
        if self._history and time.monotonic() - self._history[0] < HISTORY_TTL_SECONDS:
            return self._history[1]
        today = self.now().date()
        start = today.replace(day=1)
        start = (start.replace(month=start.month - 4) if start.month > 4 else start.replace(year=start.year - 1, month=start.month + 8))
        try:
            conversion = self.client.analytics_conversion("trial-paid", start.isoformat(), today.isoformat(), "month")
            history = build_history_input(conversion)
        except AdaptyError:
            history = HistoryInput()
        self._history = (time.monotonic(), history)
        return history

    def winner_for(self, detail: dict) -> str | None:
        """For a completed test, the flow its placement now shows (the stop body is not echoed by the API)."""
        store = getattr(self.client, "store", None)
        if store is not None and detail["ab_test_id"] in store.winners:
            return store.winners[detail["ab_test_id"]]
        placement_id = (detail.get("placement") or {}).get("placement_id")
        if detail.get("state") != "completed" or not placement_id:
            return None
        try:
            placement = self.client.get_placement(placement_id)
        except AdaptyError:
            return None
        arm_flows = {f["flow_id"] for f in detail.get("flows", [])}
        for audience in placement.get("audiences", []):
            if audience.get("content_type") == "flow" and audience.get("flow_id") in arm_flows:
                return audience["flow_id"]
        return None

    # ------------------------------------------------------------------ dossiers
    def dossier(self, test_id: str, assumptions: Assumptions | None = None) -> tuple[TestDossier, AuditResult | None]:
        detail = self.client.get_test(test_id)
        total = tree = None
        if detail.get("state") != "draft":
            try:
                total = self.client.metrics_total(test_id, detail.get("type", "flow"))
            except AdaptyError:
                total = None
            try:
                tree = self.client.metrics_tree(test_id, detail.get("type", "flow"), {})
            except AdaptyError:
                tree = None
        winner = self.winner_for(detail)
        test_input = build_test_input(detail, total, tree, self.catalog, winner)
        dossier = build_dossier(test_input, self.history(), self.settings.adapty_app_id, self.now(), assumptions)
        audit = None
        if dossier.verdict.code == "COMPLETED":
            flow_ids = [a.flow_id for a in dossier.arms]
            try:
                metrics = {m["flow_id"]: m for m in self.client.flow_metrics(flow_ids)}
            except AdaptyError:
                metrics = {}
            audit = audit_completed(dossier, winner, metrics)
            dossier = dossier.model_copy(update={"audit": audit})
        return dossier, audit

    def overview(self, assumptions: Assumptions | None = None) -> list[dict[str, Any]]:
        rows = []
        for listed in self.client.list_tests():
            try:
                dossier, audit = self.dossier(listed["ab_test_id"], assumptions)
            except AdaptyError as exc:
                rows.append({"test_id": listed["ab_test_id"], "title": listed.get("title"), "state": listed.get("state"), "error": str(exc)})
                continue
            rows.append({
                "test_id": dossier.test.test_id, "title": dossier.test.title, "state": dossier.test.state,
                "placement_id": dossier.test.placement_id, "placement_title": dossier.test.placement_title,
                "started_at": dossier.test.started_at, "stopped_at": dossier.test.stopped_at,
                "verdict": dossier.verdict, "timeline": dossier.timeline, "warnings": dossier.warnings,
                "recommended_action": next((a for a in dossier.actions if a.recommended), None),
                "audit_grade": audit.grade if audit else None,
                "pending_trials": dossier.trial_lag.pending_trials_total,
                "sample_progress": dossier.sample.progress,
            })
        return rows

    def opportunities(self) -> list[PlacementOpportunity]:
        tests = self.client.list_tests()
        details = {t["ab_test_id"]: self.client.get_test(t["ab_test_id"]) for t in tests if t.get("state") == "draft"}
        flows = self.client.list_flows()
        metrics = self.client.flow_metrics([f["id"] for f in flows])
        return rank_placements(self.settings.adapty_app_id, self.client.list_placements(), tests, flows, metrics, self.catalog, details)

    def narration(self, test_id: str, provider: str | None = None) -> Narration:
        dossier, audit = self.dossier(test_id)
        return narrate(dossier, self.settings, provider, audit)

    # ------------------------------------------------------------------ approval gate
    def execute(self, test_id: str, action_id: str, approved: bool, approver: str, note: str | None = None) -> dict[str, Any]:
        dossier, _ = self.dossier(test_id)
        action = next((a for a in dossier.actions if a.id == action_id), None)
        if action is None:
            opportunities = {o.draft_test_id: o.action for o in self.opportunities() if o.action}
            action = opportunities.get(test_id) if action_id == "start_draft" else None
        if action is None:
            raise ExecutionRefused(404, f"action {action_id} is not available for this test right now; the dossier was recomputed")
        preview = {"test_id": test_id, "action": action.model_dump(), "command": action_as_text(action), "verdict": dossier.verdict.code}
        if not action.cli_command:
            return {**preview, "status": "nothing_to_run"}
        if not approved:
            self._log({"event": "dry_run", **preview, "approver": approver, "note": note})
            return {**preview, "status": "dry_run"}
        if self.client.mode == "live" and not self.settings.allow_live_writes:
            self._log({"event": "blocked", **preview, "approver": approver, "note": note})
            raise ExecutionRefused(403, "live writes are disabled; set REFEREE_ALLOW_LIVE_WRITES=true to let approved actions reach Adapty", preview)
        status, payload = self.client.request(action.api_method or "POST", action.api_path or "", None, action.api_body)
        record = {"event": "executed" if status < 400 else "failed", **preview, "approver": approver, "note": note,
                  "adapty_status": status, "adapty_response": payload}
        self._log(record)
        if status >= 400:
            raise ExecutionRefused(status if status in (400, 403, 404, 409, 429) else 502, f"Adapty refused the write ({status})", {**preview, "adapty_response": payload})
        return {**preview, "status": "executed", "adapty_status": status, "adapty_response": payload}

    def _log(self, record: dict[str, Any]) -> None:
        record = {"at": datetime.now(timezone.utc).isoformat(), "mode": self.client.mode, **record}
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.audit_log_path.exists():
            return []
        lines = self.audit_log_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()][::-1]

    def preview_action(self, action: ActionPreview) -> str:
        return action_as_text(action)

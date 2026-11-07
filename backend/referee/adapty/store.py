"""In-memory copy of the captured Adapty responses, answering the real developer API routes.

Reads come from fixtures/. Writes (create, start, stop, archive) mutate the copy so the demo can
approve an action and watch the dashboard change, without touching the Lumen app.
"""

from __future__ import annotations

import copy
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs

FIXTURES = Path(__file__).resolve().parent / "fixtures"

Query = dict[str, list[str]]
Handler = Callable[[dict[str, str], Query, Any], Any]


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.tests = load("ab_tests_list.json")
        self.test_details: dict[str, dict] = {}
        for name in ("ab_test_get_onboarding.json", "ab_test_get_main_na.json",
                     "ab_test_get_settings_completed.json", "ab_test_get_ai_limit_draft.json"):
            detail = load(name)
            self.test_details[detail["ab_test_id"]] = detail
        self.metrics_list = load("ab_tests_metrics_list.json")
        self.metrics_get = {
            "b2c90b2b-59b0-48fc-b821-b90061d1ae1e": {
                None: load("ab_test_metrics_get_onboarding_lifetime.json"),
                "country": load("ab_test_metrics_get_onboarding_by_country.json"),
            }
        }
        self.metrics_total = {"b2c90b2b-59b0-48fc-b821-b90061d1ae1e": load("ab_test_metrics_total_onboarding.json")}
        self.flows = load("flows_list.json")
        self.flow_metrics = load("flows_metrics_list.json")
        self.placements = load("placements_list.json")
        self.placement_details = {"2d81af2b-6159-4416-924b-e3d927e468e5": load("placement_get_onboarding.json")}
        self.segments = load("segments_list.json")
        self.products = load("products_list.json")
        self.chart = load("analytics_chart_revenue_week_by_product.json")
        self.conversions = {
            "install-paid": load("analytics_conversion_install_paid_by_flow.json"),
            "trial-paid": load("analytics_conversion_trial_paid.json"),
        }
        # Known winners of completed tests (the API does not echo the stop body). The seed stopped the
        # Settings test with "Settings - Upgrade" as the winner.
        self.winners: dict[str, str] = {"35299a82-0d41-4b50-a874-bf86e11c33d0": "a7c2595b-2c9b-4dc2-9e30-8ff715e6ecaa"}

    # ------------------------------------------------------------ reads
    def list_tests(self, query: Query) -> dict:
        data = self.tests["data"]
        states = query.get("filter[state]")
        if states:
            wanted = set(states[0].split(","))
            data = [t for t in data if t["state"] in wanted]
        placements = query.get("filter[placement_id]")
        if placements:
            wanted = set(placements[0].split(","))
            data = [t for t in data if t["placement"]["placement_id"] in wanted]
        return {"data": copy.deepcopy(data), "meta": {"pagination": {"count": len(data), "page": 1, "pages": 1}}}

    def get_test(self, test_id: str) -> dict:
        detail = self.test_details.get(test_id)
        if detail is None:
            raise NotFound(test_id)
        listed = next((t for t in self.tests["data"] if t["ab_test_id"] == test_id), None)
        merged = copy.deepcopy(detail)
        if listed:
            merged.update({k: listed[k] for k in ("state", "started_at", "stopped_at")})
        return merged

    def metrics_rows(self, query: Query) -> dict:
        ids = query.get("filter[ab_test_id]", [""])[0]
        wanted = set(filter(None, ids.split(",")))
        rows = [r for r in self.metrics_list["data"] if not wanted or r["ab_test_id"] in wanted]
        return {"data": copy.deepcopy(rows)}

    def _row(self, test_id: str) -> dict | None:
        return next((r for r in self.metrics_list["data"] if r["ab_test_id"] == test_id), None)

    def metrics_tree(self, test_id: str, body: Any) -> dict:
        by = (body or {}).get("segmentation_by")
        exact = self.metrics_get.get(test_id, {})
        if by in exact:
            return copy.deepcopy(exact[by])
        if by is None and None in exact:
            return copy.deepcopy(exact[None])
        row = self._row(test_id)
        detail = self.get_test(test_id)
        if row is None:
            return {"data": {"level": "root", "title": detail["title"], "views": 0, "items": []}}
        root = {k: v for k, v in row.items() if k != "items"}
        root.update({"level": "root", "title": detail["title"], "items": []})
        for arm in row["items"]:
            node = dict(arm)
            flow = next((f for f in detail["flows"] if f["flow_id"] == arm.get("flow_id")), None)
            node.update({"level": "variation", "title": flow["title"] if flow else "?", "values": [], "items": []})
            root["items"].append(node)
        return {"data": root}

    def metrics_total_of(self, test_id: str) -> dict:
        if test_id in self.metrics_total:
            return copy.deepcopy(self.metrics_total[test_id])
        row = self._row(test_id)
        detail = self.get_test(test_id)
        arms = []
        for flow in detail["flows"]:
            arm = next((a for a in (row or {}).get("items", []) if a.get("flow_id") == flow["flow_id"]), None)
            base = dict(arm) if arm else {"views": 0, "purchases": 0, "trials": 0, "revenue": 0, "unique_paid_subscribers": 0,
                                          "probability": 0, "low_boundary": 0, "average_per_1000": 0, "upper_boundary": 0,
                                          "p_value": None, "weight": flow["weight"], "flow_id": flow["flow_id"],
                                          "variation_id": flow.get("variation_id")}
            base.update({"title": flow["title"], "active_trials_rate": 1 if base.get("trials") else 0})
            arms.append(base)
        return {"data": {"metrics": arms,
                         "ab_test": {"ab_test_id": test_id, "title": detail["title"], "goal": detail.get("goal"), "vars": {}},
                         "state": detail["state"], "started_at": detail["started_at"], "stopped_at": detail["stopped_at"],
                         "active_trials_rate": 1 if any(a.get("trials") for a in arms) else 0}}

    def get_placement(self, placement_id: str) -> dict:
        if placement_id in self.placement_details:
            return copy.deepcopy(self.placement_details[placement_id])
        listed = next((p for p in self.placements["data"] if p["id"] == placement_id), None)
        if listed is None:
            raise NotFound(placement_id)
        live_tests = [t for t in self.tests["data"] if t["placement"]["placement_id"] == placement_id and t["state"] == "live"]
        audiences = [{"content_type": "flow_ab_test", "ab_test_id": t["ab_test_id"], "ab_test_title": t["title"],
                      "segment_ids": t["segment_ids"], "priority": i} for i, t in enumerate(live_tests)]
        for test_id, winner in self.winners.items():
            test = next((t for t in self.tests["data"] if t["ab_test_id"] == test_id), None)
            if test and test["placement"]["placement_id"] == placement_id:
                flow = next((f for f in self.flows["data"] if f["id"] == winner), None)
                audiences.append({"content_type": "flow", "flow_id": winner, "flow_title": flow["name"] if flow else "?",
                                  "segment_ids": [], "priority": len(audiences)})
        return {**copy.deepcopy(listed), "audiences": audiences}

    def flow_metrics_for(self, query: Query) -> dict:
        ids = query.get("filter[flow_id]", [""])[0]
        wanted = set(filter(None, ids.split(",")))
        rows = [r for r in self.flow_metrics["data"] if not wanted or r["flow_id"] in wanted]
        return {"data": copy.deepcopy(rows)}

    def conversion(self, body: Any) -> dict:
        conversion_id = (body or {}).get("conversion_id", "install-paid")
        return copy.deepcopy(self.conversions.get(conversion_id, self.conversions["install-paid"]))

    # ------------------------------------------------------------ writes (mocked)
    def create_test(self, body: Any) -> dict:
        body = body or {}
        if not body.get("title") or not body.get("flows"):
            raise BadRequest("title and flows are required")
        test_id = str(uuid.uuid4())
        placement = next((p for p in self.placements["data"] if p["id"] == body.get("placement_id")), None)
        flows = []
        for index, arm in enumerate(body["flows"]):
            flow = next((f for f in self.flows["data"] if f["id"] == arm["flow_id"]), None)
            flows.append({"flow_id": arm["flow_id"], "flow_name": flow["name"] if flow else "?", "weight": arm["weight"],
                          "title": arm.get("title") or chr(65 + index), "variation_id": str(uuid.uuid4())})
        listed = {"ab_test_id": test_id, "title": body["title"], "type": "flow", "state": "draft",
                  "placement": {"placement_id": body.get("placement_id"), "title": placement["title"] if placement else "?"},
                  "segment_ids": body.get("segment_ids", []), "priority": 0, "started_at": None, "stopped_at": None}
        self.tests["data"].insert(0, listed)
        self.test_details[test_id] = {**listed, "goal": body.get("goal"), "paywalls": [], "flows": flows, "created_at": _now_iso()}
        return self.get_test(test_id)

    def start_test(self, test_id: str, body: Any) -> dict:
        listed = self._listed(test_id)
        if listed["state"] != "draft":
            raise BadRequest("only drafts start")
        listed["state"] = "live"
        listed["started_at"] = _now_iso()
        if body and body.get("segment_ids") is not None:
            listed["segment_ids"] = list(body["segment_ids"])
        return self.get_test(test_id)

    def stop_test(self, test_id: str, body: Any) -> dict:
        listed = self._listed(test_id)
        if listed["state"] != "live":
            raise BadRequest("only live tests stop")
        body = body or {}
        winner = body.get("winner_flow_id") or body.get("another_flow_id_to_run")
        if not winner and not listed["segment_ids"]:
            raise BadRequest("stopping with no content is refused on All users")
        listed["state"] = "completed"
        listed["stopped_at"] = _now_iso()
        if winner:
            self.winners[test_id] = winner
        return self.get_test(test_id)

    def archive_test(self, test_id: str) -> dict:
        listed = self._listed(test_id)
        if listed["state"] == "live":
            raise BadRequest("archiving a live test is refused")
        listed["state"] = "archived"
        return self.get_test(test_id)

    def _listed(self, test_id: str) -> dict:
        listed = next((t for t in self.tests["data"] if t["ab_test_id"] == test_id), None)
        if listed is None:
            raise NotFound(test_id)
        return listed

    # ------------------------------------------------------------ routing (same paths as the real API)
    def routes(self) -> list[tuple[str, re.Pattern[str], Handler]]:
        app = r"^/apps/(?P<app>[^/]+)"
        table: list[tuple[str, str, Handler]] = [
            ("GET", app + r"/ab-tests/$", lambda m, q, b: self.list_tests(q)),
            ("GET", app + r"/ab-tests/metrics/$", lambda m, q, b: self.metrics_rows(q)),
            ("GET", app + r"/ab-tests/(?P<id>[^/]+)/$", lambda m, q, b: self.get_test(m["id"])),
            ("POST", app + r"/ab-tests/$", lambda m, q, b: self.create_test(b)),
            ("DELETE", app + r"/ab-tests/(?P<id>[^/]+)/$", lambda m, q, b: self.archive_test(m["id"])),
            ("POST", app + r"/ab-tests/(?P<id>[^/]+)/metrics/$", lambda m, q, b: self.metrics_tree(m["id"], b)),
            ("GET", app + r"/ab-tests/(?P<id>[^/]+)/metrics/total/$", lambda m, q, b: self.metrics_total_of(m["id"])),
            ("POST", app + r"/ab-tests/(?P<id>[^/]+)/start/$", lambda m, q, b: self.start_test(m["id"], b)),
            ("POST", app + r"/ab-tests/(?P<id>[^/]+)/stop/$", lambda m, q, b: self.stop_test(m["id"], b)),
            ("GET", app + r"/flows/$", lambda m, q, b: copy.deepcopy(self.flows)),
            ("GET", app + r"/flows/metrics/$", lambda m, q, b: self.flow_metrics_for(q)),
            ("GET", app + r"/placements/$", lambda m, q, b: copy.deepcopy(self.placements)),
            ("GET", app + r"/placements/(?P<id>[^/]+)/$", lambda m, q, b: self.get_placement(m["id"])),
            ("GET", app + r"/segments/$", lambda m, q, b: copy.deepcopy(self.segments)),
            ("GET", app + r"/products/$", lambda m, q, b: copy.deepcopy(self.products)),
            ("POST", app + r"/analytics/metrics/$", lambda m, q, b: copy.deepcopy(self.chart)),
            ("POST", app + r"/analytics/conversion/$", lambda m, q, b: self.conversion(b)),
        ]
        return [(method, re.compile(pattern), fn) for method, pattern, fn in table]

    def dispatch(self, method: str, path: str, query: Query | str | None = None, body: Any = None) -> tuple[int, Any]:
        """Answer a request the way the real API would: (status, json)."""
        if isinstance(query, str):
            query = parse_qs(query)
        query = query or {}
        if not path.endswith("/"):
            path += "/"
        with self.lock:
            for route_method, pattern, handler in self.routes():
                match = pattern.match(path)
                if match and route_method == method.upper():
                    try:
                        return 200, handler(match.groupdict(), query, body)
                    except NotFound as exc:
                        return 404, {"errors": [{"code": "not_found", "detail": str(exc)}]}
                    except BadRequest as exc:
                        return 400, {"errors": [{"code": "bad_request", "detail": str(exc)}]}
        return 404, {"errors": [{"code": "no_route", "detail": f"{method} {path}"}]}

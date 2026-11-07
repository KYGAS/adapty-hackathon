"""Two clients, one interface. The live client talks to api-admin.adapty.io with the developer token; the
mock client answers from the fixture store. The referee and the proxy never know which one they hold."""

from __future__ import annotations

import time
from typing import Any, Protocol

import httpx

from ..config import Settings
from .store import Store

READ_POSTS = ("/metrics/", "/analytics/")  # POST routes that only read


class AdaptyError(Exception):
    def __init__(self, status: int, payload: Any):
        super().__init__(f"Adapty API {status}: {payload}")
        self.status = status
        self.payload = payload


def is_read_request(method: str, path: str) -> bool:
    """True for GETs and for the POST routes that compute metrics or analytics without changing state."""
    if method.upper() == "GET":
        return True
    if method.upper() == "POST":
        normalized = "/" + path.strip("/") + "/"
        if normalized.endswith("/metrics/") or normalized.endswith("/metrics/total/"):
            return True
        if "/analytics/" in normalized:
            return True
    return False


class AdaptyClient(Protocol):
    mode: str
    app_id: str

    def request(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None) -> tuple[int, Any]: ...
    def list_tests(self, test_type: str = "flow", states: list[str] | None = None) -> list[dict]: ...
    def get_test(self, test_id: str) -> dict: ...
    def metrics_rows(self, test_ids: list[str], test_type: str = "flow") -> list[dict]: ...
    def metrics_total(self, test_id: str, test_type: str = "flow") -> dict: ...
    def metrics_tree(self, test_id: str, test_type: str = "flow", body: dict | None = None) -> dict: ...
    def list_flows(self) -> list[dict]: ...
    def flow_metrics(self, flow_ids: list[str]) -> list[dict]: ...
    def list_placements(self) -> list[dict]: ...
    def get_placement(self, placement_id: str) -> dict: ...
    def list_segments(self) -> list[dict]: ...
    def list_products(self) -> list[dict]: ...
    def analytics_conversion(self, conversion_id: str, date_from: str, date_to: str, period_unit: str = "month",
                             segmentation: str | None = None) -> dict: ...
    def analytics_chart(self, chart_id: str, date_from: str, date_to: str, period_unit: str = "week",
                        segmentation: str | None = None) -> dict: ...
    def start_test(self, test_id: str, placement_id: str, segment_ids: list[str]) -> dict: ...
    def stop_test(self, test_id: str, winner_flow_id: str | None = None, another_flow_id: str | None = None) -> dict: ...
    def create_test(self, body: dict) -> dict: ...


class _Base:
    """Typed helpers on top of request(); shared by both clients."""

    app_id: str

    def request(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None) -> tuple[int, Any]:
        raise NotImplementedError

    def _ok(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None) -> Any:
        status, payload = self.request(method, path, query, body)
        if status >= 400:
            raise AdaptyError(status, payload)
        return payload

    def _app(self, suffix: str) -> str:
        return f"/apps/{self.app_id}/{suffix.lstrip('/')}"

    def list_tests(self, test_type: str = "flow", states: list[str] | None = None) -> list[dict]:
        query: dict[str, Any] = {"type": test_type, "page[size]": 100}
        if states:
            query["filter[state]"] = ",".join(states)
        return self._ok("GET", self._app("ab-tests/"), query)["data"]

    def get_test(self, test_id: str) -> dict:
        return self._ok("GET", self._app(f"ab-tests/{test_id}/"))

    def metrics_rows(self, test_ids: list[str], test_type: str = "flow") -> list[dict]:
        if not test_ids:
            return []
        return self._ok("GET", self._app("ab-tests/metrics/"), {"type": test_type, "filter[ab_test_id]": ",".join(test_ids)})["data"]

    def metrics_total(self, test_id: str, test_type: str = "flow") -> dict:
        return self._ok("GET", self._app(f"ab-tests/{test_id}/metrics/total/"), {"type": test_type})["data"]

    def metrics_tree(self, test_id: str, test_type: str = "flow", body: dict | None = None) -> dict:
        return self._ok("POST", self._app(f"ab-tests/{test_id}/metrics/"), {"type": test_type}, body or {})["data"]

    def list_flows(self) -> list[dict]:
        return self._ok("GET", self._app("flows/"), {"page[size]": 100})["data"]

    def flow_metrics(self, flow_ids: list[str]) -> list[dict]:
        if not flow_ids:
            return []
        return self._ok("GET", self._app("flows/metrics/"), {"filter[flow_id]": ",".join(flow_ids)})["data"]

    def list_placements(self) -> list[dict]:
        return self._ok("GET", self._app("placements/"), {"page[size]": 100})["data"]

    def get_placement(self, placement_id: str) -> dict:
        return self._ok("GET", self._app(f"placements/{placement_id}/"))

    def list_segments(self) -> list[dict]:
        return self._ok("GET", self._app("segments/"), {"page[size]": 100})["data"]

    def list_products(self) -> list[dict]:
        return self._ok("GET", self._app("products/"), {"page[size]": 100})["data"]

    def analytics_conversion(self, conversion_id: str, date_from: str, date_to: str, period_unit: str = "month",
                             segmentation: str | None = None) -> dict:
        body: dict[str, Any] = {"conversion_id": conversion_id, "filters": {"date": [date_from, date_to]}, "period_unit": period_unit}
        if segmentation:
            body["segmentation"] = segmentation
        return self._ok("POST", self._app("analytics/conversion/"), None, body)["data"]

    def analytics_chart(self, chart_id: str, date_from: str, date_to: str, period_unit: str = "week",
                        segmentation: str | None = None) -> dict:
        body: dict[str, Any] = {"chart_id": chart_id, "filters": {"date": [date_from, date_to]}, "period_unit": period_unit}
        if segmentation:
            body["segmentation"] = segmentation
        return self._ok("POST", self._app("analytics/metrics/"), None, body)["data"]

    # ---- writes: only ever called by the approval-gated action executor
    def start_test(self, test_id: str, placement_id: str, segment_ids: list[str]) -> dict:
        return self._ok("POST", self._app(f"ab-tests/{test_id}/start/"), None, {"placement_id": placement_id, "segment_ids": segment_ids})

    def stop_test(self, test_id: str, winner_flow_id: str | None = None, another_flow_id: str | None = None) -> dict:
        body: dict[str, Any] = {}
        if winner_flow_id:
            body["winner_flow_id"] = winner_flow_id
        elif another_flow_id:
            body["another_flow_id_to_run"] = another_flow_id
        return self._ok("POST", self._app(f"ab-tests/{test_id}/stop/"), None, body)

    def create_test(self, body: dict) -> dict:
        return self._ok("POST", self._app("ab-tests/"), None, body)


class MockAdaptyClient(_Base):
    mode = "mock"

    def __init__(self, app_id: str, store: Store | None = None, fixture_set: str = "captured"):
        self.app_id = app_id
        self.store = store or Store(fixture_set)

    def request(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None) -> tuple[int, Any]:
        normalized = {k: [str(v)] for k, v in (query or {}).items()}
        return self.store.dispatch(method, path, normalized, body)


class LiveAdaptyClient(_Base):
    mode = "live"

    def __init__(self, app_id: str, token: str, base_url: str, cache_ttl: float = 60.0, timeout: float = 30.0):
        if not token:
            raise ValueError("live mode needs a developer token (ADAPTY_TOKEN or `adapty auth login`)")
        self.app_id = app_id
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {token}", "accept": "application/json",
                     "user-agent": "adapty-referee/0.1", "x-adapty-interactive": "false"},
            timeout=timeout,
        )
        self._cache: dict[str, tuple[float, int, Any]] = {}
        self.cache_ttl = cache_ttl

    def request(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None) -> tuple[int, Any]:
        if not path.endswith("/") and "/migrations" not in path:
            path += "/"
        key = f"{method} {path} {sorted((query or {}).items())} {body!r}"
        cacheable = is_read_request(method, path)
        if cacheable:
            hit = self._cache.get(key)
            if hit and time.monotonic() - hit[0] < self.cache_ttl:
                return hit[1], hit[2]
        response = self._http.request(method.upper(), path, params=query or None, json=body if body is not None else None)
        try:
            payload = response.json() if response.content else None
        except ValueError:
            payload = {"raw": response.text}
        if cacheable and response.status_code < 400:
            self._cache[key] = (time.monotonic(), response.status_code, payload)
        return response.status_code, payload

    def close(self) -> None:
        self._http.close()


def make_client(settings: Settings) -> AdaptyClient:
    if settings.is_live:
        return LiveAdaptyClient(settings.adapty_app_id, settings.adapty_token or "", settings.adapty_api_url)
    return MockAdaptyClient(settings.adapty_app_id, fixture_set=settings.adapty_fixtures)

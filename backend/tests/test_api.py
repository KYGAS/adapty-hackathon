import pytest
from fastapi.testclient import TestClient

from referee.api.app import create_app
from tests.conftest import APP_ID, DRAFT, ONBOARDING, SETTINGS


@pytest.fixture
def api(settings):
    return TestClient(create_app(settings))


def test_health(api):
    body = api.get("/api/health").json()
    assert body["ok"] and body["adapty_mode"] == "mock" and body["live_writes_allowed"] is False


def test_overview_and_dossier(api):
    rows = api.get("/api/referee/tests").json()
    codes = {r["title"]: r["verdict"]["code"] for r in rows}
    assert codes["Onboarding: annual trial vs weekly first"] == "WAIT_TRIAL_LAG"
    assert codes["Main: 3 plans vs lifetime anchor (NA)"] == "NOT_DECIDABLE"
    assert codes["AI limit: Pro vs 3 plans"] == "NOT_STARTED"
    assert codes["Settings: upgrade vs lifetime anchor"] == "COMPLETED"
    completed = next(r for r in rows if r["title"].startswith("Settings"))
    assert completed["audit_grade"] == "F"
    dossier = api.get(f"/api/referee/tests/{ONBOARDING}/dossier").json()
    assert dossier["verdict"]["code"] == "WAIT_TRIAL_LAG"
    assert dossier["trial_lag"]["pending_trials_total"] == 137
    assert api.get(f"/api/referee/tests/{ONBOARDING}/dossier", params={"mde": 0.5}).json()["sample"]["required_per_arm"] == 1110
    assert api.get("/api/referee/tests/nope/dossier").status_code == 404
    assert api.get(f"/api/referee/tests/{SETTINGS}/dossier").json()["audit"]["grade"] == "F"


def test_memo_with_template_provider(api):
    body = api.post(f"/api/referee/tests/{ONBOARDING}/memo", json={"provider": "template"}).json()
    assert body["provider"] == "template" and body["guard_passed"]
    assert "137" in body["memo"]["memo_markdown"]


def test_memo_falls_back_when_provider_is_missing(api, monkeypatch):
    monkeypatch.setenv("CLAUDE_CLI_PATH", "definitely-not-a-binary")
    from referee.llm import providers
    monkeypatch.setattr(providers, "discover_claude_cli", lambda hint: None)
    body = api.post(f"/api/referee/tests/{ONBOARDING}/memo", json={"provider": "cli"}).json()
    assert body["provider"] == "template" and body["fallback_used"]
    assert body["guard_violations"][0].startswith("provider unavailable")


def test_opportunities_rank_the_ready_draft_first(api):
    rows = api.get("/api/referee/opportunities").json()
    assert rows[0]["title"] == "AI edits limit reached" and rows[0]["draft_test_id"] == DRAFT
    assert rows[0]["action"]["kind"] == "start_draft"
    assert all(r["has_live_test"] for r in rows if r["score"] == 0 and r["views"] > 0)


def test_proxy_reads_pass_and_writes_are_refused(api):
    listing = api.get(f"/adapty/apps/{APP_ID}/ab-tests/", params={"type": "flow"})
    assert listing.status_code == 200 and len(listing.json()["data"]) == 4
    assert listing.headers["x-adapty-mode"] == "mock"
    tree = api.post(f"/adapty/apps/{APP_ID}/ab-tests/{ONBOARDING}/metrics/", params={"type": "flow"}, json={})
    assert tree.status_code == 200 and tree.json()["data"]["level"] == "root"
    stop = api.post(f"/adapty/apps/{APP_ID}/ab-tests/{ONBOARDING}/stop/", json={})
    assert stop.status_code == 403
    assert api.delete(f"/adapty/apps/{APP_ID}/ab-tests/{SETTINGS}/").status_code == 403
    assert api.post(f"/adapty/apps/{APP_ID}/ab-tests/{ONBOARDING}/metrics/", content=b"not json").status_code == 400


def test_execute_requires_approval_and_logs(api):
    dry = api.post("/api/referee/actions/execute", json={"test_id": DRAFT, "action_id": "start_draft", "approved": False, "approver": "pm"})
    assert dry.status_code == 200 and dry.json()["status"] == "dry_run"
    assert "adapty ab-tests start" in dry.json()["command"]
    missing = api.post("/api/referee/actions/execute", json={"test_id": DRAFT, "action_id": "stop_winner:x", "approved": True, "approver": "pm"})
    assert missing.status_code == 404
    nothing = api.post("/api/referee/actions/execute", json={"test_id": ONBOARDING, "action_id": "keep_running", "approved": True, "approver": "pm"})
    assert nothing.json()["status"] == "nothing_to_run"
    done = api.post("/api/referee/actions/execute", json={"test_id": DRAFT, "action_id": "start_draft", "approved": True, "approver": "pm"})
    assert done.status_code == 200 and done.json()["status"] == "executed"
    assert done.json()["adapty_response"]["state"] == "live"
    assert api.get(f"/api/referee/tests/{DRAFT}/dossier").json()["test"]["state"] == "live"
    log = api.get("/api/referee/audit-log").json()
    assert [e["event"] for e in log] == ["executed", "dry_run"]
    assert api.post("/api/referee/actions/execute", json={"test_id": DRAFT, "action_id": "start_draft", "approved": True}).status_code == 422


def test_live_writes_are_blocked_without_the_flag(settings, client, monkeypatch):
    client.mode = "live"
    api = TestClient(create_app(settings, client))
    blocked = api.post("/api/referee/actions/execute", json={"test_id": DRAFT, "action_id": "start_draft", "approved": True, "approver": "pm"})
    assert blocked.status_code == 403
    assert "REFEREE_ALLOW_LIVE_WRITES" in blocked.json()["detail"]["message"]
    assert api.get("/api/referee/audit-log").json()[0]["event"] == "blocked"


def test_dev_reset_restores_the_draft_and_clears_the_log(api):
    action = next(a for a in api.get(f"/api/referee/tests/{DRAFT}/dossier").json()["actions"] if a["kind"] == "start_draft")
    body = api.post("/api/referee/actions/execute", json={"test_id": DRAFT, "action_id": action["id"], "approved": True, "approver": "demo"}).json()
    assert body["status"] == "executed"
    assert api.get(f"/api/referee/tests/{DRAFT}/dossier").json()["test"]["state"] == "live"
    assert len(api.get("/api/referee/audit-log").json()) >= 1
    assert api.post("/api/dev/reset").json()["status"] == "reset"
    assert api.get(f"/api/referee/tests/{DRAFT}/dossier").json()["test"]["state"] == "draft"
    assert api.get("/api/referee/audit-log").json() == []

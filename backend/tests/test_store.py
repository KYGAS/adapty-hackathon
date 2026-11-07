from referee.adapty.store import Store
from tests.conftest import APP_ID, DRAFT, MAIN_NA, ONBOARDING, SETTINGS


def test_dispatch_reads():
    s = Store()
    status, payload = s.dispatch("GET", f"/apps/{APP_ID}/ab-tests/", {"type": ["flow"], "filter[state]": ["live"]})
    assert status == 200 and {t["state"] for t in payload["data"]} == {"live"}
    status, payload = s.dispatch("GET", f"/apps/{APP_ID}/ab-tests/{ONBOARDING}/metrics/total/")
    assert status == 200 and len(payload["data"]["metrics"]) == 2
    status, payload = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/{MAIN_NA}/metrics/", None, {})
    assert status == 200 and payload["data"]["level"] == "root" and len(payload["data"]["items"]) == 2
    status, _ = s.dispatch("GET", f"/apps/{APP_ID}/ab-tests/nope/")
    assert status == 404
    status, _ = s.dispatch("GET", "/apps/x/unknown/")
    assert status == 404


def test_trailing_slash_is_optional_and_query_string_accepted():
    s = Store()
    status, payload = s.dispatch("GET", f"/apps/{APP_ID}/flows/metrics", "filter[flow_id]=16f65c46-6a6a-4ad8-81ab-14e5a4ae03bf")
    assert status == 200 and len(payload["data"]) == 1


def test_write_lifecycle():
    s = Store()
    status, _ = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/{DRAFT}/stop/", None, {})
    assert status == 400  # only live tests stop
    status, payload = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/{DRAFT}/start/", None, {"placement_id": "p", "segment_ids": []})
    assert status == 200 and payload["state"] == "live"
    status, _ = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/{ONBOARDING}/stop/", None, {})
    assert status == 400  # All users audience refuses no-content
    status, payload = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/{ONBOARDING}/stop/", None, {"winner_flow_id": "00ac93b0-487c-46a3-a72c-748fc64feadc"})
    assert status == 200 and payload["state"] == "completed"
    assert s.winners[ONBOARDING] == "00ac93b0-487c-46a3-a72c-748fc64feadc"
    status, _ = s.dispatch("DELETE", f"/apps/{APP_ID}/ab-tests/{MAIN_NA}/")
    assert status == 400  # live
    status, payload = s.dispatch("DELETE", f"/apps/{APP_ID}/ab-tests/{SETTINGS}/")
    assert status == 200 and payload["state"] == "archived"


def test_create_draft_and_placement_synthesis():
    s = Store()
    body = {"title": "New", "goal": "g", "placement_id": "75dae32c-b1a6-415b-a87b-834819e08a80",
            "flows": [{"flow_id": "16f65c46-6a6a-4ad8-81ab-14e5a4ae03bf", "weight": 50}, {"flow_id": "63861760-06be-4776-8185-5e53536cc72d", "weight": 50}]}
    status, payload = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/", None, body)
    assert status == 200 and payload["state"] == "draft" and payload["flows"][1]["title"] == "B"
    status, _ = s.dispatch("POST", f"/apps/{APP_ID}/ab-tests/", None, {"title": "x"})
    assert status == 400
    status, placement = s.dispatch("GET", f"/apps/{APP_ID}/placements/89eb1d46-d64f-4dec-b72f-97f348c0f19c/")
    assert status == 200 and placement["audiences"][0]["content_type"] == "flow"

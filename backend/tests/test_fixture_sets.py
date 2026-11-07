import pytest

from referee.adapty.store import FIXTURE_SETS, Store, fixtures_dir


def test_captured_set_loads_without_a_manifest():
    store = Store("captured")
    assert store.fixture_set == "captured"
    assert len(store.test_details) == 4
    assert "b2c90b2b-59b0-48fc-b821-b90061d1ae1e" in store.metrics_total


def test_unknown_set_is_rejected():
    with pytest.raises(ValueError):
        fixtures_dir("imaginary")


@pytest.mark.skipif(not FIXTURE_SETS["expanded"].exists(), reason="expanded set not generated")
def test_expanded_set_answers_the_same_routes():
    store = Store("expanded")
    assert store.fixture_set == "expanded"
    status, tests = store.dispatch("GET", "/apps/x/ab-tests/", {"type": ["flow"]})
    assert status == 200 and len(tests["data"]) >= 4
    for test in tests["data"]:
        detail_status, detail = store.dispatch("GET", f"/apps/x/ab-tests/{test['ab_test_id']}/")
        assert detail_status == 200 and detail["flows"], test["title"]
        if test["state"] != "draft":
            total_status, total = store.dispatch("GET", f"/apps/x/ab-tests/{test['ab_test_id']}/metrics/total/")
            assert total_status == 200 and len(total["data"]["metrics"]) == len(detail["flows"])
    status, placements = store.dispatch("GET", "/apps/x/placements/")
    assert status == 200 and placements["data"]

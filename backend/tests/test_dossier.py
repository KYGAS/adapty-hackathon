from datetime import timedelta

import pytest

from referee.models import Assumptions
from tests.conftest import DRAFT, MAIN_NA, NOW, ONBOARDING, SETTINGS


def test_onboarding_waits_for_trial_lag_despite_p2bb_100(make_dossier):
    d = make_dossier(ONBOARDING)
    assert d.verdict.code == "WAIT_TRIAL_LAG"
    leader = next(a for a in d.arms if a.is_leader)
    assert leader.title == "B" and leader.p2bb == 100.0
    control = next(a for a in d.arms if a.is_control)
    assert control.trials_pending == 66 and control.trial_days_max == 7
    assert control.matures_at == NOW + timedelta(days=8)  # 7-day trial plus one grace day
    assert d.trial_lag.leader_could_flip
    assert d.trial_lag.pending_trials_total == 137
    assert control.projected_rpv_high > leader.projected_rpv_low
    assert "They resolve on 15 Nov 2026" in d.verdict.headline
    # Resolved trials are not a call date: the headline must also name the sample gate.
    assert "safe call" not in d.verdict.headline and "planned sample" in d.verdict.headline
    assert d.actions[0].kind == "keep_running" and d.actions[0].recommended
    override = d.actions[1]
    assert override.kind == "stop_winner" and not override.recommended
    assert override.cli_command.startswith("adapty ab-tests stop b2c90b2b") and "--winner 00ac93b0" in override.cli_command


def test_onboarding_sample_size_and_mde(make_dossier):
    d = make_dossier(ONBOARDING)
    assert d.sample.baseline_source.startswith("pooled")
    assert d.sample.required_per_arm == 6172
    assert d.sample.min_views_per_arm == 254
    assert 0 < d.sample.progress < 0.1
    assert d.timeline.horizon_days == 60
    assert d.sample.mde_detectable_at_horizon < d.sample.mde_detectable_now
    assert d.pairwise[0].significant and d.pairwise[0].p_value < 1e-6


def test_main_na_is_not_decidable_at_this_traffic(make_dossier):
    d = make_dossier(MAIN_NA)
    assert d.verdict.code == "NOT_DECIDABLE"
    assert d.sample.required_per_arm > 10000
    assert d.sample.days_to_sample > d.assumptions.max_wait_days
    assert "revenue_range_unreliable_under_50_payers" in d.warnings
    assert d.verdict.leader_title == "B"


def test_bigger_mde_makes_main_na_a_waiting_test(make_dossier):
    d = make_dossier(MAIN_NA, assumptions=Assumptions(mde_relative=3.0, max_wait_days=365))
    assert d.verdict.code == "INSUFFICIENT_PAYERS"
    assert d.sample.required_per_arm < 500


def test_draft_is_ready_to_start(make_dossier):
    d = make_dossier(DRAFT)
    assert d.verdict.code == "NOT_STARTED"
    assert len(d.actions) == 1
    assert d.actions[0].kind == "start_draft"
    assert "--all-users" in d.actions[0].cli_command
    assert d.actions[0].api_body == {"placement_id": "0dfdf0d2-f36a-4b02-9b85-a654ecc3182e", "segment_ids": []}


def test_completed_test_has_no_action(make_dossier):
    d = make_dossier(SETTINGS)
    assert d.verdict.code == "COMPLETED"
    assert d.actions[0].kind == "none"
    assert d.sample.required_per_arm is None


def test_builder_is_deterministic(make_dossier):
    a = make_dossier(ONBOARDING).model_dump()
    b = make_dossier(ONBOARDING).model_dump()
    assert a == b


def test_clock_moves_the_verdict_forward(make_dossier):
    later = make_dossier(ONBOARDING, now=NOW + timedelta(days=30))
    # Thirty days on with the same counts the trials would be long matured; active_trials_rate from the API still says open,
    # so the referee keeps trusting the API flag.
    assert later.timeline.days_running == pytest.approx(30.54, abs=0.01)
    assert later.verdict.code == "WAIT_TRIAL_LAG"


def test_three_arm_tests_get_pairwise_correction(make_dossier, client, catalog):
    from referee.adapty.normalize import build_history_input, build_test_input
    from referee.dossier import build_dossier
    detail = client.get_test(ONBOARDING)
    detail["flows"].append({**detail["flows"][1], "flow_id": "third", "title": "C", "flow_name": "Third"})
    total = client.metrics_total(ONBOARDING)
    total["metrics"].append({**total["metrics"][0], "flow_id": "third", "title": "C", "views": 200, "purchases": 10, "revenue": 300.0})
    ti = build_test_input(detail, total, None, catalog)
    history = build_history_input(client.analytics_conversion("trial-paid", "2026-07-01", "2026-11-07"))
    d = build_dossier(ti, history, "app", NOW)
    assert len(d.pairwise) == 2
    assert "three_or_more_arms_adapty_p_value_absent_pairwise_holm_used" in d.warnings
    assert all(p.adjusted_p >= p.p_value for p in d.pairwise)


@pytest.mark.parametrize("reached, days, has_date, expected", [
    (True, 400.0, True, ""),
    (False, float("inf"), False, ", but the planned sample is out of reach at this traffic"),
    (False, 171.8, True, ", but the planned sample needs until 28 Apr 2027, past the 60-day limit"),
    (False, 20.0, True, "; the planned sample is reached around 28 Apr 2027"),
])
def test_after_trials_clause_names_the_sample_gate(reached, days, has_date, expected):
    from datetime import datetime, timezone
    from referee.dossier import after_trials_clause
    when = datetime(2027, 4, 28, 12, tzinfo=timezone.utc) if has_date else None
    assert after_trials_clause(reached, days, when, 60.0) == expected

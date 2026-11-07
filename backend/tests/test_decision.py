import math

from referee.stats.decision import Decision, DecisionInputs, VerdictCode, decide


def base(**overrides) -> DecisionInputs:
    values = dict(
        state="live", days_running=10.0, min_views_per_arm=5000, required_views_per_arm=3841,
        leader_payers=120, pending_could_flip=False, significant_vs_control=True, p2bb_leader=99.0,
        days_to_sample=0.0, days_to_maturity=0.0,
    )
    values.update(overrides)
    return DecisionInputs(**values)


def test_draft_and_finished_states():
    assert decide(base(state="draft")).code == VerdictCode.NOT_STARTED
    assert decide(base(state="completed")).code == VerdictCode.COMPLETED
    assert decide(base(state="archived")).reasons == ("state_archived",)


def test_trial_lag_beats_everything_else():
    d = decide(base(pending_could_flip=True, days_to_maturity=6.5, p2bb_leader=100.0))
    assert d.code == VerdictCode.WAIT_TRIAL_LAG
    assert d.wait_days == 6.5
    assert "open_trials_can_flip_leader" in d.reasons
    assert not d.is_call


def test_insufficient_payers_blocks_a_call():
    d = decide(base(leader_payers=35, days_to_sample=4.0))
    assert d.code == VerdictCode.INSUFFICIENT_PAYERS
    assert d.wait_days == 4.0
    reached = decide(base(leader_payers=35, days_to_sample=0.0))
    assert reached.code == VerdictCode.INSUFFICIENT_PAYERS
    assert reached.wait_days == 0.0


def test_unreachable_sample_outranks_insufficient_payers():
    d = decide(base(leader_payers=1, min_views_per_arm=40, days_to_sample=237.0))
    assert d.code == VerdictCode.NOT_DECIDABLE
    assert d.wait_days == 237.0


def test_call_winner():
    d = decide(base())
    assert d == Decision(VerdictCode.CALL_WINNER, 0.0, ("sample_reached", "significant_after_correction", "p2bb_above_threshold"))
    assert d.is_call


def test_min_runtime_guard_delays_a_call():
    d = decide(base(days_running=2.0))
    assert d.code == VerdictCode.WAIT_MIN_RUNTIME
    assert d.wait_days == 5.0


def test_call_no_difference_variants():
    not_sig = decide(base(significant_vs_control=False, p2bb_leader=70.0))
    assert not_sig.code == VerdictCode.CALL_NO_DIFFERENCE
    assert "not_significant" in not_sig.reasons and "p2bb_below_threshold" in not_sig.reasons
    disagree = decide(base(significant_vs_control=True, p2bb_leader=70.0))
    assert disagree.code == VerdictCode.CALL_NO_DIFFERENCE
    assert "significant_after_correction" in disagree.reasons
    other = decide(base(significant_vs_control=False, p2bb_leader=99.0))
    assert "p2bb_above_threshold" in other.reasons


def test_wait_for_sample_with_eta():
    d = decide(base(min_views_per_arm=300, days_to_sample=12.0))
    assert d.code == VerdictCode.WAIT_SAMPLE
    assert d.wait_days == 12.0
    assert "peeking_guard" in d.reasons


def test_not_decidable_when_sample_is_out_of_reach():
    assert decide(base(min_views_per_arm=300, days_to_sample=200.0)).code == VerdictCode.NOT_DECIDABLE
    assert decide(base(min_views_per_arm=300, days_to_sample=math.inf)).code == VerdictCode.NOT_DECIDABLE
    assert decide(base(min_views_per_arm=300, required_views_per_arm=None, days_to_sample=5.0)).code == VerdictCode.NOT_DECIDABLE

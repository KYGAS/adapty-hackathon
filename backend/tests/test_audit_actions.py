from datetime import timedelta

from referee import models
from referee.actions import action_as_text
from referee.audit import audit_completed, grade_from_score
from referee.dossier import build_dossier
from referee.models import ArmInput, HistoryInput
from tests.conftest import NOW, SETTINGS


def test_grades():
    assert [grade_from_score(s) for s in (100, 90, 80, 60, 45, 10)] == ["A", "A", "B", "C", "D", "F"]


def test_settings_audit_is_an_f_and_reversed(make_dossier, client):
    d = make_dossier(SETTINGS)
    winner = client.store.winners[SETTINGS]
    metrics = {m["flow_id"]: m for m in client.flow_metrics([a.flow_id for a in d.arms])}
    audit = audit_completed(d, winner, metrics)
    assert audit.grade == "F" and audit.score == 0
    assert audit.declared_winner_title.startswith("A (Settings - Upgrade)")
    assert audit.realized.status == "reversed"
    assert audit.realized.winner_rpv == 0.0 and audit.realized.alternative_rpv > 0


def test_strong_completed_test_grades_well():
    # 5% vs 6.5% paid conversion on 9,000 viewers per arm: above the 8,160 the 20% MDE plan needs.
    arms = [
        ArmInput(flow_id="ctl", title="A", flow_name="Control", views=9000, purchases=450, payers=450, revenue=22500.0, p2bb=1.0),
        ArmInput(flow_id="win", title="B", flow_name="Winner", views=9000, purchases=585, payers=585, revenue=30000.0, p2bb=99.0),
    ]
    test = models.TestInput(test_id="t", title="Strong", state="completed", started_at=NOW - timedelta(days=21), stopped_at=NOW,
                            arms=arms, winner_flow_id="win")
    d = build_dossier(test, HistoryInput(trials_started=700, trials_paid=300), "app", NOW)
    audit = audit_completed(d, "win", {"win": {"views": 1000, "revenue": 3500.0}, "ctl": {"views": 1000, "revenue": 2500.0}})
    assert audit.grade == "A"
    assert audit.realized.status == "confirmed"
    assert audit.evidence.p_value < 0.05


def test_action_text_lists_command_and_api_call(make_dossier):
    from tests.conftest import DRAFT
    text = action_as_text(make_dossier(DRAFT).actions[0])
    assert "adapty ab-tests start" in text and "POST /apps/" in text

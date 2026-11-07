from referee.llm.guard import allowed_numbers, check_memo, check_text, extract_numbers
from referee.llm.prompts import narration_view, template_memo
from referee.models import Memo
from tests.conftest import MAIN_NA, ONBOARDING, SETTINGS


def test_extract_numbers_handles_money_percent_and_thousands():
    assert extract_numbers("B made $1,527.90 on 285 viewers (12.28%) by 15 Nov 2026") == ["1527.90", "285", "12.28", "15", "2026"]
    assert extract_numbers("no digits here") == []


def test_allowed_numbers_variants():
    allowed = allowed_numbers({"a": 1527.9004, "b": 0.4409, "c": 285, "d": "15 Nov 2026", "e": True, "f": None})
    assert {"1528", "1527.9", "1527.90", "285"} <= allowed
    assert {"44", "44.1", "44.09", "0.44"} <= allowed
    assert {"15", "2026"} <= allowed
    assert "1" not in allowed  # booleans never count as numbers


def test_check_text_flags_unknown_numbers_only():
    allowed = allowed_numbers({"views": 285, "revenue": 1527.9})
    assert check_text("285 viewers made $1,528", allowed) == []
    violations = check_text("roughly 300 viewers and a 44% rate", allowed)
    assert len(violations) == 2
    assert violations[0].startswith("300 ") and violations[1].startswith("44 ")


def test_template_memo_passes_the_guard_for_every_seeded_test(make_dossier):
    for test_id in (ONBOARDING, MAIN_NA, SETTINGS):
        view = narration_view(make_dossier(test_id))
        memo = template_memo(view)
        assert check_memo(memo, view) == [], test_id
        assert memo.headline and memo.memo_markdown


def test_invented_number_in_llm_memo_is_caught(make_dossier):
    view = narration_view(make_dossier(ONBOARDING))
    memo = template_memo(view)
    tampered = Memo(**{**memo.model_dump(), "summary": "Arm A will earn about $2,000 more."})
    violations = check_memo(tampered, view)
    assert len(violations) == 1 and violations[0].startswith("2000 ")

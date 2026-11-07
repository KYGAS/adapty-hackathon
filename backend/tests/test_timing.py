import math
from datetime import datetime, timedelta, timezone

import pytest

from referee.stats.timing import (
    MIN_ELAPSED_DAYS,
    date_after,
    days_to_reach,
    elapsed_days,
    parse_horizon_days,
    viewers_per_day,
)

START = datetime(2026, 11, 7, 4, 7, 55, tzinfo=timezone.utc)


def test_elapsed_days_never_negative():
    assert elapsed_days(START, START + timedelta(hours=12)) == pytest.approx(0.5)
    assert elapsed_days(START, START - timedelta(days=1)) == 0.0


def test_viewers_per_day_floors_short_runs():
    assert viewers_per_day(539, 0.5) == pytest.approx(1078.0)
    assert viewers_per_day(539, 0.0) == pytest.approx(539 / MIN_ELAPSED_DAYS)
    with pytest.raises(ValueError):
        viewers_per_day(-1, 1.0)


def test_days_to_reach():
    assert days_to_reach(1000, 254, 508.0) == pytest.approx((1000 - 254) / 508.0)
    assert days_to_reach(100, 254, 10.0) == 0.0
    assert math.isinf(days_to_reach(1000, 10, 0.0))


def test_date_after():
    assert date_after(START, 1.5) == START + timedelta(days=1.5)
    assert date_after(START, math.inf) is None
    assert date_after(START, math.nan) is None


@pytest.mark.parametrize("goal,expected", [
    ("Find which onboarding offer maximises 60-day revenue per install", 60),
    ("Lift 14 day retention", 14),
    ("Maximise 2-week revenue", 14),
    ("Does a lifetime anchor lift annual share in North America?", 30),
    (None, 30),
    ("", 30),
])
def test_parse_horizon_days(goal, expected):
    assert parse_horizon_days(goal) == expected

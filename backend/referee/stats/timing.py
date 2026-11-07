"""Time to decision: how long until the sample size is reached and the trials have matured."""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta

MIN_ELAPSED_DAYS = 1.0 / 24.0  # below one hour the traffic rate is not meaningful


def elapsed_days(started_at: datetime, now: datetime) -> float:
    return max(0.0, (now - started_at).total_seconds() / 86400.0)


def viewers_per_day(views: int, elapsed: float) -> float:
    if views < 0:
        raise ValueError("views must not be negative")
    return views / max(elapsed, MIN_ELAPSED_DAYS)


def days_to_reach(target: int, current: int, rate_per_day: float) -> float:
    """Days until `current` grows to `target` at `rate_per_day`. 0 when already there, inf without traffic."""
    if current >= target:
        return 0.0
    if rate_per_day <= 0.0:
        return math.inf
    return (target - current) / rate_per_day


def date_after(now: datetime, days: float) -> datetime | None:
    if math.isinf(days) or math.isnan(days):
        return None
    return now + timedelta(days=days)


def parse_horizon_days(goal: str | None, default: int = 30) -> int:
    """Read the measurement horizon out of a goal such as 'maximises 60-day revenue per install'."""
    if not goal:
        return default
    match = re.search(r"(\d+)\s*-?\s*day", goal, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*-?\s*week", goal, flags=re.IGNORECASE)
    if match:
        return int(match.group(1)) * 7
    return default

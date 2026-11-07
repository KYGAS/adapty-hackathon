"""Conversion-rate estimates and the two-proportion z-test."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .normal import two_sided_p_value, z_for_confidence


@dataclass(frozen=True)
class Interval:
    low: float
    high: float


@dataclass(frozen=True)
class TwoProportionResult:
    p1: float
    p2: float
    difference: float
    relative_lift: float | None
    standard_error: float
    z: float
    p_value: float


def _check_counts(successes: int, trials: int) -> None:
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("successes must be between 0 and trials")


def proportion(successes: int, trials: int) -> float:
    _check_counts(successes, trials)
    return successes / trials if trials else 0.0


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> Interval:
    """Wilson score interval. With no trials the rate is unknown, so the interval is [0, 1]."""
    _check_counts(successes, trials)
    if trials == 0:
        return Interval(0.0, 1.0)
    z = z_for_confidence(confidence)
    n = float(trials)
    p = successes / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denominator
    margin = (z / denominator) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    return Interval(max(0.0, centre - margin), min(1.0, centre + margin))


def relative_lift(p_control: float, p_treatment: float) -> float | None:
    """(treatment - control) / control, undefined when the control rate is zero."""
    if p_control <= 0.0:
        return None
    return (p_treatment - p_control) / p_control


def two_proportion_z_test(x1: int, n1: int, x2: int, n2: int) -> TwoProportionResult:
    """Pooled two-sided z-test of H0: p1 == p2. Arm 1 is the control."""
    _check_counts(x1, n1)
    _check_counts(x2, n2)
    if n1 == 0 or n2 == 0:
        raise ValueError("both arms need at least one trial")
    p1 = x1 / n1
    p2 = x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n1 + 1.0 / n2))
    if se == 0.0:
        return TwoProportionResult(p1, p2, p2 - p1, relative_lift(p1, p2), 0.0, 0.0, 1.0)
    z = (p2 - p1) / se
    return TwoProportionResult(p1, p2, p2 - p1, relative_lift(p1, p2), se, z, two_sided_p_value(z))

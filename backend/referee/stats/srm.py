"""Sample ratio mismatch: does the observed traffic split match the configured weights?"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .normal import two_sided_p_value


@dataclass(frozen=True)
class SrmResult:
    total: int
    worst_arm: int
    expected_share: float
    observed_share: float
    z: float
    p_value: float
    mismatch: bool


def sample_ratio_mismatch(observed: list[int], weights: list[float], alpha: float = 0.01) -> SrmResult:
    """Per-arm binomial z-tests of observed share vs weight share, Bonferroni-combined across arms."""
    if len(observed) != len(weights) or not observed:
        raise ValueError("observed and weights must be non-empty and the same length")
    if any(o < 0 for o in observed) or any(w <= 0 for w in weights):
        raise ValueError("counts must be non-negative and weights positive")
    total = sum(observed)
    weight_sum = float(sum(weights))
    if total == 0:
        return SrmResult(0, 0, weights[0] / weight_sum, 0.0, 0.0, 1.0, False)
    worst = SrmResult(total, 0, weights[0] / weight_sum, observed[0] / total, 0.0, 1.0, False)
    for index, (count, weight) in enumerate(zip(observed, weights)):
        expected = weight / weight_sum
        observed_share = count / total
        se = math.sqrt(expected * (1.0 - expected) / total)
        z = (observed_share - expected) / se if se > 0 else 0.0
        p = min(1.0, two_sided_p_value(z) * len(observed))
        if p < worst.p_value or index == 0:
            worst = SrmResult(total, index, expected, observed_share, z, p, p < alpha)
    return worst

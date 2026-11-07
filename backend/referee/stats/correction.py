"""Multiple-comparison corrections for tests with three or more arms (pairwise against the control)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorrectedTest:
    index: int
    p_value: float
    adjusted_p: float
    rejected: bool


def _validate(p_values: list[float], alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1")
    for p in p_values:
        if not 0.0 <= p <= 1.0:
            raise ValueError("p-values must be between 0 and 1")


def bonferroni(p_values: list[float], alpha: float = 0.05) -> list[CorrectedTest]:
    _validate(p_values, alpha)
    m = len(p_values)
    return [CorrectedTest(i, p, min(1.0, p * m), min(1.0, p * m) <= alpha) for i, p in enumerate(p_values)]


def holm(p_values: list[float], alpha: float = 0.05) -> list[CorrectedTest]:
    """Holm step-down: uniformly more powerful than Bonferroni, same family-wise error control."""
    _validate(p_values, alpha)
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = min(1.0, (m - rank) * p_values[idx])
        running = max(running, candidate)
        adjusted[idx] = running
    return [CorrectedTest(i, p_values[i], adjusted[i], adjusted[i] <= alpha) for i in range(m)]


def correct(p_values: list[float], method: str = "holm", alpha: float = 0.05) -> list[CorrectedTest]:
    if method == "holm":
        return holm(p_values, alpha)
    if method == "bonferroni":
        return bonferroni(p_values, alpha)
    raise ValueError(f"unknown correction method: {method}")

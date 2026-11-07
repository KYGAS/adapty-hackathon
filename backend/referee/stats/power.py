"""Sample size, power and minimum detectable effect for a two-arm conversion test."""

from __future__ import annotations

import math

from .normal import norm_cdf, norm_ppf


def _validate_rates(p_control: float, p_treatment: float) -> None:
    if not 0.0 < p_control < 1.0:
        raise ValueError("p_control must be strictly between 0 and 1")
    if not 0.0 < p_treatment < 1.0:
        raise ValueError("p_treatment must be strictly between 0 and 1")


def _validate_alpha_power(alpha: float, power: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1")
    if not 0.0 < power < 1.0:
        raise ValueError("power must be strictly between 0 and 1")


def sample_size_per_arm_exact(p_control: float, p_treatment: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Unrounded viewers per arm so a two-sided pooled z-test detects p_treatment vs p_control."""
    _validate_rates(p_control, p_treatment)
    _validate_alpha_power(alpha, power)
    if p_treatment == p_control:
        raise ValueError("the rates must differ")
    z_alpha = norm_ppf(1.0 - alpha / 2.0)
    z_beta = norm_ppf(power)
    p_bar = (p_control + p_treatment) / 2.0
    numerator = z_alpha * math.sqrt(2.0 * p_bar * (1.0 - p_bar)) + \
        z_beta * math.sqrt(p_control * (1.0 - p_control) + p_treatment * (1.0 - p_treatment))
    return (numerator ** 2) / ((p_treatment - p_control) ** 2)


def required_sample_size_per_arm(p_control: float, mde_relative: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Viewers per arm needed to detect a relative lift of mde_relative (0.2 = 20%) over p_control."""
    if mde_relative == 0.0:
        raise ValueError("mde_relative must not be zero")
    p_treatment = p_control * (1.0 + mde_relative)
    return math.ceil(sample_size_per_arm_exact(p_control, p_treatment, alpha, power))


def power_at_sample_size(p_control: float, p_treatment: float, n_per_arm: int, alpha: float = 0.05) -> float:
    """Probability a two-sided pooled z-test at level alpha rejects H0 given the true rates and n viewers per arm."""
    _validate_rates(p_control, p_treatment)
    _validate_alpha_power(alpha, 0.5)
    if n_per_arm <= 0:
        raise ValueError("n_per_arm must be positive")
    z_alpha = norm_ppf(1.0 - alpha / 2.0)
    p_bar = (p_control + p_treatment) / 2.0
    se_null = math.sqrt(2.0 * p_bar * (1.0 - p_bar) / n_per_arm)
    se_alt = math.sqrt((p_control * (1.0 - p_control) + p_treatment * (1.0 - p_treatment)) / n_per_arm)
    delta = p_treatment - p_control
    upper = norm_cdf((delta - z_alpha * se_null) / se_alt)
    lower = norm_cdf((-delta - z_alpha * se_null) / se_alt)
    return min(1.0, upper + lower)


def mde_at_sample_size(p_control: float, n_per_arm: int, alpha: float = 0.05, power: float = 0.8,
                       tolerance: float = 1e-6) -> float:
    """Smallest relative lift detectable with n viewers per arm. Returns inf when even the largest lift is out of reach."""
    _validate_rates(p_control, 0.5)
    _validate_alpha_power(alpha, power)
    if n_per_arm <= 0:
        raise ValueError("n_per_arm must be positive")
    max_lift = (1.0 - p_control) / p_control * (1.0 - 1e-9)

    def needed(lift: float) -> float:
        return sample_size_per_arm_exact(p_control, p_control * (1.0 + lift), alpha, power)

    if needed(max_lift) > n_per_arm:
        return math.inf
    low, high = 0.0, max_lift
    while high - low > tolerance:
        mid = (low + high) / 2.0
        if needed(mid) > n_per_arm:
            low = mid
        else:
            high = mid
    return high

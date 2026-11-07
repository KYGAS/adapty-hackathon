"""Standard normal distribution helpers without scipy."""

from __future__ import annotations

import math

SQRT2 = math.sqrt(2.0)


def norm_cdf(z: float) -> float:
    """P(Z <= z) for a standard normal variable."""
    return 0.5 * (1.0 + math.erf(z / SQRT2))


def norm_sf(z: float) -> float:
    """P(Z > z), computed with erfc to keep precision in the tail."""
    return 0.5 * math.erfc(z / SQRT2)


def two_sided_p_value(z: float) -> float:
    """P(|Z| >= |z|)."""
    return 2.0 * norm_sf(abs(z))


# Coefficients of Acklam's rational approximation of the normal quantile.
_A = (-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
      1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00)
_B = (-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
      6.680131188771972e01, -1.328068155288572e01)
_C = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
      -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00)
_D = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
      3.754408661907416e00)
_P_LOW = 0.02425
_P_HIGH = 1.0 - _P_LOW


def norm_ppf(p: float) -> float:
    """Inverse of norm_cdf. Acklam's approximation followed by one Newton step (relative error below 1e-12)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be strictly between 0 and 1")
    if p < _P_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    elif p <= _P_HIGH:
        q = p - 0.5
        r = q * q
        x = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / \
            (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    # One Newton-Raphson refinement using the exact erf-based CDF.
    error = norm_cdf(x) - p
    density = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
    return x - error / density


def z_for_confidence(confidence: float) -> float:
    """Two-sided critical value, e.g. 1.96 for 0.95."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1")
    return norm_ppf(1.0 - (1.0 - confidence) / 2.0)

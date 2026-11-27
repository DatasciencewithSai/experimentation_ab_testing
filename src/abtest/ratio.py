"""Ratio metrics analyzed with the delta method.

A ratio metric divides two per-unit sums, e.g. clicks / page views or revenue /
sessions, where the unit of randomization (user) is coarser than the unit of
analysis (page view, session). Treating each page view as independent
understates the variance because page views from the same user are correlated.
The delta method gives the variance of the ratio of means from per-user totals.

Reference: Deng, Knoblich & Lu (2018), "Applying the Delta Method in Metric
Analytics"; Kohavi, Tang & Xu (2020), ch. 18.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class RatioEstimate:
    ratio: float  # sum(numerator) / sum(denominator)
    variance: float  # delta-method variance of the ratio
    n: int  # randomization units


@dataclass(frozen=True)
class RatioTestResult:
    effect: float  # ratio_b - ratio_a
    statistic: float  # z
    p_value: float
    ci_low: float
    ci_high: float
    ratio_a: float
    ratio_b: float
    relative_effect: float  # ratio_b / ratio_a - 1
    relative_ci_low: float
    relative_ci_high: float


def relative_lift(
    estimate_a: float,
    variance_a: float,
    estimate_b: float,
    variance_b: float,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Relative lift B / A - 1 and its delta-method confidence interval.

    Takes each arm's estimate (a mean, proportion or ratio) and the variance of
    that estimate, with the arms independent:
    Var(B/A) ≈ Var(B)/A² + B² Var(A)/A⁴. Returns NaNs when A is 0.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if variance_a < 0 or variance_b < 0:
        raise ValueError("variances must be non-negative")
    if estimate_a == 0:
        return math.nan, math.nan, math.nan
    rel = estimate_b / estimate_a - 1
    se = math.sqrt(variance_b / estimate_a**2 + estimate_b**2 * variance_a / estimate_a**4)
    crit = stats.norm.ppf(1 - alpha / 2)
    return rel, rel - crit * se, rel + crit * se


def _as_unit_arrays(numerator, denominator) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(numerator, dtype=float)
    y = np.asarray(denominator, dtype=float)
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError("numerator and denominator must be 1-D (one value per unit)")
    if x.shape != y.shape:
        raise ValueError("numerator and denominator must have the same length")
    if x.size < 2:
        raise ValueError("need at least 2 randomization units")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("numerator and denominator must be finite")
    if y.mean() == 0:
        raise ValueError("denominator must not sum to zero")
    return x, y


def delta_method_ratio(numerator, denominator) -> RatioEstimate:
    """Ratio of sums and its delta-method variance.

    Args:
        numerator: per-unit numerator totals (e.g. clicks per user).
        denominator: per-unit denominator totals (e.g. page views per user).

    Var(R) ≈ (Var(x) - 2 R Cov(x, y) + R² Var(y)) / (n ȳ²), with R = x̄ / ȳ.
    """
    x, y = _as_unit_arrays(numerator, denominator)
    n = x.size
    ratio = x.mean() / y.mean()
    cov = np.cov(x, y, ddof=1)
    var_x, var_y, cov_xy = cov[0, 0], cov[1, 1], cov[0, 1]
    variance = (var_x - 2 * ratio * cov_xy + ratio**2 * var_y) / (n * y.mean() ** 2)
    return RatioEstimate(float(ratio), float(max(variance, 0.0)), n)


def ratio_metric_test(
    numerator_a,
    denominator_a,
    numerator_b,
    denominator_b,
    alpha: float = 0.05,
) -> RatioTestResult:
    """Two-sided z-test for the difference in a ratio metric (B - A).

    Inputs are per-randomization-unit totals for control (A) and treatment (B).
    Also returns the relative lift ratio_b / ratio_a - 1 with a delta-method CI.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    a = delta_method_ratio(numerator_a, denominator_a)
    b = delta_method_ratio(numerator_b, denominator_b)
    crit = stats.norm.ppf(1 - alpha / 2)

    diff = b.ratio - a.ratio
    se = math.sqrt(a.variance + b.variance)
    z = diff / se if se > 0 else 0.0
    p_value = float(2 * stats.norm.sf(abs(z)))

    rel, rel_low, rel_high = relative_lift(a.ratio, a.variance, b.ratio, b.variance, alpha)

    return RatioTestResult(
        effect=diff,
        statistic=z,
        p_value=p_value,
        ci_low=diff - crit * se,
        ci_high=diff + crit * se,
        ratio_a=a.ratio,
        ratio_b=b.ratio,
        relative_effect=rel,
        relative_ci_low=rel_low,
        relative_ci_high=rel_high,
    )

"""Fixed-horizon frequentist tests."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class TestResult:
    effect: float  # treatment - control
    statistic: float
    p_value: float
    ci_low: float
    ci_high: float


def two_proportion_ztest(
    conversions_a: int,
    n_a: int,
    conversions_b: int,
    n_b: int,
    alpha: float = 0.05,
    pooled: bool = True,
) -> TestResult:
    """Two-sided z-test for difference in proportions (B - A).

    The CI always uses the unpooled SE. The test statistic uses the pooled SE
    (the classic test of p_a == p_b) unless ``pooled=False``, in which case it
    uses the same unpooled SE so the p-value and CI always agree.
    """
    if n_a <= 0 or n_b <= 0:
        raise ValueError("sample sizes must be positive")
    p_a, p_b = conversions_a / n_a, conversions_b / n_b
    p_pool = (conversions_a + conversions_b) / (n_a + n_b)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    diff = p_b - p_a
    se_test = se_pool if pooled else se
    z = diff / se_test if se_test > 0 else 0.0
    p_value = 2 * stats.norm.sf(abs(z))
    crit = stats.norm.ppf(1 - alpha / 2)
    return TestResult(diff, z, p_value, diff - crit * se, diff + crit * se)


def welch_ttest(a, b, alpha: float = 0.05) -> TestResult:
    """Welch's t-test for difference in means (mean(b) - mean(a))."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.size < 2 or b.size < 2:
        raise ValueError("each group needs at least 2 observations")
    va, vb = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    se = math.sqrt(va + vb)
    diff = b.mean() - a.mean()
    if se == 0:  # both arms constant: the difference is known exactly
        t = 0.0 if diff == 0 else math.copysign(math.inf, diff)
        return TestResult(diff, t, 1.0 if diff == 0 else 0.0, diff, diff)
    df = (va + vb) ** 2 / (va**2 / (a.size - 1) + vb**2 / (b.size - 1))
    t = diff / se
    p_value = 2 * stats.t.sf(abs(t), df)
    crit = stats.t.ppf(1 - alpha / 2, df)
    return TestResult(diff, t, p_value, diff - crit * se, diff + crit * se)

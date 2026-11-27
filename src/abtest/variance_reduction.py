"""Variance reduction with pre-experiment data (CUPED).

CUPED (Controlled-experiment Using Pre-Experiment Data) adjusts each unit's metric
with a covariate measured before the experiment started, usually the same metric
in a pre-period. Because the covariate cannot be affected by the treatment, the
adjustment leaves the effect unbiased while removing the variance it explains:
the variance shrinks by a factor of about 1 - corr(Y, X)².

Reference: Deng, Xu, Kohavi & Walker (2013), "Improving the Sensitivity of Online
Controlled Experiments by Utilizing Pre-Experiment Data"; Kohavi, Tang & Xu
(2020), ch. 22.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from abtest.frequentist import TestResult, welch_ttest


@dataclass(frozen=True)
class CupedResult:
    effect: float  # treatment - control, CUPED-adjusted
    statistic: float
    p_value: float
    ci_low: float
    ci_high: float
    theta: float  # adjustment coefficient Cov(Y, X) / Var(X), pooled over both arms
    variance_reduction: float  # 1 - Var(adjusted) / Var(raw), pooled over both arms
    unadjusted: TestResult  # Welch's t-test on the raw metric, for comparison


def _check_pair(y, x, name: str) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    if y.ndim != 1 or x.ndim != 1:
        raise ValueError(f"{name}: metric and covariate must be 1-D (one value per unit)")
    if y.shape != x.shape:
        raise ValueError(f"{name}: metric and covariate must have the same length")
    if y.size < 2:
        raise ValueError(f"{name}: need at least 2 units")
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(x))):
        raise ValueError(f"{name}: metric and covariate must be finite")
    return y, x


def cuped(
    metric_a,
    covariate_a,
    metric_b,
    covariate_b,
    alpha: float = 0.05,
) -> CupedResult:
    """CUPED-adjusted Welch's t-test for the difference in means (B - A).

    Args:
        metric_a, metric_b: per-unit metric during the experiment.
        covariate_a, covariate_b: per-unit pre-experiment covariate (e.g. the same
            metric in the weeks before). Units with no history can use 0, ideally
            with the share of such units balanced across arms.
        alpha: significance level for the confidence interval.

    theta is estimated on both arms pooled, and the covariate is centered on the
    pooled mean, so the adjusted means stay on the original scale.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    ya, xa = _check_pair(metric_a, covariate_a, "control")
    yb, xb = _check_pair(metric_b, covariate_b, "treatment")

    y, x = np.concatenate([ya, yb]), np.concatenate([xa, xb])
    var_x = x.var(ddof=1)
    if var_x == 0:
        raise ValueError("covariate is constant, so it cannot reduce variance")
    theta = float(np.cov(y, x, ddof=1)[0, 1] / var_x)
    x_mean = x.mean()

    adj_a = ya - theta * (xa - x_mean)
    adj_b = yb - theta * (xb - x_mean)
    adjusted = welch_ttest(adj_a, adj_b, alpha=alpha)

    var_y = y.var(ddof=1)
    var_adj = np.concatenate([adj_a, adj_b]).var(ddof=1)
    reduction = float(1 - var_adj / var_y) if var_y > 0 else 0.0

    return CupedResult(
        effect=adjusted.effect,
        statistic=adjusted.statistic,
        p_value=adjusted.p_value,
        ci_low=adjusted.ci_low,
        ci_high=adjusted.ci_high,
        theta=theta,
        variance_reduction=reduction,
        unadjusted=welch_ttest(ya, yb, alpha=alpha),
    )

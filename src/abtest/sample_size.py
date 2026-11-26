"""Sample size calculations for two-arm tests (per-arm sizes)."""

from __future__ import annotations

import math

from scipy.stats import norm


def _z(alpha: float, power: float, two_sided: bool) -> tuple[float, float]:
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be in (0, 1)")
    z_alpha = norm.ppf(1 - alpha / 2) if two_sided else norm.ppf(1 - alpha)
    return z_alpha, norm.ppf(power)


def sample_size_proportions(
    baseline: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
    relative: bool = False,
    two_sided: bool = True,
) -> int:
    """Per-arm sample size to detect a change in a conversion rate.

    baseline: control conversion rate, e.g. 0.10.
    mde: minimum detectable effect; absolute (0.01 = +1pp) unless relative=True.
    """
    if not 0 < baseline < 1:
        raise ValueError("baseline must be in (0, 1)")
    p2 = baseline * (1 + mde) if relative else baseline + mde
    if not 0 < p2 < 1 or p2 == baseline:
        raise ValueError("baseline + mde must be in (0, 1) and differ from baseline")
    z_a, z_b = _z(alpha, power, two_sided)
    p_bar = (baseline + p2) / 2
    num = (
        z_a * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_b * math.sqrt(baseline * (1 - baseline) + p2 * (1 - p2))
    ) ** 2
    return math.ceil(num / (p2 - baseline) ** 2)


def sample_size_means(
    std: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
    two_sided: bool = True,
) -> int:
    """Per-arm sample size to detect an absolute difference `mde` in means."""
    if std <= 0 or mde == 0:
        raise ValueError("std must be > 0 and mde non-zero")
    z_a, z_b = _z(alpha, power, two_sided)
    return math.ceil(2 * (z_a + z_b) ** 2 * std**2 / mde**2)

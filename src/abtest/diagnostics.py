"""Trustworthiness checks run before reading an experiment's results."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats

# Kohavi, Tang & Xu (2020), ch. 21, suggest a conservative threshold: with many
# experiments a day, a 0.05 cut-off raises too many false SRM alarms.
DEFAULT_SRM_THRESHOLD = 0.0005


@dataclass(frozen=True)
class SRMResult:
    statistic: float  # Pearson chi-square
    p_value: float
    df: int
    observed: tuple[int, ...]
    expected: tuple[float, ...]
    observed_ratios: tuple[float, ...]
    expected_ratios: tuple[float, ...]
    srm_detected: bool  # p_value < threshold: do not trust the results until explained


def srm_test(
    observed: Sequence[int],
    expected_ratios: Sequence[float] | None = None,
    threshold: float = DEFAULT_SRM_THRESHOLD,
) -> SRMResult:
    """Sample ratio mismatch (SRM) check: chi-square goodness-of-fit of the split.

    Args:
        observed: units (e.g. users) assigned to each variant, control first.
        expected_ratios: design allocation, e.g. ``(0.5, 0.5)`` or ``(1, 1, 2)``;
            normalized to sum to 1. Defaults to an equal split.
        threshold: flag SRM when the p-value is below this.

    Example (Kohavi et al. 2020, ch. 3): ``srm_test([821_588, 815_482])`` gives
    p ≈ 1.8e-6 for a design 50/50 split, so the experiment should not be trusted.
    """
    counts = np.asarray(observed, dtype=float)
    if counts.ndim != 1 or counts.size < 2:
        raise ValueError("observed must list counts for at least 2 variants")
    if not np.all(np.isfinite(counts)) or np.any(counts < 0):
        raise ValueError("observed counts must be finite and non-negative")
    if np.any(counts != np.round(counts)):
        raise ValueError("observed counts must be integers")
    total = counts.sum()
    if total <= 0:
        raise ValueError("observed counts must not all be zero")
    if not 0 < threshold < 1:
        raise ValueError("threshold must be in (0, 1)")

    if expected_ratios is None:
        ratios = np.full(counts.size, 1 / counts.size)
    else:
        ratios = np.asarray(expected_ratios, dtype=float)
        if ratios.shape != counts.shape:
            raise ValueError("expected_ratios must have one entry per variant")
        if not np.all(np.isfinite(ratios)) or np.any(ratios <= 0):
            raise ValueError("expected_ratios must be finite and positive")
        ratios = ratios / ratios.sum()

    expected = total * ratios
    statistic = float(np.sum((counts - expected) ** 2 / expected))
    df = counts.size - 1
    p_value = float(stats.chi2.sf(statistic, df))
    return SRMResult(
        statistic=statistic,
        p_value=p_value,
        df=df,
        observed=tuple(int(c) for c in counts),
        expected=tuple(float(e) for e in expected),
        observed_ratios=tuple(float(c / total) for c in counts),
        expected_ratios=tuple(float(r) for r in ratios),
        srm_detected=p_value < threshold,
    )

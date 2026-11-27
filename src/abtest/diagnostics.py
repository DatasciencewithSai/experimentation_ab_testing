"""Trustworthiness checks run before reading an experiment's results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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


@dataclass(frozen=True)
class AASimulationResult:
    p_values: np.ndarray  # one per simulated A/A split
    alpha: float
    false_positive_rate: float  # share of splits with p < alpha; should be close to alpha
    fpr_binomial_p: float  # two-sided binomial test of false_positive_rate == alpha
    ks_statistic: float  # Kolmogorov-Smirnov distance of p-values from Uniform(0, 1)
    ks_p_value: float
    looks_valid: bool  # neither check rejects at the given threshold


def aa_test_simulation(
    data,
    test: Callable | None = None,
    n_sims: int = 1000,
    alpha: float = 0.05,
    treatment_share: float = 0.5,
    threshold: float = 0.01,
    seed: int | None = 0,
) -> AASimulationResult:
    """Replay random A/A splits of historical data to validate an analysis.

    With no real difference between arms, a trustworthy pipeline gives p-values
    that are Uniform(0, 1), so about ``alpha`` of splits come out significant
    (Kohavi, Tang & Xu 2020, ch. 19). Skewed metrics, too few units, or a
    variance formula that ignores the unit of randomization all show up here.

    Args:
        data: per-unit values, either one array or a tuple of equal-length arrays
            (e.g. ``(clicks, views)`` for a ratio metric).
        test: called as ``test(*arrays_a, *arrays_b)`` and must return an object
            with a ``p_value`` attribute. Defaults to Welch's t-test for one array
            and the delta-method ratio test for two.
        n_sims: number of random splits.
        alpha: significance level whose false positive rate is checked.
        treatment_share: fraction of units assigned to B in each split.
        threshold: ``looks_valid`` is False if either check has p below this.
        seed: random seed, for reproducible results.
    """
    arrays = (data,) if isinstance(data, np.ndarray) or np.ndim(data[0]) == 0 else tuple(data)
    arrays = tuple(np.asarray(a) for a in arrays)
    if any(a.ndim != 1 for a in arrays):
        raise ValueError("data must be one 1-D array or a tuple of 1-D arrays")
    n = arrays[0].size
    if any(a.size != n for a in arrays):
        raise ValueError("all data arrays must have the same length")
    if n_sims < 10:
        raise ValueError("n_sims must be at least 10")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if not 0 < treatment_share < 1:
        raise ValueError("treatment_share must be in (0, 1)")
    if not 0 < threshold < 1:
        raise ValueError("threshold must be in (0, 1)")
    n_b = int(round(n * treatment_share))
    if n_b < 2 or n - n_b < 2:
        raise ValueError("each arm needs at least 2 units")

    if test is None:
        if len(arrays) == 1:
            from abtest.frequentist import welch_ttest as test
        elif len(arrays) == 2:
            from abtest.ratio import ratio_metric_test as test
        else:
            raise ValueError("pass a test function for more than 2 data arrays")

    rng = np.random.default_rng(seed)
    p_values = np.empty(n_sims)
    for i in range(n_sims):
        perm = rng.permutation(n)
        idx_a, idx_b = perm[n_b:], perm[:n_b]
        result = test(*(a[idx_a] for a in arrays), *(a[idx_b] for a in arrays))
        p_values[i] = result.p_value

    false_positives = int(np.sum(p_values < alpha))
    fpr_p = float(stats.binomtest(false_positives, n_sims, alpha).pvalue)
    ks = stats.kstest(p_values, "uniform")
    return AASimulationResult(
        p_values=p_values,
        alpha=alpha,
        false_positive_rate=false_positives / n_sims,
        fpr_binomial_p=fpr_p,
        ks_statistic=float(ks.statistic),
        ks_p_value=float(ks.pvalue),
        looks_valid=fpr_p >= threshold and ks.pvalue >= threshold,
    )

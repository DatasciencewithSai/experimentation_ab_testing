import numpy as np
import pytest

from abtest import delta_method_ratio, ratio_metric_test, welch_ttest


def _simulate_users(rng, n, ctr):
    """Per-user page views and clicks with user-level heterogeneity in CTR."""
    views = rng.poisson(5, n) + 1
    user_ctr = rng.beta(ctr * 4, (1 - ctr) * 4, n)
    clicks = rng.binomial(views, user_ctr)
    return clicks, views


def test_variance_matches_bootstrap():
    rng = np.random.default_rng(7)
    clicks, views = _simulate_users(rng, 2000, 0.1)
    est = delta_method_ratio(clicks, views)
    idx = rng.integers(0, clicks.size, size=(4000, clicks.size))
    boot = clicks[idx].sum(axis=1) / views[idx].sum(axis=1)
    assert est.ratio == pytest.approx(clicks.sum() / views.sum())
    assert est.variance == pytest.approx(boot.var(ddof=1), rel=0.1)


def test_reduces_to_welch_when_denominator_is_one():
    rng = np.random.default_rng(3)
    a, b = rng.normal(10, 2, 500), rng.normal(10.3, 3, 400)
    r = ratio_metric_test(a, np.ones_like(a), b, np.ones_like(b))
    w = welch_ttest(a, b)
    assert r.effect == pytest.approx(w.effect)
    assert r.statistic == pytest.approx(w.statistic)


def test_aa_false_positive_rate_near_alpha():
    rng = np.random.default_rng(11)
    p_values = []
    for _ in range(1000):
        ca, va = _simulate_users(rng, 500, 0.1)
        cb, vb = _simulate_users(rng, 500, 0.1)
        p_values.append(ratio_metric_test(ca, va, cb, vb).p_value)
    assert np.mean(np.array(p_values) < 0.05) == pytest.approx(0.05, abs=0.02)


def test_naive_pageview_level_variance_is_too_small():
    # Treating page views as independent Bernoulli trials understates the variance.
    rng = np.random.default_rng(5)
    clicks, views = _simulate_users(rng, 2000, 0.1)
    est = delta_method_ratio(clicks, views)
    naive = est.ratio * (1 - est.ratio) / views.sum()
    assert est.variance > 1.5 * naive


def test_detects_effect_and_relative_lift():
    rng = np.random.default_rng(9)
    ca, va = _simulate_users(rng, 5000, 0.10)
    cb, vb = _simulate_users(rng, 5000, 0.12)
    r = ratio_metric_test(ca, va, cb, vb)
    assert r.effect == pytest.approx(r.ratio_b - r.ratio_a)
    assert r.p_value < 0.001
    assert r.ci_low > 0
    assert r.relative_effect == pytest.approx(r.ratio_b / r.ratio_a - 1)
    assert r.relative_ci_low < r.relative_effect < r.relative_ci_high
    assert r.relative_ci_low > 0


@pytest.mark.parametrize(
    "num, den",
    [
        ([1.0], [1.0]),
        ([1.0, 2.0], [1.0]),
        ([1.0, 2.0], [0.0, 0.0]),
        ([1.0, np.nan], [1.0, 1.0]),
        ([[1.0, 2.0]], [[1.0, 1.0]]),
    ],
)
def test_invalid_inputs(num, den):
    with pytest.raises(ValueError):
        delta_method_ratio(num, den)


def test_invalid_alpha():
    with pytest.raises(ValueError):
        ratio_metric_test([1, 2], [1, 1], [1, 2], [1, 1], alpha=1.5)


def test_relative_effect_sign_with_negative_baseline():
    a, b = np.array([-10.0, -12.0, -8.0]), np.array([-9.0, -11.0, -7.0])
    r = ratio_metric_test(a, np.ones(3), b, np.ones(3))
    assert r.relative_effect == pytest.approx(0.1)  # B is higher, so the lift is positive

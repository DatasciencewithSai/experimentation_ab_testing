import numpy as np
import pytest

from abtest import cuped


def _simulate(rng, n, effect=0.0, rho=0.8):
    """Pre-period covariate x and in-experiment metric y with corr(x, y) = rho."""
    x = rng.normal(10, 2, n)
    noise = rng.normal(0, 2, n)
    y = 10 + rho * (x - 10) + np.sqrt(1 - rho**2) * noise + effect
    return y, x


def test_theta_is_pooled_regression_slope():
    rng = np.random.default_rng(1)
    ya, xa = _simulate(rng, 1000)
    yb, xb = _simulate(rng, 1000, effect=0.1)
    r = cuped(ya, xa, yb, xb)
    slope = np.polyfit(np.concatenate([xa, xb]), np.concatenate([ya, yb]), 1)[0]
    assert r.theta == pytest.approx(slope)


def test_variance_reduction_is_about_rho_squared():
    rng = np.random.default_rng(2)
    ya, xa = _simulate(rng, 20_000, rho=0.7)
    yb, xb = _simulate(rng, 20_000, rho=0.7)
    r = cuped(ya, xa, yb, xb)
    assert r.variance_reduction == pytest.approx(0.49, abs=0.02)
    width = r.ci_high - r.ci_low
    raw_width = r.unadjusted.ci_high - r.unadjusted.ci_low
    assert width == pytest.approx(raw_width * np.sqrt(1 - 0.49), rel=0.03)


def test_matches_ancova_regression():
    # OLS of y on [1, treatment, x] gives nearly the same effect (it uses the
    # within-arm slope instead of the pooled one).
    rng = np.random.default_rng(3)
    ya, xa = _simulate(rng, 3000)
    yb, xb = _simulate(rng, 3000, effect=0.2)
    r = cuped(ya, xa, yb, xb)
    y = np.concatenate([ya, yb])
    design = np.column_stack(
        [np.ones(y.size), np.r_[np.zeros(ya.size), np.ones(yb.size)], np.r_[xa, xb]]
    )
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    assert r.effect == pytest.approx(coef[1], abs=0.005)


def test_unbiased_and_more_powerful():
    rng = np.random.default_rng(4)
    effects, raw_effects, rejections, raw_rejections = [], [], 0, 0
    for _ in range(500):
        ya, xa = _simulate(rng, 300)
        yb, xb = _simulate(rng, 300, effect=0.15)
        r = cuped(ya, xa, yb, xb)
        effects.append(r.effect)
        raw_effects.append(r.unadjusted.effect)
        rejections += r.p_value < 0.05
        raw_rejections += r.unadjusted.p_value < 0.05
    assert np.mean(effects) == pytest.approx(0.15, abs=0.01)
    assert np.std(effects) < 0.7 * np.std(raw_effects)
    assert rejections > raw_rejections


def test_aa_false_positive_rate_near_alpha():
    rng = np.random.default_rng(5)
    p_values = []
    for _ in range(1000):
        ya, xa = _simulate(rng, 200)
        yb, xb = _simulate(rng, 200)
        p_values.append(cuped(ya, xa, yb, xb).p_value)
    assert np.mean(np.array(p_values) < 0.05) == pytest.approx(0.05, abs=0.02)


@pytest.mark.parametrize(
    "args",
    [
        ([1.0], [1.0], [1.0, 2.0], [1.0, 2.0]),
        ([1.0, 2.0], [1.0], [1.0, 2.0], [1.0, 2.0]),
        ([1.0, np.nan], [1.0, 2.0], [1.0, 2.0], [1.0, 2.0]),
        ([1.0, 2.0], [3.0, 3.0], [1.0, 2.0], [3.0, 3.0]),
    ],
)
def test_invalid_inputs(args):
    with pytest.raises(ValueError):
        cuped(*args)


def test_invalid_alpha():
    with pytest.raises(ValueError):
        cuped([1, 2], [1, 2], [1, 2], [2, 1], alpha=0)

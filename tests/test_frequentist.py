import numpy as np
import pytest
from scipy import stats

from abtest import two_proportion_ztest, welch_ttest


def test_ztest_no_difference():
    r = two_proportion_ztest(100, 1000, 100, 1000)
    assert r.effect == 0
    assert r.p_value == 1.0


def test_ztest_significant():
    r = two_proportion_ztest(100, 1000, 150, 1000)
    assert r.p_value < 0.01
    assert r.ci_low > 0


def test_welch_matches_scipy():
    rng = np.random.default_rng(1)
    a, b = rng.normal(0, 1, 200), rng.normal(0.3, 2, 150)
    r = welch_ttest(a, b)
    ref = stats.ttest_ind(b, a, equal_var=False)
    assert np.isclose(r.statistic, ref.statistic)
    assert np.isclose(r.p_value, ref.pvalue)


def test_welch_zero_variance():
    same = welch_ttest([1.0, 1.0, 1.0], [1.0, 1.0])
    assert same.p_value == 1.0 and same.effect == 0
    shifted = welch_ttest([1.0, 1.0, 1.0], [2.0, 2.0])
    assert shifted.p_value == 0.0 and shifted.ci_low == shifted.ci_high == 1.0


def test_ztest_unpooled_matches_manual():
    r = two_proportion_ztest(100, 1000, 130, 1200, pooled=False)
    p_a, p_b = 0.1, 130 / 1200
    se = np.sqrt(p_a * (1 - p_a) / 1000 + p_b * (1 - p_b) / 1200)
    assert r.statistic == pytest.approx((p_b - p_a) / se)
    assert r.p_value == pytest.approx(2 * stats.norm.sf(abs(r.statistic)))

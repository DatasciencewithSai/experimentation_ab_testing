import numpy as np
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

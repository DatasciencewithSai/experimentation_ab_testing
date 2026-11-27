import numpy as np
import pytest
from scipy import stats

from abtest import srm_test


def test_kohavi_book_example():
    # Kohavi, Tang & Xu (2020), ch. 3: 821,588 vs 815,482 on a 50/50 design, p ≈ 1.8e-6
    r = srm_test([821_588, 815_482])
    assert r.p_value == pytest.approx(1.8e-6, rel=0.02)
    assert r.srm_detected


def test_matches_scipy_chisquare_unequal_split():
    observed = [10_120, 9_870, 20_310]
    r = srm_test(observed, expected_ratios=[1, 1, 2])
    expected = np.array([0.25, 0.25, 0.5]) * sum(observed)
    ref = stats.chisquare(observed, f_exp=expected)
    assert r.statistic == pytest.approx(ref.statistic)
    assert r.p_value == pytest.approx(ref.pvalue)
    assert r.df == 2
    assert r.expected_ratios == pytest.approx((0.25, 0.25, 0.5))


def test_balanced_split_not_flagged():
    r = srm_test([5000, 5000])
    assert r.statistic == 0
    assert r.p_value == 1.0
    assert not r.srm_detected


def test_false_alarm_rate_under_correct_assignment():
    rng = np.random.default_rng(0)
    p_values = [srm_test(rng.multinomial(10_000, [0.5, 0.5])).p_value for _ in range(2000)]
    assert np.mean(np.array(p_values) < 0.05) == pytest.approx(0.05, abs=0.015)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"observed": [100]},
        {"observed": [100, -1]},
        {"observed": [100, 1.5]},
        {"observed": [0, 0]},
        {"observed": [100, 100], "expected_ratios": [1, 1, 1]},
        {"observed": [100, 100], "expected_ratios": [1, 0]},
        {"observed": [100, 100], "threshold": 0},
    ],
)
def test_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        srm_test(**kwargs)

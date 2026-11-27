import numpy as np
import pytest
from scipy import stats

from abtest import aa_test_simulation, srm_test, two_proportion_ztest, welch_ttest


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


# --- A/A simulation -------------------------------------------------------------


def _users(rng, n):
    views = rng.poisson(5, n) + 1
    clicks = rng.binomial(views, rng.beta(0.4, 3.6, n))
    return clicks, views


def test_aa_valid_for_normal_metric():
    rng = np.random.default_rng(0)
    r = aa_test_simulation(rng.normal(10, 3, 2000), n_sims=1000, seed=1)
    assert r.p_values.shape == (1000,)
    assert r.false_positive_rate == pytest.approx(0.05, abs=0.02)
    assert r.looks_valid


def test_aa_ks_matches_scipy():
    rng = np.random.default_rng(0)
    r = aa_test_simulation(rng.normal(size=500), n_sims=200, seed=2)
    ref = stats.kstest(r.p_values, "uniform")
    assert r.ks_statistic == pytest.approx(ref.statistic)
    assert r.ks_p_value == pytest.approx(ref.pvalue)


def test_aa_is_reproducible_with_seed():
    data = np.random.default_rng(0).exponential(size=300)
    r1 = aa_test_simulation(data, n_sims=50, seed=7)
    r2 = aa_test_simulation(data, n_sims=50, seed=7)
    assert np.array_equal(r1.p_values, r2.p_values)


def test_aa_valid_for_ratio_metric_with_delta_method():
    clicks, views = _users(np.random.default_rng(3), 3000)
    r = aa_test_simulation((clicks, views), n_sims=1000, seed=4)
    assert r.looks_valid


def test_aa_catches_naive_pageview_level_analysis():
    # Treating each page view as an independent trial ignores that users were
    # randomized, so A/A tests come out "significant" far more often than 5%.
    clicks, views = _users(np.random.default_rng(3), 3000)

    def naive_test(clicks_a, views_a, clicks_b, views_b):
        return two_proportion_ztest(clicks_a.sum(), views_a.sum(), clicks_b.sum(), views_b.sum())

    r = aa_test_simulation((clicks, views), test=naive_test, n_sims=1000, seed=4)
    assert r.false_positive_rate > 0.1
    assert not r.looks_valid


def test_aa_unequal_split():
    rng = np.random.default_rng(0)
    seen = []

    def record(a, b):
        seen.append((a.size, b.size))
        return welch_ttest(a, b)

    aa_test_simulation(rng.normal(size=1000), test=record, n_sims=10, treatment_share=0.2)
    assert seen[0] == (800, 200)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": ([1.0, 2.0, 3.0, 4.0], [1.0, 2.0])},
        {"data": [[[1.0, 2.0]]]},
        {"data": [1.0, 2.0, 3.0, 4.0, 5.0], "n_sims": 5},
        {"data": [1.0, 2.0, 3.0, 4.0, 5.0], "alpha": 1},
        {"data": [1.0, 2.0, 3.0, 4.0, 5.0], "treatment_share": 1},
        {"data": [1.0, 2.0, 3.0], "treatment_share": 0.5},
        {"data": ([1.0] * 10, [1.0] * 10, [1.0] * 10)},
        {"data": []},
        {"data": ()},
    ],
)
def test_aa_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        aa_test_simulation(**kwargs)

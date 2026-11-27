import numpy as np
import pytest
from scipy import stats

from abtest import (
    Metric,
    adjust_p_values,
    cuped,
    ratio_metric_test,
    relative_lift,
    scorecard,
    two_proportion_ztest,
    welch_ttest,
)

# --- adjust_p_values ------------------------------------------------------------


def test_holm_known_values():
    # sorted: 0.005*4=0.02, 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> cumulative max
    adj = adjust_p_values([0.01, 0.04, 0.03, 0.005], method="holm")
    assert adj == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_bh_matches_scipy():
    p = np.random.default_rng(0).uniform(0, 0.2, 25)
    assert adjust_p_values(p, "bh") == pytest.approx(stats.false_discovery_control(p))


def test_bonferroni_and_none():
    p = [0.01, 0.3, 0.5]
    assert adjust_p_values(p, "bonferroni") == pytest.approx([0.03, 0.9, 1.0])
    assert adjust_p_values(p, "none") == pytest.approx(p)
    assert adjust_p_values([], "bh").size == 0


@pytest.mark.parametrize("p, method", [([0.1, 1.2], "bh"), ([np.nan], "bh"), ([0.1], "x")])
def test_adjust_invalid(p, method):
    with pytest.raises(ValueError):
        adjust_p_values(p, method)


# --- relative_lift --------------------------------------------------------------


def test_relative_lift_coverage():
    # The delta-method CI for B/A - 1 should cover the true lift ~95% of the time.
    rng = np.random.default_rng(1)
    covered = 0
    for _ in range(1000):
        a, b = rng.normal(10, 3, 1000), rng.normal(10.5, 3, 1000)
        _, lo, hi = relative_lift(a.mean(), a.var(ddof=1) / 1000, b.mean(), b.var(ddof=1) / 1000)
        covered += lo < 0.05 < hi
    assert covered / 1000 == pytest.approx(0.95, abs=0.02)


def test_relative_lift_zero_baseline_and_invalid():
    assert all(np.isnan(relative_lift(0.0, 0.1, 1.0, 0.1)))
    with pytest.raises(ValueError):
        relative_lift(1.0, -0.1, 1.0, 0.1)


# --- scorecard ------------------------------------------------------------------


def _users(rng, n, ctr):
    views = rng.poisson(5, n) + 1
    clicks = rng.binomial(views, rng.beta(ctr * 4, (1 - ctr) * 4, n))
    return clicks, views


@pytest.fixture
def data():
    rng = np.random.default_rng(42)
    n = 5000
    pre_a, pre_b = rng.gamma(2, 10, n), rng.gamma(2, 10, n)
    rev_a = 0.8 * pre_a + rng.gamma(2, 5, n)
    rev_b = 0.8 * pre_b + rng.gamma(2, 5, n) * 1.15  # treatment raises revenue
    load_a, load_b = rng.normal(1.0, 0.2, n), rng.normal(1.0, 0.2, n)
    clicks_a, views_a = _users(rng, n, 0.10)
    clicks_b, views_b = _users(rng, n, 0.10)
    return dict(
        n=n,
        rev=(rev_a, rev_b),
        pre=(pre_a, pre_b),
        load=(load_a, load_b),
        ctr=(clicks_a, views_a, clicks_b, views_b),
    )


def test_each_metric_matches_its_underlying_test(data):
    ra, rb = data["rev"]
    pa, pb = data["pre"]
    card = scorecard(
        [
            Metric.mean("revenue", ra, rb, covariate_a=pa, covariate_b=pb, role="oec"),
            Metric.mean("revenue_raw", ra, rb),
            Metric.proportion("conversion", 500, 5000, 560, 5000),
            Metric.ratio("ctr", *data["ctr"]),
        ],
        correction="none",
    )
    c, w = cuped(ra, pa, rb, pb), welch_ttest(ra, rb)
    z, r = two_proportion_ztest(500, 5000, 560, 5000, pooled=False), ratio_metric_test(*data["ctr"])
    assert card["revenue"].effect == pytest.approx(c.effect)
    assert card["revenue"].p_value == pytest.approx(c.p_value)
    assert card["revenue"].cuped and not card["revenue_raw"].cuped
    assert card["revenue_raw"].p_value == pytest.approx(w.p_value)
    assert card["conversion"].p_value == pytest.approx(z.p_value)
    assert card["conversion"].relative_effect == pytest.approx(0.12)
    assert card["ctr"].p_value == pytest.approx(r.p_value)
    assert card["ctr"].relative_ci_low == pytest.approx(r.relative_ci_low)


def test_ship_when_oec_improves_and_guardrails_pass(data):
    card = scorecard(
        [
            Metric.mean(
                "revenue",
                *data["rev"],
                covariate_a=data["pre"][0],
                covariate_b=data["pre"][1],
                role="oec",
            ),
            Metric.mean("load_time", *data["load"], role="guardrail", higher_is_better=False),
        ],
        sample_counts=[data["n"], data["n"]],
    )
    assert card.decision == "ship"
    assert card["revenue"].status == "positive"
    assert card["load_time"].status == "pass"
    assert not card.srm.srm_detected


def test_srm_overrides_everything(data):
    card = scorecard(
        [Metric.mean("revenue", *data["rev"], role="oec")], sample_counts=[50_000, 48_500]
    )
    assert card.decision == "invalid"
    assert "Sample ratio mismatch" in card.reasons[0]


def test_guardrail_failure_blocks_ship(data):
    load_a, load_b = data["load"]
    card = scorecard(
        [
            Metric.mean("revenue", *data["rev"], role="oec"),
            Metric.mean(
                "load_time", load_a, load_b + 0.05, role="guardrail", higher_is_better=False
            ),
        ]
    )
    assert card["revenue"].status == "positive"
    assert card["load_time"].status == "fail"
    assert card.decision == "don't ship"


def test_guardrail_margin_is_non_inferiority(data):
    load_a, load_b = data["load"]
    # +0.3% slower: not significant, but CI must sit inside a margin to pass.
    shifted = load_b + 0.003
    wide = Metric.mean(
        "load", load_a, shifted, role="guardrail", higher_is_better=False, margin=0.05
    )
    tight = Metric.mean(
        "load", load_a, shifted, role="guardrail", higher_is_better=False, margin=0.001
    )
    oec = Metric.mean("revenue", *data["rev"], role="oec")
    assert scorecard([oec, wide])["load"].status == "pass"
    assert scorecard([oec, tight])["load"].status == "fail"


def test_negative_and_inconclusive_oec(data):
    ra, rb = data["rev"]
    assert scorecard([Metric.mean("revenue", rb, ra, role="oec")]).decision == "don't ship"
    assert scorecard([Metric.mean("revenue", ra, ra[::-1], role="oec")]).decision == (
        "inconclusive"
    )
    lower_better = Metric.mean("revenue", ra, rb, role="oec", higher_is_better=False)
    assert scorecard([lower_better]).decision == "don't ship"


def test_secondary_metrics_are_corrected(data):
    rng = np.random.default_rng(0)
    noise = [Metric.mean(f"m{i}", rng.normal(size=500), rng.normal(size=500)) for i in range(20)]
    card = scorecard([Metric.mean("revenue", *data["rev"], role="oec"), *noise])
    secondary = [m for m in card.metrics if m.role == "secondary"]
    adj = adjust_p_values([m.p_value for m in secondary], "bh")
    assert [m.adjusted_p_value for m in secondary] == pytest.approx(adj)
    assert all(m.adjusted_p_value >= m.p_value for m in secondary)
    assert card["revenue"].adjusted_p_value == card["revenue"].p_value


def test_to_markdown(data):
    card = scorecard(
        [
            Metric.mean(
                "revenue",
                *data["rev"],
                covariate_a=data["pre"][0],
                covariate_b=data["pre"][1],
                role="oec",
            ),
            Metric.proportion("conversion", 500, 5000, 520, 5000),
        ],
        sample_counts=[data["n"], data["n"]],
    )
    md = card.to_markdown()
    assert md.startswith("**Decision: ship**")
    assert "| revenue (CUPED) | oec |" in md
    assert "(adj " in md
    assert "SRM check" in md


def test_invalid_scorecards(data):
    oec = Metric.mean("revenue", *data["rev"], role="oec")
    other = Metric.mean("revenue", *data["load"])
    with pytest.raises(ValueError):
        scorecard([Metric("x", "mean", data["load"])])  # no OEC
    with pytest.raises(ValueError):
        scorecard([oec, Metric.mean("x", *data["load"], role="oec")])  # two OECs
    with pytest.raises(ValueError):
        scorecard([oec, other])  # duplicate names
    with pytest.raises(ValueError):
        scorecard([oec], alpha=0)
    with pytest.raises(ValueError):
        scorecard([oec], correction="fdr")
    with pytest.raises(ValueError):
        scorecard([oec], expected_ratios=[1, 1])
    with pytest.raises(ValueError):
        scorecard([oec, "not a metric"])


@pytest.mark.parametrize(
    "build",
    [
        lambda: Metric.mean("", [1.0, 2.0], [1.0, 2.0]),
        lambda: Metric.mean("x", [1.0, 2.0], [1.0, 2.0], role="primary"),
        lambda: Metric.mean("x", [1.0, 2.0], [1.0, 2.0], margin=0.01),
        lambda: Metric.mean("x", [1.0, 2.0], [1.0, 2.0], role="guardrail", margin=-1),
        lambda: Metric.mean("x", [1.0, 2.0], [1.0, 2.0], covariate_a=[1.0, 2.0]),
        lambda: Metric.mean("x", [[1.0, 2.0]], [1.0, 2.0]),
        lambda: Metric.proportion("x", 11, 10, 5, 10),
        lambda: Metric.proportion("x", 1, 0, 5, 10),
        lambda: Metric("x", "median", ()),
    ],
)
def test_invalid_metrics(build):
    with pytest.raises(ValueError):
        build()


# --- regressions from code review -------------------------------------------------


def _oec():
    rng = np.random.default_rng(0)
    return Metric.mean("oec", rng.normal(size=200), rng.normal(size=200), role="oec")


def test_margin_guardrail_with_negative_control_value():
    # Profit per user is negative in control and improves in treatment: must pass.
    rng = np.random.default_rng(1)
    a, b = rng.normal(-10, 1, 2000), rng.normal(-9.5, 1, 2000)
    g = Metric.mean("profit", a, b, role="guardrail", margin=0.01)
    r = scorecard([_oec(), g])["profit"]
    assert r.status == "pass"
    assert r.relative_effect == pytest.approx(0.05, abs=0.01)  # (B - A) / |A| > 0


def test_margin_guardrail_with_zero_control_rate():
    no_errors = Metric.proportion(
        "errors", 0, 1000, 0, 1000, role="guardrail", higher_is_better=False, margin=0.1
    )
    assert scorecard([_oec(), no_errors])["errors"].status == "pass"
    new_errors = Metric.proportion(
        "errors", 0, 1000, 30, 1000, role="guardrail", higher_is_better=False, margin=0.1
    )
    assert scorecard([_oec(), new_errors])["errors"].status == "fail"


def test_constant_secondary_metric_does_not_crash():
    card = scorecard([_oec(), Metric.mean("refunds", np.zeros(500), np.zeros(500))])
    assert card["refunds"].p_value == 1.0
    assert card["refunds"].status == "neutral"


def test_proportion_status_agrees_with_ci():
    # Very unequal arms near the edge: pooled and unpooled tests can disagree.
    # Here the pooled test gives p = 0.060 while the unpooled CI excludes 0.
    pooled = two_proportion_ztest(12, 200, 2000, 20000)
    assert pooled.p_value > 0.05 and pooled.ci_low > 0
    card = scorecard([Metric.proportion("conv", 12, 200, 2000, 20000, role="oec")])
    r = card["conv"]
    assert r.p_value < 0.05 and r.ci_low > 0
    assert r.status == "positive"
    ref = two_proportion_ztest(12, 200, 2000, 20000, pooled=False)
    assert r.p_value == pytest.approx(ref.p_value)


def test_covariates_are_keyword_only():
    with pytest.raises(TypeError):
        Metric.mean("x", [1.0, 2.0], [1.0, 2.0], [1.0, 2.0], [1.0, 2.0])


@pytest.mark.parametrize(
    "build",
    [
        lambda: Metric.mean("x", [1.0, np.nan], [1.0, 2.0]),
        lambda: Metric.mean("x", [1.0], [1.0, 2.0]),
        lambda: Metric.ratio("x", [1.0, 2.0], [1.0], [1.0, 2.0], [1.0, 2.0]),
        lambda: Metric.ratio("x", [1.0, np.inf], [1.0, 1.0], [1.0, 2.0], [1.0, 2.0]),
    ],
)
def test_metric_inputs_validated_at_construction(build):
    with pytest.raises(ValueError):
        build()

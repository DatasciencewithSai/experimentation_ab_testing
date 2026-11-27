# experimentation_ab_testing

A Python toolkit for designing and analyzing A/B tests.

| Module | What it does |
|---|---|
| `abtest.sample_size` | Per-arm sample size for proportions (absolute or relative MDE) and means |
| `abtest.frequentist` | Two-proportion z-test and Welch's t-test with confidence intervals |
| `abtest.bayesian` | Beta-Binomial posterior: P(B > A), expected lift, expected loss |
| `abtest.sequential` | Mixture SPRT with always-valid p-values, safe to check at every look |
| `abtest.diagnostics` | Sample ratio mismatch (SRM) check; A/A simulator that replays random splits to validate an analysis |
| `abtest.variance_reduction` | CUPED: adjust with pre-experiment data for tighter CIs, same effect |
| `abtest.scorecard` | OEC + guardrails + secondary metrics in one report with a ship decision; multiple-testing correction |
| `abtest.ratio` | Delta-method variance and z-test for ratio metrics (CTR, revenue per session) |

## Apps

| App | Run it |
|---|---|
| [Sequential test monitor](apps/sequential_monitor/) — mSPRT + Bayesian, peek-safe | `cd apps/sequential_monitor && pip install -r requirements.txt && python app.py` |
| [Sample size calculator](apps/sample_size_calculator/) — power curve and test duration | `cd apps/sample_size_calculator && pip install -r requirements.txt && python app.py` |

Both were copied from their original repos and still use their own math for now;
see [docs/REPO_PLAN.md](docs/REPO_PLAN.md) for the plan to move them onto the library.

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from abtest import (
    sample_size_proportions,
    two_proportion_ztest,
    beta_binomial_test,
    msprt_proportions,
    srm_test,
    ratio_metric_test,
    cuped,
    aa_test_simulation,
)

sample_size_proportions(baseline=0.10, mde=0.10, relative=True)  # per-arm n
two_proportion_ztest(100, 1000, 130, 1000)  # z, p, CI
beta_binomial_test(100, 1000, 130, 1000).prob_b_beats_a
msprt_proportions(100, 1000, 130, 1000).always_valid_p

srm_test([821_588, 815_482]).srm_detected  # True: p ≈ 1.8e-6, don't trust results
# per-user clicks and page views for control and treatment
ratio_metric_test(clicks_a, views_a, clicks_b, views_b).relative_effect
# in-experiment metric and the same metric from the pre-period, per user
cuped(y_a, pre_a, y_b, pre_b).variance_reduction
# does the analysis give ~5% false positives on historical data with no treatment?
aa_test_simulation(historical_metric).looks_valid
```

### Scorecard

```python
from abtest import Metric, scorecard

card = scorecard(
    [
        Metric.mean("revenue_per_user", rev_a, rev_b, pre_a, pre_b, role="oec"),  # CUPED
        Metric.mean(
            "page_load_s", load_a, load_b, role="guardrail", higher_is_better=False, margin=0.02
        ),  # at most 2% slower
        Metric.ratio("ctr", clicks_a, views_a, clicks_b, views_b),
        Metric.proportion("conversion", 500, 5000, 540, 5000),
    ],
    sample_counts=[n_a, n_b],  # SRM check
)
card.decision  # "ship" | "don't ship" | "inconclusive" | "invalid"
print(card.to_markdown())
```

## Development

```bash
pytest
ruff check . && ruff format --check .
```

CI runs both on every push and pull request (Python 3.10–3.13).

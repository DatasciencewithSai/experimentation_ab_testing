# experimentation_ab_testing

A Python toolkit for designing and analyzing A/B tests.

| Module | What it does |
|---|---|
| `abtest.sample_size` | Per-arm sample size for proportions (absolute or relative MDE) and means |
| `abtest.frequentist` | Two-proportion z-test and Welch's t-test with confidence intervals |
| `abtest.bayesian` | Beta-Binomial posterior: P(B > A), expected lift, expected loss |
| `abtest.sequential` | Mixture SPRT with always-valid p-values, safe to check at every look |
| `abtest.diagnostics` | Sample ratio mismatch (SRM) check: chi-square test of the observed split |
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
)

sample_size_proportions(baseline=0.10, mde=0.10, relative=True)  # per-arm n
two_proportion_ztest(100, 1000, 130, 1000)  # z, p, CI
beta_binomial_test(100, 1000, 130, 1000).prob_b_beats_a
msprt_proportions(100, 1000, 130, 1000).always_valid_p

srm_test([821_588, 815_482]).srm_detected  # True: p ≈ 1.8e-6, don't trust results
# per-user clicks and page views for control and treatment
ratio_metric_test(clicks_a, views_a, clicks_b, views_b).relative_effect
```

## Development

```bash
pytest
ruff check . && ruff format --check .
```

CI runs both on every push and pull request (Python 3.10–3.13).

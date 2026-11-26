# experimentation_ab_testing

A Python toolkit for designing and analyzing A/B tests.

| Module | What it does |
|---|---|
| `abtest.sample_size` | Per-arm sample size for proportions (absolute or relative MDE) and means |
| `abtest.frequentist` | Two-proportion z-test and Welch's t-test with confidence intervals |
| `abtest.bayesian` | Beta-Binomial posterior: P(B > A), expected lift, expected loss |
| `abtest.sequential` | Mixture SPRT with always-valid p-values, safe to check at every look |

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
)

sample_size_proportions(baseline=0.10, mde=0.10, relative=True)  # per-arm n
two_proportion_ztest(100, 1000, 130, 1000)  # z, p, CI
beta_binomial_test(100, 1000, 130, 1000).prob_b_beats_a
msprt_proportions(100, 1000, 130, 1000).always_valid_p
```

## Development

```bash
pytest
ruff check . && ruff format --check .
```

CI runs both on every push and pull request (Python 3.10–3.13).

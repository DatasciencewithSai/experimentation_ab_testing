"""abtest: design and analyze A/B tests."""

from abtest.bayesian import beta_binomial_test
from abtest.diagnostics import srm_test
from abtest.frequentist import two_proportion_ztest, welch_ttest
from abtest.ratio import delta_method_ratio, ratio_metric_test
from abtest.sample_size import sample_size_means, sample_size_proportions
from abtest.sequential import msprt_proportions

__all__ = [
    "beta_binomial_test",
    "delta_method_ratio",
    "msprt_proportions",
    "ratio_metric_test",
    "sample_size_means",
    "sample_size_proportions",
    "srm_test",
    "two_proportion_ztest",
    "welch_ttest",
]

__version__ = "0.1.0"

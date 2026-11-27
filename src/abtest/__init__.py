"""abtest: design and analyze A/B tests."""

from abtest.bayesian import beta_binomial_test
from abtest.diagnostics import aa_test_simulation, srm_test
from abtest.frequentist import two_proportion_ztest, welch_ttest
from abtest.ratio import delta_method_ratio, ratio_metric_test, relative_lift
from abtest.sample_size import sample_size_means, sample_size_proportions
from abtest.scorecard import Metric, adjust_p_values, scorecard
from abtest.sequential import msprt_proportions
from abtest.variance_reduction import cuped

__all__ = [
    "Metric",
    "aa_test_simulation",
    "adjust_p_values",
    "beta_binomial_test",
    "cuped",
    "delta_method_ratio",
    "msprt_proportions",
    "ratio_metric_test",
    "relative_lift",
    "sample_size_means",
    "sample_size_proportions",
    "scorecard",
    "srm_test",
    "two_proportion_ztest",
    "welch_ttest",
]

__version__ = "0.1.0"

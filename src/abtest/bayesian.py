"""Bayesian analysis of conversion rates with a Beta-Binomial model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BayesResult:
    prob_b_beats_a: float
    expected_lift: float  # E[(p_b - p_a) / p_a]
    expected_loss_choosing_b: float  # E[max(p_a - p_b, 0)]
    expected_loss_choosing_a: float  # E[max(p_b - p_a, 0)]


def beta_binomial_test(
    conversions_a: int,
    n_a: int,
    conversions_b: int,
    n_b: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    draws: int = 200_000,
    seed: int | None = 0,
) -> BayesResult:
    """Monte Carlo posterior comparison of two Beta-Binomial conversion rates."""
    rng = np.random.default_rng(seed)
    pa = rng.beta(prior_alpha + conversions_a, prior_beta + n_a - conversions_a, draws)
    pb = rng.beta(prior_alpha + conversions_b, prior_beta + n_b - conversions_b, draws)
    diff = pb - pa
    return BayesResult(
        prob_b_beats_a=float((diff > 0).mean()),
        expected_lift=float((diff / pa).mean()),
        expected_loss_choosing_b=float(np.maximum(-diff, 0).mean()),
        expected_loss_choosing_a=float(np.maximum(diff, 0).mean()),
    )

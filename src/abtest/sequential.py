"""Sequential (always-valid) testing via the mixture SPRT (mSPRT).

Reference: Johari, Pekelis & Walsh (2017), "Always Valid Inference".
The p-value can be checked after every batch of data without inflating
the false positive rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SequentialResult:
    likelihood_ratio: float
    always_valid_p: float
    reject: bool


def msprt_proportions(
    conversions_a: int,
    n_a: int,
    conversions_b: int,
    n_b: int,
    alpha: float = 0.05,
    tau: float = 0.01,
    previous_p: float = 1.0,
) -> SequentialResult:
    """mSPRT for difference in proportions with a normal mixing prior N(0, tau^2).

    Pass the always-valid p-value from the previous look as `previous_p`
    so the returned p-value is the running minimum, as the method requires.
    """
    if n_a <= 0 or n_b <= 0:
        raise ValueError("sample sizes must be positive")
    p_a, p_b = conversions_a / n_a, conversions_b / n_b
    var = p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b
    if var == 0:
        return SequentialResult(1.0, previous_p, previous_p <= alpha)
    diff = p_b - p_a
    t2 = tau**2
    lr = math.sqrt(var / (var + t2)) * math.exp(diff**2 * t2 / (2 * var * (var + t2)))
    p = min(previous_p, 1.0 / lr)
    return SequentialResult(lr, p, p <= alpha)

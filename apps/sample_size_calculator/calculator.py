from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize


power_solver = NormalIndPower()


@dataclass(frozen=True)
class CalculatorInputs:
    baseline_rate: float
    expected_rate: float
    alpha: float
    power: float
    daily_visitors: int


@dataclass(frozen=True)
class CalculatorResults:
    sample_per_group: int
    total_sample_size: int
    absolute_effect: float
    relative_effect: float | None
    effect_size: float
    estimated_days: int | None
    estimated_weeks: float | None


def validate_inputs(inputs: CalculatorInputs) -> list[str]:
    errors: list[str] = []

    if not 0 < inputs.baseline_rate < 1:
        errors.append("Baseline conversion rate must be between 0 and 1.")
    if not 0 < inputs.expected_rate < 1:
        errors.append("Expected conversion rate must be between 0 and 1.")
    if inputs.expected_rate == inputs.baseline_rate:
        errors.append("Expected rate must differ from the baseline rate.")
    if not 0 < inputs.alpha < 1:
        errors.append("Alpha must be between 0 and 1.")
    if not 0 < inputs.power < 1:
        errors.append("Power must be between 0 and 1.")
    if inputs.daily_visitors <= 0:
        errors.append("Daily visitors must be greater than 0.")

    return errors


def calculate_sample_size(inputs: CalculatorInputs) -> CalculatorResults:
    absolute_effect = inputs.expected_rate - inputs.baseline_rate
    relative_effect = None
    if inputs.baseline_rate != 0:
        relative_effect = absolute_effect / inputs.baseline_rate

    effect_size = abs(
        proportion_effectsize(inputs.baseline_rate, inputs.expected_rate)
    )
    sample_per_group = math.ceil(
        power_solver.solve_power(
            effect_size=effect_size,
            power=inputs.power,
            alpha=inputs.alpha,
            ratio=1.0,
            alternative="two-sided",
        )
    )
    total_sample_size = sample_per_group * 2
    estimated_days = math.ceil(total_sample_size / inputs.daily_visitors)
    estimated_weeks = round(estimated_days / 7, 1)

    return CalculatorResults(
        sample_per_group=sample_per_group,
        total_sample_size=total_sample_size,
        absolute_effect=absolute_effect,
        relative_effect=relative_effect,
        effect_size=effect_size,
        estimated_days=estimated_days,
        estimated_weeks=estimated_weeks,
    )


def build_power_curve(inputs: CalculatorInputs, target_sample_per_group: int) -> tuple[np.ndarray, np.ndarray]:
    max_sample = max(200, int(target_sample_per_group * 1.8))
    min_sample = max(20, int(target_sample_per_group * 0.2))
    sample_sizes = np.linspace(min_sample, max_sample, 40)
    effect_size = abs(
        proportion_effectsize(inputs.baseline_rate, inputs.expected_rate)
    )
    powers = np.array(
        [
            power_solver.power(
                effect_size=effect_size,
                nobs1=size,
                alpha=inputs.alpha,
                ratio=1.0,
                alternative="two-sided",
            )
            for size in sample_sizes
        ]
    )
    return sample_sizes, powers


def build_effect_comparison(
    baseline_rate: float,
    alpha: float,
    power: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lower = max(0.001, baseline_rate * 0.6)
    upper = min(0.999, baseline_rate * 1.5)

    if math.isclose(lower, upper):
        upper = min(0.999, lower + 0.05)

    expected_rates = np.linspace(lower, upper, 35)
    plotted_expected_rates = []
    sample_sizes = []
    relative_lifts = []

    for expected_rate in expected_rates:
        if math.isclose(expected_rate, baseline_rate):
            continue
        effect_size = abs(proportion_effectsize(baseline_rate, expected_rate))
        plotted_expected_rates.append(expected_rate)
        sample_sizes.append(
            power_solver.solve_power(
                effect_size=effect_size,
                power=power,
                alpha=alpha,
                ratio=1.0,
                alternative="two-sided",
            )
        )
        relative_lifts.append(((expected_rate - baseline_rate) / baseline_rate) * 100)

    return (
        np.array(plotted_expected_rates),
        np.array(sample_sizes),
        np.array(relative_lifts),
    )

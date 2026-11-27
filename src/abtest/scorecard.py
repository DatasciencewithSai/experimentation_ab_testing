"""Experiment scorecard: OEC, guardrails and secondary metrics with one decision.

Follows Kohavi, Tang & Xu (2020), ch. 6-7:

* The **OEC** (overall evaluation criterion) is the single metric the ship
  decision is based on. It is tested at ``alpha`` with no correction.
* **Guardrail** metrics must not get worse. Each is checked on its own (no
  multiple-testing correction, which would make harm harder to detect). With a
  ``margin`` it is a non-inferiority check: the harmful end of the CI on B - A
  must stay within ``margin * |control|``. Without one, it fails only on a
  significant move in the harmful direction.
* **Secondary** metrics explain the result and are not part of the decision. Their
  p-values are adjusted for multiple comparisons (Benjamini-Hochberg by default).

The result is only trusted if the split passes the SRM check.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from abtest.diagnostics import SRMResult, srm_test
from abtest.frequentist import two_proportion_ztest, welch_ttest
from abtest.ratio import _as_unit_arrays, delta_method_ratio, ratio_metric_test, relative_lift
from abtest.variance_reduction import _check_pair, _cuped_adjust

ROLES = ("oec", "guardrail", "secondary")
KINDS = ("mean", "proportion", "ratio")
CORRECTIONS = ("bh", "holm", "bonferroni", "none")


def adjust_p_values(p_values: Sequence[float], method: str = "bh") -> np.ndarray:
    """Adjust p-values for multiple comparisons.

    Args:
        p_values: raw p-values.
        method: ``"bh"`` (Benjamini-Hochberg, controls the false discovery rate),
            ``"holm"`` (Holm-Bonferroni, controls the family-wise error rate),
            ``"bonferroni"`` or ``"none"``.

    Returns adjusted p-values in the input order, capped at 1.
    """
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1:
        raise ValueError("p_values must be 1-D")
    if np.any(np.isnan(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("p_values must be in [0, 1]")
    if method not in CORRECTIONS:
        raise ValueError(f"method must be one of {CORRECTIONS}")
    m = p.size
    if m == 0 or method == "none":
        return p.copy()
    if method == "bonferroni":
        return np.minimum(p * m, 1.0)

    order = np.argsort(p)
    ranked = p[order]
    if method == "holm":
        adj = np.maximum.accumulate(ranked * (m - np.arange(m)))
    else:  # bh
        adj = np.minimum.accumulate((ranked * (m / np.arange(1, m + 1)))[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out


@dataclass(frozen=True)
class Metric:
    """One scorecard metric. Build it with ``Metric.mean``, ``.proportion`` or ``.ratio``."""

    name: str
    kind: str
    data: tuple = field(repr=False)
    role: str = "secondary"
    higher_is_better: bool = True
    margin: float | None = None  # guardrails only: tolerated degradation, relative to |control|

    def __post_init__(self):
        if not self.name:
            raise ValueError("metric name must not be empty")
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        if self.role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}")
        if self.margin is not None:
            if self.role != "guardrail":
                raise ValueError("margin applies to guardrail metrics only")
            if not (math.isfinite(self.margin) and self.margin >= 0):
                raise ValueError("margin must be a non-negative relative change, e.g. 0.01")

    @classmethod
    def mean(cls, name, values_a, values_b, *, covariate_a=None, covariate_b=None, **kwargs):
        """Mean of a per-unit metric; pass pre-period covariates to apply CUPED."""
        if (covariate_a is None) != (covariate_b is None):
            raise ValueError("pass covariates for both arms or neither")
        if covariate_a is None:
            # values double as their own "covariate" just for validation
            data = (_check_pair(values_a, values_a, "control")[0],)
            data += (_check_pair(values_b, values_b, "treatment")[0],)
        else:
            data = (*_check_pair(values_a, covariate_a, "control"),)
            data += (*_check_pair(values_b, covariate_b, "treatment"),)
        return cls(name, "mean", data, **kwargs)

    @classmethod
    def proportion(cls, name, successes_a, n_a, successes_b, n_b, **kwargs):
        """Share of units with an event, e.g. conversion rate."""
        for s, n in ((successes_a, n_a), (successes_b, n_b)):
            if n <= 0 or not 0 <= s <= n:
                raise ValueError("need n > 0 and 0 <= successes <= n in each arm")
        return cls(name, "proportion", (successes_a, n_a, successes_b, n_b), **kwargs)

    @classmethod
    def ratio(cls, name, numerator_a, denominator_a, numerator_b, denominator_b, **kwargs):
        """Ratio of per-unit sums (e.g. clicks / page views), via the delta method."""
        data = (*_as_unit_arrays(numerator_a, denominator_a),)
        data += (*_as_unit_arrays(numerator_b, denominator_b),)
        return cls(name, "ratio", data, **kwargs)


@dataclass(frozen=True)
class MetricResult:
    name: str
    role: str
    value_a: float  # control estimate
    value_b: float  # treatment estimate
    effect: float  # B - A
    ci_low: float
    ci_high: float
    relative_effect: float  # (B - A) / |A|
    relative_ci_low: float
    relative_ci_high: float
    p_value: float
    adjusted_p_value: float  # after multiple-testing correction (secondary metrics only)
    status: str  # "positive" | "negative" | "neutral", or "pass" | "fail" for guardrails
    cuped: bool = False


@dataclass(frozen=True)
class ScorecardResult:
    decision: str  # "ship" | "don't ship" | "inconclusive" | "invalid"
    reasons: tuple[str, ...]
    metrics: tuple[MetricResult, ...]
    srm: SRMResult | None
    alpha: float
    correction: str

    def __getitem__(self, name: str) -> MetricResult:
        for m in self.metrics:
            if m.name == name:
                return m
        raise KeyError(name)

    def to_markdown(self) -> str:
        """Scorecard as a Markdown report."""
        lines = [f"**Decision: {self.decision}**", ""]
        lines += [f"- {r}" for r in self.reasons]
        if self.srm is not None:
            lines.append(f"- SRM check p = {self.srm.p_value:.3g}")
        level = f"{1 - self.alpha:.0%}"
        lines += [
            "",
            f"| Metric | Role | Control | Treatment | Lift | {level} CI (lift) | p | Status |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for m in self.metrics:
            p = f"{m.p_value:.3g}"
            if m.role == "secondary" and self.correction != "none":
                p += f" (adj {m.adjusted_p_value:.3g})"
            name = m.name + (" (CUPED)" if m.cuped else "")
            lines.append(
                f"| {name} | {m.role} | {m.value_a:.4g} | {m.value_b:.4g} "
                f"| {m.relative_effect:+.2%} "
                f"| [{m.relative_ci_low:+.2%}, {m.relative_ci_high:+.2%}] "
                f"| {p} | {m.status} |"
            )
        return "\n".join(lines)


def _evaluate(metric: Metric, alpha: float) -> dict:
    d = metric.data
    if metric.kind == "proportion":
        sa, na, sb, nb = d
        r = two_proportion_ztest(sa, na, sb, nb, alpha=alpha, pooled=False)
        pa, pb = sa / na, sb / nb
        var_a, var_b = pa * (1 - pa) / na, pb * (1 - pb) / nb
        value_a, value_b = pa, pb
    elif metric.kind == "ratio":
        r = ratio_metric_test(*d, alpha=alpha)
        ea, eb = delta_method_ratio(d[0], d[1]), delta_method_ratio(d[2], d[3])
        value_a, value_b, var_a, var_b = ea.ratio, eb.ratio, ea.variance, eb.variance
    else:  # mean
        if len(d) == 4:
            ya, xa, yb, xb = d
            a, b, _ = _cuped_adjust(ya, xa, yb, xb)
        else:
            a, b = d
        r = welch_ttest(a, b, alpha=alpha)
        value_a, value_b = a.mean(), b.mean()
        var_a, var_b = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    rel, rel_low, rel_high = relative_lift(value_a, var_a, value_b, var_b, alpha)
    return dict(
        value_a=float(value_a),
        value_b=float(value_b),
        effect=float(r.effect),
        ci_low=float(r.ci_low),
        ci_high=float(r.ci_high),
        relative_effect=rel,
        relative_ci_low=rel_low,
        relative_ci_high=rel_high,
        p_value=float(r.p_value),
    )


def _direction(effect: float, higher_is_better: bool) -> str:
    good = effect > 0 if higher_is_better else effect < 0
    return "positive" if good else "negative"


def scorecard(
    metrics: Sequence[Metric],
    alpha: float = 0.05,
    correction: str = "bh",
    sample_counts: Sequence[int] | None = None,
    expected_ratios: Sequence[float] | None = None,
) -> ScorecardResult:
    """Analyze an experiment's metrics and return a ship decision.

    Args:
        metrics: exactly one metric with ``role="oec"``, plus any guardrails and
            secondary metrics. Names must be unique.
        alpha: significance level.
        correction: multiple-testing correction for secondary metrics
            (see ``adjust_p_values``).
        sample_counts: units assigned to (control, treatment) for the SRM check.
        expected_ratios: design split for the SRM check; defaults to equal.

    Decision rules, in order: SRM detected -> "invalid"; any guardrail fails ->
    "don't ship"; OEC significantly better -> "ship"; significantly worse ->
    "don't ship"; otherwise "inconclusive".
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if correction not in CORRECTIONS:
        raise ValueError(f"correction must be one of {CORRECTIONS}")
    metrics = list(metrics)
    if any(not isinstance(m, Metric) for m in metrics):
        raise ValueError("metrics must be Metric objects")
    names = [m.name for m in metrics]
    if len(set(names)) != len(names):
        raise ValueError("metric names must be unique")
    if sum(m.role == "oec" for m in metrics) != 1:
        raise ValueError("exactly one metric must have role='oec'")
    if expected_ratios is not None and sample_counts is None:
        raise ValueError("expected_ratios needs sample_counts")

    srm = srm_test(sample_counts, expected_ratios) if sample_counts is not None else None
    raw = [_evaluate(m, alpha) for m in metrics]

    secondary = [i for i, m in enumerate(metrics) if m.role == "secondary"]
    adjusted: dict[int, float] = {}
    if secondary:
        adj = adjust_p_values([raw[i]["p_value"] for i in secondary], correction)
        adjusted = dict(zip(secondary, adj.tolist(), strict=True))

    results, reasons = [], []
    oec = None
    for i, (m, r) in enumerate(zip(metrics, raw, strict=True)):
        p_adj = adjusted.get(i, r["p_value"])
        harmful = _direction(r["effect"], m.higher_is_better) == "negative"
        if m.role == "guardrail":
            if m.margin is None:
                failed = harmful and r["p_value"] < alpha
            else:
                # non-inferiority on the absolute CI: harm may not exceed margin * |A|
                tolerance = m.margin * abs(r["value_a"])
                if m.higher_is_better:
                    failed = r["ci_low"] < -tolerance
                else:
                    failed = r["ci_high"] > tolerance
            status = "fail" if failed else "pass"
            if failed:
                if m.margin is None:
                    how = "significantly worse"
                else:
                    how = f"could be worse than the {m.margin:.2%} margin"
                reasons.append(f"Guardrail '{m.name}' failed: {how}.")
        elif p_adj < alpha and r["effect"] != 0:
            status = _direction(r["effect"], m.higher_is_better)
        else:
            status = "neutral"
        result = MetricResult(
            name=m.name,
            role=m.role,
            adjusted_p_value=float(p_adj),
            status=status,
            cuped=m.kind == "mean" and len(m.data) == 4,
            **r,
        )
        results.append(result)
        if m.role == "oec":
            oec = result

    guardrail_failed = bool(reasons)
    if srm is not None and srm.srm_detected:
        decision = "invalid"
        reasons.insert(
            0,
            f"Sample ratio mismatch (p = {srm.p_value:.2g}): find the cause before "
            "trusting any metric.",
        )
    elif guardrail_failed:
        decision = "don't ship"
    elif oec.status == "positive":
        decision = "ship"
        reasons.append(f"OEC '{oec.name}' improved ({oec.relative_effect:+.2%}).")
    elif oec.status == "negative":
        decision = "don't ship"
        reasons.append(f"OEC '{oec.name}' got worse ({oec.relative_effect:+.2%}).")
    else:
        decision = "inconclusive"
        reasons.append(f"OEC '{oec.name}' showed no significant change.")

    return ScorecardResult(
        decision=decision,
        reasons=tuple(reasons),
        metrics=tuple(results),
        srm=srm,
        alpha=alpha,
        correction=correction,
    )

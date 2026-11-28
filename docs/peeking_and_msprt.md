# The peeking problem, and why we should monitor tests with mSPRT

**TL;DR.** A p-value is only valid if you look at it once, at the sample size you
planned. If you check every day and stop the first time p < 0.05, about **1 in 5** tests
with no real effect gets declared a winner, not 1 in 20. The usual fixes either stop you
looking or cost a lot of power. **Proposal: monitor every test with mSPRT** (always-valid
p-values). You can look as often as you like, false wins stay under 5%, and big effects
can stop early.

Video (60 s): [`visuals/ab_test_flow/peeking_msprt.mp4`](../visuals/ab_test_flow/peeking_msprt.mp4) ·
numbers: [`visuals/ab_test_flow/peeking_msprt_numbers.py`](../visuals/ab_test_flow/peeking_msprt_numbers.py)

---

## 1. What is peeking?

A classic (fixed-horizon) A/B test works like this:

1. Pick the sample size up front. For example, with a 4% CTR baseline, a +10% relative
   minimum effect, α = 0.05 and 80% power, you need **39,475 users per variant**
   (`sample_size_proportions(0.04, 0.10, relative=True)`): about 14 days at 3,000/day.
2. Wait until you reach it.
3. Look **once** and test.

**Peeking** means checking the p-value before then (daily, hourly, on a dashboard) and
stopping as soon as it dips below 0.05.

## 2. Why it breaks

Under "no real difference", the p-value wanders at random as data comes in. α = 5% is the
chance that it is below 0.05 **at one point you fixed in advance**. If you check 14 times,
noise gets 14 chances to cross the line, and you stop at the first crossing.

### One example

This is a simulated test where A and B are **identical** (an A/A test, seed 2275):

| Day | A CTR | B CTR | "Lift" | Naive p | mSPRT p |
|---:|---:|---:|---:|---:|---:|
| 1 | 3.87% | 4.47% | +15.5% | 0.245 | 0.98 |
| 2 | 3.90% | 4.52% | +15.8% | 0.093 | 0.69 |
| **5** | 3.75% | 4.29% | **+14.4%** | **0.017** ← "ship it!" | 0.24 |
| 7 | 3.75% | 4.15% | +10.5% | 0.038 | 0.24 |
| 14 | 4.01% | 4.05% | +1.0% | 0.766 | 0.24 |

If you peeked, you shipped on day 5. If you waited, you saw nothing (correct). mSPRT never
went below 0.24, so it never called a winner.

### How often it happens

Simulation: 4,000 A/A tests, 3,000 users per arm per day, two-proportion z-test.

| How you look | False "wins" (should be 5%) |
|---|---:|
| Once, on day 14 | **5.2%** |
| Every day for 14 days, stop at first p < 0.05 | **21.7%** |
| Every day for 28 days | **27.7%** |

The more you look, the worse it gets. With unlimited looks, a naive test eventually
"wins" with probability approaching 100%.

## 3. Solutions people use

| # | Approach | How it works | Catch |
|---|---|---|---|
| 1 | **Don't peek** (fixed horizon) | Pre-register n, analyse once. | Valid, but you are blind for the whole test. You can't stop a big win (or a harmful bug) early, and people peek anyway. |
| 2 | **Bonferroni** | Use α / k at each of k looks (0.05 / 14 ≈ 0.0036). | Very conservative: false wins drop to 2.1%, but **power falls from 83% to 58%** in our simulation. |
| 3 | **Group sequential / alpha spending** (Pocock, O'Brien–Fleming) | Plan k looks and spend α across them with stricter early thresholds. | Statistically sound and efficient, but the number and timing of looks must be planned in advance. Unplanned looks break it. |
| 4 | **Bayesian "chance to beat control"** | Stop when P(B > A) > 95%. | Answers a different question. Stopping on it whenever you like still inflates false wins, and results depend on the prior. |
| 5 | **mSPRT / always-valid inference** | A sequential likelihood-ratio test whose p-value is valid at *every* look. | Needs a tuning parameter τ, and loses some power compared with a perfectly timed single look (see trade-offs). |

## 4. Proposal: use mSPRT

### What it is (in plain words)

The **mixture Sequential Probability Ratio Test** (Robbins 1970; Johari, Pekelis & Walsh
2017, *Always Valid Inference*) tracks a likelihood ratio:

> Λₙ = how much more likely the data are if there **is** an effect (averaged over
> plausible effect sizes, a normal "mixture" with spread τ) than if there is **none**.

When the data look like noise, Λ stays near or below 1. When a real effect builds up, Λ
grows. The rule:

> **Stop and declare a winner as soon as Λₙ ≥ 1/α = 20.**
> Equivalently, the always-valid p-value pₙ = min(pₙ₋₁, 1/Λₙ) drops below 0.05.

Why is it safe to peek? Under "no effect", Λₙ is (approximately, for large samples) a martingale, so by Ville's inequality the
chance it *ever* reaches 1/α is at most α, **no matter how often or when you look**. The
always-valid p-value only goes down, so a "win" can't flicker on and off as the naive one
does.

### The rule we'd adopt

1. Plan as today: compute the fixed-horizon n (`sample_size_proportions`) and set
   **τ ≈ the minimum detectable effect in absolute terms** (here 0.4 pp = 0.004).
2. Run for at least one full week (weekly seasonality), then **look as often as you like**.
3. **Stop for a win** when the always-valid p < 0.05.
4. **Cap the test at 2× the planned n.** If it hasn't stopped by then, call it "no
   detectable effect" and move on.

### What it buys us (same simulation, daily looks, 28-day cap)

| | Naive peeking | mSPRT |
|---|---:|---:|
| False wins with no real effect | 27.7% | **1.4%** |
| Power, true +10% lift | (meaningless) | **90%** (median stop: day 13) |
| Power, true +20% lift | (meaningless) | **100%** (median stop: **day 5**) |

For comparison, a fixed-horizon test always takes 14 days and has 83% power at +10%.

### Why mSPRT over the alternatives

- **Matches how people actually work.** Dashboards are open every day. mSPRT makes that
  safe instead of forbidding it.
- **No look schedule to plan.** Unlike alpha spending, you don't fix the number or timing
  of looks, and an extra look costs nothing.
- **Much less conservative than Bonferroni** for the same protection.
- **Fast when it matters.** Big wins (and big regressions) are caught in days.
- **Simple and proven.** It's one formula, already in this repo
  (`abtest.msprt_proportions`), and it's the basis of Optimizely's Stats Engine.

### Trade-offs to be honest about

- **Power at the planned n is lower.** Stopping at exactly day 14 gives mSPRT 52% power
  vs 83% for a single look. That is the price of being allowed to look any time, and why
  we cap at 2× n rather than 1×.
- **No early stop for "no effect".** A null test runs to the cap. Add a separate futility
  or guardrail rule if that matters.
- **τ matters a bit.** Too small makes it slow to detect large effects; too large makes it
  slow on small ones. τ = MDE is a sound default.
- **Multiple metrics still need correction** (e.g. `adjust_p_values`). mSPRT fixes
  *looks over time*, not *many metrics*.

## 5. How to run it

```python
from abtest import msprt_proportions

p = 1.0  # always-valid p-value carried between looks
for day in daily_cumulative_counts:  # (conv_a, n_a, conv_b, n_b) so far
    r = msprt_proportions(*day, alpha=0.05, tau=0.004, previous_p=p)
    p = r.always_valid_p
    if r.reject:
        print("Stop: B differs from A", p)
        break
```

The interactive version is `apps/sequential_monitor`.

## 6. Reproduce the numbers

```bash
.venv/bin/python visuals/ab_test_flow/peeking_msprt_numbers.py
```

All simulations use fixed seeds and the `abtest` package (`two_proportion_ztest`,
`msprt_proportions`, `sample_size_proportions`).

## References

- Johari, Pekelis & Walsh (2017). *Peeking at A/B Tests: Why it matters, and what to do
  about it.* KDD. Also *Always Valid Inference*, arXiv:1512.04922.
- Robbins (1970). *Statistical methods related to the law of the iterated logarithm.*
- Kohavi, Tang & Xu (2020). *Trustworthy Online Controlled Experiments*, ch. 17.
- O'Brien & Fleming (1979). *A multiple testing procedure for clinical trials.*

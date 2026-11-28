"""Numbers for the peeking / mSPRT explainer (video and docs/peeking_and_msprt.md).

Run from the repo root:  .venv/bin/python visuals/ab_test_flow/peeking_msprt_numbers.py
Takes a few minutes. Every figure is a fixed-seed simulation using the abtest package.

Setup: CTR baseline 4%, 3,000 users per arm per day (14 days = 42,000 per arm, which is
>= the 39,475 needed for a +10% relative lift at alpha 0.05 / power 80%). Each day we
"peek" at the cumulative data with the two-proportion z-test and with mSPRT.
"""

from __future__ import annotations

import numpy as np

from abtest import msprt_proportions, sample_size_proportions, two_proportion_ztest

BASE, PER_DAY, ALPHA = 0.04, 3000, 0.05
TAU = 0.004  # mSPRT mixing sd = the MDE in absolute terms (0.4 pp)
EXAMPLE_SEED = 2275  # an A/A path where a daily peek falsely "wins" on day 5


def daily_paths(rng, p_b, days):
    ca = np.cumsum(rng.binomial(PER_DAY, BASE, days))
    cb = np.cumsum(rng.binomial(PER_DAY, p_b, days))
    return ca, cb


def peek(ca, cb):
    """Daily naive p-values and running always-valid mSPRT p-values."""
    naive, av, p = [], [], 1.0
    for d in range(len(ca)):
        n = PER_DAY * (d + 1)
        naive.append(two_proportion_ztest(int(ca[d]), n, int(cb[d]), n).p_value)
        p = msprt_proportions(int(ca[d]), n, int(cb[d]), n, tau=TAU, previous_p=p).always_valid_p
        av.append(p)
    return np.array(naive), np.array(av)


def simulate(p_b, sims, seed, days):
    rng = np.random.default_rng(seed)
    out = dict(fixed=0, naive=0, bonferroni=0, msprt=0)
    stop_days = []
    for _ in range(sims):
        naive, av = peek(*daily_paths(rng, p_b, days))
        out["fixed"] += naive[-1] < ALPHA
        out["naive"] += (naive < ALPHA).any()
        out["bonferroni"] += (naive < ALPHA / days).any()
        hit = np.flatnonzero(av <= ALPHA)
        if hit.size:
            out["msprt"] += 1
            stop_days.append(hit[0] + 1)
    rates = {k: v / sims for k, v in out.items()}
    rates["median_stop_day"] = float(np.median(stop_days)) if stop_days else None
    return rates


def main():
    print("users per arm needed:", sample_size_proportions(BASE, 0.10, relative=True))

    print("\nExample A/A path (seed", EXAMPLE_SEED, ")")
    ca, cb = daily_paths(np.random.default_rng(EXAMPLE_SEED), BASE, 14)
    naive, av = peek(ca, cb)
    for d in range(14):
        n = PER_DAY * (d + 1)
        print(
            f"day {d + 1:2d}  A {100 * ca[d] / n:.2f}%  B {100 * cb[d] / n:.2f}%  "
            f"lift {100 * (cb[d] / ca[d] - 1):+5.1f}%  naive p {naive[d]:.3f}  mSPRT p {av[d]:.3f}"
        )

    print("\n14 days, A/A (4,000 sims):", simulate(BASE, 4000, 1, 14))
    print("14 days, +10% (2,000 sims):", simulate(BASE * 1.1, 2000, 2, 14))
    print("28 days, A/A (3,000 sims):", simulate(BASE, 3000, 1, 28))
    print("28 days, +10% (2,000 sims):", simulate(BASE * 1.1, 2000, 2, 28))
    print("28 days, +20% (2,000 sims):", simulate(BASE * 1.2, 2000, 3, 28))


if __name__ == "__main__":
    main()

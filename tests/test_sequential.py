import numpy as np

from abtest import msprt_proportions


def test_detects_large_effect():
    r = msprt_proportions(1000, 10000, 1300, 10000)
    assert r.reject


def test_p_value_monotone():
    r1 = msprt_proportions(100, 1000, 130, 1000)
    r2 = msprt_proportions(200, 2000, 205, 2000, previous_p=r1.always_valid_p)
    assert r2.always_valid_p <= r1.always_valid_p


def test_controls_false_positives_under_peeking():
    rng = np.random.default_rng(42)
    sims, rejections = 300, 0
    for _ in range(sims):
        a = rng.random(5000) < 0.1
        b = rng.random(5000) < 0.1
        p = 1.0
        for n in range(250, 5001, 250):
            r = msprt_proportions(int(a[:n].sum()), n, int(b[:n].sum()), n, previous_p=p)
            p = r.always_valid_p
            if r.reject:
                rejections += 1
                break
    assert rejections / sims <= 0.08

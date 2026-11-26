from abtest import beta_binomial_test


def test_clear_winner():
    r = beta_binomial_test(100, 1000, 150, 1000)
    assert r.prob_b_beats_a > 0.99
    assert r.expected_loss_choosing_b < r.expected_loss_choosing_a


def test_symmetric():
    r = beta_binomial_test(100, 1000, 100, 1000)
    assert 0.45 < r.prob_b_beats_a < 0.55

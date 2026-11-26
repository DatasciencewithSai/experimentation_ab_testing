import pytest

from abtest import sample_size_means, sample_size_proportions


def test_proportions_known_value():
    # 10% -> 12%, alpha .05 two-sided, 80% power: ~3841 per arm (standard formula)
    n = sample_size_proportions(0.10, 0.02)
    assert 3800 <= n <= 3900


def test_relative_mde_matches_absolute():
    assert sample_size_proportions(0.10, 0.2, relative=True) == sample_size_proportions(0.10, 0.02)


def test_means_known_value():
    # d = 0.5 -> ~63 per arm
    assert sample_size_means(std=1.0, mde=0.5) == 63


def test_invalid_inputs():
    with pytest.raises(ValueError):
        sample_size_proportions(1.2, 0.01)
    with pytest.raises(ValueError):
        sample_size_means(0, 1)

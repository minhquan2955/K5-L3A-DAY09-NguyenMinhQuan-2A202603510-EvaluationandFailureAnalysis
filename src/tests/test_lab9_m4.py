"""M4 bootstrap validation and pairing checks."""
import pytest

from lab9.stats import paired_bootstrap


@pytest.mark.parametrize('a,b', [([], []), ([1], []), ([float('nan')], [0]), ([1], [float('inf')])])
def test_bootstrap_rejects_invalid_pairs(a, b):
    with pytest.raises(ValueError):
        paired_bootstrap(a, b)


def test_constant_paired_difference_has_no_sampling_noise():
    assert paired_bootstrap([0, 1, 2], [1, 2, 3]) == (-1.0, -1.0, -1.0)


def test_seeded_bootstrap_is_reproducible():
    a, b = [1, 0, 0.5, 1], [0, 1, 0.5, 0]
    assert paired_bootstrap(a, b) == paired_bootstrap(a, b)

"""M5 slice checks use paired item means, including statistically significant drops."""
from copy import deepcopy

from lab9.gate import slice_check


def report(values):
    return {'rows': [{'item_id': f'E-{i}', 'seed': seed, 'pass_rate': value,
                      'slices': ['money_movement']}
                     for i, value in enumerate(values) for seed in (11, 22)]}


def spec(**options):
    return {'bootstrap': {'n_resamples': 1000, 'rng': 2027, 'confidence': 0.95},
            'slices': [{'name': 'money_movement', 'metric': 'pass_rate',
                        'blocking': True, **options}]}


def test_slice_significant_drop_blocks_even_above_floor():
    blocked, lines = slice_check(report([0.9, 0.9, 0.9]), report([1, 1, 1]),
                                 spec(min=0.8, no_significant_drop=True))
    assert blocked == ['slice:money_movement/pass_rate']
    assert 'CI' in lines[0] and 'BLOCK' in lines[0]


def test_identical_slice_passes_and_nonblocking_failure_warns():
    clean = report([1, 1, 1])
    assert slice_check(clean, clean, spec(min=0.9, no_significant_drop=True))[0] == []
    warning = spec(min=0.9)
    warning['slices'][0]['blocking'] = False
    blocked, lines = slice_check(report([0, 0, 0]), clean, warning)
    assert not blocked and 'warn' in lines[0]


def test_missing_slice_or_mismatched_items_cannot_pass():
    clean = report([1, 1, 1])
    assert slice_check({'rows': []}, clean, spec(min=0.9))[0]
    changed = deepcopy(clean)
    changed['rows'] = changed['rows'][:-2]
    assert slice_check(changed, clean, spec(min=0.9, no_significant_drop=True))[0]

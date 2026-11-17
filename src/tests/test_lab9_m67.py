"""M6/M7 boundary and report-integrity regression cases."""
from copy import deepcopy
import json

import pytest

from lab9 import gate, stats


def report():
    return {'manifest': {'eval_set_sha': 'x', 'items': 2, 'seeds': [11, 22]},
            'rows': [{'item_id': item, 'seed': seed, 'pass_rate': True, 'slices': ['money']}
                     for item in ('E-1', 'E-2') for seed in (11, 22)],
            'metrics': {'pass_rate': 1.0}, 'evaluator_failures': []}


SPEC = {'eval_set_version': 'v2', 'seeds': [11, 22],
        'metrics': [{'id': 'pass_rate', 'blocking': True, 'kind': 'capability',
                     'threshold': {'min': 0.8, 'no_significant_drop': True}}],
        'slices': [{'name': 'money', 'metric': 'pass_rate', 'min': 0.8,
                    'blocking': True, 'no_significant_drop': True}]}


@pytest.mark.parametrize('args', [(0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, 0),
                                  (3, 1, 4), (5.0, 2, 1), (True, 1, 1)])
def test_both_pass_estimators_reject_invalid_counts(args):
    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            fn(*args)


def test_pass_estimators_ordering_and_extremes():
    for c in range(6):
        for k in range(1, 6):
            assert stats.pass_hat_k(5, c, k) <= c / 5 + 1e-12
            assert c / 5 <= stats.pass_at_k(5, c, k) + 1e-12
    assert stats.pass_hat_k(5, 5, 5) == stats.pass_at_k(5, 5, 5) == 1


@pytest.mark.parametrize('kind', ['duplicate', 'none', 'nan', 'inf', 'errors', 'seeds',
                                  'slice', 'summary', 'missing_metric'])
def test_integrity_rejects_tampering(kind):
    base, pr = report(), report()
    if kind == 'duplicate':
        pr['rows'][1] = deepcopy(pr['rows'][0])
    elif kind in ('none', 'nan', 'inf'):
        pr['rows'][0]['pass_rate'] = {'none': None, 'nan': float('nan'), 'inf': float('inf')}[kind]
    elif kind == 'errors':
        pr['evaluator_failures'] = ['grader crashed even though summary is green']
    elif kind == 'seeds':
        pr['manifest']['seeds'] = [11]
        pr['rows'] = [r for r in pr['rows'] if r['seed'] == 11]
    elif kind == 'slice':
        pr['rows'][0]['slices'] = []
    elif kind == 'summary':
        pr['rows'][0]['pass_rate'] = False
    else:
        del pr['metrics']['pass_rate']
    assert gate.integrity_check(pr, base, SPEC)
    blocked, lines = gate.check(pr, base, SPEC)
    assert blocked == ['integrity'] and any('INTEGRITY' in line for line in lines)


@pytest.mark.parametrize('kind', ['drop_metric', 'drop_slice', 'min', 'significance',
                                  'blocking', 'slice_min', 'slice_significance', 'slice_blocking'])
def test_ratchet_rejects_weaker_rules(kind):
    loose = deepcopy(SPEC)
    if kind == 'drop_metric':
        loose['metrics'] = []
    elif kind == 'drop_slice':
        loose['slices'] = []
    elif kind == 'min':
        loose['metrics'][0]['threshold']['min'] = 0.7
    elif kind == 'significance':
        loose['metrics'][0]['threshold'].pop('no_significant_drop')
    elif kind == 'blocking':
        loose['metrics'][0]['blocking'] = False
    elif kind == 'slice_min':
        loose['slices'][0]['min'] = 0.7
    elif kind == 'slice_significance':
        loose['slices'][0].pop('no_significant_drop')
    else:
        loose['slices'][0]['blocking'] = False
    assert gate.integrity_check(report(), report(), loose, SPEC)


def test_clean_report_and_stricter_spec_pass_integrity():
    strict = deepcopy(SPEC)
    strict['metrics'][0]['threshold']['min'] = 0.9
    assert gate.integrity_check(report(), report(), strict, SPEC) == []


def test_gate_cli_reads_protected_base_spec_from_environment(tmp_path, monkeypatch, capsys):
    import yaml

    clean = report()
    clean['run_id'] = 'test'
    loose = deepcopy(SPEC)
    loose['metrics'][0]['threshold']['min'] = 0.7
    pr, baseline = tmp_path / 'pr.json', tmp_path / 'baseline.json'
    current, protected = tmp_path / 'current.yaml', tmp_path / 'protected.yaml'
    for path in (pr, baseline):
        path.write_text(json.dumps(clean), encoding='utf-8')
    current.write_text(yaml.safe_dump(loose), encoding='utf-8')
    protected.write_text(yaml.safe_dump(SPEC), encoding='utf-8')
    monkeypatch.setenv('EVAL_BASE_SPEC', str(protected))
    assert gate.main(['--pr', str(pr), '--baseline', str(baseline), '--spec', str(current)]) == 1
    assert 'ratchet' in capsys.readouterr().out

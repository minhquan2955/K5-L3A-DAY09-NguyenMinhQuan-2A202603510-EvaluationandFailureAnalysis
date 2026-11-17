"""Replay M1 evidence from src/: python scripts/m1_trace_audit.py."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab8.shapes import SHAPES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape


def main():
    baseline = []
    for n in range(1, 15):
        for seed in (11, 22, 33, 44, 55):
            case = investigate('swarm', f'C-{n:03d}', seed)
            trial = case['trial']
            baseline.append({'claim': f'C-{n:03d}', 'seed': seed,
                             'passed': trial['lab8_pass'], 'reason': trial['lab8_reason'],
                             'events': trial['events'], 'snapshot': trial['snapshot'],
                             'result': trial['result']})
    anchors = []
    cases = [('FM-01', 'leaky_trace', 'C-010'),
             ('FM-02', 'ignore_denied', 'C-007'),
             ('FM-03', 'ticket_trust', 'C-002'),
             ('FM-04', 'sum_parts', 'C-014'),
             ('FM-05', 'pre_deducted', 'C-008'),
             ('FM-06', 'stale_clause', 'C-006'),
             ('FM-07', 'sibling_refund', 'C-001'),
             ('FM-08', 'misreport', 'C-014')]
    for fm, bug, claim in cases:
        shape = f'm1_{bug}'
        SHAPES[shape] = make_shape(shape, {bug, 'no_override'})
        broken = investigate(shape, claim, 11)
        fixed = investigate('fixed', claim, 11)
        anchors.append({'fm': fm, 'shape': shape, 'claim': claim, 'seed': 11,
                        'broken': broken, 'fixed': fixed})
        print(fm, claim, 'broken:', broken['trial']['lab8_reason'],
              'fixed:', fixed['trial']['lab8_pass'])
        for i, event in enumerate(broken['trial']['events'], 1):
            print(i, event['kind'], json.dumps(event.get('payload'), ensure_ascii=True))
        print('ledger:', broken['trial']['snapshot'], 'unexpected:', broken['trial']['unexpected_rows'])
    out = Path('data/eval/m1_trace_evidence.json')
    out.write_text(json.dumps({'baseline': baseline, 'anchors': anchors},
                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert len(baseline) == 70 and all(a['fixed']['trial']['lab8_pass'] for a in anchors)
    print('swarm:', sum(t['passed'] for t in baseline), '/ 70; evidence:', out)


if __name__ == '__main__':
    main()

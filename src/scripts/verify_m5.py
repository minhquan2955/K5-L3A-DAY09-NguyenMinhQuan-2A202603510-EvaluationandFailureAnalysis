"""Reproduce M5 eval-set and slice-gate evidence; run from src/."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys


def main():
    log = []

    def run(args, expected=0):
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', *args],
                                capture_output=True, text=True, encoding='utf-8')
        text = '$ python -m ' + ' '.join(args) + '\n' + result.stdout + result.stderr
        print(text.encode('ascii', errors='backslashreplace').decode(), flush=True)
        log.append(text + f'exit_status={result.returncode}\n')
        if result.returncode != expected:
            raise RuntimeError(f'Expected exit {expected}, got {result.returncode}')
        return result.stdout

    run(['lab9.evalset', '--v2', '--build'])
    items = [json.loads(line) for line in Path('data/eval/eval_set_v2.jsonl').read_text(encoding='utf-8').splitlines()]
    counts = Counter(fm for item in items for fm in item['failure_modes'])
    assert len(items) == 28 and all(counts[fm] >= 3 for item in items
                                  if item['split'] == 'adversarial' for fm in item['failure_modes'])
    log.append('failure_mode_item_counts=' + json.dumps(dict(sorted(counts.items()))) + '\n')
    for shape, out in [('swarm', 'baseline_v2'), ('fixed', 'eval_fixed_v2'),
                       ('honest_refactor', 'eval_honest_refactor_v2'), ('slice_regression', 'eval_slice_regression')]:
        run(['lab9.eval', '--shape', shape, '--spec', 'config/metric_spec_v2.yaml',
             '--out', f'reports/{out}.json'])
    for report, expected in [('baseline_v2', 0), ('eval_fixed_v2', 0),
                             ('eval_honest_refactor_v2', 0), ('eval_slice_regression', 1)]:
        output = run(['lab9.gate', '--pr', f'reports/{report}.json',
                      '--baseline', 'reports/baseline_v2.json', '--spec', 'config/metric_spec_v2.yaml'], expected)
        if expected == 1:
            verdict = next(line for line in output.splitlines() if line.startswith('exit 1'))
            assert verdict.endswith('blocked: slice:money_movement/pass_rate'), verdict
    Path('reports/gate_m5.txt').write_text('\n'.join(log), encoding='utf-8')


if __name__ == '__main__':
    main()

"""Run M6/M7 evidence commands and save their exact output; run from src/."""
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

    spec = 'config/metric_spec_v2.yaml'
    baseline = 'reports/baseline_v2.json'
    run(['lab9.evalset', '--v2', '--check'])
    run(['lab9.mutation', '--spec', spec, '--aa', '66,77,88,99,110'])
    for shape, name in [('swarm', 'baseline_v2'), ('fixed', 'eval_fixed_v2'),
                        ('honest_refactor', 'eval_honest_refactor_v2'),
                        ('seeded_regression', 'eval_seeded_regression_v2'),
                        ('slice_regression', 'eval_slice_regression'),
                        ('flaky_regression', 'eval_flaky_regression')]:
        run(['lab9.eval', '--shape', shape, '--spec', spec, '--out', f'reports/{name}.json'])
        expected = 1 if shape.endswith('regression') else 0
        output = run(['lab9.gate', '--pr', f'reports/{name}.json',
                      '--baseline', baseline, '--spec', spec, '--base-spec', spec], expected)
        if shape == 'flaky_regression':
            assert 'pass_hat_5' in next(line for line in output.splitlines() if line.startswith('exit 1'))
    run(['lab9.mutation', '--spec', spec, '--baseline', baseline, '--base-spec', spec])
    run(['lab9.traps', '--pr', 'reports/eval_slice_regression.json', '--baseline', baseline, '--spec', spec])
    for name in ('evaluator_errors_as_nan', 'dropped_failing_rows', 'cherry_picked_seeds', 'loosened_spec'):
        args = ['lab9.gate', '--pr', f'reports/traps/{name}.json', '--baseline', baseline,
                '--spec', f'reports/traps/{name}.spec.yaml' if name == 'loosened_spec' else spec]
        if name == 'loosened_spec':
            args += ['--base-spec', spec]
        assert 'INTEGRITY' in run(args, expected=1)
    Path('reports/gate_m67.txt').write_text('\n'.join(log), encoding='utf-8')


if __name__ == '__main__':
    main()

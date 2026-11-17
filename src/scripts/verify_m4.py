"""Reproduce core CI locally and save command-generated gate evidence. Run from src/."""
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

    run(['lab9.evalset', '--check'])
    for shape, out in [('swarm', 'baseline_v1'), ('swarm', 'eval_pr'),
                       ('fixed', 'eval_fixed'), ('seeded_regression', 'eval_seeded_regression')]:
        run(['lab9.eval', '--shape', shape, '--out', f'reports/{out}.json'])
    for report, expected in [('eval_pr', 0), ('eval_fixed', 0), ('eval_seeded_regression', 1)]:
        output = run(['lab9.gate', '--pr', f'reports/{report}.json',
                      '--baseline', 'reports/baseline_v1.json'], expected)
        if expected == 1:
            verdict = next(line for line in output.splitlines() if line.startswith('exit 1'))
            assert 'pass_rate' in verdict
    run(['lab9.ci_check', '--pr', 'reports/eval_pr.json', '--baseline', 'reports/baseline_v1.json'])
    Path('reports/gate_m4.txt').write_text('\n'.join(log), encoding='utf-8')


if __name__ == '__main__':
    main()

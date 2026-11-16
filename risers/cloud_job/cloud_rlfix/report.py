"""Report of the RoboLab test of the still-arm rule for RoboLab wordings (cloud_job/cloud_rlfix.sh), against v3-jpeg.

Usage: cd positronic && uv run --locked python ../cloud_job/cloud_rlfix/report.py > ../tests_robolab/results_cloud_rlfix.md
Reads the runs rl_v3jpegrl_s<k>_p<n> and rl_v3jpeg_s<k>_p<n> (13 Nov) in ~/evals: the task of each episode (static.json), RoboLab's progress signal
(subtask.parquet: [status, completed, total, score]) and the timing reports (*.timing.txt).
"""

import glob
import json
import os
import re
import statistics
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
EVALS = Path(os.path.expanduser('~/evals'))
GROUP = {'color': 'visual', 'semantics': 'visual', 'size': 'visual', 'conjunction': 'relational',
         'counting': 'relational', 'spatial': 'relational', 'affordance': 'procedural', 'reorientation': 'procedural',
         'sorting': 'procedural', 'stacking': 'procedural'}


def progress(folder: Path) -> list[list[float]]:
    files = sorted(folder.rglob('subtask*.parquet'))
    if not files:
        return []
    return [list(map(float, v)) for v in pq.read_table(files[0], columns=['value']).column('value').to_pylist()]


RUNS = (('v3-jpeg', 'v3jpeg'), ('v3-jpeg + RoboLab rule', 'v3jpegrl'))


def results(run: str) -> dict[str, dict]:
    rows = {}
    for f in glob.glob(str(EVALS / f'rl_{run}_s*_p*' / '**' / 'static.json'), recursive=True):
        static = json.loads(Path(f).read_text())
        values = progress(Path(f).parent)
        last = values[-1] if values else [0.0, 0.0, 0.0, 0.0]
        rows[static.get('eval.task')] = {'success': static.get('eval.success'), 'score': last[3]}
    return rows


def main() -> None:
    meta = {m['task_name']: m for m in json.loads((HERE / 'task_metadata.json').read_text())}
    order = [t for k in (1, 2, 3) for t in json.loads((HERE / f's{k}.json').read_text())]
    runs = {label: results(run) for label, run in RUNS}
    log = EVALS / 'rl_v3jpegrl.server.log'
    fired = log.read_text(errors='replace').count('task now') if log.exists() else 0
    print('# v3-jpeg with the still-arm rule for RoboLab wordings: cloud test')
    print()
    print('13 Nov. v3 has a still-arm rule: when the arm is still for 3 model calls with the gripper open, the model gets '
          'only the pick part of the task ("pick up the X."). Its wording matched 0 of the 120 RoboLab tasks; the new '
          'wording matches 54, and the same tasks of the board as before. Image v3-jpeg with that code mounted, on the '
          'same 12 RoboLab tasks as the test of v3-jpeg, with the default instruction and both shoulder cameras; cloud '
          'VM with an L40S GPU, 3 tasks at a time. The score of a task is RoboLab\'s graded score at the end of the '
          f'episode, from 0 to 1. The rule gave the pick part in {fired} sessions.')
    print()
    print('| Category | Tasks | ' + ' | '.join(f'{label}: successes | {label}: mean score' for label, _ in RUNS) + ' |')
    print('|---|---|' + '---|---|' * len(RUNS))
    for group in ('visual', 'relational', 'procedural', 'all'):
        sel = [t for t in order if group == 'all' or GROUP.get(meta[t]['attributes'].split(',')[0].strip()) == group]
        cells = []
        for label, _ in RUNS:
            done = [t for t in sel if t in runs[label]]
            cells += [f"{sum(bool(runs[label][t]['success']) for t in done)}" + ('' if len(done) == len(sel) else f' ({len(done)} done)'),
                      f"{statistics.mean(runs[label][t]['score'] for t in done):.2f}" if done else '-']
        print(f'| {"**all**" if group == "all" else group} | {len(sel)} | ' + ' | '.join(cells) + ' |')
    print()
    print('## Per task')
    print()
    print('| Task | Instruction | ' + ' | '.join(label for label, _ in RUNS) + ' |')
    print('|---|---|' + '---|' * len(RUNS))
    for t in order:
        cells = []
        for label, _ in RUNS:
            r = runs[label].get(t)
            cells.append('-' if r is None else f"{'yes' if r['success'] else 'no'} ({r['score']:.2f})")
        print(f"| {t} | {meta[t]['instruction'][:55]} | " + ' | '.join(cells) + ' |')
    print()
    print('## Time per model call')
    print()
    for f in sorted(glob.glob(str(EVALS / 'rl_v3jpegrl_s*_p*.timing.txt'))):
        text = Path(f).read_text()
        n = re.search(r'infer calls:\s+(\d+)', text)
        m = re.search(r'infer p50 / p95:\s+([\d.]+) / ([\d.]+) ms', text)
        if n and m:
            print(f'- {Path(f).name[:-11]}: {n[1]} calls, p50 {float(m[1]):.0f} ms, p95 {float(m[2]):.0f} ms')


if __name__ == '__main__':
    main()

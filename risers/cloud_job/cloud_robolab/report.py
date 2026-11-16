"""Report of the RoboLab test of the image v3-jpeg (cloud_job/cloud_robolab.sh).

Usage: cd positronic && uv run --locked python ../cloud_job/cloud_robolab/report.py > ../tests_robolab/results_cloud_robolab.md
Reads the runs rl_v3jpeg_s<k>_p<n> in ~/evals: the task of each episode (static.json), RoboLab's progress signal
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


def main() -> None:
    meta = {m['task_name']: m for m in json.loads((HERE / 'task_metadata.json').read_text())}
    order = [t for k in (1, 2, 3) for t in json.loads((HERE / f's{k}.json').read_text())]
    rows = {}
    for f in glob.glob(str(EVALS / 'rl_v3jpeg_s*_p*' / '**' / 'static.json'), recursive=True):
        static = json.loads(Path(f).read_text())
        task = static.get('eval.task')
        values = progress(Path(f).parent)
        last = values[-1] if values else [0.0, 0.0, 0.0, 0.0]
        rows[task] = {
            'success': static.get('eval.success'),
            'score': last[3],
            'best': max((v[3] for v in values), default=0.0),
            'done': f'{last[1]:.0f}/{last[2]:.0f}',
        }
    print('# v3-jpeg on RoboLab: cloud test')
    print()
    print('The submitted image v3-jpeg (v3 with JPEG frames) on 12 RoboLab tasks, 4 of each RoboLab category, with '
          'the default instruction and both shoulder cameras. Cloud VM with an L40S GPU; 3 tasks at a time, one '
          'policy server. The score of a task is RoboLab\'s graded score at the end of the episode, from 0 to 1 (the '
          'share of the subtasks done). The platform ranks RoboLab by the mean of this score.')
    print()
    print('| Category | Tasks run | Successes | Mean score |')
    print('|---|---|---|---|')
    for group in ('visual', 'relational', 'procedural', 'all'):
        sel = [t for t in order if t in rows and (group == 'all' or GROUP.get(
            meta[t]['attributes'].split(',')[0].strip()) == group)]
        if not sel:
            print(f'| {group} | 0 | - | - |')
            continue
        ok = sum(bool(rows[t]['success']) for t in sel)
        mean = statistics.mean(rows[t]['score'] for t in sel)
        print(f'| {"**all**" if group == "all" else group} | {len(sel)} | {ok} | {mean:.2f} |')
    print()
    print('## Per task')
    print()
    print('| Task | Instruction | Kind | Difficulty | Episode s | Success | Subtasks done | Score at end | Best score |')
    print('|---|---|---|---|---|---|---|---|---|')
    for t in order:
        m = meta[t]
        r = rows.get(t)
        cells = (['-'] * 4 if r is None
                 else ['yes' if r['success'] else 'no', r['done'], f"{r['score']:.2f}", f"{r['best']:.2f}"])
        print(f"| {t} | {m['instruction'][:50]} | {m['attributes']} | {m['difficulty_label']} | {m['episode_s']} | "
              + ' | '.join(cells) + ' |')
    print()
    print('## Time per model call')
    print()
    for f in sorted(glob.glob(str(EVALS / 'rl_v3jpeg_s*_p*.timing.txt'))):
        text = Path(f).read_text()
        n = re.search(r'infer calls:\s+(\d+)', text)
        m = re.search(r'infer p50 / p95:\s+([\d.]+) / ([\d.]+) ms', text)
        if n and m:
            print(f'- {Path(f).name[:-11]}: {n[1]} calls, p50 {float(m[1]):.0f} ms, p95 {float(m[2]):.0f} ms')


if __name__ == '__main__':
    main()

"""Report of the RoboLab test of the new rules of v3 (cloud_job/cloud_v3x_rl.sh), against the platform's run of v3.

Usage: cd positronic && uv run --locked python ../cloud_job/cloud_v3x_rl/report.py > ../tests_robolab/results_cloud_v3x_rl.md
Reads the runs rl_rlctl, rl_rlword and rl_rlall (rl_<name>_s<k>_p<n>, 14 Nov) in ~/evals, their server logs, and the
platform's RoboLab run of v3 on 10 Nov (platform_v3_result.json): the task of each episode (static.json), RoboLab's progress signal
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


RUNS = (('Control (v3-jpeg-rl)', 'rlctl'), ('Training wording + steps', 'rlword'), ('All new rules', 'rlall'))


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
    platform = json.loads((HERE / 'platform_v3_result.json').read_text())['scores']['per_task']
    runs['Platform, v3 (10 Nov)'] = {t: {'success': v['successes'] > 0, 'score': v['mean_subtask_score']}
                                     for t, v in platform.items()}
    labels = [label for label, _ in RUNS] + ['Platform, v3 (10 Nov)']
    print('# v3 with the new rules: RoboLab, the 12 tasks of the platform')
    print()
    print('14 Nov. Image v3-jpeg with the code of cloud_v3x_rl/code mounted, on the 12 tasks of the platform\'s '
          'robolab.subset_12 (default instruction, both shoulder cameras), one episode each; cloud VM with an L40S GPU, '
          '3 tasks at a time, the variants one after the other. "Control": no new rule (v3-jpeg-rl, with the still-arm '
          'rule for RoboLab wordings). "Training wording + steps": the task in the wording of MolmoBot\'s training data '
          '("Pick up the X and place it in or on the Y"), and a task of several objects one step at a time, in the order '
          'of the task (the next step after the gripper let go of a held object). "All": also the deeper grasp after a '
          'miss and the vote before a close. The last column is the platform\'s own run of v3 (10 Nov). The score of '
          'a task is RoboLab\'s graded score at the end of the episode, from 0 to 1; the platform ranks RoboLab by its '
          'mean.')
    print()
    print('| Category | Tasks | ' + ' | '.join(f'{label}: successes | {label}: mean score' for label in labels) + ' |')
    print('|---|---|' + '---|---|' * len(labels))
    for group in ('visual', 'relational', 'procedural', 'all'):
        sel = [t for t in order if group == 'all' or GROUP.get(meta[t]['attributes'].split(',')[0].strip()) == group]
        cells = []
        for label in labels:
            done = [t for t in sel if t in runs[label]]
            cells += [f"{sum(bool(runs[label][t]['success']) for t in done)}" + ('' if len(done) == len(sel) else f' ({len(done)} done)'),
                      f"{statistics.mean(runs[label][t]['score'] for t in done):.2f}" if done else '-']
        print(f'| {"**all**" if group == "all" else group} | {len(sel)} | ' + ' | '.join(cells) + ' |')
    print()
    print('## Per task')
    print()
    print('| Task | Instruction | ' + ' | '.join(labels) + ' |')
    print('|---|---|' + '---|' * len(labels))
    for t in order:
        cells = []
        for label in labels:
            r = runs[label].get(t)
            cells.append('-' if r is None else f"{'yes' if r['success'] else 'no'} ({r['score']:.2f})")
        print(f"| {t} | {meta[t]['instruction'][:55]} | " + ' | '.join(cells) + ' |')
    print()
    print('## What the rules did')
    print()
    for _, run in RUNS:
        log = EVALS / f'rl_{run}.server.log'
        if not log.exists():
            continue
        text = log.read_text(errors='replace')
        counts = [line.split('Rules so far: ', 1)[1].strip() for line in text.splitlines() if 'Rules so far' in line]
        print(f"- {run}: tasks reworded {text.count(' as [')}, next steps {text.count('next step')}, still-arm pick part "
              f"{text.count('task now')}, deeper grasps {text.count('cm deeper first')}"
              + (f'; last counts {counts[-1]}' if counts else ''))
    print()
    print('## Time per model call')
    print()
    for f in sorted(glob.glob(str(EVALS / 'rl_rl*_s*_p*.timing.txt'))):
        text = Path(f).read_text()
        n = re.search(r'infer calls:\s+(\d+)', text)
        m = re.search(r'infer p50 / p95:\s+([\d.]+) / ([\d.]+) ms', text)
        if n and m:
            print(f'- {Path(f).name[:-11]}: {n[1]} calls, p50 {float(m[1]):.0f} ms, p95 {float(m[2]):.0f} ms')


if __name__ == '__main__':
    main()

"""Summarize the 8 November local tests into tests_1108/results.md (close tasks and the blocked camera) and
tests_1108/results_open.md (open tasks: runs named op_*).

Usage (with ~/molmobot_src/venv/bin/python -I):
  summarize.py            write both files for every run in status.tsv
  summarize.py --line R   print one line for run R
"""

import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
PROJECT = D.parent
SET = json.loads((D / 'close17.json').read_text())
OPEN_SET = json.loads((D / 'open30.json').read_text())
KEYS = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')
LOGS = {'push': 'push starts', 'camera': 'uses the other shoulder camera', 'still': 'the arm is still and the gripper is open',
        'pull': 'open pull starts'}

_spec = importlib.util.spec_from_file_location('compare_runs', PROJECT / 'eval_local/compare_runs.py')
compare_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_runs)


def episodes(run: str) -> dict:
    out = {}
    for f in glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*/*/*/static.json')):
        s = json.loads(Path(f).read_text())
        out['/'.join(str(s[k]) for k in KEYS)] = compare_runs.episode(Path(f).parent)
    return out


def log_counts(run: str) -> dict:
    text = ''.join(Path(f).read_text() for f in glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*.server.log')))
    return {k: text.count(v) for k, v in LOGS.items()}


def open_line(run: str) -> str:
    eps = episodes(run)
    parts = []
    for group in ('open datagen', 'open hard'):
        sel = [e for e in OPEN_SET if e['group'] == group and e['path'] in eps]
        parts.append(f"{group} {sum(eps[e['path']]['ok'] for e in sel)}/{len(sel)}")
    pulled = len({line.split('Session ')[1].split(':')[0] for f in glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*.server.log'))
                  for line in Path(f).read_text().splitlines() if 'open pull starts' in line})
    return f"{run}: {', '.join(parts)}; pulls {log_counts(run)['pull']} in {pulled} episodes"


def line(run: str) -> str:
    if run.startswith('op_'):
        return open_line(run)
    eps = episodes(run)
    close = [e for e in SET if e['group'] == 'close hard']
    ok_close = sum(eps[e['path']]['ok'] for e in close if e['path'] in eps)
    done_close = sum(e['path'] in eps for e in close)
    other = [e for e in SET if e['group'] != 'close hard']
    ok_other = sum(eps[e['path']]['ok'] for e in other if e['path'] in eps)
    c = log_counts(run)
    return (f"{run}: close hard {ok_close}/{done_close}, other blocked-camera episodes {ok_other}/{sum(e['path'] in eps for e in other)}; "
            f"pushes {c['push']}, camera switches {c['camera']}, still-arm switches {c['still']}")


def runs_started() -> list[str]:
    if not (D / 'status.tsv').exists():
        return []
    seen = []
    for row in (D / 'status.tsv').read_text().splitlines():
        r = row.split('\t')[0]
        if r and r not in seen:
            seen.append(r)
    return seen


def main():
    if sys.argv[1:2] == ['--line']:
        print(line(sys.argv[2]))
        return
    write_open([r for r in runs_started() if r.startswith('op_')])
    runs = [r for r in runs_started() if not r.startswith('op_')]
    data = {r: episodes(r) for r in runs}
    out = ['# Local tests, 8 November: close tasks and the blocked camera', '',
           'MolmoBot-Img-DROID with the v3 settings (half overlap, left camera, 12 actions per call, 3 flow steps, '
           'still-arm rule) and the changes named per run. Local PC (RTX 4070).', '']
    out += ['| Run | Result |', '|---|---|'] + [f'| {r} | {line(r).split(": ", 1)[1]} |' for r in runs] + ['']
    out += ['| Board # | Episode | v3 board | Top 7 | Left camera blocked | ' + ' | '.join(runs) + ' |',
            '|---|---|---|---|---|' + '---|' * len(runs)]
    for e in SET:
        cells = []
        for r in runs:
            x = data[r].get(e['path'])
            cells.append('' if x is None else (f"OK {x['time']:.1f} s" if x['ok'] else 'no'))
        out.append(f"| {e['board_index']} | {e['task']} | {'OK' if e['v3_ok'] else 'no'} | {e['top7_solved']}/7 | "
                   f"{'yes' if e['left_camera_blocked'] else ''} | " + ' | '.join(cells) + ' |')
    (D / 'results.md').write_text('\n'.join(out) + '\n')


def write_open(runs: list[str]):
    data = {r: episodes(r) for r in runs}
    out = ['# Local tests, 8 November: open tasks', '',
           'The 30 open episodes of the board. Settings of image v4, plus the open changes named per run. Local PC.', '']
    out += ['| Run | Result |', '|---|---|'] + [f'| {r} | {open_line(r).split(": ", 1)[1]} |' for r in runs] + ['']
    out += ['| Board # | Episode | Kind | v3 board | Top 7 | ' + ' | '.join(runs) + ' |', '|---|---|---|---|---|' + '---|' * len(runs)]
    for e in OPEN_SET:
        cells = []
        for r in runs:
            x = data[r].get(e['path'])
            cells.append('' if x is None else (f"OK {x['time']:.1f} s" if x['ok'] else 'no'))
        out.append(f"| {e['board_index']} | {e['task']} | {e['kind']} | {'OK' if e['v3_ok'] else 'no'} | {e['top7_solved']}/7 | "
                   + ' | '.join(cells) + ' |')
    (D / 'results_open.md').write_text('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()

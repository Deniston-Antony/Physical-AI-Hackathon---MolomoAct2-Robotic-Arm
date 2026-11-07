"""Summarize the 7 November local tests (all parts of a run together) into tests_1107/results.md.

Usage (with ~/molmobot_src/venv/bin/python -I):
  summarize.py            write results.md
  summarize.py --line R   print one line for run R
An episode counts as frozen when it failed and, after the first 5 s, the median joint change over 3 s windows is
below FROZEN_RAD.
"""

import glob
import importlib.util
import json
import os
import re
import statistics as st
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

D = Path(__file__).resolve().parent
PROJECT = D.parent
FROZEN_RAD = 0.02
FROZEN19 = json.loads((D / 'frozen19.json').read_text())
HARD28 = json.loads((PROJECT / 'eval_local/hard28.json').read_text())
RUNS = {
    'frz_now': (FROZEN19, '5 flow steps, board wording (the 60% image)'),
    'frz_word': (FROZEN19, '5 flow steps, training wording'),
    'frz_flow3': (FROZEN19, '3 flow steps, board wording'),
    'frz_both': (FROZEN19, '3 flow steps, training wording'),
    'hard_flow3': (HARD28, '3 flow steps, board wording'),
    'hard_both': (HARD28, '3 flow steps, training wording'),
    'frz_still3': (FROZEN19, '3 flow steps, board wording, still-arm rule'),
    'hard_still3': (HARD28, '3 flow steps, board wording, still-arm rule'),
}
STILL_LOG = 'the arm is still and the gripper is open'
REFERENCE = {'play12_flow5': 'overnight: 5 flow steps, board wording (the 60% image)', 'grip40': 'overnight: the same and the gripper rule'}
KEYS = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')
SHORT = {'FrankaPickandPlaceDroidMiniBench': 'pnp normal', 'FrankaPickandPlaceHardBench': 'pnp hard', 'FrankaPickHardBench': 'pick hard'}

_spec = importlib.util.spec_from_file_location('compare_runs', PROJECT / 'eval_local/compare_runs.py')
compare_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_runs)


def motion(d: Path) -> float | None:
    t = pq.read_table(d / 'robot_state.q.parquet', columns=['ts.harness.world', 'value'])
    ts = np.asarray(t.column(0).to_pylist(), dtype=np.float64) / 1e9
    q = np.asarray(t.column(1).to_pylist(), dtype=np.float64)
    vals = []
    for start in np.arange(ts[0] + 5.0, ts[-1] - 3.0, 1.0):
        a, b = np.searchsorted(ts, start), np.searchsorted(ts, start + 3.0)
        if b < len(ts):
            vals.append(float(np.abs(q[b] - q[a]).max()))
    return float(np.median(vals)) if vals else None


def episodes(prefix: str) -> dict:
    out = {}
    for f in glob.glob(os.path.expanduser(f'~/evals/{prefix}_p*/*/*/static.json')):
        s = json.loads(Path(f).read_text())
        e = compare_runs.episode(Path(f).parent)
        e['motion'] = motion(Path(f).parent)
        e['frozen'] = not e['ok'] and e['motion'] is not None and e['motion'] < FROZEN_RAD
        out['/'.join(str(s[k]) for k in KEYS)] = e
    return out


def infer_p50(prefix: str) -> float | None:
    vals = []
    for f in glob.glob(os.path.expanduser(f'~/evals/{prefix}_p*.server.log')):
        vals += [float(x) for x in re.findall(r'MolmoBot inference over \d+ calls: p50 (\d+) ms', Path(f).read_text())]
    return st.median(vals) if vals else None


def rule_used(prefix: str) -> int:
    return sum(Path(f).read_text().count(STILL_LOG) for f in glob.glob(os.path.expanduser(f'~/evals/{prefix}_p*.server.log')))


def stats(prefix: str, eps_set: list) -> dict:
    eps = episodes(prefix)
    by_set = {}
    for e in eps_set:
        x = eps.get(e['path'])
        if x is not None:
            c = by_set.setdefault(SHORT[e['set']], [0, 0])
            c[0] += x['ok']
            c[1] += 1
    return dict(
        eps=eps, done=len(eps), ok=sum(e['ok'] for e in eps.values()), frozen=sum(e['frozen'] for e in eps.values()),
        by_set=by_set, wait=100 * st.mean(e['wait'] for e in eps.values()) if eps else None, infer=infer_p50(prefix),
        rule=rule_used(prefix),
    )


def fmt(v, f):
    return '-' if v is None else format(v, f)


def line(run: str, s: dict) -> str:
    sets = ', '.join(f'{k} {v[0]}/{v[1]}' for k, v in s['by_set'].items())
    return (f"{run}: {s['ok']}/{s['done']} solved ({sets}), frozen {s['frozen']}, robot waits {fmt(s['wait'], '.0f')}%, "
            f"inference p50 {fmt(s['infer'], '.0f')} ms, rule used {s['rule']} times")


def runs_started() -> list[str]:
    seen = set()
    if (D / 'status.tsv').exists():
        seen = {row.split('\t')[0] for row in (D / 'status.tsv').read_text().splitlines() if row}
    return [r for r in RUNS if r in seen]


def table(title: str, rows: dict, names: dict, eps_set: list) -> list[str]:
    out = [f'## {title}', '', '| Run | Setting | Solved | By set | Frozen | Robot waits | Inference p50 | Rule used |',
           '|---|---|---|---|---|---|---|---|']
    for r, s in rows.items():
        sets = ', '.join(f'{k} {v[0]}/{v[1]}' for k, v in s['by_set'].items())
        out.append(f"| {r} | {names[r]} | {s['ok']}/{s['done']} | {sets} | {s['frozen']} | {fmt(s['wait'], '.0f')}% | "
                   f"{fmt(s['infer'], '.0f')} ms | {s['rule']} |")
    out += ['', '| Episode | Set | ' + ' | '.join(rows) + ' |', '|---|---|' + '---|' * len(rows)]
    for e in eps_set:
        cells = []
        for s in rows.values():
            x = s['eps'].get(e['path'])
            if x is None:
                cells.append('')
            elif x['ok']:
                cells.append(f"OK {x['time']:.1f} s")
            else:
                cells.append(f"frozen ({fmt(x['motion'], '.3f')})" if x['frozen'] else f"no ({fmt(x['motion'], '.3f')})")
        out.append(f"| {e['task'][:55]} | {SHORT[e['set']]} | " + ' | '.join(cells) + ' |')
    return out + ['']


def main():
    if sys.argv[1:2] == ['--line']:
        run = sys.argv[2]
        print(line(run, stats(f't7_{run}', RUNS[run][0])))
        return
    started = runs_started()
    names = {r: RUNS[r][1] for r in RUNS} | REFERENCE
    out = ['# Local tests, 7 November', '', 'Model: MolmoBot-Img-DROID, half overlap, left camera, 12 actions per call. '
           f'Local PC (RTX 4070). Frozen: failed, and the median joint change over 3 s is below {FROZEN_RAD} rad '
           '(the number in brackets).', '']
    frz = {r: stats(f't7_{r}', FROZEN19) for r in started if RUNS[r][0] is FROZEN19}
    if frz:
        out += table('19 episodes where the arm froze on the board', frz, names, FROZEN19)
    hard = {r: stats(f'ovn_{r}', HARD28) for r in REFERENCE}
    for r in ('hard_flow3', 'hard_both', 'hard_still3'):
        if r in started:
            hard[r] = stats(f't7_{r}', HARD28)
    out += table('28 hard episodes (eval_local/hard28.json)', hard, names, HARD28)
    (D / 'results.md').write_text('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()

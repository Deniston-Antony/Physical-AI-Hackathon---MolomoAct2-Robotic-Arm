"""Summarize the overnight runs (all parts of a run together) into overnight/results.md.

Usage (with ~/molmobot_src/venv/bin/python):
  summarize.py            write results.md
  summarize.py --line R   print one line for run R
  summarize.py --best     print the best step-1 run: most successes, then the shorter mean episode
"""

import glob
import importlib.util
import json
import os
import re
import statistics as st
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
PROJECT = D.parent
SET = json.loads((PROJECT / 'eval_local/hard28.json').read_text())
STEP1 = {
    'base': 'play 8 actions, 10 flow steps (the submitted image)',
    'play12': 'play 12 actions, 10 flow steps',
    'flow5': 'play 8 actions, 5 flow steps',
    'play12_flow5': 'play 12 actions, 5 flow steps',
}
KEYS = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')

_spec = importlib.util.spec_from_file_location('compare_runs', PROJECT / 'eval_local/compare_runs.py')
compare_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_runs)


def episodes(run: str) -> dict:
    out = {}
    for f in glob.glob(os.path.expanduser(f'~/evals/ovn_{run}_p*/*/*/static.json')):
        s = json.loads(Path(f).read_text())
        e = compare_runs.episode(Path(f).parent)
        out['/'.join(str(s[k]) for k in KEYS)] = e
    return out


def infer_p50(run: str) -> float | None:
    vals = []
    for f in glob.glob(os.path.expanduser(f'~/evals/ovn_{run}_p*.server.log')):
        vals += [float(x) for x in re.findall(r'MolmoBot inference over \d+ calls: p50 (\d+) ms', Path(f).read_text())]
    return st.median(vals) if vals else None


def stats(run: str, base: dict) -> dict:
    eps = episodes(run)
    ok = [p for p, e in eps.items() if e['ok']]
    shared = [p for p in ok if p in base and base[p]['ok']]
    by_set = {cfg: sum(1 for e in SET if e['set'] == cfg and e['path'] in ok) for cfg in ('FrankaPickHardBench', 'FrankaPickandPlaceHardBench')}
    return dict(
        done=len(eps), ok=len(ok), pick=by_set['FrankaPickHardBench'], pnp=by_set['FrankaPickandPlaceHardBench'],
        wait=100 * st.mean(e['wait'] for e in eps.values()) if eps else None,
        mean_time=st.mean(e['time'] for e in eps.values()) if eps else None,
        shared=len(shared),
        t_run=st.median(eps[p]['time'] for p in shared) if shared else None,
        t_base=st.median(base[p]['time'] for p in shared) if shared else None,
        infer=infer_p50(run), eps=eps,
    )


def line(run: str, s: dict) -> str:
    f = lambda v, fmt: '-' if v is None else format(v, fmt)
    return (f"{run}: {s['ok']}/{s['done']} solved (hard pick {s['pick']}/16, hard pick-and-place {s['pnp']}/12), "
            f"robot waits {f(s['wait'], '.0f')}%, inference p50 {f(s['infer'], '.0f')} ms, "
            f"time to success on {s['shared']} episodes also solved by base: {f(s['t_run'], '.1f')} s vs {f(s['t_base'], '.1f')} s")


def runs_started() -> list[str]:
    order = list(STEP1) + ['grip40']
    seen = set()
    if (D / 'status.tsv').exists():
        seen = {l.split('\t')[0] for l in (D / 'status.tsv').read_text().splitlines() if l}
    return [r for r in order if r in seen]


def main():
    base = episodes('base')
    if sys.argv[1:2] == ['--line']:
        print(line(sys.argv[2], stats(sys.argv[2], base)))
        return
    if sys.argv[1:2] == ['--best']:
        done = {r: stats(r, base) for r in STEP1 if episodes(r)}
        print(max(done, key=lambda r: (done[r]['ok'], -(done[r]['mean_time'] or 1e9))))
        return
    step2_base = (D / 'step2_base.txt').read_text().strip() if (D / 'step2_base.txt').exists() else None
    names = {**STEP1, 'grip40': f'gripper rule (open only below 40) on {step2_base}'}
    rows = {r: stats(r, base) for r in runs_started()}
    f = lambda v, fmt: '-' if v is None else format(v, fmt)
    out = ['# Overnight test results', '', 'Episodes: `eval_local/hard28.json` (16 hard pick, 12 hard pick-and-place). '
           'Model: MolmoBot-Img-DROID, half overlap, left camera. Local PC (RTX 4070).', '',
           '| Run | Setting | Solved | Hard pick | Hard pick and place | Robot waits | Inference p50 | Time to success (shared with base) |',
           '|---|---|---|---|---|---|---|---|']
    for r, s in rows.items():
        out.append(f"| {r} | {names[r]} | {s['ok']}/{s['done']} | {s['pick']}/16 | {s['pnp']}/12 | {f(s['wait'], '.0f')}% | "
                   f"{f(s['infer'], '.0f')} ms | {f(s['t_run'], '.1f')} s vs {f(s['t_base'], '.1f')} s ({s['shared']} episodes) |")
    out += ['', '## Per episode', '', '| Episode | Set | ' + ' | '.join(rows) + ' |', '|---|---|' + '---|' * len(rows)]
    for e in SET:
        cells = []
        for s in rows.values():
            x = s['eps'].get(e['path'])
            cells.append('' if x is None else (f"OK {x['time']:.1f} s" if x['ok'] else 'no'))
        out.append(f"| {e['task'][:55]} | {'pick' if e['set'] == 'FrankaPickHardBench' else 'pick and place'} | " + ' | '.join(cells) + ' |')
    (D / 'results.md').write_text('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()

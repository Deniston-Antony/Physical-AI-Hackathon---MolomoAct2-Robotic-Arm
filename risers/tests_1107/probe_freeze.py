"""Ask MolmoBot again at frozen moments of the local runs, with changed inputs, and measure how far each answer moves.

Usage (from the positronic folder, as the server runs):
  PYTHONPATH=~/molmobot_src/repo/MolmoBot ~/molmobot_src/venv/bin/python ../tests_1107/probe_freeze.py [RUN ...]
RUN defaults to t7_frz_now. Output: tests_1107/probe_freeze.md and probe_freeze.json.
Move: the largest joint change (rad) from the arm's joints to the 12 actions that the robot plays (actions 4-15).
A frozen answer moves about 0.005 rad; a normal answer moves 0.05-0.3 rad.
"""

import glob
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq

from positronic.simulator.molmo_spaces import mapping
from positronic.vendors.molmobot.policy import _MmapCheckpointWrapper, exterior_side, training_wording

D = Path(__file__).resolve().parent
CHECKPOINT = os.path.expanduser('~/molmobot_src/MolmoBot-Img-DROID')
PERIOD_S = 1 / 15
SKIP = 4
TIMES_S = (8.0, 20.0)
SAMPLES = 3
PLACE = re.compile(r'pick up the (?P<item>.+) and place it on the (?P<target>.+?)\.?', re.IGNORECASE)

_spec = importlib.util.spec_from_file_location('summarize', D / 'summarize.py')
summarize = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(summarize)


def frames(path: Path, indices: list[int]) -> dict[int, np.ndarray]:
    want, out = set(indices), {}
    with av.open(str(path)) as c:
        for i, f in enumerate(c.decode(video=0)):
            if i in want:
                out[i] = f.to_ndarray(format='rgb24')
            if len(out) == len(want):
                break
    return out


def pick_only(task: str) -> str:
    m = PLACE.fullmatch(task.strip())
    return f'pick up the {m["item"]}.' if m else task


VARIANTS = {
    'same': lambda task, cam: (task, cam, 5),
    'other camera': lambda task, cam: (task, 1 - cam, 5),
    'pick-only task': lambda task, cam: (pick_only(task), cam, 5),
    'pick-only + other camera': lambda task, cam: (pick_only(task), 1 - cam, 5),
    'training wording': lambda task, cam: (training_wording(task), cam, 5),
    '10 flow steps': lambda task, cam: (task, cam, 10),
}


def moments(run: str) -> list[dict]:
    out = []
    for f in sorted(glob.glob(os.path.expanduser(f'~/evals/{run}_p*/*/*/static.json'))):
        d = Path(f).parent
        e = summarize.compare_runs.episode(d)
        m = summarize.motion(d)
        frozen = not e['ok'] and m is not None and m < summarize.FROZEN_RAD
        q = np.asarray(pq.read_table(d / 'robot_state.q.parquet', columns=['value']).column(0).to_pylist(), np.float32)
        grip = np.asarray(pq.read_table(d / 'grip.parquet', columns=['value']).column(0).to_pylist(), np.float32)
        times = TIMES_S if frozen else (1.0,)
        idx = [min(int(round(t / PERIOD_S)), len(q) - 1) for t in times]
        out.append(dict(dir=d, task=e['task'], ok=e['ok'], frozen=frozen, motion=m, idx=idx, q=q, grip=grip))
    return out


def main():
    runs = sys.argv[1:] or ['t7_frz_now']
    agent = _MmapCheckpointWrapper(CHECKPOINT, num_flow_steps=5, states_mode='cross_attn')
    rows = []
    for run in runs:
        for ep in moments(run):
            d = ep['dir']
            need = [0, *ep['idx']]
            ext = frames(d / 'image.exterior.mp4', need)
            ext2 = frames(d / 'image.exterior_2.mp4', need)
            wrist = frames(d / 'image.wrist.mp4', need)
            # The camera index the run used: 0 = image.exterior, 1 = image.exterior_2 (the server picks the left one).
            cam = 0 if exterior_side(ext[0], ext2[0]) == 'left' else 1
            for i in ep['idx']:
                joints = ep['q'][i]
                state = np.append(joints, ep['grip'][i] * mapping.GRIPPER_QPOS_CLOSED).astype(np.float32)
                res = {}
                for name, v in VARIANTS.items():
                    task, c, steps = v(ep['task'], cam)
                    agent.num_flow_steps = steps
                    images = [(ext, ext2)[c][i], wrist[i]]
                    moves, grips = [], []
                    for _ in range(SAMPLES):
                        chunk = agent.get_action_chunk(images=images, task_description=task, state=state)
                        played = chunk[SKIP:]
                        moves.append(float(np.abs(played[:, :7] - joints).max()))
                        grips.append(float(played[:, 7].max()))
                    res[name] = dict(move=moves, grip=grips)
                row = dict(run=run, ep=str(d), task=ep['task'], ok=ep['ok'], frozen=ep['frozen'], t=i * PERIOD_S, res=res)
                rows.append(row)
                print(f"{row['task'][:50]:50s} t={row['t']:4.1f} {'FROZEN' if ep['frozen'] else ('ok' if ep['ok'] else 'fail')} "
                      + ' '.join(f"{k}={np.median(r['move']):.3f}" for k, r in res.items()), flush=True)
    (D / 'probe_freeze.json').write_text(json.dumps(rows, indent=1))
    write_md(rows)


def write_md(rows: list[dict]):
    names = list(VARIANTS)
    out = ['# Probe: ask MolmoBot again at frozen moments', '',
           'Median move (rad) of 3 answers. A frozen answer moves about 0.005 rad. Moves above 0.03 rad are in bold.', '',
           '| Episode | State | t (s) | ' + ' | '.join(names) + ' |', '|---|---|---|' + '---|' * len(names)]
    for r in rows:
        state = 'frozen' if r['frozen'] else ('solved' if r['ok'] else 'failed')
        cells = []
        for n in names:
            m = float(np.median(r['res'][n]['move']))
            cells.append(f'**{m:.3f}**' if m > 0.03 else f'{m:.3f}')
        out.append(f"| {r['task'][:50]} | {state} | {r['t']:.1f} | " + ' | '.join(cells) + ' |')
    frozen = [r for r in rows if r['frozen']]
    if frozen:
        out += ['', f'Frozen moments where the answer moves above 0.03 rad (of {len(frozen)}):', '']
        for n in names:
            k = sum(float(np.median(r['res'][n]['move'])) > 0.03 for r in frozen)
            out.append(f'- {n}: {k}')
    (D / 'probe_freeze.md').write_text('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()

"""Sort the episodes of a local pick-and-place run by how far the robot got, and save a picture strip of each.

Usage: python episode_phases.py <run dir> [strip dir]   (run with ~/molmobot_src/venv/bin/python -I)
From the gripper signals: the first close command, whether the fingers stopped on an object (closure below
`HELD_BELOW` while the close command holds), and the first open command after that. A strip holds 6 frames of the
exterior and the wrist video, from the start to the end of the episode.
"""

import json
import sys
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

HELD_BELOW = 0.9  # a closed gripper with nothing between the fingers reads about 1.0
FRAMES = 6


def signal(d: Path, name: str):
    t = pq.read_table(d / f'{name}.parquet', columns=['ts.harness.world', 'value'])
    ts = np.asarray(t.column(0).to_pylist(), dtype=np.int64)
    return ts, np.asarray(t.column(1).to_pylist(), dtype=np.float32)


def frames(path: Path, n: int) -> list[np.ndarray]:
    with av.open(str(path)) as c:
        all_frames = [f.to_ndarray(format='rgb24') for f in c.decode(c.streams.video[0])]
    idx = np.linspace(0, len(all_frames) - 1, n).round().astype(int)
    return [all_frames[i] for i in idx]


def strip(d: Path, out: Path) -> None:
    rows = [np.concatenate(frames(d / f'image.{cam}.mp4', FRAMES), axis=1) for cam in ('exterior', 'wrist')]
    img = Image.fromarray(np.concatenate(rows, axis=0))
    img.thumbnail((1800, 1800))
    img.save(out)


def phases(d: Path) -> dict:
    s = json.loads((d / 'static.json').read_text())
    tg_t, tg = signal(d, 'target_grip')
    g_t, g = signal(d, 'grip')
    t0 = g_t[0]
    end = (g_t[-1] - t0) / 1e9
    closed = np.flatnonzero(tg > 0.5)
    first_close = (tg_t[closed[0]] - t0) / 1e9 if len(closed) else None
    held = release = None
    if len(closed):
        after = g_t >= tg_t[closed[0]]
        cmd_at = np.interp(g_t, tg_t, tg)
        holding = after & (cmd_at > 0.5) & (g < HELD_BELOW) & (g > 0.05)
        if holding.any():
            held = (g_t[np.flatnonzero(holding)[0]] - t0) / 1e9
            opened = np.flatnonzero((tg_t > g_t[np.flatnonzero(holding)[0]]) & (tg < 0.5))
            release = (tg_t[opened[0]] - t0) / 1e9 if len(opened) else None
    if s.get('eval.success'):
        verdict = 'success'
    elif first_close is None:
        verdict = 'never closed the gripper'
    elif held is None:
        verdict = 'closed on nothing'
    elif release is None:
        verdict = 'held the object until the time ran out'
    else:
        verdict = 'let go, but not next to the target (or dropped it)'
    return dict(task=s['eval.task'], ok=bool(s.get('eval.success')), end=end, first_close=first_close, held=held,
                release=release, verdict=verdict)


def main(run_dir: str, strip_dir: str | None = None):
    rows = []
    for i, d in enumerate(sorted(p.parent for p in Path(run_dir).glob('*/*/static.json'))):
        r = phases(d)
        rows.append(r)
        fmt = lambda x: '-' if x is None else f'{x:4.1f}s'
        print(f"{i:2d} {r['verdict']:48s} close {fmt(r['first_close'])} holds {fmt(r['held'])} "
              f"lets go {fmt(r['release'])} end {r['end']:4.1f}s | {r['task'][:60]}")
        if strip_dir:
            Path(strip_dir).mkdir(parents=True, exist_ok=True)
            strip(d, Path(strip_dir) / f'{i:02d}.jpg')
    counts = {}
    for r in rows:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
    print(counts)


if __name__ == '__main__':
    main(*sys.argv[1:3])

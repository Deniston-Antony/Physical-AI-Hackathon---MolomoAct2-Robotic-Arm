"""Compare the grasp timeline of the top 5 teams with ours on the reliable board episodes (tests_1108/reliable34.json).

Usage: ~/molmobot_src/venv/bin/python competition_runs/board_videos/reliable_report.py [local run, e.g. reliable_v3]
Top teams and our board v3 run: outcome and duration from the board, closes read from the wrist video
(moves.json, written by measure_moves.py). A local run: closes from the recorded gripper signal.
"""

import glob
import json
import os
import statistics
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grip_from_video as G  # noqa: E402

P = Path(__file__).resolve().parent.parent.parent
REPLAYS = Path('/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/board_replays')
OUR_TAG = 'd2504d'
# Sets where the wrist-video closure is right: the gripper starts open on the board, and a close before 1 s is in
# 0 % (DataGen, DroidMini) or 8 % (OpenHard, CloseHard) of their videos. The hard pick sets move the wrist camera per
# episode, and the closure of their videos is wrong in 29-50 % of them.
VIDEO_OK = {'OpenDataGen', 'CloseDataGen', 'PickDroidMini', 'PickandPlaceDroidMini', 'OpenHard', 'CloseHard'}
KEYS = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')


def local_run(run: str) -> dict:
    out = {}
    for f in glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*/*/*/static.json')):
        d = os.path.dirname(f) + '/'
        s = json.loads(Path(f).read_text())
        t = pq.read_table(d + 'grip.parquet', columns=['ts.harness.world', 'value'])
        gt = np.asarray(t.column(0).to_pylist()) / 1e9
        g = np.clip(np.asarray(t.column(1).to_pylist(), dtype=float).ravel(), 0, 1)
        ev = G.grasp_events(g, gt - gt[0])
        out['/'.join(str(s[k]) for k in KEYS)] = {'ok': bool(s.get('eval.success')), 'duration_s': gt[-1] - gt[0],
                                                  'first_close_s': ev['first_close_s'], 'closes': ev['closes']}
    return out


def video(m: dict, group: str) -> dict | None:
    """A video measurement that can be right: its set is in VIDEO_OK and it has no close before 1 s."""
    if group not in VIDEO_OK or (m['first_close_s'] is not None and m['first_close_s'] < 1.0):
        return None
    return m


def med(values: list) -> str:
    values = [v for v in values if v is not None]
    return f'{statistics.median(values):.1f}' if values else '-'


def main() -> None:
    run = sys.argv[1] if len(sys.argv) > 1 else None
    eps = json.loads((P / 'tests_1108' / 'reliable34.json').read_text())
    top, ours = [], None
    for folder in REPLAYS.iterdir():
        if (folder / 'moves.json').exists():
            moves = json.loads((folder / 'moves.json').read_text())
            if folder.name.split('_')[-2] == OUR_TAG:
                ours = moves
            else:
                top.append(moves)
    local = local_run(run) if run else {}
    done = [e for e in eps if e['path'] in local]
    print(f'# The {len(eps)} reliable board episodes: top 5 vs us')
    print()
    print('Reliable: 3 or more of the top 5 teams solve the episode, and 2 or more of our 3 board runs fail it.')
    print('First close and closes: for the top teams and our board v3 run, read from the wrist video (right within 1 s')
    print('in about 3 of 4 episodes); for a local run, from the recorded gripper signal.')
    print()
    if run:
        print(f'Solved by the local run {run}: {sum(local[e["path"]]["ok"] for e in done)}/{len(done)} '
              f'(board v3 on the same episodes: {sum(e["v3_ok"] for e in done)}/{len(done)})')
        print()
    groups = sorted({e['group'] for e in eps}, key=lambda g: -sum(e['group'] == g for e in eps))
    print('| Set | Episodes | Top-5 solves (of 5 each) | Board v3 / v4 / v5 | Local run |'
          ' Top first close s | Our board v3 first close s | Local first close s | Top closes | Our board closes |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for g in groups + ['All']:
        sel = [e for e in eps if g in ('All', e['group'])]
        idx = [e['board_index'] for e in sel]
        top_ok = [v for t in top for e in sel if t[e['board_index']]['ok'] and (v := video(t[e['board_index']], e['group']))]
        our_v = [v for e in sel if (v := video(ours[e['board_index']], e['group']))]
        loc = [local[e['path']] for e in sel if e['path'] in local]
        print(f"| {g} | {len(sel)} | {sum(e['top5_solved'] for e in sel)} | "
              f"{sum(e['v3_ok'] for e in sel)} / {sum(e['v4_ok'] for e in sel)} / {sum(e['v5_ok'] for e in sel)} | "
              f"{sum(x['ok'] for x in loc) if loc else '-'}{'/' + str(len(loc)) if loc else ''} | "
              f"{med([m['first_close_s'] for m in top_ok])} | {med([m['first_close_s'] for m in our_v])} | "
              f"{med([x['first_close_s'] for x in loc])} | {med([m['closes'] for m in top_ok])} | "
              f"{med([m['closes'] for m in our_v])} |")
    print()
    print('## Per episode')
    print()
    print('| Board # | Set | Task | Top solves | Top time s | Top first close s | Board v3 | Board v3 first close s, '
          'closes | Local | Local first close s, closes |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for e in sorted(eps, key=lambda e: (e['group'], e['board_index'])):
        i = e['board_index']
        top_ok = [v for t in top if t[i]['ok'] and (v := video(t[i], e['group']))]
        o = video(ours[i], e['group']) or {'first_close_s': None, 'closes': '-'}
        x = local.get(e['path'])
        loc = (f"{'OK' if x['ok'] else 'no'} {x['duration_s']:.1f} s", f"{med([x['first_close_s']])}, {x['closes']}") \
            if x else ('-', '-')
        print(f"| {i} | {e['group']} | {e['task'][:50]} | {e['top5_solved']} | {e['top5_median_s']} | "
              f"{med([m['first_close_s'] for m in top_ok])} | {'OK' if e['v3_ok'] else 'no'} | "
              f"{med([o['first_close_s']])}, {o['closes']} | {loc[0]} | {loc[1]} |")
    all_reliable(top, ours)


def all_reliable(top: list, ours: list) -> None:
    """The grasp timeline over every board episode that 3 or more of the top 5 solve, in the VIDEO_OK sets."""
    sets = json.loads((P / 'competition_runs' / 'episode_sets.json').read_text())
    group = [s['set'].removeprefix('Franka').removesuffix('Bench').removesuffix('Config') for s in sets]
    print()
    print('## Every episode that 3 or more of the top 5 solve (sets with a right video closure)')
    print()
    print('| Set | Episodes | Top successes: first close s, closes, time s | Our board v3 successes: first close s, '
          'closes, time s | Our board v3 failures: first close s, closes |')
    print('|---|---|---|---|---|')
    for g in sorted(VIDEO_OK):
        idx = [i for i in range(len(sets)) if group[i] == g and sum(t[i]['ok'] for t in top) >= 3]
        tops = [v for t in top for i in idx if t[i]['ok'] and (v := video(t[i], g))]
        good = [v for i in idx if ours[i]['ok'] and (v := video(ours[i], g))]
        bad = [v for i in idx if not ours[i]['ok'] and (v := video(ours[i], g))]

        def cell(ms: list, time: bool = True) -> str:
            if not ms:
                return '-'
            parts = [med([m['first_close_s'] for m in ms]), med([m['closes'] for m in ms])]
            return ', '.join(parts + ([med([m['duration_s'] for m in ms])] if time else [])) + f' (n={len(ms)})'

        print(f'| {g} | {len(idx)} | {cell(tops)} | {cell(good)} | {cell(bad, False)} |')


if __name__ == '__main__':
    main()

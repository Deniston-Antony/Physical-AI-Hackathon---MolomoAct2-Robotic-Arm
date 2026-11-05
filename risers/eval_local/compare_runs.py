"""Compare local runs on the same episodes: success, episode time, and the share of time the robot waits.

Usage: python compare_runs.py <run dir A> <run dir B>   (run with a python that has pyarrow, e.g. ~/molmobot_src/venv)
A gap between two arm commands that is longer than 1.5 control periods counts as waiting, and so does the time
before the first command.
"""

import json
import statistics as st
import sys
from pathlib import Path

import pyarrow.parquet as pq

PERIOD_S = 1 / 15


def episode(d: Path) -> dict:
    s = json.loads((d / 'static.json').read_text())
    cmd = pq.read_table(d / 'robot_command.joints.parquet', columns=['ts.harness.world']).column(0).to_pylist()
    q = pq.read_table(d / 'robot_state.q.parquet', columns=['ts.harness.world']).column(0).to_pylist()
    start, end = q[0], q[-1]
    duration = (end - start) / 1e9
    waiting = (cmd[0] - start) / 1e9 if cmd else duration
    for a, b in zip(cmd, cmd[1:]):
        gap = (b - a) / 1e9
        if gap > 1.5 * PERIOD_S:
            waiting += gap - PERIOD_S
    key = (s.get('molmo.benchmark'), s.get('molmo.episode_index'), s['eval.task'])
    return dict(key=key, task=s['eval.task'], ok=bool(s.get('eval.success')), time=duration, wait=waiting / duration)


def run(path: str) -> dict:
    return {e['key']: e for e in map(episode, sorted(p.parent for p in Path(path).glob('*/*/static.json')))}


def main(a_path: str, b_path: str):
    a, b = run(a_path), run(b_path)
    shared = [k for k in a if k in b]
    print(f"{'task':45s} {'A':>12s} {'B':>12s}")
    for k in shared:
        fa, fb = a[k], b[k]
        print(f"{fa['task'][:45]:45s} {'OK ' if fa['ok'] else 'no '}{fa['time']:5.1f}s {100*fa['wait']:3.0f}% "
              f"{'OK ' if fb['ok'] else 'no '}{fb['time']:5.1f}s {100*fb['wait']:3.0f}%")
    for name, r in (('A', a), ('B', b)):
        es = [r[k] for k in shared]
        print(f"{name}: {sum(e['ok'] for e in es)}/{len(es)} succeeded, robot waits {100 * st.mean(e['wait'] for e in es):.0f}% "
              f"of the time, median episode {st.median(e['time'] for e in es):.1f} s")
    both = [k for k in shared if a[k]['ok'] and b[k]['ok']]
    if both:
        print(f"on the {len(both)} episodes both solved: median time to success A {st.median(a[k]['time'] for k in both):.1f} s, "
              f"B {st.median(b[k]['time'] for k in both):.1f} s")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

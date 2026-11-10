"""Gripper trace of local episodes: position (base frame), axis, motion and grip every 2 s.

Usage: arm_trace.py <run prefix, e.g. t8_cl_base> [first episode number]
"""
import glob, json, os, sys
from pathlib import Path
import numpy as np, pyarrow.parquet as pq

def quat2mat(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

def load(d, f):
    t = pq.read_table(d / f, columns=['ts.harness.world', 'value'])
    return np.asarray(t.column(0).to_pylist()) / 1e9, np.asarray(t.column(1).to_pylist())

files = sorted(glob.glob(os.path.expanduser(f'~/evals/{sys.argv[1]}_p*/*/*/static.json')))
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
for f in files[start:]:
    d = Path(f).parent; s = json.loads(Path(f).read_text())
    qt, q = load(d, 'robot_state.q.parquet'); et, ee = load(d, 'robot_state.ee_pose.parquet'); gt, g = load(d, 'grip.parquet')
    t0 = qt[0]
    print(f"== {s['eval.task']} {'OK' if s.get('eval.success') else 'FAIL'} {qt[-1]-t0:.1f}s sides {s.get('molmo.exterior_sides')}")
    for t in np.arange(0, qt[-1] - t0, 2.0):
        i = np.searchsorted(qt, t0 + t); j = min(np.searchsorted(qt, t0 + t + 2), len(q) - 1)
        p = ee[i][:3]; ax = quat2mat(ee[i][3:7])[:, 2]
        print(f"  t={t:4.1f} pos ({p[0]:+.2f},{p[1]:+.2f},{p[2]:+.2f}) axis ({ax[0]:+.2f},{ax[1]:+.2f},{ax[2]:+.2f}) "
              f"moves {np.abs(q[j]-q[i]).max():.2f} rad/2s, tcp {np.linalg.norm(ee[j][:3]-p)*100:4.1f} cm/2s, grip {g[i]:.2f}")

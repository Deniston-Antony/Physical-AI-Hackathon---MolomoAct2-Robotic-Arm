import json, os, sys, glob
import pyarrow.parquet as pq
root = sys.argv[1]
rows = []
for st in sorted(glob.glob(os.path.join(root, '*', '*', 'static.json'))):
    d = os.path.dirname(st)
    s = json.load(open(st))
    def col(name, c='value'):
        t = pq.read_table(os.path.join(d, name + '.parquet'), columns=['ts.harness.world', c])
        return t.column('ts.harness.world').to_pylist(), t.column(c).to_pylist()
    tg_t, tg = col('target_grip')
    g_t, g = col('grip')
    p_t, pose = col('robot_state.ee_pose')
    t0 = g_t[0]
    dur = (g_t[-1] - t0) / 1e9
    z = [p[2] for p in pose]
    # first time the model commanded a close
    close_idx = next((i for i, v in enumerate(tg) if v > 0.5), None)
    lift = None
    if close_idx is not None:
        tc = tg_t[close_idx]
        zc = [zz for tt, zz in zip(p_t, z) if tt >= tc]
        lift = (max(zc) - zc[0]) if zc else None
    rows.append(dict(
        ep=os.path.basename(d), cfg=s.get('molmo.task_config'), scene=s.get('molmo.scene_dataset'),
        task=s.get('eval.task'), ok=bool(s.get('eval.success')), timeout=s.get('eval.timeout'),
        horizon=s.get('molmo.task_horizon'), dur=round(dur, 1),
        late50=s.get('inference.policy.eval.schedule.late_p50_ms'), late90=s.get('inference.policy.eval.schedule.late_p90_ms'),
        dropped=s.get('inference.policy.eval.schedule.dropped'), gapmax=s.get('inference.policy.eval.schedule.gap_max_ms'),
        tg_max=round(max(tg), 3), g_max=round(max(g), 3), g_end=round(g[-1], 3),
        closed_frac=round(sum(1 for v in tg if v > 0.5) / len(tg), 2),
        lift=None if lift is None else round(lift, 3),
    ))
json.dump(rows, open(sys.argv[2], 'w'), indent=0)
print(len(rows), 'episodes')

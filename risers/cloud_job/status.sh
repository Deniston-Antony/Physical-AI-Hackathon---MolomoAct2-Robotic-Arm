#!/usr/bin/env bash
# Show the state of the open/close job: local tests (one line per episode), cloud training, saved models, job logs.
# Usage: bash cloud_job/status.sh          (once)
#        watch -n 60 bash cloud_job/status.sh   (refresh every minute; Ctrl+C to stop)
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
SSD="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/molmobot_openclose_2026-11-09"
echo "=== $(date '+%F %T') ==="

echo; echo "--- Local tests on this PC ---"
for unit in risers-ckqueue risers-midtest risers-finish; do
  printf '%-16s %s\n' "$unit" "$(systemctl --user is-active "$unit" 2>/dev/null)"
done
"$HOME/molmobot_src/venv/bin/python" -I - "$P/tests_1108" <<'PY' 2>/dev/null
import importlib.util, json, sys
d = sys.argv[1]
spec = importlib.util.spec_from_file_location('s', d + '/summarize.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
sets = {'open30.json': ('op_pull', 'v4 + pull'), 'close15.json': ('img_v4', 'v4'), 'closedatagen15.json': (None, '')}
runs = [('mid1000_open', 'open30.json', 'step-1000 model, open'), ('v5_open', 'open30.json', 'final model, open'),
        ('v5_close', 'close15.json', 'final model, hard close'), ('v5_closen', 'closedatagen15.json', 'final model, normal close')]
runs += [(f'op_step{n}', 'open30.json', f'step-{n} model, open') for n in (2400, 2200, 2000, 1800, 1600, 1400, 1200, 800, 600, 400, 200)]
for run, set_file, label in runs:
    eps = s.episodes(run)
    if not eps:
        continue
    episodes = json.load(open(f'{d}/{set_file}'))
    base_run, base_label = sets[set_file]
    base = s.episodes(base_run) if base_run else {}
    print(f'\n{label} ({run}): {len(eps)}/{len(episodes)} done, {sum(e["ok"] for e in eps.values())} solved'
          + (f' | {base_label} on the same episodes: {sum(base[p]["ok"] for p in eps if p in base)}' if base else ''))
    for e in episodes:
        x = eps.get(e['path'])
        if x is None:
            continue
        b = base.get(e['path'])
        res = f"OK {x['time']:.1f} s" if x['ok'] else 'no'
        old = ('OK' if b['ok'] else 'no') if b else '-'
        print(f"  #{e['board_index']:<4} {e['task']:<36} {res:<10} | {base_label or 'board'}: {old}")
PY
tail -1 "$P/tests_1108/tests.log"

echo; echo "--- Cloud training ---"
T=$(cut -d' ' -f1 "$J/train_ip" 2>/dev/null)
if out=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "ubuntu@$T" \
  'grep -a -E "\[step=" ~/train.log | tail -1 | grep -o "step=[0-9/]*, eta=[^]]*"; grep -a "train/action_flow_loss=" ~/train.log | tail -1 | tr -d " "; grep -a -m1 "TRAIN done\|Traceback" ~/train.log; true' 2>/dev/null); then
  echo "$out"
else
  echo "training VM not reachable (deleted after training, or the network is down)"
fi

echo; echo "--- Models on the SSD ---"
ls "$SSD/experts" 2>/dev/null | sort -V | tr '\n' ' '; echo
ls "$SSD"/*.pt 2>/dev/null

echo; echo "--- Job logs (last lines) ---"
grep -aE '^[0-9]{4}-' "$J/checkpoint_queue.log" 2>/dev/null | tail -4
tail -3 "$J/finish_job.log" 2>/dev/null
tail -5 "$J/after_training.log" 2>/dev/null
tail -2 "$J/ledger.txt"

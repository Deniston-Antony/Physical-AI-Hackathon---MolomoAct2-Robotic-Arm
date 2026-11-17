#!/usr/bin/env bash
# Only 3 policy servers fit in the GPU memory of the L40S (10.9 GB each, plus the simulators). The 4th stream
# (reliable_touch_b) failed with CUDA out of memory and was stopped. This script runs its 17 episodes in the free
# slots: 5 at the end of the stream reliable_touch_a (its set file grows), 9 in a new stream reliable_touch_c when the
# first of the other streams ends, 3 in reliable_touch_d when the second ends. It writes ~/cloud_eval/ALL_DONE2 when
# every stream has ended.
set -uo pipefail
D=$HOME/cloud_eval
V5=docker.io/denistonantony/molmobot-img-droid@sha256:f8feb081c51914945daf3fed7bd03c6cac7d1cc9402ed1e707a10edd785df517
say() { echo "$(date '+%F %T') $*" >> "$D/vm.log"; }
ended() { grep -cE '\[reliable_(v3_a|v3_b|touch_a)\] STREAM DONE' "$D/vm.log"; }

python3 -I - "$D" <<'PY'
import json, os, sys
d = sys.argv[1]
b = json.load(open(f'{d}/touch_b.json'))
a = json.load(open(f'{d}/touch_a.json'))
json.dump(b[:9], open(f'{d}/touch_c.json', 'w'), indent=1)
json.dump(b[14:], open(f'{d}/touch_d.json', 'w'), indent=1)
json.dump(a + b[9:14], open(f'{d}/touch_a.new', 'w'), indent=1)
os.replace(f'{d}/touch_a.new', f'{d}/touch_a.json')
PY
say "MORE: 5 episodes of reliable_touch_b added to reliable_touch_a; 9 wait for the first free slot, 3 for the second"
until [ "$(ended)" -ge 1 ]; do sleep 20; done
say "MORE: a slot is free; stream reliable_touch_c starts (9 episodes)"
bash "$D/run_stream.sh" reliable_touch_c "$D/touch_c.json" "$V5" 8004 &
until [ "$(ended)" -ge 2 ]; do sleep 20; done
say "MORE: a second slot is free; stream reliable_touch_d starts (3 episodes)"
bash "$D/run_stream.sh" reliable_touch_d "$D/touch_d.json" "$V5" 8005 &
wait
until [ -f "$D/ALL_DONE" ]; do sleep 20; done
say "ALL DONE 2: $(ls "$HOME"/evals/t8_reliable_*_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
touch "$D/ALL_DONE2"

#!/usr/bin/env bash
# Run the two tests on the 34 reliable board episodes (tests_1108/reliable34.json) on the cloud VM risers-eval:
# v3 (our board best) and v5-touch. The VM runs cloud_job/cloud_eval/vm_run.sh: 4 streams side by side, 2 per image.
# Every 2 min this script copies the episodes to ~/evals (names t8_reliable_v3_pcloud_a1 and so on, so the tracker,
# summarize.py and reliable_report.py read them as parts of the runs reliable_v3 and reliable_touch). At the end it
# DELETES the VM (also on an error, and at the latest 2 h 50 min after the VM was made), writes the reports and copies
# the runs to the SSD. The local units risers-reliable and risers-reliable2 wait for this unit and then run only the
# episodes that the cloud did not finish.
# With RESUME=1 it skips the setup and the start of the VM job (for a job that runs). DONE_FILE is the file that the VM
# job writes at its end (default ALL_DONE; ALL_DONE2 when cloud_eval/vm_more.sh runs the streams that did not fit).
# Run under systemd-run (unit risers-cloudeval). Log: cloud_job/cloud_eval.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
RESUME=${RESUME:-0} DONE_FILE=${DONE_FILE:-ALL_DONE}
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
C=$J/cloud_eval
D=$P/tests_1108
LOG=$J/cloud_eval.log
NB=/home/antonlucy/.nebius/bin/nebius
# eval_vm: the id of the VM and the time it was made (seconds), written when the VM is made; eval_ip: its address.
read -r VM_ID CREATED < "$J/eval_vm"
PRICE=2.28  # $ per hour, gpu-l40s-d 1gpu-32vcpu-192gb
DEADLINE=$((CREATED + 170 * 60))
IP=$(cat "$J/eval_ip")
STAGE=$HOME/evals_cloud  # a copy of ~/evals of the VM
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/local_tests_reliable34"
PY=$HOME/molmobot_src/venv/bin/python
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "ubuntu@$IP")
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
status() { printf '%s\tcloud\t%s\t%s\n' "$1" "$2" "$(date +%s)" >> "$D/status.tsv"; }
cost() { python3 -I -c "import sys; h = (int(sys.argv[1]) - int(sys.argv[2])) / 3600; print(f'{h:.2f} h = \${h * float(sys.argv[3]):.2f}')" "$(date +%s)" "$CREATED" "$PRICE"; }
fetch() { rsync -rt --no-perms --no-owner --no-group "$@"; }

DELETED=false
delete_vm() {
  [ "$DELETED" = true ] && return
  for attempt in 1 2 3 4 5; do
    if "$NB" --profile risers-sa compute instance delete --id "$VM_ID" >> "$LOG" 2>&1; then
      DELETED=true
      say "DELETED risers-eval after $(cost)"
      echo "$(date '+%F %T') DELETED risers-eval (ran $(cost))" >> "$J/ledger.txt"
      break
    fi
    say "delete attempt $attempt failed"
    sleep 60
  done
  "$NB" --profile risers-sa compute instance list --parent-id project-e00q19nppr00ffpv0qkagn >> "$LOG" 2>&1
  "$NB" --profile risers-sa compute disk list --parent-id project-e00q19nppr00ffpv0qkagn >> "$LOG" 2>&1
}
trap delete_vm EXIT
trap 'say "STOP: stopped by a signal"; exit 1' TERM INT

count() { ls "$HOME"/evals/t8_"$1"_pcloud_*/*/*/static.json 2>/dev/null | wc -l; }

# Copy the episodes and logs of the VM home: t8_reliable_v3_a_p1 -> ~/evals/t8_reliable_v3_pcloud_a1 (and .runner.log,
# .server.log), and the new lines of the VM log to this log.
VM_LINES=0
pull() {
  mkdir -p "$STAGE"
  fetch "ubuntu@$IP:evals/" "$STAGE/" 2>> "$LOG" || return 1
  local f base new
  for f in "$STAGE"/t8_reliable_*; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    new=$(echo "$base" | sed -E 's/^t8_reliable_(v3|touch)_([a-d])_p([0-9]+)/t8_reliable_\1_pcloud_\2\3/')
    if [ -d "$f" ]; then fetch "$f/" "$HOME/evals/$new/"; else cp -p "$f" "$HOME/evals/$new"; fi
  done
  fetch "ubuntu@$IP:cloud_eval/vm.log" "$J/cloud_eval_vm.log" 2>/dev/null || return 0
  local n; n=$(wc -l < "$J/cloud_eval_vm.log")
  if [ "$n" -gt "$VM_LINES" ]; then
    sed -n "$((VM_LINES + 1)),${n}p" "$J/cloud_eval_vm.log" | sed -E 's/^(.{19}) /\1 [vm] /' >> "$LOG"
    VM_LINES=$n
  fi
}

if [ "$RESUME" != 1 ]; then
say "START: VM risers-eval made $(date -d "@$CREATED" +%T) (L40S, \$$PRICE/h); wait for ssh, uv and docker on it"
until "${SSH[@]}" 'test -x ~/.local/bin/uv && docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null; do
  [ "$(date +%s)" -lt $((CREATED + 20 * 60)) ] || { say "STOP: the VM is not ready 20 min after it was made"; exit 1; }
  sleep 20
done
say "VM ready: $("${SSH[@]}" 'nproc; free -g | awk "/Mem/ {print \$2\" GB RAM\"}"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader' | tr '\n' ' ')"
"${SSH[@]}" 'mkdir -p ~/positronic ~/cloud_eval ~/evals' || { say "STOP: ssh failed"; exit 1; }
fetch --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .ruff_cache --exclude .pytest_cache \
  "$P/positronic/" "ubuntu@$IP:positronic/" 2>> "$LOG" || { say "STOP: copy of positronic failed"; exit 1; }
fetch "$C/" "ubuntu@$IP:cloud_eval/" 2>> "$LOG" || { say "STOP: copy of the job files failed"; exit 1; }
"${SSH[@]}" 'cd ~/cloud_eval || exit 1; nohup setsid bash vm_run.sh > vm_run.out 2>&1 < /dev/null & exit 0' \
  || { say "STOP: the VM job did not start"; exit 1; }
say "VM job started (setup, image pulls, then 4 streams: v3 a/b, v5-touch a/b, 17 episodes each)"
else
  say "RESUME: the VM job runs; copy its episodes until $DONE_FILE"
fi
status reliable_v3 running
status reliable_touch running

T0='' LAST='' FAILS=0
while :; do
  sleep 120
  if pull; then FAILS=0; else FAILS=$((FAILS + 1)); say "copy from the VM failed ($FAILS in a row)"; fi
  [ "$FAILS" -lt 10 ] || { say "STOP: the VM does not answer"; break; }
  # The VM log has UTC times.
  [ -n "$T0" ] || ! grep -q 'STREAMS:' "$J/cloud_eval_vm.log" 2>/dev/null \
    || T0=$(date -u -d "$(grep -m1 'STREAMS:' "$J/cloud_eval_vm.log" | cut -c1-19)" +%s)
  a=$(count reliable_v3) b=$(count reliable_touch)
  if [ "$a $b" != "$LAST" ] && [ -n "$T0" ] && [ $((a + b)) -gt 0 ]; then
    LAST="$a $b"
    mins=$(( ($(date +%s) - T0) / 60 ))
    end=$(python3 -I -c "import sys, time; done, t0 = int(sys.argv[1]), int(sys.argv[2]); now = time.time()
left = 68 - done; t = now + left * (now - t0) / max(done, 1)
print(time.strftime('%H:%M', time.localtime(t + 300)), f'{(t + 300 - int(sys.argv[3])) / 3600 * float(sys.argv[4]):.2f}')" \
      $((a + b)) "$T0" "$CREATED" "$PRICE")
    say "PROGRESS v3 $a/34, v5-touch $b/34 in $mins min of streams; end about ${end% *}, cost at the end about \$${end#* } (now $(cost))"
  fi
  "${SSH[@]}" "test -f ~/cloud_eval/$DONE_FILE" 2>/dev/null && { pull; say "the VM job ended"; break; }
  [ "$(date +%s)" -lt "$DEADLINE" ] || { pull; say "STOP: 2 h 50 min limit; the VM is deleted with the episodes copied so far"; break; }
done
fetch --exclude "*.json" "ubuntu@$IP:cloud_eval/" "$J/cloud_eval_vm/" 2>> "$LOG" || true
delete_vm

for run in reliable_v3 reliable_touch; do
  n=$(count "$run")
  if [ "$n" -ge 34 ]; then status "$run" done; else status "$run" partial; fi
  say "RESULT $run: $n of 34 episodes from the cloud$([ "$n" -ge 34 ] || echo '; the local unit runs the rest after the grasp tests')"
done
# The reports and the SSD copy, only for a run that has cloud episodes.
for run in reliable_v3 reliable_touch; do
  [ "$(count "$run")" -gt 0 ] || continue
  md=$D/results_${run/reliable_v3/reliable}.md
  "$PY" "$P/competition_runs/board_videos/reliable_report.py" "$run" > "$md" 2>> "$LOG" \
    && say "REPORT $run: $(grep -m1 '^Solved' "$md")"
  mkdir -p "$OUT/$run"
  fetch "$HOME"/evals/t8_${run}_pcloud_* "$OUT/$run/" 2>> "$LOG" && cp "$md" "$OUT/" && say "$run copied to the SSD" \
    || say "copy of $run to the SSD failed"
done
say "DONE"

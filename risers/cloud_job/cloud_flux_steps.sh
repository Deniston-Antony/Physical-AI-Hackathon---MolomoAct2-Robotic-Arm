#!/usr/bin/env bash
# FLUX 3 Action with fewer denoising steps on the cloud VM risers-flux (cloud_flux/vm_flux.sh): the GD model at 4, 2
# and 1 denoising steps, both cameras, hybrid schedule, full gripper, 24 GB cap, 40 episodes each (120 total).
# Every 2 min this script copies the episodes to ~/evals (names t8_conc_<name>_ps<k>_<n>). At the end it DELETES the
# VM (also on an error, and at the latest 3 h after the VM was made), writes tests_1117/results_cloud_flux_steps.md
# and copies the runs to the SSD.
# Run under systemd-run (unit risers-fluxsteps). Log: cloud_job/cloud_flux_steps.log. Cost ledger: cloud_job/ledger.txt.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.nebius/bin
set -uo pipefail
RESUME=${RESUME:-0} DONE_FILE=${DONE_FILE:-ALL_DONE}
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
C=$J/cloud_flux_steps
D=$P/tests_1117
LOG=$J/cloud_flux_steps.log
NB=/home/antonlucy/.nebius/bin/nebius
read -r VM_ID CREATED PRICE < "$J/flux_vm"
TOTAL=120  # 3 runs × 40 episodes
DEADLINE=$((CREATED + 180 * 60))  # 3 h
IP=$(cat "$J/flux_ip")
NAMES=(fluxhyb4 fluxhyb2 fluxhyb1)
STAGE=$HOME/evals_cloud_flux_steps
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/cloud_tests_flux_steps"
STAGE_SRC=$HOME/main_stage/positronic
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
      say "DELETED risers-flux after $(cost)"
      echo "$(date '+%F %T') DELETED risers-flux (ran $(cost))" >> "$J/ledger.txt"
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

count() { ls "$HOME"/evals/t8_"$1"_ps*/*/*/static.json 2>/dev/null | wc -l; }

VM_LINES=0
pull() {
  mkdir -p "$STAGE"
  fetch "ubuntu@$IP:evals/" "$STAGE/" 2>> "$LOG" || return 1
  local f base new
  for f in "$STAGE"/t8_conc_* "$STAGE"/conc_*.server.log; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    new=$(echo "$base" | sed -E 's/^t8_conc_([a-z0-9]+)_s([1-4])_p([0-9]+)/t8_conc_\1_ps\2_\3/')
    if [ -d "$f" ]; then fetch "$f/" "$HOME/evals/$new/"; else cp -p "$f" "$HOME/evals/$new"; fi
  done
  fetch "ubuntu@$IP:cloud_flux/vm.log" "$J/cloud_flux_steps_vm.log" 2>/dev/null || return 0
  fetch "ubuntu@$IP:cloud_flux/gpu.log" "$J/cloud_flux_steps_gpu.log" 2>/dev/null
  local n; n=$(wc -l < "$J/cloud_flux_steps_vm.log")
  if [ "$n" -gt "$VM_LINES" ]; then
    sed -n "$((VM_LINES + 1)),${n}p" "$J/cloud_flux_steps_vm.log" | sed -E 's/^(.{19}) /\1 [vm] /' >> "$LOG"
    VM_LINES=$n
  fi
}

if [ "$RESUME" != 1 ]; then
say "START: VM risers-flux made $(date -d "@$CREATED" +%T) (\$$PRICE/h); wait for ssh, uv and docker on it"
until "${SSH[@]}" 'test -x ~/.local/bin/uv && docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null; do
  [ "$(date +%s)" -lt $((CREATED + 20 * 60)) ] || { say "STOP: the VM is not ready 20 min after it was made"; exit 1; }
  sleep 20
done
say "VM ready: $("${SSH[@]}" 'nproc; free -g | awk "/Mem/ {print \$2\" GB RAM\"}"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader' | tr '\n' ' ')"
"${SSH[@]}" 'mkdir -p ~/positronic ~/cloud_flux ~/evals' || { say "STOP: ssh failed"; exit 1; }
fetch --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .ruff_cache --exclude .pytest_cache \
  "$STAGE_SRC/" "ubuntu@$IP:positronic/" 2>> "$LOG" || { say "STOP: copy of positronic failed"; exit 1; }
fetch "$C/" "ubuntu@$IP:cloud_flux/" 2>> "$LOG" || { say "STOP: copy of the job files failed"; exit 1; }
"${SSH[@]}" 'cd ~/cloud_flux || exit 1; nohup setsid bash vm_flux.sh > vm_flux.out 2>&1 < /dev/null & exit 0' \
  || { say "STOP: the VM job did not start"; exit 1; }
say "VM job started (setup, image pull, then fluxhyb4, fluxhyb2, fluxhyb1, each with 4 streams)"
else
  say "RESUME: the VM job runs; copy its episodes until $DONE_FILE"
fi
mkdir -p "$D"
for name in "${NAMES[@]}"; do status "conc_$name" running; done

T0='' LAST='' FAILS=0
while :; do
  sleep 120
  if pull; then FAILS=0; else FAILS=$((FAILS + 1)); say "copy from the VM failed ($FAILS in a row)"; fi
  [ "$FAILS" -lt 10 ] || { say "STOP: the VM does not answer"; break; }
  [ -n "$T0" ] || ! grep -q 'STREAMS:' "$J/cloud_flux_steps_vm.log" 2>/dev/null \
    || T0=$(date -d "$(grep -m1 'STREAMS:' "$J/cloud_flux_steps_vm.log" | cut -c1-19)" +%s)
  a=$(count "conc_fluxhyb4") b=$(count "conc_fluxhyb2") c=$(count "conc_fluxhyb1")
  if [ "$a $b $c" != "$LAST" ] && [ -n "$T0" ] && [ $((a + b + c)) -gt 0 ]; then
    LAST="$a $b $c"
    mins=$(( ($(date +%s) - T0) / 60 ))
    end=$(python3 -I -c "import sys, time; done, t0 = int(sys.argv[1]), int(sys.argv[2]); now = time.time()
left = int(sys.argv[5]) - done; t = now + left * (now - t0) / max(done, 1)
print(time.strftime('%H:%M', time.localtime(t + 300)), f'{(t + 300 - int(sys.argv[3])) / 3600 * float(sys.argv[4]):.2f}')" \
      $((a + b + c)) "$T0" "$CREATED" "$PRICE" "$TOTAL")
    say "PROGRESS fluxhyb4 $a/40, fluxhyb2 $b/40, fluxhyb1 $c/40 in $mins min of streams; end about ${end% *}, cost ~\$${end#* } (now $(cost))"
  fi
  "${SSH[@]}" "test -f ~/cloud_flux/$DONE_FILE" 2>/dev/null && { pull; say "the VM job ended"; break; }
  [ "$(date +%s)" -lt "$DEADLINE" ] || { pull; say "STOP: 3 h limit; the VM is deleted with the episodes copied so far"; break; }
done
fetch --exclude "*.json" "ubuntu@$IP:cloud_flux/" "$J/cloud_flux_vm_steps/" 2>> "$LOG" || true
delete_vm

for name in "${NAMES[@]}"; do
  run=conc_$name
  n=$(count "$run")
  want=40
  if [ "$n" -ge "$want" ]; then status "$run" done; else status "$run" partial; fi
  say "RESULT $run: $n of $want episodes"
done
mkdir -p "$OUT" "$D"
"$PY" "$C/report.py" > "$D/results_cloud_flux_steps.md" 2>> "$LOG" && say "REPORT: tests_1117/results_cloud_flux_steps.md written"
fetch "$HOME"/evals/t8_conc_fluxhyb* "$HOME"/evals/conc_fluxhyb*.server.log "$D/results_cloud_flux_steps.md" "$J"/cloud_flux_steps_gpu.log "$J"/cloud_flux_steps_vm.log "$OUT/" 2>> "$LOG" \
  && say "copied to the SSD" || say "copy to the SSD failed"
say "DONE"

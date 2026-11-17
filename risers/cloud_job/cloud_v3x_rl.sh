#!/usr/bin/env bash
# The RoboLab test of the new rules of v3 on the cloud VM risers-v3xrl (L40S): the variants of cloud_v3x_rl/images one
# after the other, on the 12 tasks of the platform's robolab.subset_12, 3 at a time (cloud_v3x_rl/vm_robolab.sh). The
# eval client is positronic main, from a snapshot in STAGE_SRC. Every 2 min this script copies the episodes to ~/evals
# (runs rl_<name>_s<k>_p<n>). At the end it DELETES the VM (also on an error, and at the latest 2 h 45 min after the VM
# was made), writes tests_robolab/results_cloud_v3x_rl.md and copies the runs to the SSD.
# Run under systemd-run (unit risers-v3xrl). Log: cloud_job/cloud_v3x_rl.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
C=$J/cloud_v3x_rl
D=$P/tests_robolab
LOG=$J/cloud_v3x_rl.log
NB=/home/antonlucy/.nebius/bin/nebius
# v3xrl_vm: the id of the VM and the time it was made (seconds), written when the VM is made; v3xrl_ip: its address.
read -r VM_ID CREATED < "$J/v3xrl_vm"
PRICE=2.28  # $ per hour, gpu-l40s-d 1gpu-32vcpu-192gb (the gpu-l40s-a price is assumed the same)
TOTAL=$((12 * $(grep -c . "$C/images")))
DEADLINE=$((CREATED + 165 * 60))
IP=$(cat "$J/v3xrl_ip")
STAGE_SRC=$HOME/robolab_stage/positronic
STAGE="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/cloud_stage/evals_cloud_v3x_rl"  # a copy of ~/evals of the VM, on the SSD
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/cloud_tests_robolab_v3x"
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "ubuntu@$IP")
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
cost() { python3 -I -c "import sys; h = (int(sys.argv[1]) - int(sys.argv[2])) / 3600; print(f'{h:.2f} h = \${h * float(sys.argv[3]):.2f}')" "$(date +%s)" "$CREATED" "$PRICE"; }
fetch() { rsync -rt --no-perms --no-owner --no-group "$@"; }
count() { find "$HOME"/evals/rl_rl*_s* -name static.json 2>/dev/null | wc -l; }
mkdir -p "$D"

DELETED=false
delete_vm() {
  [ "$DELETED" = true ] && return
  for attempt in 1 2 3 4 5; do
    if "$NB" --profile risers-sa compute instance delete --id "$VM_ID" >> "$LOG" 2>&1; then
      DELETED=true
      say "DELETED risers-v3xrl after $(cost)"
      echo "$(date '+%F %T') DELETED risers-v3xrl (ran $(cost))" >> "$J/ledger.txt"
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

VM_LINES=0
pull() {  # copy the episodes and logs of the VM home, and the new lines of the VM log to this log
  mkdir -p "$STAGE"
  fetch "ubuntu@$IP:evals/" "$STAGE/" 2>> "$LOG" || return 1
  local f
  for f in "$STAGE"/rl_rl*; do
    [ -e "$f" ] || continue
    if [ -d "$f" ]; then fetch "$f/" "$HOME/evals/$(basename "$f")/"; else cp -p "$f" "$HOME/evals/"; fi
  done
  fetch "ubuntu@$IP:cloud_robolab/vm.log" "$J/cloud_v3x_rl_vm.log" 2>/dev/null || return 0
  fetch "ubuntu@$IP:cloud_robolab/gpu.log" "$J/cloud_v3x_rl_gpu.log" 2>/dev/null
  local n; n=$(wc -l < "$J/cloud_v3x_rl_vm.log")
  if [ "$n" -gt "$VM_LINES" ]; then
    sed -n "$((VM_LINES + 1)),${n}p" "$J/cloud_v3x_rl_vm.log" | sed -E 's/^(.{19}) /\1 [vm] /' >> "$LOG"
    VM_LINES=$n
  fi
}

say "START: VM risers-v3xrl made $(date -d "@$CREATED" +%T) (\$$PRICE/h); wait for ssh, uv and docker on it"
until "${SSH[@]}" 'test -x ~/.local/bin/uv && docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null; do
  [ "$(date +%s)" -lt $((CREATED + 20 * 60)) ] || { say "STOP: the VM is not ready 20 min after it was made"; exit 1; }
  sleep 20
done
say "VM ready: $("${SSH[@]}" 'nproc; free -g | awk "/Mem/ {print \$2\" GB RAM\"}"; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader' | tr '\n' ' ')"
"${SSH[@]}" 'mkdir -p ~/positronic ~/cloud_robolab ~/evals' || { say "STOP: ssh failed"; exit 1; }
fetch --delete "$STAGE_SRC/" "ubuntu@$IP:positronic/" 2>> "$LOG" || { say "STOP: copy of positronic failed"; exit 1; }
fetch "$C/" "ubuntu@$IP:cloud_robolab/" 2>> "$LOG" || { say "STOP: copy of the job files failed"; exit 1; }
"${SSH[@]}" 'cd ~/cloud_robolab || exit 1; nohup setsid bash vm_robolab.sh > vm_robolab.out 2>&1 < /dev/null & exit 0' \
  || { say "STOP: the VM job did not start"; exit 1; }
say "VM job started (system libraries, Isaac Sim install, image pull, server, then 3 streams of 4 tasks)"

T0='' LAST='' FAILS=0
while :; do
  sleep 120
  if pull; then FAILS=0; else FAILS=$((FAILS + 1)); say "copy from the VM failed ($FAILS in a row)"; fi
  [ "$FAILS" -lt 10 ] || { say "STOP: the VM does not answer"; break; }
  # The VM log has Central European Time.
  [ -n "$T0" ] || ! grep -q 'STREAMS:' "$J/cloud_v3x_rl_vm.log" 2>/dev/null \
    || T0=$(date -d "$(grep -m1 'STREAMS:' "$J/cloud_v3x_rl_vm.log" | cut -c1-19)" +%s)
  a=$(count)
  if [ "$a" != "$LAST" ] && [ -n "$T0" ] && [ "$a" -gt 0 ]; then
    LAST=$a
    mins=$(( ($(date +%s) - T0) / 60 ))
    end=$(python3 -I -c "import sys, time; done, t0 = int(sys.argv[1]), int(sys.argv[2]); now = time.time()
left = int(sys.argv[5]) - done; t = now + left * (now - t0) / max(done, 1)
print(time.strftime('%H:%M', time.localtime(t + 300)), f'{(t + 300 - int(sys.argv[3])) / 3600 * float(sys.argv[4]):.2f}')" \
      "$a" "$T0" "$CREATED" "$PRICE" "$TOTAL")
    say "PROGRESS $a/$TOTAL episodes in $mins min of streams; end about ${end% *}, cost at the end about \$${end#* } (now $(cost))"
  fi
  "${SSH[@]}" "test -f ~/cloud_robolab/ALL_DONE" 2>/dev/null && { pull; say "the VM job ended"; break; }
  [ "$(date +%s)" -lt "$DEADLINE" ] || { pull; say "STOP: 2 h 45 min limit; the VM is deleted with the episodes copied so far"; break; }
done
fetch --exclude "*.json" "ubuntu@$IP:cloud_robolab/" "$J/cloud_v3x_rl_vm/" 2>> "$LOG" || true
delete_vm

say "RESULT: $(count) of $TOTAL episodes"
(cd "$P/positronic" && uv run --locked python "$C/report.py") > "$D/results_cloud_v3x_rl.md" 2>> "$LOG" \
  && say "REPORT: tests_robolab/results_cloud_v3x_rl.md written"
mkdir -p "$OUT"
fetch "$HOME"/evals/rl_rl* "$D/results_cloud_v3x_rl.md" "$J"/cloud_v3x_rl_gpu.log "$J"/cloud_v3x_rl_vm.log "$OUT/" 2>> "$LOG" \
  && say "copied to the SSD" || say "copy to the SSD failed"
say "DONE"

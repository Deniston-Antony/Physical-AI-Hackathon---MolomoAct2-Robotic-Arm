#!/usr/bin/env bash
# The test of the gripper check of v3 on the cloud VM risers-peck (13 Nov). Image v3 with 3 flow steps closes the
# gripper on nothing about every 2 s. The servers of cloud_peck/images share the GPU: each is image v3 with the code
# of cloud_peck/code_<name> mounted over the code of the image, and its own flags. Each server gets 4 episodes at a
# time on the 40 episodes of conc40.json (cloud_peck/vm_peck.sh). Every 2 min this script copies the episodes to
# ~/evals (names t8_conc_<name>_ps1_1 and so on, so summarize.py reads them as parts of the run conc_<name>). At the
# end it DELETES the VM (also on an error, and at the latest 2 h 15 min after the VM was made), writes
# tests_1108/results_cloud_peck.md and copies the runs to the SSD.
# With RESUME=1 it skips the setup and the start of the VM job (for a job that runs).
# Run under systemd-run (unit risers-peck). Log: cloud_job/cloud_peck.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
RESUME=${RESUME:-0} DONE_FILE=${DONE_FILE:-ALL_DONE}
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
C=$J/cloud_peck
D=$P/tests_1108
LOG=$J/cloud_peck.log
NB=/home/antonlucy/.nebius/bin/nebius
# peck_vm: the id of the VM, the time it was made (seconds) and its price ($ per hour).
read -r VM_ID CREATED PRICE < "$J/peck_vm"
TOTAL=40  # episodes per server
DEADLINE=$((CREATED + 135 * 60))
# The H100 VM has 16 CPUs: it runs 2 servers. The run of v3 as it is (v3b) is left out there.
[ "$PRICE" != 4.50 ] || sed -i '/^v3b /d' "$C/images"
IP=$(cat "$J/peck_ip")
mapfile -t NAMES < <(awk '{print $1}' "$C/images")
STAGE=$HOME/evals_cloud_peck_$(IFS=_; echo "${NAMES[*]}")  # a copy of ~/evals of the VM
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/cloud_tests_v3_peck"
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
      say "DELETED risers-peck after $(cost)"
      echo "$(date '+%F %T') DELETED risers-peck (ran $(cost))" >> "$J/ledger.txt"
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

# Copy the episodes and logs of the VM home: t8_conc_v6_s1_p1 -> ~/evals/t8_conc_v6_ps1_1 (and .runner.log,
# .timing.txt), the server logs, and the new lines of the VM log to this log.
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
  fetch "ubuntu@$IP:cloud_peck/vm.log" "$J/cloud_peck_vm.log" 2>/dev/null || return 0
  fetch "ubuntu@$IP:cloud_peck/gpu.log" "$J/cloud_peck_gpu.log" 2>/dev/null
  local n; n=$(wc -l < "$J/cloud_peck_vm.log")
  if [ "$n" -gt "$VM_LINES" ]; then
    sed -n "$((VM_LINES + 1)),${n}p" "$J/cloud_peck_vm.log" | sed -E 's/^(.{19}) /\1 [vm] /' >> "$LOG"
    VM_LINES=$n
  fi
}

if [ "$RESUME" != 1 ]; then
say "START: VM risers-peck made $(date -d "@$CREATED" +%T) (\$$PRICE/h); wait for ssh, uv and docker on it"
until "${SSH[@]}" 'test -x ~/.local/bin/uv && docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null; do
  [ "$(date +%s)" -lt $((CREATED + 20 * 60)) ] || { say "STOP: the VM is not ready 20 min after it was made"; exit 1; }
  sleep 20
done
say "VM ready: $("${SSH[@]}" 'nproc; free -g | awk "/Mem/ {print \$2\" GB RAM\"}"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader' | tr '\n' ' ')"
"${SSH[@]}" 'mkdir -p ~/positronic ~/cloud_peck ~/evals' || { say "STOP: ssh failed"; exit 1; }
fetch --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .ruff_cache --exclude .pytest_cache \
  "$P/positronic/" "ubuntu@$IP:positronic/" 2>> "$LOG" || { say "STOP: copy of positronic failed"; exit 1; }
fetch "$C/" "ubuntu@$IP:cloud_peck/" 2>> "$LOG" || { say "STOP: copy of the job files failed"; exit 1; }
"${SSH[@]}" 'cd ~/cloud_peck || exit 1; nohup setsid bash vm_peck.sh > vm_peck.out 2>&1 < /dev/null & exit 0' \
  || { say "STOP: the VM job did not start"; exit 1; }
say "VM job started (setup, image pull, ${#NAMES[@]} servers, then 4 streams of 10 episodes per server)"
else
  say "RESUME: the VM job runs; copy its episodes until $DONE_FILE"
fi
for name in "${NAMES[@]}"; do status "conc_$name" running; done

T0='' LAST='' FAILS=0
while :; do
  sleep 120
  if pull; then FAILS=0; else FAILS=$((FAILS + 1)); say "copy from the VM failed ($FAILS in a row)"; fi
  [ "$FAILS" -lt 10 ] || { say "STOP: the VM does not answer"; break; }
  # The VM log has Central European Time.
  [ -n "$T0" ] || ! grep -q 'STREAMS:' "$J/cloud_peck_vm.log" 2>/dev/null \
    || T0=$(date -d "$(grep -m1 'STREAMS:' "$J/cloud_peck_vm.log" | cut -c1-19)" +%s)
  a=0 b=0 parts=''
  for name in "${NAMES[@]}"; do n=$(count "conc_$name"); a=$((a + n)); parts="$parts $name $n/$TOTAL"; done
  if [ "$parts" != "$LAST" ] && [ -n "$T0" ] && [ "$a" -gt 0 ]; then
    LAST="$parts"
    mins=$(( ($(date +%s) - T0) / 60 ))
    end=$(python3 -I -c "import sys, time; done, t0 = int(sys.argv[1]), int(sys.argv[2]); now = time.time()
left = int(sys.argv[5]) - done; t = now + left * (now - t0) / max(done, 1)
print(time.strftime('%H:%M', time.localtime(t + 300)), f'{(t + 300 - int(sys.argv[3])) / 3600 * float(sys.argv[4]):.2f}')" \
      $((a + b)) "$T0" "$CREATED" "$PRICE" $((TOTAL * ${#NAMES[@]})))
    say "PROGRESS$parts in $mins min of streams; end about ${end% *}, cost at the end about \$${end#* } (now $(cost))"
  fi
  "${SSH[@]}" "test -f ~/cloud_peck/$DONE_FILE" 2>/dev/null && { pull; say "the VM job ended"; break; }
  [ "$(date +%s)" -lt "$DEADLINE" ] || { pull; say "STOP: 2 h 15 min limit; the VM is deleted with the episodes copied so far"; break; }
done
fetch --exclude "*.json" "ubuntu@$IP:cloud_peck/" "$J/cloud_peck_vm/" 2>> "$LOG" || true
delete_vm

for name in "${NAMES[@]}"; do
  run=conc_$name
  n=$(count "$run")
  if [ "$n" -ge "$TOTAL" ]; then status "$run" done; else status "$run" partial; fi
  say "RESULT $run: $n of $TOTAL episodes"
done
"$PY" "$C/report.py" > "$D/results_cloud_peck.md" 2>> "$LOG" && say "REPORT: tests_1108/results_cloud_peck.md written"
mkdir -p "$OUT"
for name in "${NAMES[@]}"; do
  fetch "$HOME"/evals/t8_conc_"$name"_ps* "$HOME/evals/conc_$name.server.log" "$OUT/" 2>> "$LOG" || say "copy of $name to the SSD failed"
done
fetch "$D/results_cloud_peck.md" "$J"/cloud_peck_gpu.log "$OUT/" 2>> "$LOG" && say "copied to the SSD" || say "copy to the SSD failed"
say "DONE"

#!/usr/bin/env bash
# The board-load test of v3 with JPEG camera frames on the cloud VM risers-jpeg (11 Nov, H100: no L40S was free).
# Two servers share the GPU: v3jpeg (image v3 with the MolmoBot code of branch molmobot-v3-jpeg, cloud_jpeg/code_v3jpeg,
# mounted over the code of the image) and v3raw (image v3 as it is, raw frames). Each server gets 4 episodes at a time
# on the 40 episodes of conc40.json (cloud_jpeg/vm_jpeg.sh). Every 2 min this script copies the episodes to ~/evals (names t8_conc_<name>_ps1_1 and so on, so
# summarize.py reads them as parts of the run conc_<name>). At the end it DELETES the VM (also on an error, and at the
# latest 2 h 30 min after the VM was made), writes tests_1108/results_cloud_jpeg.md and copies the runs to the SSD.
# With RESUME=1 it skips the setup and the start of the VM job (for a job that runs).
# Run under systemd-run (unit risers-jpeg). Log: cloud_job/cloud_jpeg.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
RESUME=${RESUME:-0} DONE_FILE=${DONE_FILE:-ALL_DONE}
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
C=$J/cloud_jpeg
D=$P/tests_1108
LOG=$J/cloud_jpeg.log
NB=/home/antonlucy/.nebius/bin/nebius
# jpeg_vm: the id of the VM and the time it was made (seconds), written when the VM is made; jpeg_ip: its address.
read -r VM_ID CREATED < "$J/jpeg_vm"
PRICE=4.50  # $ per hour (assumed from the H100 of 9 Nov)
TOTAL=40  # episodes per server
DEADLINE=$((CREATED + 150 * 60))
IP=$(cat "$J/jpeg_ip")
mapfile -t NAMES < <(awk '{print $1}' "$C/images")
STAGE=$HOME/evals_cloud_jpeg_$(IFS=_; echo "${NAMES[*]}")  # a copy of ~/evals of the VM
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/cloud_tests_v3_jpeg"
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
      say "DELETED risers-jpeg after $(cost)"
      echo "$(date '+%F %T') DELETED risers-jpeg (ran $(cost))" >> "$J/ledger.txt"
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
  fetch "ubuntu@$IP:cloud_jpeg/vm.log" "$J/cloud_jpeg_vm.log" 2>/dev/null || return 0
  fetch "ubuntu@$IP:cloud_jpeg/gpu.log" "$J/cloud_jpeg_gpu.log" 2>/dev/null
  local n; n=$(wc -l < "$J/cloud_jpeg_vm.log")
  if [ "$n" -gt "$VM_LINES" ]; then
    sed -n "$((VM_LINES + 1)),${n}p" "$J/cloud_jpeg_vm.log" | sed -E 's/^(.{19}) /\1 [vm] /' >> "$LOG"
    VM_LINES=$n
  fi
}

if [ "$RESUME" != 1 ]; then
say "START: VM risers-jpeg made $(date -d "@$CREATED" +%T) (\$$PRICE/h); wait for ssh, uv and docker on it"
until "${SSH[@]}" 'test -x ~/.local/bin/uv && docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null; do
  [ "$(date +%s)" -lt $((CREATED + 20 * 60)) ] || { say "STOP: the VM is not ready 20 min after it was made"; exit 1; }
  sleep 20
done
say "VM ready: $("${SSH[@]}" 'nproc; free -g | awk "/Mem/ {print \$2\" GB RAM\"}"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader' | tr '\n' ' ')"
"${SSH[@]}" 'mkdir -p ~/positronic ~/cloud_jpeg ~/evals' || { say "STOP: ssh failed"; exit 1; }
fetch --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .ruff_cache --exclude .pytest_cache \
  "$P/positronic/" "ubuntu@$IP:positronic/" 2>> "$LOG" || { say "STOP: copy of positronic failed"; exit 1; }
fetch "$C/" "ubuntu@$IP:cloud_jpeg/" 2>> "$LOG" || { say "STOP: copy of the job files failed"; exit 1; }
"${SSH[@]}" 'cd ~/cloud_jpeg || exit 1; nohup setsid bash vm_jpeg.sh > vm_jpeg.out 2>&1 < /dev/null & exit 0' \
  || { say "STOP: the VM job did not start"; exit 1; }
say "VM job started (setup, image pull, 2 servers, then 4 streams of 10 episodes per server)"
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
  [ -n "$T0" ] || ! grep -q 'STREAMS:' "$J/cloud_jpeg_vm.log" 2>/dev/null \
    || T0=$(date -d "$(grep -m1 'STREAMS:' "$J/cloud_jpeg_vm.log" | cut -c1-19)" +%s)
  a=$(count "conc_${NAMES[0]}") b=0
  [ "${#NAMES[@]}" -lt 2 ] || b=$(count "conc_${NAMES[1]}")
  if [ "$a $b" != "$LAST" ] && [ -n "$T0" ] && [ $((a + b)) -gt 0 ]; then
    LAST="$a $b"
    mins=$(( ($(date +%s) - T0) / 60 ))
    end=$(python3 -I -c "import sys, time; done, t0 = int(sys.argv[1]), int(sys.argv[2]); now = time.time()
left = int(sys.argv[5]) - done; t = now + left * (now - t0) / max(done, 1)
print(time.strftime('%H:%M', time.localtime(t + 300)), f'{(t + 300 - int(sys.argv[3])) / 3600 * float(sys.argv[4]):.2f}')" \
      $((a + b)) "$T0" "$CREATED" "$PRICE" $((TOTAL * ${#NAMES[@]})))
    say "PROGRESS ${NAMES[0]} $a/$TOTAL${NAMES[1]:+, ${NAMES[1]} $b/$TOTAL} in $mins min of streams; end about ${end% *}, cost at the end about \$${end#* } (now $(cost))"
  fi
  "${SSH[@]}" "test -f ~/cloud_jpeg/$DONE_FILE" 2>/dev/null && { pull; say "the VM job ended"; break; }
  [ "$(date +%s)" -lt "$DEADLINE" ] || { pull; say "STOP: 2 h 30 min limit; the VM is deleted with the episodes copied so far"; break; }
done
fetch --exclude "*.json" "ubuntu@$IP:cloud_jpeg/" "$J/cloud_jpeg_vm/" 2>> "$LOG" || true
delete_vm

for name in "${NAMES[@]}"; do
  run=conc_$name
  n=$(count "$run")
  if [ "$n" -ge "$TOTAL" ]; then status "$run" done; else status "$run" partial; fi
  say "RESULT $run: $n of $TOTAL episodes"
done
"$PY" "$C/report.py" > "$D/results_cloud_jpeg.md" 2>> "$LOG" && say "REPORT: tests_1108/results_cloud_jpeg.md written"
mkdir -p "$OUT"
fetch "$HOME"/evals/t8_conc_v3jpeg* "$HOME"/evals/t8_conc_v3raw* "$HOME"/evals/conc_v3jpeg.server.log "$HOME"/evals/conc_v3raw.server.log "$D/results_cloud_jpeg.md" "$J"/cloud_jpeg_gpu.log "$OUT/" 2>> "$LOG" \
  && say "copied to the SSD" || say "copy to the SSD failed"
say "DONE"

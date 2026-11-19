#!/usr/bin/env bash
# Router image test: make an L40S VM, build + test the router image on it (router_image/vm_router.sh),
# copy the logs back, delete the VM. Hard limit 3 h from the VM's creation. Log: cloud_job/cloud_router.log.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.nebius/bin
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition; J=$P/cloud_job; LOG=$J/cloud_router.log
NB=/home/antonlucy/.nebius/bin/nebius
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
start=$(date +%s)
bash "$J/create_router_vm.sh"
tail -1 "$LOG" | grep -q 'VM running' && [ "$(stat -c %Y "$J/flux_vm")" -ge "$start" ] || { say "STOP: no VM"; exit 1; }
read -r VM_ID CREATED PRICE < "$J/flux_vm"; IP=$(cat "$J/flux_ip"); DEADLINE=$((CREATED + 180 * 60))
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "ubuntu@$IP")
delete() { "$NB" --profile risers-sa compute instance delete --id "$VM_ID" >> "$LOG" 2>&1
  h=$(python3 -c "print(round(($(date +%s)-$CREATED)/3600,2))"); c=$(python3 -c "print(round($h*$PRICE,2))")
  say "DELETED VM after $h h = \$$c"; echo "$(date '+%F %T') DELETED risers-flux $VM_ID after $h h = \$$c (router test)" >> "$J/ledger.txt"; }
fetch() { mkdir -p "$J/cloud_router_vm"; rsync -rt -e "ssh -o BatchMode=yes" "ubuntu@$IP:router/*.log" "$J/cloud_router_vm/" 2>/dev/null
  rsync -rt -e "ssh -o BatchMode=yes" --include='*/' --include='static.json' --include='*.log' --exclude='*' "ubuntu@$IP:evals/" "$J/cloud_router_vm/evals/" 2>/dev/null; }
until "${SSH[@]}" 'test -x ~/.local/bin/uv && docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null; do
  [ "$(date +%s)" -lt $((CREATED + 1200)) ] || { say "STOP: VM not ready in 20 min"; delete; exit 1; }; sleep 20; done
say "VM ready"
"${SSH[@]}" 'mkdir -p ~/positronic ~/router ~/evals'
rsync -rt --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .ruff_cache --exclude .pytest_cache \
  -e "ssh -o BatchMode=yes" "$HOME/main_stage/positronic/" "ubuntu@$IP:positronic/" 2>>"$LOG" \
  && rsync -rt --exclude __pycache__ -e "ssh -o BatchMode=yes" "$P/router_image/" "ubuntu@$IP:router/" 2>>"$LOG" \
  || { say "STOP: copy failed"; delete; exit 1; }
"${SSH[@]}" 'nohup setsid bash ~/router/vm_router.sh > ~/router/vm_router.out 2>&1 < /dev/null & exit 0'
say "VM job started"
seen=0
while :; do
  sleep 120
  n=$("${SSH[@]}" 'wc -l < ~/router/vm.log' 2>/dev/null || echo "$seen")
  [ "$n" -gt "$seen" ] && { "${SSH[@]}" "tail -n +$((seen+1)) ~/router/vm.log" 2>/dev/null | sed 's/^/[vm] /' >> "$LOG"; seen=$n; }
  if "${SSH[@]}" 'test -e ~/router/ALL_DONE' 2>/dev/null; then
    fetch
    a=$(grep '\[A\] served' "$J/cloud_router_vm/vm.log" | tail -1); b=$(grep '\[B\] [0-9]' "$J/cloud_router_vm/vm.log" | tail -1)
    if grep -q 'ALL DONE' "$J/cloud_router_vm/vm.log" && ! echo "$a" | grep -q 'v3 sessions 0' && echo "$a" | grep -q 'flux sessions 0' \
       && echo "$b" | grep -q 'FLUX serves'; then
      "${SSH[@]}" 'sudo shutdown -c; sudo shutdown -P +180 "push window over"' >> "$LOG" 2>&1
      say "PASSED: VM kept for the push until $(date -d '+180 min' +%H:%M); then it powers off (disk cost only)"
      exit 0
    fi
    say "FAILED: see the [A]/[B] lines"; delete; exit 1
  fi
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then fetch; say "STOP: 3 h limit"; delete; exit 1; fi
done

#!/usr/bin/env bash
# Make the cloud VM risers-v3xms (L40S only: the job runs 2 MolmoBot servers with 8 eval processes) for the test of the
# new rules of v3 on the board tasks, then start cloud_v3x_ms.sh (unit risers-v3xms). A platform with no free capacity
# makes the VM STOPPED: this script then deletes it and tries the next preset, every 5 min until UNTIL (default 1 h).
# Run under systemd-run (unit risers-v3xms-create). Log: cloud_job/cloud_v3x_ms.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
J=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/cloud_job
LOG=$J/cloud_v3x_ms.log
NB=/home/antonlucy/.nebius/bin/nebius
PROJECT=project-e00q19nppr00ffpv0qkagn
SUB=vpcsubnet-e00hcve3ffjg2eh6ts
UNTIL=${UNTIL:-$(($(date +%s) + 3600))}
KEY=$(cut -d' ' -f1,2 ~/.ssh/id_ed25519.pub)
UD="#cloud-config
ssh_authorized_keys:
  - \"$KEY\"
runcmd:
  - [usermod, -aG, docker, ubuntu]
  - [su, -l, ubuntu, -c, 'curl -LsSf -o /tmp/uv-install.sh https://astral.sh/uv/install.sh && sh /tmp/uv-install.sh']
  - [shutdown, -P, '+165', 'budget guard: v3 rules test VM powers off after 2 h 45 min']"
# "<platform> <preset> <$ per hour>". The gpu-l40s-a price is assumed equal to gpu-l40s-d.
FIRST=("gpu-l40s-d 1gpu-32vcpu-192gb 2.28" "gpu-l40s-a 1gpu-32vcpu-128gb 2.28")
LATER=("gpu-l40s-d 1gpu-32vcpu-192gb 2.28" "gpu-l40s-a 1gpu-32vcpu-128gb 2.28")
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
nb() { "$NB" --profile risers-sa "$@"; }
state() { nb compute instance get --id "$1" --format json 2>/dev/null | python3 -I -c "import json, sys; print(json.load(sys.stdin)['status'].get('state'))" 2>/dev/null; }

say "CREATE: try L40S, then H100, every 5 min until $(date -d "@$UNTIL" +%T)"
round=0
while [ "$(date +%s)" -lt "$UNTIL" ]; do
  round=$((round + 1))
  if [ "$round" = 1 ]; then opts=("${FIRST[@]}"); else opts=("${LATER[@]}"); fi
  for opt in "${opts[@]}"; do
    set -- $opt
    out=$(nb compute instance create --parent-id "$PROJECT" --name risers-v3xms --labels "job=risers-v3xms" \
      --resources-platform "$1" --resources-preset "$2" \
      --boot-disk-attach-mode read_write --boot-disk-managed-disk-name risers-v3xms-boot \
      --boot-disk-managed-disk-source-image-family-image-family ubuntu24.04-cuda12 \
      --boot-disk-managed-disk-size-gibibytes 200 --boot-disk-managed-disk-type network_ssd \
      --network-interfaces "[{\"name\":\"eth0\",\"subnet_id\":\"$SUB\",\"ip_address\":{},\"public_ip_address\":{}}]" \
      --cloud-init-user-data "$UD" 2>&1 | sed 's/\x1b\[[0-9;]*m//g')
    now=$(date +%s)
    id=$(echo "$out" | grep -m1 -oE 'computeinstance-[a-z0-9]+')
    st=$([ -n "$id" ] && state "$id")
    say "CREATE: $1 $2: ${id:-no id} state ${st:-unknown}"
    if [ "$st" = RUNNING ]; then
      nb compute instance get --id "$id" --format json | python3 -I -c "import json, sys
d = json.load(sys.stdin); print(d['status']['network_interfaces'][0]['public_ip_address']['address'].split('/')[0])" > "$J/v3xms_ip"
      echo "$id $now $3" > "$J/v3xms_vm"
      echo "$(date '+%F %T') CREATED risers-v3xms $id $1 $2 ~\$$3/h (v3 new rules on the board tasks: ctl, all | deep, vote; 2 batches of 2 servers, 40 eps each, 4 at a time; L40S only; poweroff guard +2h45, delete at 2 h 30)" >> "$J/ledger.txt"
      systemd-run --user --unit=risers-v3xms --collect bash "$J/cloud_v3x_ms.sh" >> "$LOG" 2>&1 \
        && say "CREATE: VM running; cloud_v3x_ms.sh started (unit risers-v3xms)" \
        || { say "CREATE: cloud_v3x_ms.sh did not start; delete the VM"; nb compute instance delete --id "$id" >> "$LOG" 2>&1; }
      exit 0
    fi
    [ -z "$id" ] || nb compute instance delete --id "$id" >> "$LOG" 2>&1 || say "CREATE: delete of $id failed"
    sleep 20
  done
  sleep 300
done
say "CREATE: STOP: no capacity until $(date -d "@$UNTIL" +%T)"
nb compute instance list --parent-id "$PROJECT" --format json | python3 -I -c "import json, sys
print('VMs:', [(i['metadata']['name'], i['status']['state']) for i in json.load(sys.stdin).get('items', [])])" >> "$LOG" 2>&1

#!/usr/bin/env bash
# Make the cloud VM risers-jpeg (L40S) for the board-load test of v3 with JPEG frames, then start cloud_jpeg.sh
# (unit risers-jpeg).
# The L40S platforms can have no free capacity: the VM is then made STOPPED, and this script deletes it and tries the
# next preset. It tries all presets every 5 min until UNTIL (seconds since 1970; default: 4 h from the start).
# Run under systemd-run (unit risers-jpeg-create). Log: cloud_job/cloud_jpeg.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
J=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/cloud_job
LOG=$J/cloud_jpeg.log
NB=/home/antonlucy/.nebius/bin/nebius
PROJECT=project-e00q19nppr00ffpv0qkagn
SUB=vpcsubnet-e00hcve3ffjg2eh6ts
UNTIL=${UNTIL:-$(($(date +%s) + 4 * 3600))}
KEY=$(cut -d' ' -f1,2 ~/.ssh/id_ed25519.pub)
UD="#cloud-config
ssh_authorized_keys:
  - \"$KEY\"
runcmd:
  - [usermod, -aG, docker, ubuntu]
  - [su, -l, ubuntu, -c, 'curl -LsSf -o /tmp/uv-install.sh https://astral.sh/uv/install.sh && sh /tmp/uv-install.sh']
  - [shutdown, -P, '+180', 'budget guard: JPEG-test VM powers off after 3 h']"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
nb() { "$NB" --profile risers-sa "$@"; }
state() { nb compute instance get --id "$1" --format json 2>/dev/null | python3 -I -c "import json, sys; print(json.load(sys.stdin)['status'].get('state'))" 2>/dev/null; }

say "CREATE: try the L40S presets every 5 min until $(date -d "@$UNTIL" +%T)"
while [ "$(date +%s)" -lt "$UNTIL" ]; do
  for opt in "gpu-l40s-a 1gpu-32vcpu-128gb" "gpu-l40s-a 1gpu-24vcpu-96gb" "gpu-l40s-a 1gpu-40vcpu-160gb" \
    "gpu-l40s-a 1gpu-16vcpu-64gb" "gpu-l40s-d 1gpu-32vcpu-192gb" "gpu-l40s-d 1gpu-16vcpu-96gb" "gpu-l40s-d 1gpu-48vcpu-288gb"; do
    set -- $opt
    out=$(nb compute instance create --parent-id "$PROJECT" --name risers-jpeg --labels "job=risers-jpeg" \
      --resources-platform "$1" --resources-preset "$2" \
      --boot-disk-attach-mode read_write --boot-disk-managed-disk-name risers-jpeg-boot \
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
d = json.load(sys.stdin); print(d['status']['network_interfaces'][0]['public_ip_address']['address'].split('/')[0])" > "$J/jpeg_ip"
      echo "$id $now" > "$J/jpeg_vm"
      echo "$(date '+%F %T') CREATED risers-jpeg $id $1 $2 (board-load test of v3 + JPEG frames, 40 eps, 4 at a time, alone on the GPU; poweroff guard +3h, delete at 2.5 h)" >> "$J/ledger.txt"
      systemd-run --user --unit=risers-jpeg --collect bash "$J/cloud_jpeg.sh" >> "$LOG" 2>&1 \
        && say "CREATE: VM running; cloud_jpeg.sh started (unit risers-jpeg)" \
        || { say "CREATE: cloud_jpeg.sh did not start; delete the VM"; nb compute instance delete --id "$id" >> "$LOG" 2>&1; }
      exit 0
    fi
    [ -z "$id" ] || nb compute instance delete --id "$id" >> "$LOG" 2>&1 || say "CREATE: delete of $id failed"
    sleep 20
  done
  sleep 300
done
say "CREATE: STOP: no L40S capacity until $(date -d "@$UNTIL" +%T)"
nb compute instance list --parent-id "$PROJECT" --format json | python3 -I -c "import json, sys
print('VMs:', [(i['metadata']['name'], i['status']['state']) for i in json.load(sys.stdin).get('items', [])])" >> "$LOG" 2>&1

#!/usr/bin/env bash
# Make the cloud VM risers-robolab (L40S) for the RoboLab test of the image v3-jpeg, then start cloud_robolab.sh
# (unit risers-robolab). Isaac Sim needs an RTX GPU, so only the L40S platforms are tried (not the H100).
# The L40S platforms can have no free capacity: the VM is then made STOPPED, and this script deletes it and tries the
# next preset. It tries all presets every 5 min until UNTIL (seconds since 1970; default: 1 h from the start).
# Run under systemd-run (unit risers-robolab-create). Log: cloud_job/cloud_robolab.log. Cost ledger: cloud_job/ledger.txt.
set -uo pipefail
J=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/cloud_job
LOG=$J/cloud_robolab.log
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
  - [shutdown, -P, '+200', 'budget guard: RoboLab-test VM powers off after 3 h 20 min']"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
nb() { "$NB" --profile risers-sa "$@"; }
state() { nb compute instance get --id "$1" --format json 2>/dev/null | python3 -I -c "import json, sys; print(json.load(sys.stdin)['status'].get('state'))" 2>/dev/null; }

say "CREATE: try the L40S presets every 5 min until $(date -d "@$UNTIL" +%T)"
while [ "$(date +%s)" -lt "$UNTIL" ]; do
  for opt in "gpu-l40s-d 1gpu-32vcpu-192gb" "gpu-l40s-a 1gpu-32vcpu-128gb" "gpu-l40s-a 1gpu-40vcpu-160gb" \
    "gpu-l40s-d 1gpu-48vcpu-288gb" "gpu-l40s-a 1gpu-24vcpu-96gb" "gpu-l40s-d 1gpu-16vcpu-96gb" "gpu-l40s-a 1gpu-16vcpu-64gb"; do
    set -- $opt
    out=$(nb compute instance create --parent-id "$PROJECT" --name risers-robolab --labels "job=risers-robolab" \
      --resources-platform "$1" --resources-preset "$2" \
      --boot-disk-attach-mode read_write --boot-disk-managed-disk-name risers-robolab-boot \
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
d = json.load(sys.stdin); print(d['status']['network_interfaces'][0]['public_ip_address']['address'].split('/')[0])" > "$J/robolab_ip"
      echo "$id $now" > "$J/robolab_vm"
      echo "$(date '+%F %T') CREATED risers-robolab $id $1 $2 (RoboLab test of v3-jpeg: 12 tasks, 3 at a time; poweroff guard +3h20, delete at 3 h)" >> "$J/ledger.txt"
      systemd-run --user --unit=risers-robolab --collect bash "$J/cloud_robolab.sh" >> "$LOG" 2>&1 \
        && say "CREATE: VM running; cloud_robolab.sh started (unit risers-robolab)" \
        || { say "CREATE: cloud_robolab.sh did not start; delete the VM"; nb compute instance delete --id "$id" >> "$LOG" 2>&1; }
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

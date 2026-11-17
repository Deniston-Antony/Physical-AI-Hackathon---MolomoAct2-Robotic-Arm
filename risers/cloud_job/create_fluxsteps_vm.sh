#!/usr/bin/env bash
# Make the cloud VM risers-flux for the FLUX step-count test, then start cloud_flux_steps.sh (unit risers-fluxsteps).
# FLUX needs about 33 GB of GPU memory; the test fits it in 24 GB. The VM tries L40S (48 GB, cheaper) then H100.
# A platform with no free capacity makes the VM STOPPED: this script then deletes it and tries the next preset.
# It tries every 5 min until UNTIL (seconds since 1970; default: 1 h from the start).
# Run under systemd-run (unit risers-fluxsteps-create). Log: cloud_job/cloud_flux_steps.log. Cost ledger: cloud_job/ledger.txt.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.nebius/bin
set -uo pipefail
J=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/cloud_job
LOG=$J/cloud_flux_steps.log
NB=/home/antonlucy/.nebius/bin/nebius
PROJECT=project-e00q19nppr00ffpv0qkagn
SUB=vpcsubnet-e00hcve3ffjg2eh6ts
UNTIL=${UNTIL:-$(date -d "2026-11-17 20:00:00" +%s)}
KEY=$(cut -d' ' -f1,2 ~/.ssh/id_ed25519.pub)
UD="#cloud-config
ssh_authorized_keys:
  - \"$KEY\"
runcmd:
  - [usermod, -aG, docker, ubuntu]
  - [su, -l, ubuntu, -c, 'curl -LsSf -o /tmp/uv-install.sh https://astral.sh/uv/install.sh && sh /tmp/uv-install.sh']
  - [shutdown, -P, '+200', 'budget guard: FLUX step test VM powers off after 3 h 20 min']"
# 3 runs of 40 episodes: ~2.5-3 h. Guard at 3h20.
FIRST=("gpu-l40s-d 1gpu-32vcpu-192gb 2.28" "gpu-l40s-a 1gpu-32vcpu-128gb 2.28" "gpu-h100-sxm 1gpu-16vcpu-200gb 4.50")
LATER=("gpu-l40s-d 1gpu-32vcpu-192gb 2.28" "gpu-l40s-a 1gpu-32vcpu-128gb 2.28" "gpu-h100-sxm 1gpu-16vcpu-200gb 4.50")
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
    out=$(nb compute instance create --parent-id "$PROJECT" --name risers-flux --labels "job=risers-flux" \
      --resources-platform "$1" --resources-preset "$2" \
      --boot-disk-attach-mode read_write --boot-disk-managed-disk-name risers-flux-boot \
      --boot-disk-managed-disk-source-image-family-image-family ubuntu24.04-cuda12 \
      --boot-disk-managed-disk-size-gibibytes 200 --boot-disk-managed-disk-type network_ssd \
      --network-interfaces "[{\"name\":\"eth0\",\"subnet_id\":\"$SUB\",\"ip_address\":{},\"public_ip_address\":{}}]" \
      --cloud-init-user-data "$UD" 2>&1 | sed 's/\x1b\[[0-9;]*m//g')
    now=$(date +%s)
    id=$(echo "$out" | grep -m1 -oE 'computeinstance-[a-z0-9]+')
    st=$([ -n "$id" ] && state "$id")
    say "CREATE: $1 $2: ${id:-no id} state ${st:-unknown}"
    [ -n "$id" ] || say "CREATE: error: $(echo "$out" | grep -m1 -E 'Error|error' | cut -c1-200)"
    if [ "$st" = RUNNING ]; then
      nb compute instance get --id "$id" --format json | python3 -I -c "import json, sys
d = json.load(sys.stdin); print(d['status']['network_interfaces'][0]['public_ip_address']['address'].split('/')[0])" > "$J/flux_ip"
      echo "$id $now $3" > "$J/flux_vm"
      echo "$(date '+%F %T') CREATED risers-flux $id $1 $2 ~\$$3/h (FLUX 3 Action step test: GD model at 4, 2 and 1 denoising steps; both cameras, hybrid schedule, full grip, 24 GB cap, 40 eps each, 4 at a time; poweroff guard +3h20, delete at 3 h)" >> "$J/ledger.txt"
      systemd-run --user --unit=risers-fluxsteps --collect bash "$J/cloud_flux_steps.sh" >> "$LOG" 2>&1 \
        && say "CREATE: VM running; cloud_flux_steps.sh started (unit risers-fluxsteps)" \
        || { say "CREATE: cloud_flux_steps.sh did not start; delete the VM"; nb compute instance delete --id "$id" >> "$LOG" 2>&1; }
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

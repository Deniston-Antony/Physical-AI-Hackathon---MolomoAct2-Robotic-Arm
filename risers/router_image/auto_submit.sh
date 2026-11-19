#!/usr/bin/env bash
# Wait until denistonantony/flux3-retry-droid:v1 is on Docker Hub, check it is the retry policy, then submit it
# to the ranked stage-2 eval once (fixed transaction key, so a retry never counts twice). Log: router_image/submit.log
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
L=$P/router_image/submit.log; IMG=docker.io/denistonantony/policy-router; KEY=risers-router-v3
say() { echo "$(date '+%F %T') $*" >> "$L"; }
say "WATCH: waiting for $IMG:v3 on Docker Hub (every 5 min, up to 3 days)"
end=$(( $(date +%s) + 3 * 86400 ))
while [ "$(date +%s)" -lt "$end" ]; do
  dg=$(sg docker -c "docker buildx imagetools inspect $IMG:v3 --format '{{json .Manifest.Digest}}'" 2>/dev/null | tr -d '"')
  if [ -n "$dg" ]; then
    ep=$(sg docker -c "docker buildx imagetools inspect $IMG@$dg --format '{{json .Image.Config.Entrypoint}}'" 2>/dev/null)
    echo "$ep" | grep -q '/router/front.py' || { say "STOP: $dg has an unexpected start command"; exit 1; }
    say "FOUND: $IMG@$dg; submit with key $KEY"
    # The push is complete (the manifest goes up last): the build VM is no longer needed.
    read -r VM_ID _ < "$P/cloud_job/flux_vm"
    /home/antonlucy/.nebius/bin/nebius --profile risers-sa compute instance delete --id "$VM_ID" >/dev/null 2>&1 \
      && { say "VM $VM_ID deleted"; echo "$(date '+%F %T') DELETED risers-flux $VM_ID (router image pushed)" >> "$P/cloud_job/ledger.txt"; }
    for i in $(seq 48); do
      out=$(cd "$P/positronic" && ~/.local/bin/positronic eval run --policy-image="$IMG@$dg" --transaction-key="$KEY" 2>&1)
      echo "$out" | grep -vE 'https?://' | tail -5 >> "$L"
      echo "$out" | grep -q quota_exceeded || { say "SUBMIT: done (see lines above)"; exit 0; }
      say "SUBMIT: daily quota used; retry in 1 h"; sleep 3600
    done
    exit 1
  fi
  sleep 300
done
say "STOP: image never appeared"

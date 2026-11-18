#!/usr/bin/env bash
# Wait until denistonantony/flux3-retry-droid:v1 is on Docker Hub, check it is the retry policy, then submit it
# to the ranked stage-2 eval once (fixed transaction key, so a retry never counts twice). Log: flux_submit/submit.log
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
L=$P/flux_submit/submit.log; IMG=docker.io/denistonantony/flux3-retry-droid; KEY=risers-flux3-retry-1step-v1
say() { echo "$(date '+%F %T') $*" >> "$L"; }
say "WATCH: waiting for $IMG:v1 on Docker Hub (every 5 min, up to 3 days)"
end=$(( $(date +%s) + 3 * 86400 ))
while [ "$(date +%s)" -lt "$end" ]; do
  dg=$(sg docker -c "docker buildx imagetools inspect $IMG:v1 --format '{{json .Manifest.Digest}}'" 2>/dev/null | tr -d '"')
  if [ -n "$dg" ]; then
    ep=$(sg docker -c "docker buildx imagetools inspect $IMG@$dg --format '{{json .Image.Config.Entrypoint}}'" 2>/dev/null)
    echo "$ep" | grep -q 'flux3_v3rules.server droid_retry_1step' || { say "STOP: $dg has an unexpected start command"; exit 1; }
    say "FOUND: $IMG@$dg; submit with key $KEY"
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

#!/usr/bin/env bash
# Build and push one image per checkpoint, tagged step<N>. Before the last checkpoint, wait for the
# tmux session `train` to end. Run `docker login` first.
# Usage on the VM: bash build_all.sh docker.io/denistonantony/gr00t-risers
set -uo pipefail
repo="$1"
for step in 2000 4000 6000 8000 10000; do
  if [ "$step" = 10000 ]; then
    while tmux has-session -t train 2>/dev/null; do sleep 30; done
  fi
  start=$SECONDS
  echo "=== step $step: start $(date -u +%T)"
  if nice -n 10 bash ~/build_image.sh "$step" "$repo:step$step"; then
    compressed=$(docker buildx imagetools inspect --raw "$repo:step$step" | python3 -c \
      'import json,sys; m=json.load(sys.stdin); print(round((sum(l["size"] for l in m["layers"]) + m["config"]["size"]) / 1e9, 1))')
    unpacked=$(docker image inspect -f '{{.Size}}' "$repo:step$step" 2>/dev/null | awk '{printf "%.1f", $1 / 1e9}')
    echo "=== step $step: pushed in $((SECONDS - start)) s, compressed $compressed GB (limit 50), unpacked ${unpacked:-?} GB (limit 55)"
  else
    echo "=== step $step: FAILED after $((SECONDS - start)) s"
  fi
  df -h / | tail -1
done
echo "=== all done $(date -u +%T)"

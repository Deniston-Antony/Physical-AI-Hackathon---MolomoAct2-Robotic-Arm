#!/usr/bin/env bash
# FLUX 3 Action with fewer denoising steps (the GD model at 2 steps and 1 step, default is 4), in the 24 GB GPU
# memory of a competition run. Both exterior views, hybrid schedule (stop-and-think for pick, continuous for others),
# full gripper command. Each run has 4 eval processes at a time on the 40 episodes of s1-s4.json:
#   fluxhyb4   4 steps (baseline, same as the best previous test)
#   fluxhyb2   2 steps
#   fluxhyb1   1 step
# Log: ~/cloud_flux/vm.log (Central European Time). GPU every 2 s: ~/cloud_flux/gpu.log.
# It writes ~/cloud_flux/ALL_DONE at the end, also when it stops on an error.
set -uo pipefail
D=$HOME/cloud_flux
export TZ=Europe/Berlin PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed
export MLSPACES_ASSETS_DIR=$HOME/molmospaces/assets MLSPACES_CACHE_DIR=$HOME/molmospaces/cache
CACHE=$HOME/molmospaces/cache/objects/objaverse/20260131
ASSET_URL=https://pub-3555e9bb2d304fab9c6c79819e48aa40.r2.dev/objects/objaverse/20260131
IMAGE=docker.io/denistonantony/policy-router@sha256:e41b06dd8e2c8cc86a3ea2bf69451415a8a9f42f28b0571d16c30ee973b9386f
PORT=8001
CODE=/positronic/positronic/vendors/flux3_v3rules
say() { echo "$(date '+%F %T') $*" >> "$D/vm.log"; }
stop() { say "STOP: $*"; touch "$D/ALL_DONE"; exit 1; }

remaining() {
  python3 -I - "$1" "$2" "$D/skip_$2.txt" <<'PY'
import glob, json, os, sys
eps = json.load(open(sys.argv[1]))
keys = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')
done = set()
for f in glob.glob(os.path.expanduser(f'~/evals/t8_{sys.argv[2]}_p*/*/*/static.json')):
    s = json.load(open(f))
    done.add('/'.join(str(s[k]) for k in keys))
skip = set(open(sys.argv[3]).read().split()) if os.path.exists(sys.argv[3]) else set()
print(json.dumps([e for e in eps if e['path'] not in done and e['path'] not in skip]))
PY
}

fix_assets() {
  [ -d "$CACHE" ] || return 0  # only after the simulator made it (an empty one breaks its cache check)
  for h in $(grep -ohE "objaverse_[0-9a-f]{32}\.tar\.zst|objects/objaverse/[0-9a-f]{32}/" "$1" 2>/dev/null | grep -oE "[0-9a-f]{32}" | sort -u); do
    tmp=$(mktemp -d)
    if curl -sf --max-time 300 -o "$tmp/p.tar.zst" "$ASSET_URL/objaverse_$h.tar.zst" \
      && [ "$(tar --zstd -tf "$tmp/p.tar.zst" | grep -cvE "^$h/[^/]+$")" = 0 ]; then
      tar --zstd -xf "$tmp/p.tar.zst" -C "$CACHE" --no-same-owner && say "fixed object $h"
    fi
    rm -rf "$tmp"
  done
}

server() {  # the router image as the platform runs it: its own start command, port 8000 inside
  local name=$1
  docker rm -f "srv-$name" > /dev/null 2>&1
  docker run -d --name "srv-$name" --gpus all --cpus=14 -p "$PORT:8000" "$IMAGE" > /dev/null || return 1
  local t0; t0=$(date +%s)
  for _ in $(seq 360); do
    if curl -sf -X POST "http://localhost:$PORT/api/v1/keepalive" > /dev/null; then
      say "[$name] router ready after $(( $(date +%s) - t0 )) s"; return 0; fi
    sleep 5
  done
  docker logs --tail 40 "srv-$name" >> "$D/vm.log" 2>&1; return 1
}

stream() {
  local run=$1 set=$2 part=0 rem n first
  declare -A tries=()
  while :; do
    rem=$(remaining "$set" "$run")
    n=$(python3 -I -c 'import json, sys; print(len(json.loads(sys.argv[1])))' "$rem")
    [ "$n" = 0 ] && break
    first=$(python3 -I -c 'import json, sys; print(json.loads(sys.argv[1])[0]["path"])' "$rem")
    tries[$first]=$(( ${tries[$first]:-0} + 1 ))
    if [ "${tries[$first]}" -gt 3 ]; then
      echo "$first" >> "$D/skip_$run.txt"
      say "[$run] SKIP $first: it did not finish in 3 tries"
      continue
    fi
    part=$((part + 1))
    while [ -e "$HOME/evals/t8_${run}_p$part" ]; do part=$((part + 1)); done
    (cd "$HOME/positronic" && uv run --locked positronic eval run --eval=.sim.molmo.benchmarks \
      "--eval.episode_paths=$(python3 -I -c 'import json, sys; print(json.dumps([e["path"] for e in json.loads(sys.argv[1])]))' "$rem")" \
      --policy=.remote --policy.address.host=localhost "--policy.address.port=$PORT" \
      --output_dir="$HOME/evals/t8_${run}_p$part") > "$HOME/evals/t8_${run}_p$part.runner.log" 2>&1
    local rc=$?
    fix_assets "$HOME/evals/t8_${run}_p$part.runner.log"
    [ "$rc" = 0 ] || say "[$run] part $part stopped with code $rc ($n episodes were left); it continues"
    sleep 10
  done
}

streams() {
  local name=$1 pids=() k
  say "[$name] STREAMS: 4 eval processes start, 20 s apart"
  for k in 1 2 3 4; do
    stream "conc_${name}_s$k" "$D/s$k.json" &
    pids+=($!)
    sleep 20
  done
  wait "${pids[@]}"
  docker logs "srv-$name" > "$HOME/evals/conc_$name.server.log" 2>&1
  docker rm -f "srv-$name" > /dev/null 2>&1
  say "[$name] DONE: $(ls "$HOME"/evals/t8_conc_"${name}"_s*_p*/*/*/static.json 2>/dev/null | wc -l) episodes," \
    "$(grep -c -E 'OutOfMemoryError|out of memory' "$HOME/evals/conc_$name.server.log") out-of-memory lines in the server log"
  grep -E '\\[router\\]' "$HOME/evals/conc_$name.server.log" | sed "s/^/[$name] /" >> "$D/vm.log"
}

finish() {
  for d in "$HOME"/evals/t8_conc_*_p*/; do
    [ -e "${d%/}.timing.txt" ] || (cd "$HOME/positronic" && uv run --locked positronic eval timing-report --run_dir="$d") \
      > "${d%/}.timing.txt" 2>&1
  done
  kill "$gpu_watch" 2>/dev/null
  say "ALL DONE: $(ls "$HOME"/evals/t8_conc_*_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
  touch "$D/ALL_DONE"
}

mkdir -p "$HOME/evals"
say "SETUP: uv sync, simulator environment, image pull (25 GB)"
docker pull -q "$IMAGE" > "$D/pull.log" 2>&1 &
pull=$!
# pyzed (ZED camera driver, unused in the simulator) downloads from a server that sometimes times out.
(cd "$HOME/positronic" && { UV_PYTHON=3.13 uv sync --locked || UV_PYTHON=3.13 uv sync --locked \
  || { echo "uv sync without pyzed" && UV_PYTHON=3.13 uv sync --locked --no-install-package pyzed; }; }) \
  >> "$D/setup.log" 2>&1 || stop "uv sync failed (setup.log)"
(cd "$HOME/positronic" && uv run --locked python -c \
  'from positronic.simulator.molmo_spaces.launcher import ensure_molmo_venv; ensure_molmo_venv()') >> "$D/setup.log" 2>&1 \
  || stop "the simulator environment failed (setup.log)"
wait "$pull" || stop "the image pull failed (pull.log)"
say "SETUP: done; disk $(df -h --output=used,avail / | tail -1 | tr -s ' ')"
say "ROUTER 40: the pushed router image on the 40 test episodes"
(while :; do
  echo "$(date +%T) $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)" \
    "| $(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader | tr '\n' ';')" >> "$D/gpu.log"
  sleep 2
done) &
gpu_watch=$!

if server router40; then streams router40; else say "[router40] STOP: the router did not start"; fi
docker logs srv-router40 2>/dev/null | grep '\[router\]' >> "$D/vm.log"
finish

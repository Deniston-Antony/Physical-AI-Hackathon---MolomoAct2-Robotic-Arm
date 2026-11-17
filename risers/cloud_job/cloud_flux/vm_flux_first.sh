#!/usr/bin/env bash
# The job of the cloud VM risers-flux: FLUX 3 Action DROID (the public image positro/flux3-action) on the 40 episodes
# of conc40.json, with board load (4 eval processes at a time on one server, streams s1..s4 of 10 episodes each):
#   fluxa   the image as it is published (`droid`);
#   fluxv3  the image with the rules of v3 (`droid_v3` of code_flux3v3, mounted beside the FLUX code);
#   fluxfit the published `droid` with the text encoder kept on the CPU (`droid_fit`), on 4 episodes, to measure
#           the GPU memory against the 24 GB of a competition run.
# Each server has the GPU alone, one after the other. The eval client is positronic main (~/positronic).
# Log: ~/cloud_flux/vm.log (Central European Time). GPU every 2 s: ~/cloud_flux/gpu.log.
# It writes ~/cloud_flux/ALL_DONE at the end, also when it stops on an error.
set -uo pipefail
D=$HOME/cloud_flux
export TZ=Europe/Berlin PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed
export MLSPACES_ASSETS_DIR=$HOME/molmospaces/assets MLSPACES_CACHE_DIR=$HOME/molmospaces/cache
CACHE=$HOME/molmospaces/cache/objects/objaverse/20260131
ASSET_URL=https://pub-3555e9bb2d304fab9c6c79819e48aa40.r2.dev/objects/objaverse/20260131
IMAGE=docker.io/positro/flux3-action@$(cat "$D/flux_digest")
PORT=8001
CODE=/positronic/positronic/vendors/flux3_v3rules
say() { echo "$(date '+%F %T') $*" >> "$D/vm.log"; }
stop() { say "STOP: $*"; touch "$D/ALL_DONE"; exit 1; }

remaining() {  # the episodes of a set file that a run has not finished, as JSON
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
  mkdir -p "$CACHE"
  for h in $(grep -ohE "objaverse_[0-9a-f]{32}\.tar\.zst|objects/objaverse/[0-9a-f]{32}/" "$1" 2>/dev/null | grep -oE "[0-9a-f]{32}" | sort -u); do
    tmp=$(mktemp -d)
    if curl -sf --max-time 300 -o "$tmp/p.tar.zst" "$ASSET_URL/objaverse_$h.tar.zst" \
      && [ "$(tar --zstd -tf "$tmp/p.tar.zst" | grep -cvE "^$h/[^/]+$")" = 0 ]; then
      tar --zstd -xf "$tmp/p.tar.zst" -C "$CACHE" --no-same-owner && say "fixed object $h"
    fi
    rm -rf "$tmp"
  done
}

server() {  # start the FLUX server <name> with a command of code_flux3v3 (or none: the published one); wait for it
  local name=$1 command=$2
  docker rm -f "srv-$name" > /dev/null 2>&1
  if [ -z "$command" ]; then
    docker run -d --name "srv-$name" --gpus all -p "$PORT:8000" "$IMAGE" > /dev/null || return 1
  else
    docker run -d --name "srv-$name" --gpus all -p "$PORT:8000" -v "$D/code_flux3v3:$CODE:ro" --entrypoint /bin/sh \
      "$IMAGE" -c "exec /positronic/.venv/bin/python -m positronic.vendors.flux3_v3rules.server $command \
      $3.flux_python=/opt/flux-action/.venv/bin/python $3.checkpoint=\"\$FLUX_POLICY_REPO\" \
      $3.revision=\"\$FLUX_POLICY_REVISION\" $3.subfolder=\"\$FLUX_POLICY_SUBFOLDER\"" > /dev/null || return 1
  fi
  local t0; t0=$(date +%s)
  for _ in $(seq 180); do
    if curl -sf -X POST "http://localhost:$PORT/api/v1/keepalive" > /dev/null; then
      say "[$name] server ready after $(( $(date +%s) - t0 )) s, GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) used"
      return 0
    fi
    [ -n "$(docker ps -q -f name="srv-$name")" ] || break
    sleep 5
  done
  docker logs --tail 40 "srv-$name" >> "$D/vm.log" 2>&1
  return 1
}

stream() {  # one eval process at a time for a set file against the server; a stopped part continues
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

run() {  # a server and 4 streams over the set files <prefix>1..4.json; the episodes go to runs conc_<name>_s<k>
  local name=$1 prefix=$2 command=$3 flag=$4
  say "[$name] START: server ${command:-of the image}"
  server "$name" "$command" "$flag" || { say "[$name] STOP: the server did not start"; return 1; }
  docker exec "srv-$name" sh -c "ls $CODE 2>/dev/null | tr '\n' ' '" >> "$D/vm.log" 2>&1 && echo >> "$D/vm.log"
  say "[$name] STREAMS: 4 eval processes start, 20 s apart"
  local pids=() k
  for k in 1 2 3 4; do
    stream "conc_${name}_s$k" "$D/$prefix$k.json" &
    pids+=($!)
    sleep 20
  done
  wait "${pids[@]}"
  docker logs "srv-$name" > "$HOME/evals/conc_$name.server.log" 2>&1
  docker rm -f "srv-$name" > /dev/null 2>&1
  say "[$name] DONE: $(ls "$HOME"/evals/t8_conc_"${name}"_s*_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
}

mkdir -p "$HOME/evals"
say "SETUP: uv sync, simulator environment, image pull (25 GB)"
docker pull -q "$IMAGE" > "$D/pull.log" 2>&1 &
pull=$!
(cd "$HOME/positronic" && UV_PYTHON=3.13 uv sync --locked) >> "$D/setup.log" 2>&1 || stop "uv sync failed (setup.log)"
(cd "$HOME/positronic" && uv run --locked python -c \
  'from positronic.simulator.molmo_spaces.launcher import ensure_molmo_venv; ensure_molmo_venv()') >> "$D/setup.log" 2>&1 \
  || stop "the simulator environment failed (setup.log)"
wait "$pull" || stop "the image pull failed (pull.log)"
say "SETUP: done; disk $(df -h --output=used,avail / | tail -1 | tr -s ' ')"
(while :; do
  echo "$(date +%T) $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)" >> "$D/gpu.log"
  sleep 2
done) &
gpu_watch=$!

run fluxa s '' ''
run fluxv3 s droid_v3 --model.model
say "[fluxfit] GPU log from here: line $(($(wc -l < "$D/gpu.log") + 1))"
run fluxfit fit droid_fit --model
grep -h 'FIT:' "$HOME/evals/conc_fluxfit.server.log" >> "$D/vm.log" 2>/dev/null

for d in "$HOME"/evals/t8_conc_*_p*/; do
  (cd "$HOME/positronic" && uv run --locked positronic eval timing-report --run_dir="$d") > "${d%/}.timing.txt" 2>&1
done
kill "$gpu_watch" 2>/dev/null
say "ALL DONE: $(ls "$HOME"/evals/t8_conc_*_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
touch "$D/ALL_DONE"

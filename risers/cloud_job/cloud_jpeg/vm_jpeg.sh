#!/usr/bin/env bash
# The job of the cloud VM risers-jpeg: the board-load test of v3 with JPEG camera frames, on the 40 episodes of
# conc40.json. Each policy server (one line "<name> <digest> [server flags]" of ~/cloud_jpeg/images, ports 8001 and
# up) gets 4 eval processes at a time (streams s1..s4, 10 episodes each), as the board runs about 4 episodes on one
# server. When ~/cloud_jpeg/code_<name> exists, its MolmoBot code is mounted over the code of the image. Server flags
# replace the flags of the image. So a code change needs no new public image.
# Log: ~/cloud_jpeg/vm.log (Central European Time). GPU memory every 30 s: ~/cloud_jpeg/gpu.log.
# It writes ~/cloud_jpeg/ALL_DONE at the end, also when it stops on an error.
set -uo pipefail
D=$HOME/cloud_jpeg
export TZ=Europe/Berlin PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed
export MLSPACES_ASSETS_DIR=$HOME/molmospaces/assets MLSPACES_CACHE_DIR=$HOME/molmospaces/cache
CACHE=$HOME/molmospaces/cache/objects/objaverse/20260131
ASSET_URL=https://pub-3555e9bb2d304fab9c6c79819e48aa40.r2.dev/objects/objaverse/20260131
REPO=docker.io/denistonantony/molmobot-img-droid
mapfile -t NAMES < <(awk '{print $1}' "$D/images")
mapfile -t DIGESTS < <(awk '{print $2}' "$D/images")
mapfile -t FLAGS < <(awk '{$1 = $2 = ""; sub(/^ +/, ""); print}' "$D/images")
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

server() {  # start the policy server of an image at a port, with its code folder and flags, and wait until it answers
  docker rm -f "srv-$1" >/dev/null 2>&1
  local extra=()
  [ ! -d "$D/code_$1" ] || extra+=(-v "$D/code_$1:/positronic/positronic/vendors/molmobot:ro")
  [ -z "$4" ] || extra+=(-e "MOLMOBOT_ARGS=$4")
  docker run -d --name "srv-$1" --gpus all -p "$2:8000" "${extra[@]}" "$3" >/dev/null || return 1
  for _ in $(seq 120); do
    curl -sf -X POST "http://localhost:$2/api/v1/keepalive" >/dev/null && return 0
    [ -n "$(docker ps -q -f name="srv-$1")" ] || break
    sleep 5
  done
  docker logs --tail 30 "srv-$1" >> "$D/vm.log" 2>&1
  return 1
}

stream() {  # one eval process at a time for a set file against a running server; a stopped part continues
  local run=$1 set=$2 port=$3 part=0 rem n first
  declare -A tries=()
  say "[$run] START on port $port"
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
      --policy=.remote --policy.address.host=localhost "--policy.address.port=$port" \
      --output_dir="$HOME/evals/t8_${run}_p$part") > "$HOME/evals/t8_${run}_p$part.runner.log" 2>&1
    local rc=$?
    fix_assets "$HOME/evals/t8_${run}_p$part.runner.log"
    [ "$rc" = 0 ] || say "[$run] part $part stopped with code $rc ($n episodes were left); it continues"
    sleep 10
  done
  say "[$run] STREAM DONE: $(ls "$HOME"/evals/t8_${run}_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
}

mkdir -p "$HOME/evals"
say "SETUP: uv sync, simulator environment, image pulls"
(cd "$HOME/positronic" && UV_PYTHON=3.13 uv sync --locked) >> "$D/setup.log" 2>&1 || stop "uv sync failed (setup.log)"
(cd "$HOME/positronic" && uv run --locked python -c \
  'from positronic.simulator.molmo_spaces.launcher import ensure_molmo_venv; ensure_molmo_venv()') >> "$D/setup.log" 2>&1 \
  || stop "the simulator environment failed (setup.log)"
for i in "${!NAMES[@]}"; do
  docker pull -q "$REPO@${DIGESTS[$i]}" >> "$D/setup.log" 2>&1 || stop "pull of ${NAMES[$i]} failed (setup.log)"
done
(while :; do echo "$(date +%T) $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)" >> "$D/gpu.log"; sleep 30; done) &
gpu_watch=$!
for i in "${!NAMES[@]}"; do
  server "${NAMES[$i]}" $((8001 + i)) "$REPO@${DIGESTS[$i]}" "${FLAGS[$i]}" || stop "the ${NAMES[$i]} server did not start"
  say "SETUP: ${NAMES[$i]} server ready (flags: ${FLAGS[$i]:-of the image}), GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) used"
  docker exec "srv-${NAMES[$i]}" sh -c 'echo "flags: $MOLMOBOT_ARGS"; echo "compress_images lines in server.py: $(grep -c compress_images /positronic/positronic/vendors/molmobot/server.py)"' >> "$D/vm.log" 2>&1
done

say "STREAMS: 4 eval processes per server start, 20 s apart"
pids=()
for k in 1 2 3 4; do
  for i in "${!NAMES[@]}"; do
    stream "conc_${NAMES[$i]}_s$k" "$D/s$k.json" $((8001 + i)) &
    pids+=($!)
    sleep 20
  done
done
wait "${pids[@]}"
for name in "${NAMES[@]}"; do docker logs "srv-$name" > "$HOME/evals/conc_$name.server.log" 2>&1; done
for d in "$HOME"/evals/t8_conc_*_p*/; do
  (cd "$HOME/positronic" && uv run --locked positronic eval timing-report --run_dir="$d") > "${d%/}.timing.txt" 2>&1
done
kill "$gpu_watch" 2>/dev/null
say "ALL DONE: $(ls "$HOME"/evals/t8_conc_*_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
touch "$D/ALL_DONE"

#!/usr/bin/env bash
# One test stream on the cloud VM: a policy IMAGE on a list of episodes, with its own policy server port.
# Usage: bash run_stream.sh <run> <episode set json> <image> <port>
# Made from tests_1108/run_image.sh. A run goes to ~/evals/t8_<run>_p<part>. A part that stops early continues with
# the other episodes in a new part. An episode that stops a part 3 times is skipped.
set -uo pipefail
D=$HOME/cloud_eval
CACHE=$HOME/molmospaces/cache/objects/objaverse/20260131
ASSET_URL=https://pub-3555e9bb2d304fab9c6c79819e48aa40.r2.dev/objects/objaverse/20260131
export PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed MLSPACES_ASSETS_DIR=$HOME/molmospaces/assets MLSPACES_CACHE_DIR=$HOME/molmospaces/cache
RUN=$1 SET=$2 IMAGE=$3 PORT=$4 NAME=risers-policy-$4
declare -A TRIES=()

log() { echo "$(date '+%F %T') [$RUN] $*" >> "$D/vm.log"; }

remaining() {
  python3 -I - "$SET" "$RUN" "$D/skip_$RUN.txt" <<'PY'
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
      tar --zstd -xf "$tmp/p.tar.zst" -C "$CACHE" --no-same-owner && log "fixed object $h"
    else
      log "could not fix object $h"
    fi
    rm -rf "$tmp"
  done
}

run_part() {  # start the image, run the episodes of one part against it, stop the image
  local name=$1 episodes=$2 paths ready=false
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker run -d --name "$NAME" --gpus all -p "$PORT:8000" "$IMAGE" >/dev/null || return 1
  for _ in $(seq 120); do
    if curl -sf -X POST "http://localhost:$PORT/api/v1/keepalive" >/dev/null; then ready=true; break; fi
    [ -n "$(docker ps -q -f name="$NAME")" ] || break
    sleep 5
  done
  if [ "$ready" != true ]; then docker logs --tail 40 "$NAME"; docker rm -f "$NAME" >/dev/null 2>&1; return 1; fi
  paths=$(python3 -I -c 'import json, sys; print(json.dumps([e["path"] for e in json.load(open(sys.argv[1]))]))' "$episodes")
  (cd "$HOME/positronic" && uv run --locked positronic eval run --eval=.sim.molmo.benchmarks "--eval.episode_paths=$paths" \
    --policy=.remote --policy.address.host=localhost "--policy.address.port=$PORT" --output_dir="$HOME/evals/$name")
  local rc=$?
  docker logs "$NAME" > "$HOME/evals/$name.server.log" 2>&1
  docker rm -f "$NAME" >/dev/null 2>&1
  return $rc
}

mkdir -p "$HOME/evals"
log "START on port $PORT"
part=0
while :; do
  rem=$(remaining)
  n=$(python3 -I -c 'import json, sys; print(len(json.loads(sys.argv[1])))' "$rem")
  [ "$n" = 0 ] && break
  first=$(python3 -I -c 'import json, sys; print(json.loads(sys.argv[1])[0]["path"])' "$rem")
  TRIES[$first]=$(( ${TRIES[$first]:-0} + 1 ))
  if [ "${TRIES[$first]}" -gt 3 ]; then
    echo "$first" >> "$D/skip_$RUN.txt"
    log "SKIP $first: it did not finish in 3 tries"
    continue
  fi
  part=$((part + 1))
  while [ -e "$HOME/evals/t8_${RUN}_p$part" ]; do part=$((part + 1)); done
  echo "$rem" > "$D/${RUN}_p$part.json"
  run_part "t8_${RUN}_p$part" "$D/${RUN}_p$part.json" > "$HOME/evals/t8_${RUN}_p$part.runner.log" 2>&1
  rc=$?
  fix_assets "$HOME/evals/t8_${RUN}_p$part.runner.log"
  [ "$rc" = 0 ] || log "part $part stopped with code $rc ($n episodes were left); it continues"
  sleep 10
done
log "STREAM DONE: $(ls "$HOME"/evals/t8_${RUN}_p*/*/*/static.json 2>/dev/null | wc -l) episodes"

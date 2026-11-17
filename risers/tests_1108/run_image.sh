#!/usr/bin/env bash
# One local test run of a policy IMAGE (close tasks). Usage: bash run_image.sh <run> <episode set json> <image>
# The image runs as the platform runs it (its own entrypoint and flags), on this PC's GPU, at localhost:8000.
# A run goes to ~/evals/t8_<run>_p<part>. A run that stops early continues with its other episodes in a new part.
set -uo pipefail
project=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
D=$project/tests_1108
PY=$HOME/molmobot_src/venv/bin/python
CACHE=$HOME/molmospaces/cache/objects/objaverse/20260131
ASSET_URL=https://pub-3555e9bb2d304fab9c6c79819e48aa40.r2.dev/objects/objaverse/20260131
export CHECKPOINT_DIR=$HOME/molmobot_src/MolmoBot-Img-DROID SERVER_COMMAND=droid_half_overlap
export PATH=$HOME/.local/bin:$PATH
RUN=$1 SET=$2 IMAGE=$3 ARGS="image $3"
declare -A TRIES=()

log() { echo "$(date '+%F %H:%M') $*" >> "$D/tests.log"; }
status() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$(date +%s)" >> "$D/status.tsv"; }

remaining() {
  python3 -I - "$SET" "$1" "$D/skip_$1.txt" <<'PY'
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
  docker rm -f risers-policy >/dev/null 2>&1 || true
  docker run -d --name risers-policy --gpus all -p 8000:8000 "$IMAGE" >/dev/null || return 1
  for _ in $(seq 120); do
    if curl -sf -X POST http://localhost:8000/api/v1/keepalive >/dev/null; then ready=true; break; fi
    [ -n "$(docker ps -q -f name=risers-policy)" ] || break
    sleep 5
  done
  if [ "$ready" != true ]; then docker logs --tail 40 risers-policy; docker rm -f risers-policy >/dev/null 2>&1; return 1; fi
  paths=$(python3 -I -c 'import json, sys; print(json.dumps([e["path"] for e in json.load(open(sys.argv[1]))]))' "$episodes")
  (cd "$project/positronic" && MLSPACES_ASSETS_DIR=~/molmospaces/assets MLSPACES_CACHE_DIR=~/molmospaces/cache \
    "$HOME/.local/bin/uv" run --locked positronic eval run --eval=.sim.molmo.benchmarks "--eval.episode_paths=$paths" \
    --policy=.remote --policy.address.host=localhost --policy.address.port=8000 --output_dir="$HOME/evals/$name")
  local rc=$?
  docker logs risers-policy > "$HOME/evals/$name.server.log" 2>&1
  docker rm -f risers-policy >/dev/null 2>&1
  return $rc
}

run_one() {
  local run=$1 step=$2 args=$3 part=0 rem n first rc key
  if grep -qP "^$run\t$step\tdone\t" "$D/status.tsv" 2>/dev/null; then return; fi
  status "$run" "$step" running
  log "START $run: $args"
  while :; do
    rem=$(remaining "$run")
    n=$(python3 -I -c 'import json, sys; print(len(json.loads(sys.argv[1])))' "$rem")
    [ "$n" = 0 ] && break
    first=$(python3 -I -c 'import json, sys; print(json.loads(sys.argv[1])[0]["path"])' "$rem")
    key="$run|$first"
    TRIES[$key]=$(( ${TRIES[$key]:-0} + 1 ))
    if [ "${TRIES[$key]}" -gt 3 ]; then
      echo "$first" >> "$D/skip_$run.txt"
      log "SKIP $run: $first did not finish in 3 tries"
      continue
    fi
    part=$((part + 1))
    while [ -e "$HOME/evals/t8_${run}_p$part" ]; do part=$((part + 1)); done
    echo "$rem" > "$D/${run}_p$part.json"
    run_part "t8_${run}_p$part" "$D/${run}_p$part.json" > "$HOME/evals/t8_${run}_p$part.runner.log" 2>&1
    rc=$?
    fix_assets "$HOME/evals/t8_${run}_p$part.runner.log"
    [ "$rc" = 0 ] || log "$run part $part stopped with code $rc ($n episodes were left); it continues"
    sleep 15
  done
  status "$run" "$step" done
  log "DONE $run: $("$PY" "$D/summarize.py" --line "$run" 2>> "$D/tests.log")"
}

run_one "$RUN" 1 "$ARGS"
log "RUN DONE $RUN"

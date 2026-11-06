#!/usr/bin/env bash
# Overnight local tests of MolmoBot-Img on eval_local/hard28.json (16 hard pick + 12 hard pick-and-place episodes).
# Step 1: speed settings, 2 x 2: play 8 or 12 actions per chunk, 10 or 5 flow steps.
# Step 2: the gripper rule (grip_release_below=40) on the best step-1 setting.
# A run goes to ~/evals/ovn_<run>_p<part>. A run that stops early continues with its other episodes in a new part.
set -uo pipefail
project=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
D=$project/overnight
SET=$project/eval_local/hard28.json
PY=$HOME/molmobot_src/venv/bin/python
CACHE=$HOME/molmospaces/cache/objects/objaverse/20260131
ASSET_URL=https://pub-3555e9bb2d304fab9c6c79819e48aa40.r2.dev/objects/objaverse/20260131
export CHECKPOINT_DIR=$HOME/molmobot_src/MolmoBot-Img-DROID SERVER_COMMAND=droid_half_overlap
declare -A ARGS=(
  [base]="--model.camera=left"
  [play12]="--model.camera=left --pipeline.horizon_sec=0.7667"
  [flow5]="--model.camera=left --model.num_flow_steps=5"
  [play12_flow5]="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=5"
)
declare -A TRIES=()

log() { echo "$(date '+%F %H:%M') $*" >> "$D/overnight.log"; }
status() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$(date +%s)" >> "$D/status.tsv"; }

remaining() {
  python3 -I - "$SET" "$1" "$D/skip_$1.txt" <<'PY'
import glob, json, os, sys
eps = json.load(open(sys.argv[1]))
keys = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')
done = set()
for f in glob.glob(os.path.expanduser(f'~/evals/ovn_{sys.argv[2]}_p*/*/*/static.json')):
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
    while [ -e "$HOME/evals/ovn_${run}_p$part" ]; do part=$((part + 1)); done
    echo "$rem" > "$D/${run}_p$part.json"
    SERVER_ARGS="$args" bash "$project/eval_local/run_local_eval_molmobot.sh" "ovn_${run}_p$part" "$D/${run}_p$part.json" \
      > "$HOME/evals/ovn_${run}_p$part.runner.log" 2>&1
    rc=$?
    fix_assets "$HOME/evals/ovn_${run}_p$part.runner.log"
    [ "$rc" = 0 ] || log "$run part $part stopped with code $rc ($n episodes were left); it continues"
    sleep 15
  done
  status "$run" "$step" done
  "$PY" "$D/summarize.py" > /dev/null 2>> "$D/overnight.log"
  log "DONE $run: $("$PY" "$D/summarize.py" --line "$run" 2>> "$D/overnight.log")"
}

log "STEP 1 START (speed settings)"
for run in base play12 flow5 play12_flow5; do run_one "$run" 1 "${ARGS[$run]}"; done
best=$("$PY" "$D/summarize.py" --best)
log "STEP 1 DONE. Best setting: $best"
log "STEP 2 START (gripper rule on $best)"
echo "$best" > "$D/step2_base.txt"
run_one grip40 2 "${ARGS[$best]} --model.grip_release_below=40"
log "STEP 2 DONE"
log "ALL RUNS DONE"

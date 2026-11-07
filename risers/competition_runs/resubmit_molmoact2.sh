#!/usr/bin/env bash
# Resubmit the MolmoAct2 v2 image, one run at a time, until a run scores more than 30%.
# Stops after the 4 extra submissions of 2 November (UTC), when a run scores more than 30%, or on a refusal.
# Each try has its own transaction key. A restart sends the same key again, and the platform returns the
# submission of that key without counting it again, so a restart resumes the running try.
# Run from the positronic repo. The log is competition_runs/resubmit_molmoact2.log.
set -uo pipefail
IMAGE=docker.io/denistonantony/molmoact2-droid@sha256:f3efb1a7ffc9e6d1d0df2663a8bf4c057b9dd6efafe1a84a12151542bcf26376
TARGET=0.30
LAST_DAY=2026-11-02
MAX_TRIES=4
hide() { grep -viE "api[_ -]?key|token|secret|password"; }
say() { echo "$(date -u '+%F %T UTC') $*"; }

submit() {  # print the submission id of try $1, or nothing
  local key="risers-molmoact2-v2-retry-20261102-$1" out id
  for attempt in 1 2 3; do
    out=$(timeout 300 uv run --locked positronic eval run --policy-image="$IMAGE" --transaction-key="$key" 2>&1 | hide)
    id=$(echo "$out" | grep -oE 'submission [0-9a-f]{16}' | head -1 | awk '{print $2}')
    if [ -n "$id" ]; then echo "$id"; return; fi
    if echo "$out" | grep -qiE "quota_exceeded|transaction_conflict"; then
      say "try $1: refused: $(echo "$out" | grep -iE 'quota|conflict' | head -1)" >&2
      return
    fi
    say "try $1: submit attempt $attempt gave no id: $(echo "$out" | tail -2 | tr '\n' ' ')" >&2
    sleep 60
  done
}

for try in $(seq 1 "$MAX_TRIES"); do
  if [ "$(date -u +%F)" != "$LAST_DAY" ]; then
    say "stop: it is no longer $LAST_DAY UTC, so the extra submissions are over"
    exit 0
  fi
  id=$(submit "$try")
  if [ -z "$id" ]; then
    say "stop: try $try was not accepted"
    exit 1
  fi
  say "try $try: submission $id"
  while true; do
    sleep 300
    status=$(timeout 120 uv run --locked positronic eval status --id="$id" 2>&1 | hide)
    state=$(echo "$status" | grep -oE "^submission $id [a-z_]+" | awk '{print $3}')
    case "$state" in
      running|pending) continue ;;
      finished|errored|failed|cancelled|canceled|rejected|expired) break ;;
      *) say "try $try: unclear status, checking again: $(echo "$status" | head -2 | tr '\n' ' ' | cut -c1-200)" ;;
    esac
  done
  score=$(echo "$status" | grep -oE "'primary': [0-9.]+" | awk '{print $2}')
  say "try $try: $id $state, score ${score:-none}"
  if [ -n "$score" ] && python3 -c "import sys; sys.exit(0 if float('$score') > $TARGET else 1)"; then
    say "done: $score is more than $TARGET"
    exit 0
  fi
done
say "stop: $MAX_TRIES tries used, none scored more than $TARGET"

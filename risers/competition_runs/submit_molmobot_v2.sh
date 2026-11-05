#!/usr/bin/env bash
# Submit the MolmoBot-DROID v2 image (half-overlap timing) once, on 6 November (UTC), with today's daily submission.
# A systemd timer starts it at 00:05 UTC. The transaction key makes a retry return the same submission without
# counting again. Run from the positronic repo. The log is competition_runs/submit_molmobot_v2.log.
set -uo pipefail
IMAGE=docker.io/denistonantony/molmobot-droid@sha256:c60d02a34c020b3f8cb2fed1baef467605d42b6776e859c04de1faa383e9c92e
KEY=risers-molmobot-droid-v2-half-overlap
DAY=2026-11-06
hide() { grep -viE "api[_ -]?key|token|secret|password"; }
say() { echo "$(date -u '+%F %T UTC') $*"; }

for attempt in $(seq 1 12); do
  if [ "$(date -u +%F)" != "$DAY" ]; then
    say "stop: it is not $DAY UTC"
    exit 1
  fi
  out=$(timeout 300 "$HOME/.local/bin/uv" run --locked positronic eval run --policy-image="$IMAGE" --transaction-key="$KEY" 2>&1 | hide)
  id=$(echo "$out" | grep -oE 'submission [0-9a-f]{16}' | head -1 | awk '{print $2}')
  if [ -n "$id" ]; then
    say "submitted: $id"
    echo "$out" | head -4
    exit 0
  fi
  if echo "$out" | grep -qiE "transaction_conflict"; then
    say "stop: refused: $(echo "$out" | grep -iE 'conflict' | head -1)"
    exit 1
  fi
  say "attempt $attempt gave no submission id: $(echo "$out" | tail -2 | tr '\n' ' ' | cut -c1-300)"
  sleep 300
done
say "stop: 12 attempts gave no submission id"
exit 1

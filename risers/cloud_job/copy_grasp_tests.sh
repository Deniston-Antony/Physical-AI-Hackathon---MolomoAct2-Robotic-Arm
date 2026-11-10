#!/usr/bin/env bash
# Copy the recordings of grasp tests 2 and 3 (runs op_flow10 and op_touch) to the SSD after the unit risers-grasptests
# ends. Run under systemd-run (unit risers-copytests). Log: cloud_job/grasp_tests.log.
set -uo pipefail
J=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/cloud_job
LOG=$J/grasp_tests.log
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/molmobot_openclose_2026-11-09/local_tests_with_rules"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }

while systemctl --user is-active -q risers-grasptests; do sleep 120; done
for pair in "op_flow10 grasp_flow10" "op_touch grasp_touch"; do
  set -- $pair
  if ! ls -d "$HOME"/evals/t8_$1_p* >/dev/null 2>&1; then
    say "no results of $1 to copy"
    continue
  fi
  mkdir -p "$OUT/$2"
  rsync -rt --no-perms --no-owner --no-group "$HOME"/evals/t8_$1_p* "$OUT/$2/" 2>> "$LOG" \
    && say "results of $1 copied to the SSD ($2)" || say "copy of $1 to the SSD failed"
done

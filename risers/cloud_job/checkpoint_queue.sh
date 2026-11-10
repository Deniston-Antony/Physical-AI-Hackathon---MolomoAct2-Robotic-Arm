#!/usr/bin/env bash
# Local test of the saved open/close action experts, one after the other (step 1000 was tested before). The user
# stopped the queue after step 2400 on 9 Nov: steps 2000, 1400 and 800 are not tested; their experts stay on the SSD.
# Each model runs the same 30 open episodes (tests_1108/open30.json) with the rules of the earlier
# models: the v4 flags plus the open pull. For each model: build an image from the expert on the SSD, run the 30
# episodes, and copy the results to the SSD. The images stay on this PC; cloud_job/save_images.sh (unit risers-imgsave)
# saves them to the SSD.
# A restart continues where the queue stopped. Run under systemd-run (unit risers-ckqueue).
# Log: cloud_job/checkpoint_queue.log. Table: tests_1108/results_checkpoints.md (also on the SSD).
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
D=$P/tests_1108
J=$P/cloud_job
LOG=$J/checkpoint_queue.log
SSD="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/molmobot_openclose_2026-11-09"
OUT=$SSD/local_tests_with_rules
REPO=denistonantony/molmobot-img-droid
STEPS="2400"
RULES="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.close_push_after=6 --model.camera_fallback=True --model.open_pull=True"
FLAGS="$RULES --model.open_close_expert=/opt/molmobot/action_expert_open_close.pt"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }

mkdir -p "$OUT"
say "QUEUE START: steps $STEPS, 30 open episodes each, rules: $RULES"
for step in $STEPS; do
  run=op_step$step
  expert=$SSD/experts/step$step.pt
  if grep -qP "^$run\t1\tdone\t" "$D/status.tsv" 2>/dev/null; then
    say "step $step was tested before; next"
    continue
  fi
  [ -s "$expert" ] || { say "STOP: $expert is missing (is the SSD mounted?)"; exit 1; }
  tag=$REPO:v5-step$step
  say "BUILD $tag"
  if ! bash "$P/molmobot_image/build_open_close.sh" "$tag" "$expert" "$FLAGS" >> "$LOG" 2>&1; then
    say "build of step $step failed; next"
    continue
  fi
  say "TEST step $step: 30 open episodes"
  bash "$D/run_image.sh" "$run" "$D/open30.json" "$tag"
  line=$("$HOME/molmobot_src/venv/bin/python" "$D/summarize.py" --line "$run" 2>> "$LOG")
  say "DONE step $step: $line"
  mkdir -p "$OUT/step$step"
  rsync -rt --no-perms --no-owner --no-group "$HOME"/evals/t8_${run}_p* "$OUT/step$step/" 2>> "$LOG" \
    && say "results of step $step copied to the SSD" || say "copy of step $step to the SSD failed"
  "$HOME/molmobot_src/venv/bin/python" -I "$J/checkpoint_table.py" > "$D/results_checkpoints.md" 2>> "$LOG" \
    && cp "$D/results_checkpoints.md" "$OUT/" 2>> "$LOG"
done
say "QUEUE DONE"

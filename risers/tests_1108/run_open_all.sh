#!/usr/bin/env bash
# The open-task test matrix on the 30 board open episodes (open30.json), with the image v4 settings:
# op_both2 (reword + pull, runs first in its own unit), then op_base (no open change), op_word (reword only),
# op_pull (pull only). Each run takes about 2.2 h on this PC. Results: summarize.py -> results_open.md.
set -uo pipefail
D=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/tests_1108
V4="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.close_push_after=6 --model.camera_fallback=True"
while systemctl --user is-active -q risers-open-both2; do sleep 60; done
bash "$D/run_one.sh" op_base "$D/open30.json" "$V4"
bash "$D/run_one.sh" op_word "$D/open30.json" "$V4 --model.open_as_pick=True"
bash "$D/run_one.sh" op_pull "$D/open30.json" "$V4 --model.open_pull=True"
~/molmobot_src/venv/bin/python -I "$D/summarize.py" 2>> "$D/tests.log"
echo "$(date '+%F %H:%M') OPEN MATRIX DONE" >> "$D/tests.log"

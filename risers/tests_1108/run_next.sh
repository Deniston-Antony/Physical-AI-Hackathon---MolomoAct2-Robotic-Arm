#!/usr/bin/env bash
# After the baseline (risers-close-base): the close push alone, then the camera fallback alone.
D=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/tests_1108
while systemctl --user is-active -q risers-close-base; do sleep 60; done
bash $D/run_one.sh cl_push $D/close15.json "--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.close_push_after=6"
bash $D/run_one.sh cl_cam $D/close17.json "--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.camera_fallback=True"
echo "$(date '+%F %H:%M') ALL 8 NOV RUNS DONE" >> $D/tests.log

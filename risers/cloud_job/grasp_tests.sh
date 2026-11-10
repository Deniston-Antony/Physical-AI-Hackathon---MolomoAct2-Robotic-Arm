#!/usr/bin/env bash
# Grasp tests 2 and 3 (user, 9 Nov), after the regrasp test and the checkpoint queue: the 30 open episodes
# (tests_1108/open30.json) with the final expert and
#   test 2, run op_flow10: v5 rules + 10 flow steps for open and close tasks (image v5-flow10)
#   test 3, run op_touch:  v5 rules + touch grasp, no regrasp retries (image v5-touch, rebuilt 9 Nov 19:24)
# Then the image saver runs once more to save both images to the SSD. Run under systemd-run (unit risers-grasptests).
# Log: cloud_job/grasp_tests.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
D=$P/tests_1108
LOG=$J/grasp_tests.log
REPO=denistonantony/molmobot-img-droid
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
active() { systemctl --user is-active -q "$1"; }

run_test() {  # run, image
  local run=$1 image=$2 ready=false
  say "START TEST of $image: the server must answer"
  docker rm -f risers-policy >/dev/null 2>&1
  docker run -d --name risers-policy --gpus all -p 8000:8000 "$image" >/dev/null
  for _ in $(seq 120); do
    if curl -sf -X POST http://localhost:8000/api/v1/keepalive >/dev/null; then ready=true; break; fi
    [ -n "$(docker ps -q -f name=risers-policy)" ] || break
    sleep 5
  done
  docker logs risers-policy > "$J/${run}_start_test.log" 2>&1
  docker rm -f risers-policy >/dev/null 2>&1
  if [ "$ready" != true ]; then
    say "the server of $image did not start (log cloud_job/${run}_start_test.log); no test $run"
    return
  fi
  say "TEST $run: 30 open episodes"
  bash "$D/run_image.sh" "$run" "$D/open30.json" "$image"
  local line regrasps touches pulls
  line=$("$HOME/molmobot_src/venv/bin/python" "$D/summarize.py" --line "$run" 2>> "$LOG")
  regrasps=$(cat "$HOME"/evals/t8_${run}_p*.server.log 2>/dev/null | grep -c "open regrasp starts")
  touches=$(cat "$HOME"/evals/t8_${run}_p*.server.log 2>/dev/null | grep -c "open touch grasp starts")
  pulls=$(cat "$HOME"/evals/t8_${run}_p*.server.log 2>/dev/null | grep -c "open pull starts")
  say "DONE $line; touch grasps $touches, regrasps $regrasps, pulls $pulls"
}

say "WAIT for the end of the regrasp test and the checkpoint queue"
# The regrasp test starts the queue again before it ends, so both units are inactive only after the queue.
until ! active risers-regrasp && ! active risers-ckqueue; do sleep 60; done
grep -q "QUEUE DONE" "$J/checkpoint_queue.log" && say "the queue is done" || say "WARNING: the queue stopped without QUEUE DONE"
for _ in $(seq 30); do active risers-imgsave || break; sleep 30; done
systemctl --user stop risers-imgsave 2>/dev/null
say "the grasp tests start"
run_test op_flow10 "$REPO:v5-flow10"
run_test op_touch "$REPO:v5-touch"
systemctl --user reset-failed risers-imgsave 2>/dev/null
systemd-run --user --unit risers-imgsave /usr/bin/sg docker -c "bash $J/save_images.sh" >> "$LOG" 2>&1 \
  && say "the image saver started to save v5-flow10 and v5-touch" || say "ERROR: the image saver did not start"
say "ALL GRASP TESTS DONE"

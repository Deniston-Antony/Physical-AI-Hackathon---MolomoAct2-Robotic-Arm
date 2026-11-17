#!/usr/bin/env bash
# Test of the open regrasp rule (user, 9 Nov): pause the checkpoint queue when step 2400 is done, run the 30 open
# episodes (tests_1108/open30.json) with image v5-regrasp (v5 rules + open regrasp, final expert), then start the queue
# and the image saver again. Run under systemd-run (unit risers-regrasp). Log: cloud_job/regrasp_test.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
D=$P/tests_1108
LOG=$J/regrasp_test.log
QLOG=$J/checkpoint_queue.log
REPO=denistonantony/molmobot-img-droid
IMG=$REPO:v5-regrasp
RUN=op_regrasp
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }

resume() {
  systemctl --user reset-failed risers-ckqueue risers-imgsave 2>/dev/null
  systemd-run --user --unit risers-ckqueue /usr/bin/sg docker -c "bash $J/checkpoint_queue.sh" >> "$LOG" 2>&1 \
    && say "queue started again" || say "ERROR: the queue did not start"
  sleep 5
  systemd-run --user --unit risers-imgsave /usr/bin/sg docker -c "bash $J/save_images.sh" >> "$LOG" 2>&1 \
    && say "image saver started again" || say "ERROR: the image saver did not start"
}

say "WAIT for the end of step 2400 (the queue starts to build step 2200)"
until grep -q "BUILD $REPO:v5-step2200" "$QLOG" 2>/dev/null; do
  if ! systemctl --user is-active -q risers-ckqueue; then say "the queue is not running; the test starts now"; break; fi
  sleep 5
done
systemctl --user stop risers-imgsave
systemctl --user stop risers-ckqueue
say "PAUSED the queue and the image saver"
docker rm -f risers-policy >/dev/null 2>&1
if ! docker image inspect "$REPO:v5-step2400" >/dev/null 2>&1; then
  docker tag "localhost:5000/molmobot-img-droid:v5-step2400" "$REPO:v5-step2400" && say "tag v5-step2400 is back on this PC"
fi

say "START TEST of $IMG: the server must answer"
docker run -d --name risers-policy --gpus all -p 8000:8000 "$IMG" >/dev/null
ready=false
for _ in $(seq 120); do
  if curl -sf -X POST http://localhost:8000/api/v1/keepalive >/dev/null; then ready=true; break; fi
  [ -n "$(docker ps -q -f name=risers-policy)" ] || break
  sleep 5
done
docker logs risers-policy > "$J/regrasp_start_test.log" 2>&1
docker rm -f risers-policy >/dev/null 2>&1
if [ "$ready" != true ]; then
  say "STOP: the server of $IMG did not start (log cloud_job/regrasp_start_test.log); no test"
  resume
  exit 1
fi
say "the server answers; TEST $RUN: 30 open episodes"

bash "$D/run_image.sh" "$RUN" "$D/open30.json" "$IMG"
line=$("$HOME/molmobot_src/venv/bin/python" "$D/summarize.py" --line "$RUN" 2>> "$LOG")
regrasps=$(cat "$HOME"/evals/t8_${RUN}_p*.server.log 2>/dev/null | grep -c "open regrasp starts")
pulls=$(cat "$HOME"/evals/t8_${RUN}_p*.server.log 2>/dev/null | grep -c "open pull starts")
say "DONE $line; regrasps $regrasps, pulls $pulls (the final expert without the regrasp: board 1/30)"
resume

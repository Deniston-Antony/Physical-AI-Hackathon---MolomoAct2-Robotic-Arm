#!/usr/bin/env bash
# Test image v4's settings (v3 + close push + camera fallback) on the 17 local episodes. If 6 or more of the 15 hard
# close episodes succeed (baseline 4), push image v4, run the platform start test and submit it. A refusal for the
# daily limit waits for the next UTC day. Log: tests_1108/v4_submit.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
D=$P/tests_1108
LOG=$D/v4_submit.log
V4="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.close_push_after=6 --model.camera_fallback=True"
TAG=docker.io/denistonantony/molmobot-img-droid:v4
KEY=risers-molmobot-img-v4-push-camera
NEED=6
say() { echo "$(date -u '+%F %T UTC') $*" >> "$LOG"; }
hide() { grep -viE "api[_ -]?key|token|secret|password|X-Amz|https://"; }

say "START combined test"
bash "$D/run_one.sh" cl_both "$D/close17.json" "$V4"
line=$("$HOME/molmobot_src/venv/bin/python" -I "$D/summarize.py" --line cl_both)
say "TEST: $line"
close=$(echo "$line" | grep -oE 'close hard [0-9]+/' | grep -oE '[0-9]+')
if [ "${close:-0}" -lt "$NEED" ]; then
  say "STOP: close hard ${close:-0}/15 is below $NEED, so no submission"
  exit 0
fi

say "PUSH $TAG"
docker push "$TAG" >> "$LOG" 2>&1 || { say "STOP: push failed"; exit 1; }
digest=$(docker image inspect "$TAG" --format '{{range .RepoDigests}}{{println .}}{{end}}' | grep -m1 'molmobot-img-droid@sha256')
[ -n "$digest" ] || { say "STOP: no digest"; exit 1; }
IMG=docker.io/$digest
say "IMAGE $IMG"

(cd "$P/positronic" && bash docker/test_policy_image.sh --gpu "$IMG") > "$D/v4_start_test.log" 2>&1
rc=$?
say "START TEST exit $rc: $(grep -B1 -- '--- the last 30 lines' "$D/v4_start_test.log" | head -1)"
[ "$rc" = 0 ] || { say "STOP: the start test failed"; exit 1; }

for attempt in $(seq 1 40); do
  out=$(cd "$P/positronic" && timeout 300 "$HOME/.local/bin/positronic" eval run --policy-image="$IMG" --transaction-key="$KEY" 2>&1 | hide)
  id=$(echo "$out" | grep -oE 'submission [0-9a-f]{16}' | head -1 | awk '{print $2}')
  if [ -n "$id" ]; then
    say "SUBMITTED: $id"
    echo "$out" | head -4 >> "$LOG"
    exit 0
  fi
  if echo "$out" | grep -qi "transaction_conflict"; then
    say "STOP: refused: $(echo "$out" | grep -i conflict | head -1)"
    exit 1
  fi
  say "attempt $attempt gave no submission id: $(echo "$out" | tail -3 | tr '\n' ' ' | cut -c1-400)"
  if [ "$(date -u +%F)" = 2026-11-07 ] && echo "$out" | grep -qiE "quota|limit|per day|daily|too many|rate"; then
    wait_s=$(( $(date -u -d '2026-11-08 00:05' +%s) - $(date -u +%s) ))
    say "daily limit: waiting $wait_s s for 2026-11-08 00:05 UTC"
    sleep "$wait_s"
  else
    sleep 300
  fi
done
say "STOP: 40 attempts gave no submission id"
exit 1

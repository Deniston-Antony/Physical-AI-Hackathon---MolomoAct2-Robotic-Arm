#!/usr/bin/env bash
# The push-only image is submitted (2518efd8af2927f6). After the v4 pipeline (risers-v4): wait for the board scores of
# push only and v4. If v4 was not submitted or is not above v3 (68.4375%), submit the camera-only image and wait.
# A refusal for the daily limit waits for 00:05 UTC of the next day. Log: tests_1108/v4_submit.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
D=$P/tests_1108
LOG=$D/v4_submit.log
V3_SCORE=0.684375
REPO=docker.io/denistonantony/molmobot-img-droid
say() { echo "$(date -u '+%F %T UTC') $*" >> "$LOG"; }
hide() { grep -viE "api[_ -]?key|token|secret|password|X-Amz|https://"; }

score_of() {  # wait until the submission finishes; print its primary score, or "error"
  local id=$1 out
  while :; do
    out=$(cd "$P/positronic" && timeout 120 "$HOME/.local/bin/positronic" eval status --id="$id" 2>&1 | hide)
    if echo "$out" | head -1 | grep -qE "finished|succeeded"; then
      echo "$out" | grep -oE "'primary': [0-9.]+" | head -1 | grep -oE '[0-9.]+$'
      return
    fi
    if echo "$out" | head -1 | grep -qiE "errored|failed|cancel"; then echo error; return; fi
    sleep 300
  done
}

submit() {  # push, start-test and submit one tag; print the submission id
  local tag=$1 key=$2 digest img out id attempt rc
  docker push "$REPO:$tag" >> "$LOG" 2>&1 || { say "push of $tag failed"; return 1; }
  digest=$(docker image inspect "$REPO:$tag" --format '{{range .RepoDigests}}{{println .}}{{end}}' | grep -m1 'molmobot-img-droid@sha256')
  img=docker.io/$digest
  say "IMAGE $tag = $img"
  (cd "$P/positronic" && bash docker/test_policy_image.sh --gpu "$img") > "$D/${tag}_start_test.log" 2>&1
  rc=$?
  say "START TEST $tag exit $rc: $(grep -B1 -- '--- the last 30 lines' "$D/${tag}_start_test.log" | head -1)"
  [ "$rc" = 0 ] || return 1
  for attempt in $(seq 1 300); do
    out=$(cd "$P/positronic" && timeout 300 "$HOME/.local/bin/positronic" eval run --policy-image="$img" --transaction-key="$key" 2>&1 | hide)
    id=$(echo "$out" | grep -oE 'submission [0-9a-f]{16}' | head -1 | awk '{print $2}')
    if [ -n "$id" ]; then say "SUBMITTED $tag: $id"; echo "$id"; return 0; fi
    if echo "$out" | grep -qi "transaction_conflict"; then say "refused $tag: transaction conflict"; return 1; fi
    say "submit $tag attempt $attempt: $(echo "$out" | tail -3 | tr '\n' ' ' | cut -c1-400)"
    if echo "$out" | grep -qiE "quota|limit|per day|daily|too many|rate"; then
      sleep $(( $(date -u -d 'tomorrow 00:05' +%s) - $(date -u +%s) ))
    else
      sleep 300
    fi
  done
  return 1
}

PUSH_ID=2518efd8af2927f6
while systemctl --user is-active -q risers-v4; do sleep 60; done
say "SCORE v4-push ($PUSH_ID): $(score_of "$PUSH_ID")"
v4=$(grep -oE 'SUBMITTED: [0-9a-f]{16}' "$LOG" | tail -1 | awk '{print $2}')
s4=none
if [ -n "$v4" ]; then
  s4=$(score_of "$v4")
  say "SCORE v4 combined ($v4): $s4"
fi
if [ "$s4" != none ] && [ "$s4" != error ] && python3 -I -c "import sys; sys.exit(0 if float(sys.argv[1]) > float(sys.argv[2]) else 1)" "$s4" "$V3_SCORE"; then
  say "FOLLOWUP: v4 is above v3, so no camera-only submission"
else
  say "FOLLOWUP: v4 was not submitted or is not above v3; submitting camera only"
  id=$(submit v4-camera risers-molmobot-img-v4-camera-only | tail -1)
  if [ -n "$id" ]; then say "SCORE v4-camera ($id): $(score_of "$id")"; else say "FOLLOWUP: camera only was not submitted"; fi
fi
say "FOLLOWUP DONE"

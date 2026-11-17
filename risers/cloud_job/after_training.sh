#!/usr/bin/env bash
# After the cloud training: build image v5 (v4 flags + open pull + the open/close action expert for both task kinds),
# push it, run the platform start test, and run the local tests: 30 open, 15 hard close and 15 normal close board
# episodes. Then keep the new expert only for the task kinds where it beats the checkpoint's own expert:
#   open:  v4 + open pull had 4/30 locally.
#   close: v4 had 7/15 hard close locally; the board runs of the same expert had 13, 13, 10 of the 15 normal close.
# When the new expert helps at least one kind, push an image that routes only those kinds to it (same weights, other
# flag; each task kind behaves as tested), run the start test, and submit it. Log: cloud_job/after_training.log.
# Usage: bash after_training.sh <action expert .pt>
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
D=$P/tests_1108
LOG=$P/cloud_job/after_training.log
EXPERT=${1:?expert file}
V4="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.close_push_after=6 --model.camera_fallback=True"
EXP="--model.open_pull=True --model.open_close_expert=/opt/molmobot/action_expert_open_close.pt"
REPO=docker.io/denistonantony/molmobot-img-droid
BASE_OPEN=4 BASE_CLOSE=19
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
hide() { grep -viE "api[_ -]?key|token|secret|password|X-Amz|https://"; }

build_push_test() {  # tag, flags -> sets IMG
  say "BUILD $1: $2"
  bash "$P/molmobot_image/build_open_close.sh" "$1" "$EXPERT" "$2" >> "$LOG" 2>&1 || { say "STOP: build failed"; exit 1; }
  docker push "$1" >> "$LOG" 2>&1 || { say "STOP: push failed"; exit 1; }
  local digest
  digest=$(docker image inspect "$1" --format '{{range .RepoDigests}}{{println .}}{{end}}' | grep -m1 'molmobot-img-droid@sha256')
  [ -n "$digest" ] || { say "STOP: no digest"; exit 1; }
  IMG=docker.io/$digest
  say "PUSHED $IMG"
  # A local test of a mid-training checkpoint (unit risers-midtest) uses the GPU and port 8000 until it ends.
  while systemctl --user is-active -q risers-midtest; do sleep 60; done
  (cd "$P/positronic" && bash docker/test_policy_image.sh --gpu "$IMG") > "$P/cloud_job/start_test_$(basename "${1#*:}").log" 2>&1
  local rc=$?
  say "START TEST exit $rc"
  [ "$rc" = 0 ] || { say "STOP: the start test failed"; exit 1; }
}

ok() {  # run -> successes
  "$HOME/molmobot_src/venv/bin/python" -I - "$D" "$1" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location('summarize', sys.argv[1] + '/summarize.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
print(sum(e['ok'] for e in s.episodes(sys.argv[2]).values()))
PY
}

build_push_test "$REPO:v5-openclose" "$V4 $EXP"
TESTED=$IMG
bash "$D/run_image.sh" v5_open "$D/open30.json" "$TESTED"
bash "$D/run_image.sh" v5_close "$D/close15.json" "$TESTED"
bash "$D/run_image.sh" v5_closen "$D/closedatagen15.json" "$TESTED"
open=$(ok v5_open) close_hard=$(ok v5_close) close_normal=$(ok v5_closen)
close=$((close_hard + close_normal))
say "LOCAL TESTS v5: open $open/30 (old expert $BASE_OPEN), close $close/30 = hard $close_hard + normal $close_normal (old expert $BASE_CLOSE)"

use_open=$([ "$open" -gt "$BASE_OPEN" ] && echo 1 || echo 0)
use_close=$([ "$close" -gt "$BASE_CLOSE" ] && echo 1 || echo 0)
case "$use_open$use_close" in
  11) tasks=both ;;
  10) tasks=open ;;
  01) tasks=close ;;
  *) say "STOP: the new expert beats the old one for neither task kind, so no submission"; exit 0 ;;
esac
say "ROUTE: the new expert gets $tasks tasks"
if [ "$tasks" = both ]; then
  IMG=$TESTED
else
  build_push_test "$REPO:v5-$tasks" "$V4 $EXP --model.open_close_expert_tasks=$tasks"
fi

KEY=risers-molmobot-img-v5-expert-$tasks
for attempt in $(seq 1 30); do
  out=$(cd "$P/positronic" && timeout 300 "$HOME/.local/bin/positronic" eval run --policy-image="$IMG" --transaction-key="$KEY" 2>&1 | hide)
  id=$(echo "$out" | grep -oE 'submission [0-9a-f]{16}' | head -1 | awk '{print $2}')
  if [ -n "$id" ]; then
    say "SUBMITTED: $id ($IMG, key $KEY)"
    exit 0
  fi
  if echo "$out" | grep -qi "transaction_conflict"; then
    say "STOP: refused: $(echo "$out" | grep -i conflict | head -1)"
    exit 1
  fi
  say "attempt $attempt gave no submission id: $(echo "$out" | tail -3 | tr '\n' ' ' | cut -c1-400)"
  sleep 300
done
say "STOP: 30 attempts gave no submission id"
exit 1

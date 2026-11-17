#!/usr/bin/env bash
# Local test of our board-best image (v3) on the 34 board episodes that 3 or more of the top 5 teams solve and that
# 2 or more of our 3 board runs fail (tests_1108/reliable34.json). It starts after the grasp tests
# (unit risers-grasptests) and the cloud run (unit risers-cloudeval, cloud_job/cloud_eval.sh), and runs only the
# episodes that the cloud run did not finish. Then it writes tests_1108/results_reliable.md, the comparison with the top teams, and
# copies the run to the SSD. Run under systemd-run (unit risers-reliable). Log: cloud_job/reliable_test.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
D=$P/tests_1108
LOG=$J/reliable_test.log
RUN=reliable_v3
IMAGE=denistonantony/molmobot-img-droid:v3
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/local_tests_reliable34"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
active() { systemctl --user is-active -q "$1"; }

say "WAIT for the end of the grasp tests and of the cloud run (unit risers-cloudeval)"
while active risers-grasptests || active risers-cloudeval; do sleep 60; done
for _ in $(seq 30); do active risers-imgsave || break; sleep 30; done
say "TEST $RUN: image v3 on the 34 reliable episodes"
bash "$D/run_image.sh" "$RUN" "$D/reliable34.json" "$IMAGE"
"$HOME/molmobot_src/venv/bin/python" "$P/competition_runs/board_videos/reliable_report.py" "$RUN" \
  > "$D/results_reliable.md" 2>> "$LOG" && say "DONE $RUN: $(grep -m1 '^Solved' "$D/results_reliable.md")"
mkdir -p "$OUT/$RUN"
rsync -rt --no-perms --no-owner --no-group "$HOME"/evals/t8_${RUN}_p* "$OUT/$RUN/" 2>> "$LOG" \
  && cp "$D/results_reliable.md" "$OUT/" && say "results copied to the SSD" || say "copy to the SSD failed"

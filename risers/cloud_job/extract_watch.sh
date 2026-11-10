#!/usr/bin/env bash
# Save the action expert of each checkpoint of a training run as ~/runs/<run>/experts/step<N>.pt, as soon as the
# trainer logs "Checkpoint saved to". The trainer keeps 2 checkpoints, so each one stays for 2 save intervals.
# Run on the training VM next to train_run.sh. Usage: bash extract_watch.sh <run name> <train log>
set -uo pipefail
run=$1 log=$2
out=~/runs/$run/experts
mkdir -p "$out"
PY=~/MolmoBot/MolmoBot/.venv/bin/python
while :; do
  for dir in $(grep -a -o "Checkpoint saved to [^ ]*" "$log" 2>/dev/null | awk '{print $4}'); do
    step=$(basename "$dir")
    [ -s "$out/$step.pt" ] || [ -e "$out/$step.failed" ] && continue
    if nice -n 10 "$PY" ~/cloud_job/extract_action_expert.py "$dir" "$out/$step.pt.tmp" > "$out/$step.log" 2>&1; then
      mv "$out/$step.pt.tmp" "$out/$step.pt"
      echo "$(date '+%F %T') extracted $step"
    else
      touch "$out/$step.failed"
      echo "$(date '+%F %T') extract $step failed, see $out/$step.log"
    fi
  done
  grep -qa "EXTRACT done\|Traceback" "$log" 2>/dev/null && break
  sleep 30
done
echo "$(date '+%F %T') watch ends"

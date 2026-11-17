#!/usr/bin/env bash
# Finish the cloud job without help: while the training runs, download the action expert of each checkpoint (one each
# 200 steps) to the SSD; when the training VM has saved the final expert, download it, delete the VM (with its disk),
# stop the local datagen, then run after_training.sh (image, push, start test, local tests, submit).
# A training run that stops without the expert still gives one, from its last checkpoint, if it saved one.
# Run under systemd-run. Log: cloud_job/finish_job.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
LOG=$J/finish_job.log
NB=/home/antonlucy/.nebius/bin/nebius
VM_ID=computeinstance-e00pmf3vknssw5ew5h
T=$(cut -d' ' -f1 "$J/train_ip")
RUN=openclose200
SSD="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/molmobot_openclose_2026-11-09"
OUT=$SSD/action_expert_open_close_final.pt
mkdir -p "$SSD/experts"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
remote() { ssh -o BatchMode=yes -o ConnectTimeout=20 "ubuntu@$T" "$@"; }
# exFAT keeps no owners or permissions.
fetch() { rsync -rt --no-perms --no-owner --no-group "$@"; }
fetch_experts() { fetch --include='step*.pt' --exclude='*' "ubuntu@$T:runs/$RUN/experts/" "$SSD/experts/" 2>> "$LOG"; }

delete_vm() {
  for attempt in 1 2 3 4 5; do
    if "$NB" --profile risers-sa compute instance delete --id "$VM_ID" >> "$LOG" 2>&1; then
      say "DELETED risers-train"
      echo "$(date '+%F %T') DELETED risers-train" >> "$J/ledger.txt"
      break
    fi
    say "delete attempt $attempt failed"
    sleep 60
  done
  "$NB" --profile risers-sa compute instance list --parent-id project-e00q19nppr00ffpv0qkagn >> "$LOG" 2>&1
  "$NB" --profile risers-sa compute disk list --parent-id project-e00q19nppr00ffpv0qkagn >> "$LOG" 2>&1
}

say "WAIT for the training VM"
while :; do
  fetch_experts
  if remote 'grep -q "EXTRACT done" ~/train.log' 2>/dev/null; then
    say "training and extraction done"
    break
  fi
  if ! remote 'XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user is-active -q risers-train' 2>/dev/null; then
    if remote true 2>/dev/null; then
      say "the training unit stopped without an expert; trying the last checkpoint"
      remote 'tail -30 ~/train.log' >> "$LOG" 2>&1
      remote "last=\$(ls -d ~/runs/$RUN/step* 2>/dev/null | sort -V | tail -1); [ -n \"\$last\" ] && ~/MolmoBot/MolmoBot/.venv/bin/python ~/cloud_job/extract_action_expert.py \"\$last\" ~/runs/$RUN/action_expert_open_close.pt" >> "$LOG" 2>&1 \
        || say "no checkpoint to extract"
      break
    fi
  fi
  sleep 120
done

sleep 60
fetch_experts
if remote "test -s ~/runs/$RUN/action_expert_open_close.pt" 2>/dev/null; then
  for attempt in 1 2 3; do
    fetch "ubuntu@$T:runs/$RUN/action_expert_open_close.pt" "$OUT" && break
    say "download attempt $attempt failed"
  done
fi
fetch "ubuntu@$T:train.log" "$SSD/train.log" || true
fetch "ubuntu@$T:train_openclose_stopped.log" "$SSD/train_first_run_stopped_at_step1160.log" || true
fetch "ubuntu@$T:runs/$RUN/config.yaml" "$SSD/train_config.yaml" || true
fetch "ubuntu@$T:extract_watch.log" "$SSD/extract_watch.log" || true
say "experts on the SSD: $(ls "$SSD/experts" | tr '\n' ' ')"
remote_size=$(remote "stat -c %s ~/runs/$RUN/action_expert_open_close.pt" 2>/dev/null || echo 0)
local_size=$(stat -c %s "$OUT" 2>/dev/null || echo 0)
say "expert file: remote $remote_size bytes, local $local_size bytes"
delete_vm

systemctl --user stop risers-datagen-close 2>/dev/null
for unit in $(systemctl --user list-units --type=scope --no-legend 'risers-*' | awk '{print $1}'); do
  systemctl --user stop "$unit"
done
say "stopped the local datagen"

if [ "$local_size" = 0 ] || [ "$local_size" != "$remote_size" ]; then
  say "STOP: no complete expert file, so no image"
  exit 1
fi
say "START after_training.sh"
sg docker -c "bash $J/after_training.sh '$OUT'"
say "after_training.sh ended with code $?"

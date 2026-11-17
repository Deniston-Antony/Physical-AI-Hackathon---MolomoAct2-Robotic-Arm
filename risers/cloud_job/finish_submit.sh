#!/usr/bin/env bash
# Finish the cloud job (user's plan of 9 Nov): while the training runs, copy the action expert of each checkpoint to the
# SSD. When the final expert is saved: copy it, build and push image v5-openclose (v4 flags + open pull + the new expert
# for open and close tasks), run the platform start test on the training VM, submit the image to the competition when
# the test passes, and delete the training VM (with its disk) in every case. The local tests of the checkpoints are a
# separate job. Run under systemd-run. Log: cloud_job/finish_job.log.
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
TAG=docker.io/denistonantony/molmobot-img-droid:v5-openclose
KEY=risers-molmobot-img-v5-openclose
FLAGS="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=3 --model.still_calls=3 --model.close_push_after=6 --model.camera_fallback=True --model.open_pull=True --model.open_close_expert=/opt/molmobot/action_expert_open_close.pt"
mkdir -p "$SSD/experts"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
hide() { grep -viE "api[_ -]?key|token|secret|password|X-Amz|https://"; }
remote() { ssh -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 "ubuntu@$T" "$@"; }
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

say "WAIT for the training VM (plan: push, cloud start test, submit, delete)"
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
say "experts on the SSD: $(ls "$SSD/experts" | sort -V | tr '\n' ' ')"
remote_size=$(remote "stat -c %s ~/runs/$RUN/action_expert_open_close.pt" 2>/dev/null || echo 0)
local_size=$(stat -c %s "$OUT" 2>/dev/null || echo 0)
say "final expert: remote $remote_size bytes, local $local_size bytes"
if [ "$local_size" = 0 ] || [ "$local_size" != "$remote_size" ]; then
  say "STOP: no complete final expert, so no image"
  delete_vm
  exit 1
fi

say "BUILD $TAG"
sg docker -c "bash '$P/molmobot_image/build_open_close.sh' '$TAG' '$OUT' '$FLAGS'" >> "$LOG" 2>&1 || { say "STOP: build failed"; delete_vm; exit 1; }
sg docker -c "docker push '$TAG'" >> "$LOG" 2>&1 || { say "STOP: push failed"; delete_vm; exit 1; }
digest=$(sg docker -c "docker image inspect '$TAG' --format '{{range .RepoDigests}}{{println .}}{{end}}'" | grep -m1 'molmobot-img-droid@sha256')
[ -n "$digest" ] || { say "STOP: no digest"; delete_vm; exit 1; }
IMG=docker.io/$digest
say "PUSHED $IMG"

say "CLOUD START TEST on the training VM"
fetch "$P/positronic/docker/test_policy_image.sh" "ubuntu@$T:test_policy_image.sh"
remote "bash ~/test_policy_image.sh --gpu '$IMG'" > "$J/v5_cloud_start_test.log" 2>&1
rc=$?
say "CLOUD START TEST exit $rc (log cloud_job/v5_cloud_start_test.log)"
delete_vm
[ "$rc" = 0 ] || { say "STOP: the start test failed, so no submission"; exit 1; }

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

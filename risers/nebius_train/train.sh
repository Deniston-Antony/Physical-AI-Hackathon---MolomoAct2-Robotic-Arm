#!/usr/bin/env bash
# Fine-tune GR00T N1.7 DROID on the Risers demonstrations. Run it inside tmux, so a lost ssh connection
# does not stop it. A checkpoint is saved every 2,000 steps.
# Usage on the VM: bash train.sh [steps]     (default 10000)
set -euo pipefail
steps="${1:-10000}"
cd ~/positronic/docker
docker compose run --rm -T --pull never -v "$HOME/groot-data:/data" \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e GROOT_PATCH_MISTRAL=1 -e WANDB_MODE=offline groot-train \
  --input_path=/data/datasets/risers_v1 --output_path=/data/checkpoints --exp_name=risers_v1 \
  --num_train_steps="$steps" --save_steps=2000 2>&1 | tee -a ~/train.log

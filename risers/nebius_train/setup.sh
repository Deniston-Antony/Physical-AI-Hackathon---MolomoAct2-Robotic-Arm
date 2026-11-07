#!/usr/bin/env bash
# Prepare the H100 VM for GR00T training: the positronic source, the two GR00T images and the base weights.
# Usage on the VM: bash setup.sh
set -euo pipefail
if ! docker info >/dev/null 2>&1; then
  sudo usermod -aG docker "$USER"
  echo "Added $USER to the docker group. Type exit, connect with ssh again, and run: bash setup.sh"
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv
cd ~
[ -d positronic ] || git clone --depth 1 https://github.com/Positronic-Robotics/positronic
echo "Pulling the GR00T images (about 38 GB). This takes 5-15 minutes."
docker pull -q positro/gr00t:latest & train_pull=$!
docker pull -q positro/gr00t-n17-droid:latest & weights_pull=$!
wait "$train_pull"
wait "$weights_pull"
# Training reads the weights of GR00T N1.7 DROID and of its gated backbone from this cache, with no token.
mkdir -p ~/.cache/huggingface
cid=$(docker create positro/gr00t-n17-droid:latest)
docker cp "$cid":/opt/hf/. ~/.cache/huggingface/
docker rm "$cid" >/dev/null
du -sh ~/.cache/huggingface
if [ -f ~/groot-data/datasets/risers_v1/meta/info.json ]; then echo "Dataset found."; else echo "Dataset not here yet: upload it from your PC."; fi
echo "Setup done. Next: tmux new -s train, then bash train.sh"

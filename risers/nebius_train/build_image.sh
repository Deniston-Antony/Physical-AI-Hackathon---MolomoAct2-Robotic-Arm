#!/usr/bin/env bash
# Build the policy image from one checkpoint, and push it. Run `docker login` first.
# Usage on the VM: bash build_image.sh <step> <docker.io/you/image:tag>
#   for example:   bash build_image.sh 10000 docker.io/denistonantony/gr00t-risers:v1
set -euo pipefail
step="$1"
image="$2"
run=~/groot-data/checkpoints/risers_v1
ckpt="$run/checkpoint-$step"
[ -d "$ckpt" ] || { echo "No checkpoint at $ckpt. These exist:"; ls "$run"; exit 1; }
build=~/image_build
sudo rm -rf "$build"
mkdir -p "$build"
# Copy the checkpoint without the optimizer state (about 12 GB), which the server does not read.
sudo rsync -a --exclude optimizer.pt --exclude scheduler.pt --exclude rng_state.pth "$ckpt/" "$build/checkpoint/"
# Training copies the model settings into each checkpoint only when it ends. A run stopped early has none.
if [ ! -f "$build/checkpoint/meta/positronic_model_settings.json" ]; then
  sudo mkdir -p "$build/checkpoint/meta"
  sudo cp "$run/meta/positronic_model_settings.json" "$build/checkpoint/meta/"
fi
sudo chown -R "$USER" "$build"
du -sh "$build/checkpoint"
cat > "$build/Dockerfile" <<'DOCKERFILE'
FROM positro/gr00t-n17-droid:latest
COPY checkpoint /opt/checkpoint
ENV GROOT_MODEL_SOURCE=/opt/checkpoint
DOCKERFILE
cd "$build"
docker buildx build --platform linux/amd64 --provenance=false --sbom=false -t "$image" --push .
docker buildx imagetools inspect "$image" | grep -m1 Digest
echo "Pushed $image. Next: test it with: cd ~/positronic && bash docker/test_policy_image.sh --gpu $image"

#!/usr/bin/env bash
# Build a MolmoBot policy image on this PC.
# Usage: [CHECKPOINT=<name>] [SERVER_ARGS=<flags>] bash molmobot_image/build.sh <image tag> [server command]
#   CHECKPOINT is a folder in ~/molmobot_src (default MolmoBot-DROID), for example
#   CHECKPOINT=MolmoBot-Img-DROID SERVER_ARGS=--model.camera=left \
#     bash molmobot_image/build.sh docker.io/denistonantony/molmobot-img-droid:v1 droid_half_overlap
# Run docker as `sg docker -c "bash molmobot_image/build.sh <tag>"` while the login session lacks the docker group.
# Then push it (docker push <tag>) and run the platform's start test: bash docker/test_policy_image.sh --gpu <tag>.
# That test pulls the tag, so it tests the pushed image.
set -euo pipefail
tag="${1:?usage: $0 <image tag> [server command]}"
command="${2:-droid}"
project=$(cd "$(dirname "$0")/.." && pwd)
src=$HOME/molmobot_src
# The float32 checkpoint as Hugging Face holds it. The server reads it through a memory map into a bfloat16 model.
checkpoint="${CHECKPOINT:-MolmoBot-DROID}"
weights=$src/$checkpoint
[ -f "$weights/model.pt" ] || { echo "No checkpoint at $weights"; exit 1; }

cd "$project/positronic"
docker buildx build --platform linux/amd64 --provenance=false --sbom=false --load \
  --build-context molmobot="$src/repo/MolmoBot" --build-context weights="$weights" \
  --build-arg SERVER_COMMAND="$command" --build-arg SERVER_ARGS="${SERVER_ARGS:-}" \
  --build-arg CHECKPOINT_NAME="$checkpoint" \
  -f docker/Dockerfile.serve-molmobot-droid -t "$tag" .
docker image inspect "$tag" --format 'Image size: {{.Size}} bytes'

#!/usr/bin/env bash
# Build a MolmoBot policy image with an open/close action expert, as one layer on the v1 image.
# Usage: sg docker -c "bash molmobot_image/build_open_close.sh <tag> <action expert .pt> '<server flags>'"
# The flags must name the expert: --model.open_close_expert=/opt/molmobot/action_expert_open_close.pt
set -euo pipefail
tag=${1:?tag} expert=${2:?expert file} flags=${3:?server flags}
project=$(cd "$(dirname "$0")/.." && pwd)
# Image v1 (the base of v3 and v4): MolmoBot-Img-DROID with the MolmoBot server.
base=docker.io/denistonantony/molmobot-img-droid@sha256:0c0033909eab5f281331b279a539f9cbdfce9d746d30dc213b53af868415d83a
grep -q -- '--model.open_close_expert=/opt/molmobot/action_expert_open_close.pt' <<<"$flags" \
  || { echo "The flags do not name the expert file"; exit 1; }
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
cp "$project"/positronic/positronic/vendors/molmobot/*.py "$stage"/
cp "$expert" "$stage"/action_expert_open_close.pt
docker buildx build --platform linux/amd64 --provenance=false --sbom=false --load \
  --build-arg BASE="$base" --build-arg SERVER_ARGS="$flags" \
  -f "$project/molmobot_image/Dockerfile.open_close" -t "$tag" "$stage"
docker image inspect "$tag" --format 'Image size: {{.Size}} bytes'

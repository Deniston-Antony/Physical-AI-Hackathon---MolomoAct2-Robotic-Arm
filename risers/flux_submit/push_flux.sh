#!/usr/bin/env bash
# Push the FLUX 1-step retry + fast-timing policy image to Docker Hub (only our small code layer is uploaded;
# the 25 GB base layers are linked from positro/flux3-action, no big download). Run: bash push_flux.sh
set -euo pipefail
cd "$(dirname "$0")/flux_submit"
sg docker -c "docker buildx inspect risers-push >/dev/null 2>&1 || docker buildx create --name risers-push --driver docker-container
docker buildx build --builder risers-push --platform linux/amd64 -f Dockerfile.link --provenance=false --sbom=false \
  -t docker.io/denistonantony/flux3-retry-droid:v1 --push ."
echo "PUSHED. The watcher submits it to the competition within 5 minutes."

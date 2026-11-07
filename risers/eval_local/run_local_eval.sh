#!/usr/bin/env bash
# Score a policy image on the 20 practice episodes on this PC, and keep the video of each episode.
# Usage: bash eval_local/run_local_eval.sh <image> <name>
#   for example: bash eval_local/run_local_eval.sh docker.io/denistonantony/gr00t-risers:step10000 gr00t_step10000
# The episodes go to ~/evals/<name>. Run it from a normal terminal, not from VS Code.
set -euo pipefail
image="$1"
name="$2"
out=~/evals/$name
project=$(cd "$(dirname "$0")/.." && pwd)
export MLSPACES_ASSETS_DIR=~/molmospaces/assets MLSPACES_CACHE_DIR=~/molmospaces/cache
[ ! -e "$out" ] || { echo "$out exists. Choose another name."; exit 1; }
mkdir -p ~/evals

# The containerd image store keeps the compressed layers beside the unpacked ones, about 82 GB for this image.
free_gb=$(df --output=avail -BG ~ | tail -1 | tr -dc 0-9)
store=$(docker info --format '{{.DriverStatus}}')
need=60
case "$store" in *containerd*) need=90 ;; esac
echo "Free disk: ${free_gb} GB. Docker image store: $store. This image needs about $need GB."
if ! docker image inspect "$image" >/dev/null 2>&1 && [ "$free_gb" -lt "$need" ]; then
  echo "Not enough free disk for the image. Stopping before the download."
  exit 1
fi

cleanup() { docker rm -f risers-policy >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker pull "$image"
cleanup
docker run -d --name risers-policy --gpus all -p 8000:8000 "$image" >/dev/null
echo "Waiting for the policy server to load the model..."
ready=false
for _ in $(seq 120); do
  if curl -sf -X POST http://localhost:8000/api/v1/keepalive >/dev/null; then ready=true; break; fi
  if [ -z "$(docker ps -q -f name=risers-policy)" ]; then break; fi
  sleep 5
done
if [ "$ready" != true ]; then
  echo "The policy server did not start. Its log:"
  docker logs --tail 40 risers-policy
  exit 1
fi
echo "The policy server is ready. Running the 20 episodes."

cd "$project/positronic"
uv run --locked positronic eval run --eval=molmo.franka_pick_mini \
  --policy=.remote --policy.address.host=localhost --policy.address.port=8000 \
  --output_dir="$out" 2>&1 | tee ~/evals/$name.log
echo "The episodes are in $out"

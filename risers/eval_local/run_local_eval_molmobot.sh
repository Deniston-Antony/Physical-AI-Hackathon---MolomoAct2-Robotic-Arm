#!/usr/bin/env bash
# Score MolmoBot-DROID on practice episodes on this PC, with the policy server run from its venv (no image).
# Usage: bash eval_local/run_local_eval_molmobot.sh <name> [episode list .json from make_mixed_set.py]
#   With no list it runs molmo.franka_pick_mini. SERVER_COMMAND picks the server mode (default droid,
#   or droid_overlap, which infers while the robot moves). CHECKPOINT_DIR picks the model folder (default
#   ~/molmobot_src/MolmoBot-DROID). SERVER_ARGS adds server flags, for example --model.camera=left.
# Needs: ~/molmobot_src/venv (server venv), ~/molmobot_src/repo (MolmoBot code), ~/molmobot_src/MolmoBot-DROID.
# The episodes go to ~/evals/<name>, the server log to ~/evals/<name>.server.log.
set -euo pipefail
name="$1"
episodes="${2:-}"
eval_args=(--eval=molmo.franka_pick_mini)
if [ -n "$episodes" ]; then
  paths=$(python3 -I -c 'import json, sys; print(json.dumps([e["path"] for e in json.load(open(sys.argv[1]))]))' "$episodes")
  eval_args=(--eval=.sim.molmo.benchmarks "--eval.episode_paths=$paths")
fi
out=~/evals/$name
project=$(cd "$(dirname "$0")/.." && pwd)
export PATH=$HOME/.local/bin:$PATH
export MLSPACES_ASSETS_DIR=~/molmospaces/assets MLSPACES_CACHE_DIR=~/molmospaces/cache
[ ! -e "$out" ] || { echo "$out exists. Choose another name."; exit 1; }
mkdir -p ~/evals

cd "$project/positronic"
PYTHONPATH=$HOME/molmobot_src/repo/MolmoBot PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  ~/molmobot_src/venv/bin/python -m positronic.vendors.molmobot.server "${SERVER_COMMAND:-droid}" \
  --model.checkpoint_dir="${CHECKPOINT_DIR:-$HOME/molmobot_src/MolmoBot-DROID}" ${SERVER_ARGS:-} \
  > ~/evals/$name.server.log 2>&1 &
server=$!
cleanup() { kill "$server" 2>/dev/null || true; wait "$server" 2>/dev/null || true; }
trap cleanup EXIT

echo "Waiting for the policy server to load the model..."
ready=false
for _ in $(seq 120); do
  if curl -sf -X POST http://localhost:8000/api/v1/keepalive >/dev/null; then ready=true; break; fi
  kill -0 "$server" 2>/dev/null || break
  sleep 5
done
if [ "$ready" != true ]; then
  echo "The policy server did not start. Its log:"
  tail -40 ~/evals/$name.server.log
  exit 1
fi
echo "The policy server is ready. Running the episodes."

uv run --locked positronic eval run "${eval_args[@]}" \
  --policy=.remote --policy.address.host=localhost --policy.address.port=8000 \
  --output_dir="$out" 2>&1 | tee ~/evals/$name.log
echo "The episodes are in $out"

#!/usr/bin/env bash
# The job of the cloud VM risers-eval: set up positronic, pull the two images, then run 4 test streams side by side,
# 2 per image (17 of the 34 reliable episodes each, files v3_a.json, v3_b.json, touch_a.json, touch_b.json).
# Each stream has its own policy server, as the local tests have. Log: ~/cloud_eval/vm.log.
# It writes ~/cloud_eval/ALL_DONE at the end, also when it stops on an error.
set -uo pipefail
D=$HOME/cloud_eval
export PATH=$HOME/.local/bin:$PATH UV_PYTHON=3.13 UV_PYTHON_PREFERENCE=only-managed
V3=docker.io/denistonantony/molmobot-img-droid@sha256:0a62b44de814b613a048914e8b4b892ba8973dede2a3e9c9db007477f49185fa
V5=docker.io/denistonantony/molmobot-img-droid@sha256:f8feb081c51914945daf3fed7bd03c6cac7d1cc9402ed1e707a10edd785df517
say() { echo "$(date '+%F %T') $*" >> "$D/vm.log"; }
stop() { say "STOP: $*"; touch "$D/ALL_DONE"; exit 1; }

say "SETUP: uv sync and image pulls"
(cd "$HOME/positronic" && uv sync --locked) >> "$D/setup.log" 2>&1 || stop "uv sync failed (setup.log)"
say "SETUP: uv sync ok"
docker pull -q "$V3" >> "$D/setup.log" 2>&1 || stop "pull of v3 failed (setup.log)"
docker pull -q "$V5" >> "$D/setup.log" 2>&1 || stop "pull of v5-touch failed (setup.log)"
say "SETUP: images pulled; GPU $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"

# The first stream builds the MolmoSpaces environment and downloads the first assets. The others start when its first
# scene is ready (or after 20 min), 30 s apart.
bash "$D/run_stream.sh" reliable_v3_a "$D/v3_a.json" "$V3" 8001 &
for _ in $(seq 120); do
  grep -qs 'Scene setup from episode spec completed' "$HOME"/evals/t8_reliable_v3_a_p*.runner.log && break
  sleep 10
done
say "STREAMS: the first scene is ready; the other 3 streams start"
bash "$D/run_stream.sh" reliable_touch_a "$D/touch_a.json" "$V5" 8002 &
sleep 30
bash "$D/run_stream.sh" reliable_v3_b "$D/v3_b.json" "$V3" 8003 &
sleep 30
bash "$D/run_stream.sh" reliable_touch_b "$D/touch_b.json" "$V5" 8004 &
wait
say "ALL DONE: $(ls "$HOME"/evals/t8_reliable_*_p*/*/*/static.json 2>/dev/null | wc -l) episodes"
touch "$D/ALL_DONE"

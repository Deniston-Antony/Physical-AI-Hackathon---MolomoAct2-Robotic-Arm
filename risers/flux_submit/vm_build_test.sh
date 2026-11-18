#!/usr/bin/env bash
# On the VM: build the FLUX submission image, run the organisers' start test, then 4 episodes against it.
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed TZ=Europe/Berlin
export MLSPACES_ASSETS_DIR=$HOME/molmospaces/assets MLSPACES_CACHE_DIR=$HOME/molmospaces/cache
IMG=denistonantony/flux3-retry-droid:v1
L=$HOME/build.log
say() { echo "$(date '+%F %T') $*" >> "$L"; }
say "BUILD: start"
(cd ~/positronic && for i in 1 2 3 4 5; do UV_PYTHON=3.13 uv sync --locked && break; sleep 10; done \
  && uv run --locked python -c 'from positronic.simulator.molmo_spaces.launcher import ensure_molmo_venv; ensure_molmo_venv()') > ~/setup.log 2>&1 &
setup=$!
docker build -t "$IMG" ~/flux_submit > ~/docker_build.log 2>&1 || { say "STOP: build failed"; exit 1; }
say "BUILD: done, image id $(docker image inspect -f '{{.Id}}' "$IMG")"
bash ~/test_local.sh --gpu "$IMG" > ~/start_test.log 2>&1; rc=$?
say "START TEST: exit $rc: $(grep -m1 -iE 'pass|fail|answer|ok' ~/start_test.log | cut -c1-200)"
[ "$rc" = 0 ] || { say "STOP: start test failed"; exit 1; }
wait "$setup" || { say "STOP: simulator setup failed"; exit 1; }
docker rm -f srv >/dev/null 2>&1
docker run -d --name srv --gpus all -p 8001:8000 "$IMG" > /dev/null
for _ in $(seq 120); do curl -sf -X POST http://localhost:8001/api/v1/keepalive >/dev/null && break; sleep 5; done
say "SERVER: up; $(docker logs srv 2>&1 | grep -m1 'overrode num_inference_steps')"
(cd ~/positronic && uv run --locked positronic eval run --eval=.sim.molmo.benchmarks \
  "--eval.episode_paths=$(cat ~/flux_submit/smoke.json)" --policy=.remote --policy.address.host=localhost \
  --policy.address.port=8001 --output_dir=$HOME/evals/smoke) > ~/smoke.log 2>&1
say "SMOKE: exit $?, $(ls ~/evals/smoke/*/*/static.json 2>/dev/null | wc -l) of 4 episodes finished"
docker logs srv > ~/srv.log 2>&1
say "SMOKE: $(grep -c 'Rule counts' ~/srv.log) sessions ended; last: $(grep 'Rule counts' ~/srv.log | tail -1 | cut -c1-200)"
say "ALL DONE"

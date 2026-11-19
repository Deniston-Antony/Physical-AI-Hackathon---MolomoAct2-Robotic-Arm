#!/usr/bin/env bash
# On the cloud VM: build the router image, check its size, run the platform's start test, then
#   A: 8 MolmoSpaces episodes through the router (must stay on v3)
#   B: 8 MolmoSpaces episodes with ROUTER_TEST_SWITCH=1 (first sessions on v3, then the switch to FLUX)
# Log: ~/router/vm.log. Writes ~/router/ALL_DONE at the end (also after a STOP).
set -uo pipefail
D=$HOME/router; L=$D/vm.log; IMG=denistonantony/policy-router:v1
export TZ=Europe/Berlin PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed
export MLSPACES_ASSETS_DIR=$HOME/molmospaces/assets MLSPACES_CACHE_DIR=$HOME/molmospaces/cache
say() { echo "$(date '+%F %T') $*" >> "$L"; }
stop() { say "STOP: $*"; docker rm -f rt >/dev/null 2>&1; touch "$D/ALL_DONE"; exit 1; }
say "SETUP: pull both images, uv sync"
(cd ~/positronic && for i in 1 2 3 4 5; do UV_PYTHON=3.13 uv sync --locked && break; sleep 15; done \
  && UV_NO_SYNC=1 uv run python -c 'from positronic.simulator.molmo_spaces.launcher import ensure_molmo_venv; ensure_molmo_venv()') > $D/setup.log 2>&1 &
setup=$!
docker pull -q docker.io/denistonantony/molmobot-img-droid:v3-jpeg-rl2 > $D/pull_v3.log 2>&1 &
pull_v3=$!
docker pull -q "docker.io/positro/flux3-action@$(cat $D/flux_digest)" > $D/pull_flux.log 2>&1 || stop "flux pull"
wait $pull_v3; docker image inspect denistonantony/molmobot-img-droid:v3-jpeg-rl2 >/dev/null 2>&1 || stop "v3 pull"
say "PULLED; build"
docker build -t $IMG $D > $D/build.log 2>&1 || { tail -30 $D/build.log >> $L; stop "build failed"; }
IMG=denistonantony/policy-router:v3
docker build -t $IMG -f $D/Dockerfile.flat $D > $D/build_flat.log 2>&1 || { tail -20 $D/build_flat.log >> $L; stop "flat build failed"; }
G=$(docker image inspect -f "{{.GraphDriver.Data.UpperDir}}:{{.GraphDriver.Data.LowerDir}}" $IMG)
count=$(sudo python3 -I - "$G" <<'PY2'
import os,sys,stat
B=4096; tot=0; n=0; L=[d for d in sys.argv[1].split(':') if d]
for d in L:
    for root,ds,fs in os.walk(d):
        for name in ds+fs:
            st=os.lstat(os.path.join(root,name)); n+=1
            tot+=max(1,-(-(st.st_size if stat.S_ISREG(st.st_mode) else 0)//B))*B
print(tot, n)
PY2
)
say "BUILT: $IMG, platform count $(python3 -c "print(round(${count% *}/1e9,2))") GB, ${count#* } entries (limits 55 GB, 3.3M)"
[ "${count% *}" -lt 55000000000 ] || stop "image over 55 GB by the platform count"
sed "s/--pull=always/--pull=never/" ~/positronic/docker/test_policy_image.sh > $D/test_local.sh
bash $D/test_local.sh --gpu $IMG > $D/start_test.log 2>&1 || { tail -40 $D/start_test.log >> $L; stop "start test failed"; }
say "START TEST: $(grep -m1 'answered' $D/start_test.log | cut -c1-150)"
wait $setup || stop "eval setup failed (setup.log)"
run() {  # $1 = A|B, $2 = episode file, $3 = extra docker flags
  docker rm -f rt >/dev/null 2>&1
  docker run -d --name rt --gpus all -p 8000:8000 $3 $IMG >/dev/null || stop "run $1"
  for _ in $(seq 200); do curl -sf -X POST localhost:8000/api/v1/keepalive >/dev/null && break; sleep 5; done
  say "[$1] router ready"
  local pids=() k=0
  for ep in $(python3 -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))))" $2); do
    k=$((k+1))
    (cd ~/positronic && UV_NO_SYNC=1 timeout 1500 uv run positronic eval run --eval=.sim.molmo.benchmarks \
      "--eval.episode_paths=[\"$ep\"]" --policy=.remote --policy.address.host=localhost --policy.address.port=8000 \
      --output_dir=$HOME/evals/rt_${1}_$k) > $HOME/evals/rt_${1}_$k.log 2>&1 &
    pids+=($!)
    [ $((k % 4)) = 0 ] && { wait "${pids[@]}"; pids=(); }
  done
  wait "${pids[@]}" 2>/dev/null
  docker logs rt > $D/router_$1.log 2>&1
  local ok=0 n=0
  for f in $HOME/evals/rt_${1}_*/*/*/static.json; do n=$((n+1)); python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('eval.success') else 1)" $f && ok=$((ok+1)); done
  say "[$1] $n of 8 episodes finished, $ok succeeded; router: $(grep -E '\[router\] (first task|FLUX serves|.*still open|flux ready|v3 ready|.*did not)' $D/router_$1.log | sed 's/^.*\[router\] //' | tr '\n' '|' | cut -c1-400)"
  say "[$1] served: v3 sessions $(grep -c 'ROUTER_TASK' $D/router_$1.log), flux sessions $(grep -c 'Rule counts' $D/router_$1.log)"
}
run A $D/eps_a.json ""
run B $D/eps_b.json "-e ROUTER_TEST_SWITCH=1"
docker rm -f rt >/dev/null 2>&1
say "ALL DONE"; touch $D/ALL_DONE

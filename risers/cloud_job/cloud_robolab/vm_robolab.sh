#!/usr/bin/env bash
# The job of the cloud VM risers-robolab: the submitted image v3-jpeg on 12 RoboLab tasks, 4 of each RoboLab
# category (task lists s1.json, s2.json, s3.json). One policy server on port 8001. Three eval processes at a time,
# one per task list, each with its own Isaac Sim. The eval client is positronic main (~/positronic).
# Log: ~/cloud_robolab/vm.log (Central European Time). GPU every 30 s: ~/cloud_robolab/gpu.log.
# It writes ~/cloud_robolab/ALL_DONE at the end, also when it stops on an error.
set -uo pipefail
D=$HOME/cloud_robolab
export TZ=Europe/Berlin PATH=$HOME/.local/bin:$PATH UV_PYTHON_PREFERENCE=only-managed DEBIAN_FRONTEND=noninteractive
REPO=docker.io/denistonantony/molmobot-img-droid
read -r NAME DIGEST < "$D/images"
PORT=8001
say() { echo "$(date '+%F %T') $*" >> "$D/vm.log"; }
stop() { say "STOP: $*"; touch "$D/ALL_DONE"; exit 1; }
episodes() { find "$HOME"/evals/rl_"$1"_p* -name static.json 2>/dev/null | wc -l; }

remaining() {  # the tasks of a list file that a run has not finished, as JSON
  python3 -I - "$1" "$2" "$D/skip_$2.txt" <<'PY'
import glob, json, os, sys
tasks = json.load(open(sys.argv[1]))
done = set()
for f in glob.glob(os.path.expanduser(f'~/evals/rl_{sys.argv[2]}_p*/**/static.json'), recursive=True):
    done.add(json.load(open(f)).get('eval.task'))
skip = set(open(sys.argv[3]).read().split()) if os.path.exists(sys.argv[3]) else set()
print(json.dumps([t for t in tasks if t not in done and t not in skip]))
PY
}

stream() {  # one eval process at a time for a task list; a stopped part continues with the tasks that are left
  local run=$1 set=$2 part=0 rem n first before rc idle=0
  declare -A tries=()
  say "[$run] START"
  while :; do
    rem=$(remaining "$set" "$run")
    n=$(python3 -I -c 'import json, sys; print(len(json.loads(sys.argv[1])))' "$rem")
    [ "$n" = 0 ] && break
    first=$(python3 -I -c 'import json, sys; print(json.loads(sys.argv[1])[0])' "$rem")
    tries[$first]=$(( ${tries[$first]:-0} + 1 ))
    if [ "${tries[$first]}" -gt 2 ]; then
      echo "$first" >> "$D/skip_$run.txt"
      say "[$run] SKIP $first: it did not finish in 2 tries"
      continue
    fi
    part=$((part + 1))
    while [ -e "$HOME/evals/rl_${run}_p$part" ]; do part=$((part + 1)); done
    before=$(episodes "$run")
    say "[$run] part $part: $n tasks $rem"
    (cd "$HOME/positronic" && uv run --locked positronic eval run --eval=.sim.robolab.benchmark "--eval.task=$rem" \
      --policy=.remote --policy.address.host=localhost "--policy.address.port=$PORT" \
      --output_dir="$HOME/evals/rl_${run}_p$part") > "$HOME/evals/rl_${run}_p$part.runner.log" 2>&1
    rc=$?
    [ "$rc" = 0 ] || say "[$run] part $part stopped with code $rc"
    if [ "$(episodes "$run")" = "$before" ]; then
      idle=$((idle + 1))
      tail -n 25 "$HOME/evals/rl_${run}_p$part.runner.log" >> "$D/vm.log"
      [ "$idle" -lt 2 ] || { say "[$run] STOP: 2 parts in a row recorded no episode"; break; }
    else
      idle=0
    fi
    sleep 10
  done
  say "[$run] STREAM DONE: $(episodes "$run") episodes"
}

mkdir -p "$HOME/evals"
say "SETUP: system libraries for Isaac Sim"
{ sudo apt-get update -q && sudo -E apt-get install -y -q git-lfs build-essential libatomic1 libegl1 libfontconfig1 \
    libgl1 libglib2.0-0t64 libglu1-mesa libsm6 libvulkan1 libx11-6 libxcursor1 libxext6 libxi6 libxinerama1 \
    libxrandr2 libxt6 vulkan-tools; } >> "$D/setup.log" 2>&1 || stop "apt install failed (setup.log)"
# The CUDA image has the compute part of the driver only. Isaac Sim renders with Vulkan, so it needs the graphics
# part of the same driver version.
ver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
comp=$(dpkg-query -W -f='${Package}\n' 2>/dev/null | grep -E "^libnvidia-compute-${ver%%.*}(-server)?$" | head -1)
[ -n "$comp" ] || stop "driver $ver has no libnvidia-compute package, so the graphics library cannot be matched"
gl=${comp/compute/gl}
glv=$(dpkg-query -W -f='${Version}' "$comp")
say "SETUP: driver $ver ($comp $glv); install $gl"
sudo -E apt-get install -y -q "$gl=$glv" >> "$D/setup.log" 2>&1 || stop "install of $gl=$glv failed (setup.log)"
[ "$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)" = "$ver" ] \
  || stop "nvidia-smi does not show driver $ver after the install"
say "SETUP: Vulkan: $(vulkaninfo --summary 2>&1 | grep -m2 -E 'deviceName|driverVersion' | tr -s ' ' | tr '\n' ' ')"

say "SETUP: image pull; uv sync of positronic, then of RoboLab and Isaac Sim (about 15 GB)"
docker pull -q "$REPO@$DIGEST" > "$D/pull.log" 2>&1 &
pull=$!
(cd "$HOME/positronic" && UV_PYTHON=3.13 uv sync --locked) >> "$D/setup.log" 2>&1 || stop "uv sync failed (setup.log)"
(cd "$HOME/positronic" && uv run --locked python - <<'PY'
import subprocess

from positronic.simulator.robolab import launcher

src = launcher._ensure_robolab_src()
subprocess.run(['uv', 'sync', '--project', str(src), '--python', launcher._ROBOLAB_PYTHON,
                '--extra', launcher._ROBOLAB_ISAAC_EXTRA], check=True)
PY
) >> "$D/setup.log" 2>&1 || stop "the RoboLab environment failed (setup.log)"
wait "$pull" || stop "pull of $NAME failed (pull.log)"
say "SETUP: done; disk $(df -h --output=used,avail / | tail -1 | tr -s ' ')"

(while :; do echo "$(date +%T) $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)" >> "$D/gpu.log"; sleep 30; done) &
gpu_watch=$!
docker rm -f srv >/dev/null 2>&1
docker run -d --name srv --gpus all -p "$PORT:8000" "$REPO@$DIGEST" > /dev/null || stop "the server did not start"
ready=false
for _ in $(seq 120); do
  curl -sf -X POST "http://localhost:$PORT/api/v1/keepalive" > /dev/null && { ready=true; break; }
  [ -n "$(docker ps -q -f name=srv)" ] || break
  sleep 5
done
[ "$ready" = true ] || { docker logs --tail 30 srv >> "$D/vm.log" 2>&1; stop "the $NAME server did not answer"; }
say "SETUP: $NAME server ready, GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) used"

say "STREAMS: 3 eval processes start, 2 min apart"
pids=()
for k in 1 2 3; do
  stream "${NAME}_s$k" "$D/s$k.json" &
  pids+=($!)
  [ "$k" = 3 ] || sleep 120
done
wait "${pids[@]}"
docker logs srv > "$HOME/evals/rl_$NAME.server.log" 2>&1
for d in "$HOME"/evals/rl_*_p*/; do
  (cd "$HOME/positronic" && uv run --locked positronic eval timing-report --run_dir="$d") > "${d%/}.timing.txt" 2>&1
done
kill "$gpu_watch" 2>/dev/null
say "ALL DONE: $(find "$HOME"/evals/rl_*_p* -name static.json 2>/dev/null | wc -l) episodes"
touch "$D/ALL_DONE"

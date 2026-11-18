#!/usr/bin/env bash
# Make a fresh L40S, copy flux_submit, build the image, then wait for the user's push (VM guard 3 h).
J=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/cloud_job
LOG=$J/cloud_flux_submit.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
sed -i "s/'+120', 'budget guard: FLUX submit build VM powers off after 2 h'/'+180', 'budget guard: FLUX push VM powers off after 3 h'/" "$J/create_fluxsubmit_vm.sh"
start=$(date +%s)
bash "$J/create_fluxsubmit_vm.sh"
tail -1 "$LOG" | grep -q 'VM running' && [ "$(stat -c %Y "$J/flux_ip")" -ge "$start" ] || { say "BUILD2: no VM"; exit 1; }
IP=$(cat "$J/flux_ip"); SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "ubuntu@$IP")
for i in $(seq 60); do "${SSH[@]}" 'docker info >/dev/null 2>&1 && nvidia-smi >/dev/null' 2>/dev/null && break; sleep 20; done
rsync -rt --exclude __pycache__ -e "ssh -o BatchMode=yes" /home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/flux_submit/ "ubuntu@$IP:flux_submit/" || { say "BUILD2: copy failed"; exit 1; }
"${SSH[@]}" 'docker build -t denistonantony/flux3-retry-droid:v1 ~/flux_submit > ~/docker_build.log 2>&1 && docker image inspect -f "{{.Id}}" denistonantony/flux3-retry-droid:v1' >> "$LOG" 2>&1 \
  && say "BUILD2: READY FOR PUSH at $IP" || say "BUILD2: build failed"

#!/usr/bin/env bash
# Save the test images of the open/close action experts to the SSD, and keep them on this PC.
# The images go to a local image registry whose storage is on the SSD (docker_images/registry). All test images are
# one base image (v1, about 30 GB) plus 2 small layers (the code and the expert, about 1.1 GB). The registry keeps
# each layer once, so the base is stored once and each test image adds about 1.1 GB. (`docker save` is not used: it
# writes a 30 GB copy of each image to the PC disk first.) Restore: docker_images/RESTORE.txt on the SSD.
# The checkpoint queue (risers-ckqueue, started 9 Nov 15:00) removes the tag of each image after its test. The
# registry tag (localhost:5000/...) is a second tag, so the image stays on this PC, and this script puts the first
# tag back. Run under systemd-run (unit risers-imgsave). Log: cloud_job/save_images.log.
set -uo pipefail
P=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition
J=$P/cloud_job
LOG=$J/save_images.log
QLOG=$J/checkpoint_queue.log
OUT="/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/molmobot_openclose_2026-11-09/docker_images"
STORE=$OUT/registry
LIST=$OUT/saved_images.txt
REPO=denistonantony/molmobot-img-droid
REG=localhost:5000/molmobot-img-droid
STEPS="2400"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
exists() { docker image inspect "$1" >/dev/null 2>&1; }

start_registry() {
  docker inspect -f '{{.State.Running}}' risers-registry 2>/dev/null | grep -q true && return 0
  docker rm -f risers-registry >/dev/null 2>&1
  docker run -d --name risers-registry -p 127.0.0.1:5000:5000 -v "$STORE:/var/lib/registry" registry:2 >/dev/null || return 1
  for _ in $(seq 30); do curl -sf http://127.0.0.1:5000/v2/ >/dev/null && return 0; sleep 1; done
  return 1
}

save() {  # local image, name in the registry
  local id
  id=$(docker image inspect "$1" --format '{{.Id}}')
  grep -q "^$2 $id " "$LIST" 2>/dev/null && return 0
  start_registry || { say "STOP: the registry does not start"; exit 1; }
  docker tag "$1" "$REG:$2"
  say "SAVE $1 -> SSD as $2"
  if docker push -q "$REG:$2" >> "$LOG" 2>&1; then
    # A rebuilt image replaces the line of its old version.
    [ -f "$LIST" ] && sed -i "/^$2 /d" "$LIST"
    echo "$2 $id $(date '+%F %T')" >> "$LIST"
    say "saved $2 (registry on the SSD: $(du -sh "$STORE" | cut -f1))"
  else
    say "save of $1 failed"
  fi
}

restore_tags() {  # put back each first tag that the queue removed
  for s in $STEPS; do
    if exists "$REG:v5-step$s" && ! exists "$REPO:v5-step$s"; then
      docker tag "$REG:v5-step$s" "$REPO:v5-step$s" && say "tag v5-step$s is back on this PC"
    fi
  done
}

mkdir -p "$STORE"
[ -s "$OUT/registry_image.tar" ] || docker save registry:2 -o "$OUT/registry_image.tar"
say "START: base once, then the test images"
save "$REPO:v1" v1
save "$REPO:v5-mid1000" v5-mid1000
save "$REPO:v5-openclose" v5-openclose
exists "$REPO:v5-regrasp" && save "$REPO:v5-regrasp" v5-regrasp
exists "$REPO:v5-flow10" && save "$REPO:v5-flow10" v5-flow10
exists "$REPO:v5-touch" && save "$REPO:v5-touch" v5-touch

for s in $STEPS; do
  tag=$REPO:v5-step$s
  until exists "$tag" || exists "$REG:v5-step$s"; do
    restore_tags
    if grep -q "build of step $s failed" "$QLOG" 2>/dev/null || ! systemctl --user is-active -q risers-ckqueue; then
      say "no image for step $s (the queue did not build it); next"
      continue 2
    fi
    sleep 60
  done
  exists "$tag" || docker tag "$REG:v5-step$s" "$tag"
  save "$tag" "v5-step$s"
  restore_tags
done

# Wait for the end of the queue, then keep only the first tags on this PC.
while systemctl --user is-active -q risers-ckqueue; do restore_tags; sleep 60; done
restore_tags
for s in $STEPS; do
  if exists "$REPO:v5-step$s"; then
    for extra in "$REG:v5-step$s" "$REPO:v5-step$s-kept"; do exists "$extra" && docker rmi "$extra" >> "$LOG" 2>&1; done
  fi
done
for name in v1 v5-mid1000 v5-openclose v5-regrasp v5-flow10 v5-touch; do exists "$REG:$name" && docker rmi "$REG:$name" >> "$LOG" 2>&1; done
docker rm -f risers-registry >/dev/null 2>&1
say "ALL SAVED: $(wc -l < "$LIST") images on the SSD (list: docker_images/saved_images.txt); the images stay on this PC"

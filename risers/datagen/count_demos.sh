#!/usr/bin/env bash
# Count the saved demos of each open/close config (one right shoulder video for each demo).
# Usage: bash count_demos.sh
here="$(cd "$(dirname "$0")" && pwd)"
total=0
for config in RisersOpen RisersClose RisersOpenMore RisersCloseMore \
              RisersOpenHardIthor RisersOpenHardProcthor RisersOpenHardProcObja RisersOpenHardHolodeck \
              RisersCloseHardIthor RisersCloseHardProcthor RisersCloseHardProcObja RisersCloseHardHolodeck; do
  n=0
  [ -d "$here/output/$config" ] && n=$(find "$here/output/$config" -name '*right_shoulder_camera*.mp4' | wc -l)
  printf '%-26s %5d\n' "$config" "$n"
  total=$((total + n))
done
printf '%-26s %5d\n' total "$total"

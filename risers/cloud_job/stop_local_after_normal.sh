#!/usr/bin/env bash
# Stop the local overnight run when it reaches the hard configs: the cloud VM makes the hard set.
# Run under systemd-run. It waits for the "start RisersOpenHard" line, then stops the run and its worker scope.
log=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/datagen/logs/overnight_1108.log
out=/home/antonlucy/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/datagen/output
until grep -q "start RisersOpenHard" "$log" 2>/dev/null; do
  systemctl --user is-active -q risers-datagen-1108 || { echo "$(date '+%F %T') local run ended by itself"; exit 0; }
  sleep 20
done
systemctl --user stop risers-datagen-1108
for unit in $(systemctl --user list-units --type=scope --no-legend 'risers-RisersOpenHard*' | awk '{print $1}'); do
  systemctl --user stop "$unit"
done
for dir in "$out"/RisersOpenHard*; do
  [ -e "$dir" ] && mv "$dir" "${dir}_local_stopped"
done
echo "$(date '+%F %T') stopped the local run before the hard configs"

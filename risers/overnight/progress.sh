#!/usr/bin/env bash
# Overnight test progress with estimated finish times. Watch it with:
#   watch -n 60 bash ~/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/overnight/progress.sh
D=$(cd "$(dirname "$0")" && pwd)
N=28
DEFAULT_MIN=5.3   # minutes per episode until a run has finished 2 episodes
now=$(date +%s)
hm() { local s=$1; [ "$s" -lt 0 ] && s=0; printf '%dh%02dm' $((s / 3600)) $((s % 3600 / 60)); }
field() { awk -F'\t' -v r="$1" -v st="$2" '$1 == r && $3 == st {t = $4} END {print t}' "$D/status.tsv" 2>/dev/null; }
count() { find "$HOME"/evals/ovn_"$1"_p* -mindepth 3 -maxdepth 3 -name static.json 2>/dev/null | wc -l; }

per_ep=$DEFAULT_MIN
echo "Overnight tests (MolmoBot-Img, 28 hard episodes per run)   now $(date +%H:%M)"
echo
left_total=0
for run in base play12 flow5 play12_flow5 grip40; do
  [ "$run" = base ] && echo "Step 1: speed settings"
  [ "$run" = grip40 ] && echo "Step 2: gripper rule (on the best step-1 setting)"
  start=$(field "$run" running); end=$(field "$run" done); done_n=$(count "$run")
  if [ -n "$end" ]; then
    printf '  %-13s finished  %2d/%d  took %s\n' "$run" "$done_n" "$N" "$(hm $((end - start)))"
    per_ep=$(awk -v s=$((end - start)) -v n="$done_n" 'BEGIN {printf "%.2f", (n > 0 ? s / n / 60 : 5.3)}')
  elif [ -n "$start" ]; then
    el=$((now - start))
    [ "$done_n" -ge 2 ] && per_ep=$(awk -v s="$el" -v n="$done_n" 'BEGIN {printf "%.2f", s / n / 60}')
    left=$(awk -v m="$per_ep" -v n=$((N - done_n)) 'BEGIN {printf "%d", m * n * 60}')
    left_total=$((left_total + left))
    printf '  %-13s RUNNING   %2d/%d  running %s, about %s left\n' "$run" "$done_n" "$N" "$(hm "$el")" "$(hm "$left")"
  else
    left=$(awk -v m="$per_ep" -v n="$N" 'BEGIN {printf "%d", m * n * 60 + 120}')
    left_total=$((left_total + left))
    printf '  %-13s waiting         about %s\n' "$run" "$(hm "$left")"
  fi
done
echo "Step 3: top-team videos (Claude does it while step 2 runs)"
echo
if grep -q "ALL RUNS DONE" "$D/overnight.log" 2>/dev/null; then
  echo "All runs are finished."
else
  echo "All runs finish at about $(date -d "@$((now + left_total))" '+%a %H:%M') ($(hm "$left_total") from now)"
fi
echo "Free memory: $(free -h | awk '/^Mem/ {print $7}')   Free disk: $(df -h --output=avail ~ | tail -1 | tr -d ' ')"
echo
echo "Latest events:"
tail -4 "$D/overnight.log" 2>/dev/null | sed 's/^/  /'

#!/usr/bin/env bash
# Test progress with estimated finish times. Watch it with:
#   watch -n 60 bash ~/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/tests_1107/progress.sh
D=$(cd "$(dirname "$0")" && pwd)
declare -A N=([frz_now]=19 [frz_both]=19 [hard_both]=28 [frz_word]=19 [hard_flow3]=28 [frz_flow3]=19 [frz_still3]=19 [hard_still3]=28)
declare -A MIN=([frz_now]=6.5 [frz_both]=6.0 [hard_both]=5.0 [frz_word]=6.5 [hard_flow3]=5.0 [frz_flow3]=6.0 [frz_still3]=5.0 [hard_still3]=5.0)   # minutes per episode, first guess
declare -A WHAT=(
  [frz_now]="19 frozen eps, 60% settings"
  [frz_both]="19 frozen eps, wording + 3 rounds"
  [hard_both]="28 hard eps, wording + 3 rounds"
  [frz_word]="19 frozen eps, wording only"
  [hard_flow3]="28 hard eps, 3 rounds only"
  [frz_flow3]="19 frozen eps, 3 rounds only"
  [frz_still3]="19 frozen eps, 3 rounds + still rule"
  [hard_still3]="28 hard eps, 3 rounds + still rule"
)
now=$(date +%s)
hm() { local s=$1; [ "$s" -lt 0 ] && s=0; printf '%dh%02dm' $((s / 3600)) $((s % 3600 / 60)); }
field() { awk -F'\t' -v r="$1" -v st="$2" '$1 == r && $3 == st {t = $4} END {print t}' "$D/status.tsv" 2>/dev/null; }
count() { find "$HOME"/evals/t7_"$1"_p* -mindepth 3 -maxdepth 3 -name static.json 2>/dev/null | wc -l; }

echo "Local tests of 7 November (MolmoBot-Img on the PC)   now $(date +%H:%M)"
echo
left_total=0
for run in frz_now frz_both hard_both frz_word hard_flow3 frz_flow3 frz_still3 hard_still3; do
  n=${N[$run]}
  start=$(field "$run" running); end=$(field "$run" done); done_n=$(count "$run")
  if [ -n "$end" ]; then
    printf '  %-10s %-34s finished  %2d/%d  took %s\n' "$run" "${WHAT[$run]}" "$done_n" "$n" "$(hm $((end - start)))"
  elif [ -n "$start" ]; then
    el=$((now - start))
    per=${MIN[$run]}
    [ "$done_n" -ge 2 ] && per=$(awk -v s="$el" -v k="$done_n" 'BEGIN {printf "%.2f", s / k / 60}')
    left=$(awk -v m="$per" -v k=$((n - done_n)) 'BEGIN {printf "%d", m * k * 60}')
    left_total=$((left_total + left))
    printf '  %-10s %-34s RUNNING   %2d/%d  running %s, about %s left\n' "$run" "${WHAT[$run]}" "$done_n" "$n" "$(hm "$el")" "$(hm "$left")"
  else
    left=$(awk -v m="${MIN[$run]}" -v k="$n" 'BEGIN {printf "%d", m * k * 60 + 120}')
    left_total=$((left_total + left))
    printf '  %-10s %-34s waiting         about %s\n' "$run" "${WHAT[$run]}" "$(hm "$left")"
  fi
done
echo
if grep -q "ALL RUNS DONE (still-arm rule)" "$D/tests.log" 2>/dev/null; then
  echo "All runs are finished. Results: $D/results.md"
else
  echo "All runs finish at about $(date -d "@$((now + left_total))" '+%a %H:%M') ($(hm "$left_total") from now)"
fi
echo "Free memory: $(free -h | awk '/^Mem/ {print $7}')   Free disk: $(df -h --output=avail ~ | tail -1 | tr -d ' ')"
echo
echo "Latest events:"
tail -4 "$D/tests.log" 2>/dev/null | sed 's/^/  /'

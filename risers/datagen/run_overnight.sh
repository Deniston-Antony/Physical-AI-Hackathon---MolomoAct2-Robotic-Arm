#!/usr/bin/env bash
# Generate the overnight demonstration set, one task type after another.
# Each task type runs in its own systemd scope. If the memory monitor (systemd-oomd) stops it, only that
# scope stops: VS Code and this loop continue. A failed task type runs again once with 2 workers.
# Usage: bash run_overnight.sh            (all task types)
#        bash run_overnight.sh RisersOpen RisersClose   (only these)
here="$(cd "$(dirname "$0")" && pwd)"
configs=("$@")
if [ ${#configs[@]} -eq 0 ]; then
  configs=(RisersPick RisersPickObjaverse RisersPickAndPlace RisersNextTo RisersColor \
           RisersOpen RisersClose RisersPickAndPlaceObjaverse)
fi
mkdir -p "$here/logs"

run() {  # config, workers, log
  RISERS_WORKERS="$2" systemd-run --user --scope --quiet --collect --unit="risers-$1-$(date +%s)" \
    bash "$here/run_datagen.sh" "$1" > "$3" 2>&1
}

for config in "${configs[@]}"; do
  log="$here/logs/$config.log"
  echo "$(date '+%F %T') start $config (log: $log)"
  if run "$config" 4 "$log"; then
    echo "$(date '+%F %T') done  $config: $(grep -a 'Success count' "$log" | tail -1)"
    continue
  fi
  retry="$here/logs/$config.retry.log"
  echo "$(date '+%F %T') FAILED $config, see $log. Retry with 2 workers (log: $retry)"
  if run "$config" 2 "$retry"; then
    echo "$(date '+%F %T') done  $config: $(grep -a 'Success count' "$retry" | tail -1)"
  else
    echo "$(date '+%F %T') FAILED again $config, see $retry"
  fi
done
echo "$(date '+%F %T') all finished"

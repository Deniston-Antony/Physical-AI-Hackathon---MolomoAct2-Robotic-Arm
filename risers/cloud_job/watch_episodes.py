"""Print one line when each local test episode of the open/close job ends, and each new line of the job logs.

The episodes that ended before the start are printed first. Stop with Ctrl+C.
Usage: ~/molmobot_src/venv/bin/python cloud_job/watch_episodes.py
"""

import importlib.util
import json
import re
import time
from pathlib import Path

P = Path(__file__).resolve().parent.parent
D = P / 'tests_1108'
J = P / 'cloud_job'
spec = importlib.util.spec_from_file_location('summarize', D / 'summarize.py')
summ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summ)

# Run name, episode set, label, baseline run, baseline label.
RUNS = [
    ('mid1000_open', 'open30.json', 'step-1000 model, open', 'op_pull', 'v4+pull'),
    ('v5_open', 'open30.json', 'final model, open', 'op_pull', 'v4+pull'),
    ('v5_close', 'close15.json', 'final model, hard close', 'img_v4', 'v4'),
    ('v5_closen', 'closedatagen15.json', 'final model, normal close', None, ''),
] + [(f'op_step{s}', 'open30.json', f'step-{s} model, open', 'op_pull', 'v4+pull')
     for s in (2400, 2200, 2000, 1800, 1600, 1400, 1200, 800, 600, 400, 200)]
LOGS = [J / 'finish_job.log', J / 'after_training.log', J / 'checkpoint_queue.log']
DATED = re.compile(r'^\d{4}-\d\d-\d\d ')


def stamp() -> str:
    return time.strftime('%H:%M')


def main() -> None:
    seen: set[tuple[str, str]] = set()
    log_lines = {log: 0 for log in LOGS}
    sets = {name: json.loads((D / name).read_text()) for name in {r[1] for r in RUNS}}
    bases = {r[3]: summ.episodes(r[3]) for r in RUNS if r[3]}
    print(f'{stamp()} watching the local tests and the job logs (Ctrl+C to stop)', flush=True)
    while True:
        for run, set_name, label, base_run, base_label in RUNS:
            try:
                eps = summ.episodes(run)
            except Exception:  # an episode folder that is being written
                continue
            episodes = sets[set_name]
            for e in episodes:
                x = eps.get(e['path'])
                if x is None or (run, e['path']) in seen:
                    continue
                seen.add((run, e['path']))
                res = f"OK {x['time']:.1f} s" if x['ok'] else 'no'
                base = bases.get(base_run, {}).get(e['path'])
                old = f" | {base_label}: {'OK' if base['ok'] else 'no'}" if base else ''
                solved = sum(v['ok'] for v in eps.values())
                print(f"{stamp()} {label}: #{e['board_index']} {e['task']} -> {res}{old} | {solved}/{len(eps)} solved, "
                      f"{len(eps)}/{len(episodes)} done", flush=True)
        for log in LOGS:
            if not log.exists():
                continue
            lines = log.read_text(errors='replace').splitlines()
            for line in lines[log_lines[log]:]:
                if DATED.match(line):
                    print(f'{stamp()} [{log.stem}] {line[:200]}', flush=True)
            log_lines[log] = len(lines)
        time.sleep(20)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

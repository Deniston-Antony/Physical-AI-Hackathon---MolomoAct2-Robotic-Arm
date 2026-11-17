"""Write a markdown table of the local open-task tests of the saved action experts (stdout).

Each model ran the 30 open episodes of tests_1108/open30.json with the v4 rules plus the open pull.
Usage: ~/molmobot_src/venv/bin/python -I cloud_job/checkpoint_table.py > tests_1108/results_checkpoints.md
"""

import importlib.util
import json
import time
from pathlib import Path

P = Path(__file__).resolve().parent.parent
D = P / 'tests_1108'
spec = importlib.util.spec_from_file_location('summarize', D / 'summarize.py')
summ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summ)

STEPS = [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400]


def run_name(step: int) -> str:
    return 'mid1000_open' if step == 1000 else f'op_step{step}'


def main() -> None:
    episodes = json.loads((D / 'open30.json').read_text())
    cols = [('v4 + pull', summ.episodes('op_pull'))] + [(f'step {s}', summ.episodes(run_name(s))) for s in STEPS]
    cols = [(name, eps) for name, eps in cols if eps]
    print('# Local tests of the saved open/close action experts: open tasks\n')
    print(f'Updated {time.strftime("%Y-%m-%d %H:%M")}. The 30 open episodes of the board (tests_1108/open30.json), on '
          'this PC. Rules of all runs: the v4 flags plus the open pull. "v4 + pull" uses the original action expert.\n')
    print('| Model | Solved | Episodes done | Open datagen | Open hard |')
    print('|---|---|---|---|---|')
    for name, eps in cols:
        part = {}
        for group in ('open datagen', 'open hard'):
            sel = [e for e in episodes if e['group'] == group and e['path'] in eps]
            part[group] = f"{sum(eps[e['path']]['ok'] for e in sel)}/{len(sel)}"
        print(f"| {name} | {sum(v['ok'] for v in eps.values())} | {len(eps)}/{len(episodes)} | {part['open datagen']} | "
              f"{part['open hard']} |")
    print('\n| Board # | Episode | Kind | Top 7 | ' + ' | '.join(name for name, _ in cols) + ' |')
    print('|---|---|---|---|' + '---|' * len(cols))
    for e in episodes:
        cells = []
        for _, eps in cols:
            x = eps.get(e['path'])
            cells.append('' if x is None else (f"OK {x['time']:.1f} s" if x['ok'] else 'no'))
        print(f"| {e['board_index']} | {e['task']} | {e['kind']} | {e['top7_solved']}/7 | " + ' | '.join(cells) + ' |')


if __name__ == '__main__':
    main()

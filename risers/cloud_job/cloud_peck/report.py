"""Report of the test of the late-close rule of v3 (cloud_job/cloud_peck.sh), against the earlier cloud runs of v3.

Usage: ~/molmobot_src/venv/bin/python cloud_job/cloud_peck/report.py > tests_1108/results_cloud_peck.md
Reads the runs conc_late1, conc_late and conc_v3b (13 Nov), conc_v3jpeg (11 Nov) and conc_v3 (10 Nov) in ~/evals, their
timing reports (*.timing.txt), the server logs and the board results of v3.
"""

import glob
import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cloud_flux'))
import report as base  # noqa: E402

IMAGES = [('v3 + late-close rule, 1 deferral', 'conc_late1'), ('v3 + late-close rule, each time', 'conc_late'),
          ('v3 as it is (13 Nov)', 'conc_v3b'), ('v3 + JPEG (11 Nov, H100)', 'conc_v3jpeg'), ('v3 (10 Nov, L40S)', 'conc_v3')]
FPS = 15
# A closing shorter than this (s) is not counted. A closed gripper with nothing in it reads this or more.
SHORT_S, EMPTY_GRIP = 0.4, 0.9


def signal(d: Path, name: str) -> tuple[np.ndarray, np.ndarray]:
    t = pq.read_table(d / f'{name}.parquet')
    value = np.array(t.column('value').to_pylist(), dtype=float)
    return np.array(t.column('ts.emitted.world').to_pylist(), dtype=float) / 1e9, value.reshape(len(value), -1)[:, 0]


def closings(d: Path) -> tuple[int, int, float]:
    """The closings of one episode on nothing and on something, and the time (s) the gripper was closed on nothing."""
    tg, g = signal(d, 'target_grip')
    to, o = signal(d, 'grip')
    if not len(tg):
        return 0, 0, 0.0
    cmd = np.interp(to, tg, g)
    empty = held = 0
    wasted = 0.0
    i = 0
    while i < len(to):
        if cmd[i] <= 0.5:
            i += 1
            continue
        j = i
        while j + 1 < len(to) and cmd[j + 1] > 0.5:
            j += 1
        part = o[i:j + 1]
        if to[j] - to[i] >= SHORT_S:
            if np.median(part[len(part) // 2:]) >= EMPTY_GRIP:
                empty += 1
                wasted += to[j] - to[i]
            else:
                held += 1
        i = j + 1
    return empty, held, wasted


def run_closings(run: str) -> dict[str, tuple[int, int, float, bool, float]]:
    out = {}
    for f in glob.glob(str(base.EVALS / f't8_{run}_ps*' / '*' / '*' / 'static.json')):
        s = json.loads(Path(f).read_text())
        group = 'pick' if 'Pick' in s['molmo.task_config'] else 'open' if 'Open' in s['molmo.task_config'] else 'close'
        out[f] = (*closings(Path(f).parent), bool(s.get('eval.success')), group)
    return out


def main() -> None:
    summ = base.load('summarize', base.P / 'tests_1108' / 'summarize.py')
    board = base.load('board_by_set', base.RUNS / 'board_by_set.py')
    sets = json.loads((base.RUNS / 'episode_sets.json').read_text())
    ref = board.successes(str(base.RUNS / 'molmobot_img_v3' / 'result.json'), sets)[0]
    eps = json.loads((Path(__file__).resolve().parent / 'conc40.json').read_text())
    images = [(label, run) for label, run in IMAGES if glob.glob(str(base.EVALS / f't8_{run}_ps*'))]
    runs = {label: summ.episodes(run) for label, run in images}
    print('# v3 with the late-close rule')
    print()
    print('13 Nov: image v3 plays actions 4 to 15 of each chunk of 16. In a replay of 6 recorded episodes, 55% of the '
          'chunks for an open gripper close it, and for 21% the close starts in actions 12 to 15: most of those are '
          'chance (1 or 2 of 6 chunks of the same observation). The gripper then closes on nothing, about each 2 s. '
          'With the late-close rule, a chunk closes an open gripper only when the close starts before action 12; a later '
          'close is deferred (the gripper stays open for the chunk). "1 deferral": after one deferred chunk, the next '
          'late close goes out. "Each time": each late close is deferred. The servers of 13 Nov share one GPU, with 4 '
          'eval processes at a time each, on the 40 episodes of the tests of 10 and 11 Nov.')
    print()
    print('| Group | Episodes | ' + ' | '.join(label for label, _ in images) + ' | Board v3 |')
    print('|---|---|' + '---|' * (len(images) + 1))
    for group, name in list(base.GROUPS.items()) + [('All', '**All**')]:
        sel = [e for e in eps if group in ('All', e['group'])]
        cells = []
        for label, _ in images:
            done = [e for e in sel if e['path'] in runs[label]]
            ok = sum(runs[label][e['path']]['ok'] for e in done)
            cells.append(f'{ok}' + ('' if len(done) == len(sel) else f' ({len(done)} done)'))
        print(f'| {name} | {len(sel)} | ' + ' | '.join(cells) + f" | {sum(ref[e['board_index']] for e in sel)} |")
    print()
    print('## Gripper closings and time')
    print()
    print('A closing on nothing ends with the gripper fully closed. "Charged" is the time of a model call as the harness '
          'measures it.')
    print()
    print('| Image | Closings on nothing per episode: pick / open / close | Time closed on nothing per episode (s): '
          'pick / open / close | Closings on something per episode | Calls per episode | Charged, median of the streams (ms) '
          '| Median time of a success (s) |')
    print('|---|---|---|---|---|---|---|')
    for label, run in images:
        rows = list(run_closings(run).values())
        def mean(index: int, group: str) -> str:
            sel = [r[index] for r in rows if r[4] == group]
            return f'{statistics.mean(sel):.1f}' if sel else '-'
        calls, p50 = base.charged(run)
        times = [x['time'] for x in runs[label].values() if x['ok']]
        t = f'{statistics.median(times):.1f}' if times else '-'
        held = f'{statistics.mean(r[1] for r in rows):.1f}' if rows else '-'
        per = f'{calls / len(rows):.1f}' if rows and calls else '-'
        ms = f'{statistics.median(p50):.0f}' if p50 else '-'
        print(f"| {label} | {' / '.join(mean(0, g) for g in ('pick', 'open', 'close'))} | "
              f"{' / '.join(mean(2, g) for g in ('pick', 'open', 'close'))} | {held} | {per} | {ms} | {t} |")
    print()
    for name in ('late1', 'late', 'v3b'):
        log = base.EVALS / f'conc_{name}.server.log'
        if log.exists():
            lines = [line for line in log.read_text(errors='replace').splitlines() if 'Late closes so far' in line]
            print(f"- {name}: {lines[-1].split(') ', 1)[-1].strip() if lines else 'no late-close lines in the server log'}")
    print()
    print('## Per episode')
    print()
    print('| Board # | Group | Task | ' + ' | '.join(label for label, _ in images) + ' | Board v3 |')
    print('|---|---|---|' + '---|' * (len(images) + 1))
    for e in sorted(eps, key=lambda e: (e['group'], e['board_index'])):
        cells = []
        for label, _ in images:
            x = runs[label].get(e['path'])
            cells.append('-' if x is None else (f"OK {x['time']:.1f} s" if x['ok'] else 'no'))
        print(f"| {e['board_index']} | {base.GROUPS[e['group']]} | {e['task'][:45]} | " + ' | '.join(cells)
              + f" | {'OK' if ref[e['board_index']] else 'no'} |")


if __name__ == '__main__':
    main()

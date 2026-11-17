"""Report of the board-load test of v3 with JPEG camera frames (cloud_job/cloud_jpeg.sh), against the earlier cloud runs.

Usage: ~/molmobot_src/venv/bin/python cloud_job/cloud_jpeg/report.py > tests_1108/results_cloud_jpeg.md
Reads the runs conc_v3jpeg (11 Nov) and conc_v3, conc_v4, conc_v6, conc_touch (10 Nov) in ~/evals, their timing
reports (*.timing.txt), and the board results of v3 and v4.
"""

import glob
import importlib.util
import json
import os
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parents[1]
RUNS = P / 'competition_runs'
EVALS = Path(os.path.expanduser('~/evals'))
GROUPS = {'FrankaPickHardBench': 'Pick, hard', 'FrankaPickandPlaceDroidMiniBench': 'Pick and place, normal',
          'FrankaOpenDataGenConfig': 'Open, normal', 'FrankaOpenHardBench': 'Open, hard',
          'FrankaCloseDataGenConfig': 'Close, normal', 'FrankaCloseHardBench': 'Close, hard'}
IMAGES = [('v3 + JPEG (11 Nov, H100)', 'conc_v3jpeg'), ('v3, raw frames (11 Nov, H100)', 'conc_v3raw'), ('v3 (10 Nov)', 'conc_v3'), ('v4 (10 Nov)', 'conc_v4'),
          ('v6 (10 Nov)', 'conc_v6'), ('v5-touch (10 Nov)', 'conc_touch')]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def charged(run: str) -> tuple[int, list[float]]:
    calls, p50 = 0, []
    for f in sorted(glob.glob(str(EVALS / f't8_{run}_ps*.timing.txt'))):
        text = Path(f).read_text()
        n = re.search(r'infer calls:\s+(\d+)', text)
        m = re.search(r'infer p50 / p95:\s+([\d.]+) / ([\d.]+) ms', text)
        if n and m:
            calls += int(n[1])
            p50.append(float(m[1]))
    return calls, p50


def jpeg_flags(run: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in glob.glob(str(EVALS / f't8_{run}_ps*/*/*/static.json')):
        value = str(json.loads(Path(f).read_text()).get('inference.policy.server.compress_images'))
        out[value] = out.get(value, 0) + 1
    return out


def main() -> None:
    summ = load('summarize', P / 'tests_1108' / 'summarize.py')
    board = load('board_by_set', RUNS / 'board_by_set.py')
    sets = json.loads((RUNS / 'episode_sets.json').read_text())
    ref = {name: board.successes(str(RUNS / folder / 'result.json'), sets)[0]
           for name, folder in [('v3', 'molmobot_img_v3'), ('v4', 'molmobot_img_v4')]}
    eps = json.loads((HERE / 'conc40.json').read_text())
    images = [(label, run) for label, run in IMAGES if glob.glob(str(EVALS / f't8_{run}_ps*'))]
    runs = {label: summ.episodes(run) for label, run in images}
    print('# v3 with JPEG camera frames: board-load test')
    print()
    print('11 Nov: cloud VM with an H100 GPU (no L40S was free) and 16 CPUs. Two policy servers share the GPU, each with '
          '4 eval processes at a time, as the board does, on the same 40 episodes as the tests of 10 Nov. "v3 + JPEG" is '
          'image v3 with one change: the server asks the client for JPEG frames (quality 90) in place of raw frames. '
          '"v3, raw frames" is image v3 as it is. 10 Nov: cloud VM with an L40S GPU; v3 and v4 each had the GPU alone, '
          'v6 and v5-touch shared it.')
    print()
    print('| Group | Episodes | ' + ' | '.join(label for label, _ in images) + ' | Board v3 | Board v4 |')
    print('|---|---|' + '---|' * (len(images) + 2))
    for group, name in list(GROUPS.items()) + [('All', '**All**')]:
        sel = [e for e in eps if group in ('All', e['group'])]
        cells = []
        for label, _ in images:
            done = [e for e in sel if e['path'] in runs[label]]
            ok = sum(runs[label][e['path']]['ok'] for e in done)
            cells.append(f'{ok}' + ('' if len(done) == len(sel) else f' ({len(done)} done)'))
        boards = [sum(ref[n][e['board_index']] for e in sel) for n in ('v3', 'v4')]
        print(f'| {name} | {len(sel)} | ' + ' | '.join(cells) + ' | ' + ' | '.join(map(str, boards)) + ' |')
    print()
    print('## Time per model call and the image format')
    print()
    print('"Charged" is the time of a model call as the harness measures it: the robot waits this long. '
          '"compress_images" is the value that the episodes recorded from the server handshake.')
    print()
    print('| Image | Calls | Charged p50 per stream (ms) | Median of the streams (ms) | compress_images in the episodes |')
    print('|---|---|---|---|---|')
    for label, run in images:
        calls, p50 = charged(run)
        flags = ', '.join(f'{k}: {v}' for k, v in sorted(jpeg_flags(run).items()))
        median = f'{statistics.median(p50):.0f}' if p50 else '-'
        print(f'| {label} | {calls} | {", ".join(f"{x:.0f}" for x in p50) or "-"} | {median} | {flags or "-"} |')
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
        print(f"| {e['board_index']} | {GROUPS[e['group']]} | {e['task'][:45]} | " + ' | '.join(cells)
              + f" | {'OK' if ref['v3'][e['board_index']] else 'no'} |")


if __name__ == '__main__':
    main()

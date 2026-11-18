"""Report of the FLUX 1-step fast test: 1-step baseline, faster timing, faster timing + retry after a miss.

Usage: ~/molmobot_src/venv/bin/python cloud_job/cloud_flux_fast/report_steps.py > tests_1118/results_cloud_flux_fast.md
Reads the runs conc_fbase1, conc_ffast1, conc_fretry1 (18 Nov), conc_fluxhyb1 and conc_fluxhyb4 (17 Nov) and
conc_v3jpeg in ~/evals, and the board results of v3.
"""

import glob
import json
import statistics
from pathlib import Path

import report as base

IMAGES = [('FLUX 1 step, faster timing', 'conc_ffast1'),
          ('FLUX 1 step, faster + retry', 'conc_fretry1'),
          ('FLUX 1 step (17 Nov)', 'conc_fluxhyb1'),
          ('FLUX 4 steps (17 Nov)', 'conc_fluxhyb4'),
          ('v3 + JPEG', 'conc_v3jpeg')]
FPS = 15
LEAD = {'conc_fbase1': 0.9, 'conc_ffast1': 0.35, 'conc_fretry1': 0.35, 'conc_fluxhyb1': 0.9, 'conc_fluxhyb4': 0.9}


def played(run: str) -> tuple[int, int]:
    files = glob.glob(str(base.EVALS / f't8_{run}_ps*' / '*' / '*' / 'static.json'))
    return len(files), sum(json.loads(Path(f).read_text())['inference.policy.eval.schedule.emitted'] for f in files)


def main() -> None:
    summ = base.load('summarize', base.P / 'tests_1108' / 'summarize.py')
    board = base.load('board_by_set', base.RUNS / 'board_by_set.py')
    sets = json.loads((base.RUNS / 'episode_sets.json').read_text())
    ref = board.successes(str(base.RUNS / 'molmobot_img_v3' / 'result.json'), sets)[0]
    eps = json.loads((base.HERE / 'conc40.json').read_text())
    images = [(label, run) for label, run in IMAGES if glob.glob(str(base.EVALS / f't8_{run}_ps*'))]
    runs = {label: summ.episodes(run) for label, run in images}
    print('# FLUX 3 Action at 1 denoising step: faster timing and a retry after a miss')
    print()
    print('18 Nov: FLUX at 1 denoising step, both cameras, hybrid schedule, full gripper, 24192 MiB cap. '
          '"Faster timing": the next request 0.35 s before the end of a chunk (was 0.9 s) and the arm holds 6 actions '
          'after a pick chunk (was 14); a pick chunk that keeps the gripper open plays 1.25x faster. "Retry": a close '
          'on nothing opens the gripper and lifts it 5 cm; the next close near the miss goes 2 cm deeper (the 2nd '
          'retry also turns the gripper 30 deg); at most 2 retries per episode.')
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
    print('## Time')
    print()
    print('| Run | Calls per episode | Charged median (ms) | Actions per call '
          '| Moving per episode (s) | Still per episode (s) | Median success time (s) |')
    print('|---|---|---|---|---|---|---|')
    for label, run in images:
        calls, p50 = base.charged(run)
        n, emitted = played(run)
        times = [x['time'] for x in runs[label].values() if x['ok']]
        t = f'{statistics.median(times):.1f}' if times else '-'
        if not (n and calls and p50):
            print(f'| {label} | - | - | - | - | - | {t} |')
            continue
        ms = statistics.median(p50)
        still = f'{calls / n * max(ms / 1000 - LEAD.get(run, 0), 0):.1f}'
        print(f'| {label} | {calls / n:.1f} | {ms:.0f} | {emitted / calls:.1f} | {emitted / n / FPS:.1f} | {still} | {t} |')
    print()
    for name in ('fbase1', 'ffast1', 'fretry1'):
        rules(name)
    print()
    per_episode(images, runs, eps, ref)


def rules(name: str) -> None:
    log = base.EVALS / f'conc_{name}.server.log'
    if not log.exists():
        return
    text = log.read_text(errors='replace')
    steps_line = [l for l in text.splitlines() if 'overrode num_inference_steps' in l]
    steps_info = f'; {steps_line[0].split("FIT: ")[-1]}' if steps_line else ''
    counts = [l.split('Rule counts so far: ')[-1] for l in text.splitlines() if 'Rule counts so far' in l]
    print(f"- {name}: rule counts {counts[-1] if counts else '-'}; left shoulder camera in {text.count('is the left shoulder camera')} sessions, right in "
          f"{text.count('is the right shoulder camera')}; the still-arm rule gave the pick part in "
          f"{text.count('task now')} sessions; {text.count('OutOfMemoryError')} OOM errors{steps_info}.")


def per_episode(images, runs, eps, ref) -> None:
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

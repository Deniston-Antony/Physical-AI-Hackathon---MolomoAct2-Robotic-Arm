"""Report of the FLUX 3 Action fewer-steps test: the GD model at 4, 2 and 1 denoising steps.

Usage: ~/molmobot_src/venv/bin/python cloud_job/cloud_flux_steps/report.py > tests_1117/results_cloud_flux_steps.md
Reads the runs conc_fluxhyb4, conc_fluxhyb2, conc_fluxhyb1 in ~/evals, their timing reports, and the board results
of v3 and the best previous FLUX run (conc_fluxhyb from the grip test).
"""

import glob
import json
import statistics
from pathlib import Path

import report as base

IMAGES = [('FLUX hybrid, 4 steps (baseline)', 'conc_fluxhyb4'),
          ('FLUX hybrid, 2 steps', 'conc_fluxhyb2'),
          ('FLUX hybrid, 1 step', 'conc_fluxhyb1'),
          ('Best prev FLUX (hybrid, 4 steps)', 'conc_fluxhyb'),
          ('v3 + JPEG (board)', 'conc_v3jpeg')]
FPS = 15
LEAD = {'conc_fluxhyb4': 0.9, 'conc_fluxhyb2': 0.9, 'conc_fluxhyb1': 0.9, 'conc_fluxhyb': 0.9}


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
    print('# FLUX 3 Action: fewer denoising steps (GD model)')
    print()
    print('17 Nov: the GD model (trained for 4 denoising steps) run with 4, 2 and 1 steps. All runs use both '
          'cameras, hybrid schedule (stop-and-think for pick, continuous for others), full gripper command, '
          '24192 MiB GPU cap, text encoder on CPU. 40 episodes, 4 eval processes at a time. Fewer steps should '
          'be faster (fewer forward passes through the DiT) but may lose quality.')
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
    for name in ('fluxhyb4', 'fluxhyb2', 'fluxhyb1'):
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
    print(f"- {name}: left shoulder camera in {text.count('is the left shoulder camera')} sessions, right in "
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

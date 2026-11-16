"""Report of the third FLUX 3 Action test (cloud_job/cloud_flux_fix.sh): the v3 rules with a schedule for the FLUX delay.

Usage: ~/molmobot_src/venv/bin/python cloud_job/cloud_flux/report_fix.py > tests_1108/results_cloud_flux_fix.md
Reads the runs conc_fluxv3fix, conc_fluxv3 and conc_fluxa24 (13 Nov), conc_v3jpeg (11 Nov) and conc_v3 (10 Nov) in
~/evals, their timing reports (*.timing.txt) and the board results of v3.
"""

import glob
import json
import statistics
from pathlib import Path

import report as base

IMAGES = [('FLUX, 2 views, full grip', 'conc_fluxgrip'), ('FLUX, 2 views, full grip, hybrid', 'conc_fluxhyb'),
          ('FLUX, 2 views, whole chunk', 'conc_fluxcam2'), ('FLUX, 2 views, 1.03 s', 'conc_fluxcam2s'),
          ('FLUX + v3 rules, fixed schedule', 'conc_fluxv3fix'), ('FLUX + v3 rules', 'conc_fluxv3'),
          ('FLUX as published', 'conc_fluxa24'), ('v3 + JPEG (11 Nov, H100)', 'conc_v3jpeg'),
          ('v3 (10 Nov, L40S)', 'conc_v3')]
FPS = 15
# Seconds before the end of a chunk at which the next request starts.
LEAD = {'conc_fluxgrip': 0.0, 'conc_fluxcam2': 0.0, 'conc_fluxcam2s': 0.0, 'conc_fluxv3fix': 0.9, 'conc_fluxv3': 0.2, 'conc_fluxa24': 0.0}


def played(run: str) -> tuple[int, int]:
    """The episodes of a run and the actions that the robot played in them."""
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
    print('# FLUX 3 Action DROID with the v3 rules and a schedule for the delay of a FLUX call')
    print()
    print('13 Nov: all FLUX runs are in the 24192 MiB GPU memory of a competition run, with 4 eval processes at a time '
          'on the 40 episodes of the tests of 10 and 11 Nov. "FLUX + v3 rules" has the v3 schedule: 0.77 s of each '
          'chunk, the next request 0.2 s before the end, the first 4 actions of later chunks dropped. A FLUX call '
          'takes about 0.85 s, so the robot stood still for about 0.65 s after each chunk. "Fixed schedule" requests '
          'the next chunk 0.9 s before the end, plays 1.23 s of each chunk, and drops the first 13 actions (0.87 s) '
          'of later chunks. The "2 views" runs give the policy both exterior views, as it learned from them (the other '
          'runs give it one view in both slots), and request at the end of each chunk, when the arm is still. The "full grip" runs play 1.03 s of each chunk and make the gripper command full: closed from a command of 0.35 until a command of 0.1 (the policy commands a part-closed gripper most of the time). "Hybrid" plays a pick task so, and other tasks with no stop, as the fixed schedule does. "FLUX as published" plays each chunk of 32 actions whole and requests at the end.')
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
    print('"Charged" is the time of a model call as the harness measures it. "Still" is an estimate: the calls of an '
          'episode times the part of the charged time that the lead of the schedule does not cover.')
    print()
    print('| Image | Calls per episode | Charged, median of the streams (ms) | Actions played per call '
          '| Moving per episode (s) | Still per episode (s) | Median time of a success (s) |')
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
        still = f'{calls / n * max(ms / 1000 - LEAD[run], 0):.1f}' if run in LEAD else '-'
        print(f'| {label} | {calls / n:.1f} | {ms:.0f} | {emitted / calls:.1f} | {emitted / n / FPS:.1f} | {still} | {t} |')
    print()
    for name in ('fluxgrip', 'fluxhyb', 'fluxcam2', 'fluxcam2s', 'fluxv3fix'):
        rules(name)
    print()
    per_episode(images, runs, eps, ref)


def rules(name: str) -> None:
    log = base.EVALS / f'conc_{name}.server.log'
    if not log.exists():
        return
    text = log.read_text(errors='replace')
    print(f"- {name}: left shoulder camera in {text.count('is the left shoulder camera')} sessions, right in "
          f"{text.count('is the right shoulder camera')}; the still-arm rule gave the pick part in "
          f"{text.count('task now')} sessions; {text.count('OutOfMemoryError')} out-of-memory errors.")


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

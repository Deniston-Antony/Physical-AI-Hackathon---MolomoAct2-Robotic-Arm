"""Terminal tracker of the local tests on the 30 open episodes: the checkpoint queue and the grasp tests.

Each time an episode ends, it prints the episode result and the tracker: solved and done counts of every model,
the end time estimate of the grasp tests and the saved images. It also prints the main lines of the queue, test and
image saver logs. Stop with Ctrl+C.
Usage: ~/molmobot_src/venv/bin/python cloud_job/tracker.py
"""

import glob
import importlib.util
import json
import os
import re
import statistics
import subprocess
import time
from pathlib import Path

P = Path(__file__).resolve().parent.parent
D = P / 'tests_1108'
J = P / 'cloud_job'
SSD = Path('/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/molmobot_openclose_2026-11-09')
IMAGES = SSD / 'docker_images'
BOARD = P / 'competition_runs/molmobot_img_v5_openclose/result.json'
# The user stopped the queue after step 2400 (9 Nov): steps 2000, 1400 and 800 are not tested.
QUEUE = [2400]
REFERENCE = [('v4 + pull (old expert)', 'op_pull'), ('step 1000', 'mid1000_open')]
# The grasp tests of the final expert with the v5 rules (units risers-regrasp and risers-grasptests).
TESTS = [('final + regrasp rule', 'op_regrasp'), ('final + 10 flow steps', 'op_flow10'),
         ('final + touch, no retries', 'op_touch')]
# v3 and v5-touch on the board episodes that the top 5 solve and we fail. They run on the cloud VM (unit
# risers-cloudeval); the local units risers-reliable and risers-reliable2 run the episodes it did not finish.
RELIABLE = [('v3, 34 reliable eps', 'reliable_v3'), ('v5-touch, 34 reliable eps', 'reliable_touch')]
LOGS = [J / 'checkpoint_queue.log', J / 'save_images.log', J / 'regrasp_test.log', J / 'grasp_tests.log',
        J / 'reliable_test.log', J / 'cloud_eval.log']
DATED = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ')
EPISODE_MIN = 4.3  # minutes per episode when the queue has no own data yet

spec = importlib.util.spec_from_file_location('summarize', D / 'summarize.py')
summ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summ)
SET = json.loads((D / 'open30.json').read_text())
GROUP = {e['path']: e['group'] for e in SET}
RELIABLE_SET = json.loads((D / 'reliable34.json').read_text())


def episodes(run: str) -> dict:
    try:
        return summ.episodes(run)
    except Exception:  # an episode folder that is being written
        return {}


def finish_times(run: str) -> list[float]:
    return sorted(os.path.getmtime(f) for f in glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*/*/*/static.json')))


def queue_state() -> dict[str, str]:
    state = {}
    status = D / 'status.tsv'
    if status.exists():
        for row in status.read_text().splitlines():
            parts = row.split('\t')
            if len(parts) >= 3:
                state[parts[0]] = parts[2]
    return state


def unit_active(name: str) -> bool:
    return subprocess.run(['systemctl', '--user', 'is-active', '-q', name]).returncode == 0


def counts(eps: dict) -> str:
    part = []
    for group in ('open datagen', 'open hard'):
        sel = [p for p in eps if GROUP.get(p) == group]
        part.append(f"{sum(eps[p]['ok'] for p in sel)}/{len(sel)}")
    return f"{sum(e['ok'] for e in eps.values()):>3}    {len(eps):>2}/30   {part[0]:>5}   {part[1]:>5}"


def board_line() -> str:
    if not BOARD.exists():
        return ''
    scores = json.loads(BOARD.read_text())['scores']
    per = scores['per_task']
    opened = sum(v['successes'] for k, v in per.items() if k.startswith('open '))
    closed = sum(v['successes'] for k, v in per.items() if k.startswith('close '))
    total = round(scores['primary'] * len(scores['sim_time']))
    return (f'Board, final model (step 2500): {total}/320 = {scores["primary"] * 100:.1f}% '
            f'(open {opened}/30, close {closed}/30); best so far v3 219/320 = 68.4%')


def tracker() -> str:
    state = queue_state()
    lines = ['  TRACKER, 30 open episodes per model   solved  done  datagen   hard']
    for label, run in REFERENCE:
        lines.append(f'  {label:<36}  {counts(episodes(run))}')
    for step in QUEUE:
        lines.append(f'  step {step:<31}  {counts(episodes(f"op_step{step}"))}')
    lines.append('  steps 2000, 1400, 800: cancelled (their experts stay on the SSD)')
    gaps, left = [], 0
    for label, run in TESTS:
        eps = episodes(run)
        times = finish_times(run)
        gaps += [b - a for a, b in zip(times, times[1:]) if b - a < 15 * 60]
        test_state = {'running': 'RUNNING', 'done': 'done'}.get(state.get(run, ''), 'waiting')
        if test_state != 'done':
            left += 30 - len(eps)
        lines.append(f'  {label:<26} {test_state:<9}  {counts(eps)}')
    minutes = (statistics.median(gaps) / 60) if gaps else EPISODE_MIN
    if left == 0:
        tests = 'Grasp tests: all done.'
    elif not (unit_active('risers-regrasp') or unit_active('risers-grasptests')):
        tests = f'Grasp tests: STOPPED (units risers-regrasp and risers-grasptests do not run), {left} episodes left.'
    else:
        end = time.strftime('%a %d %b %H:%M', time.localtime(time.time() + left * minutes * 60))
        tests = f'Grasp tests: {left} episodes left, about {minutes:.1f} min per episode -> end about {end}.'
    for label, run in RELIABLE:
        eps = episodes(run)
        rel_state = {'running': 'RUNNING', 'done': 'done'}.get(state.get(run, ''), 'waiting')
        lines.append(f'  {label:<26} {rel_state:<9}  {sum(e["ok"] for e in eps.values()):>3}    {len(eps):>2}/34   '
                     f'(board v3: {sum(e["v3_ok"] for e in RELIABLE_SET)}/34; on the cloud VM, see cloud_eval.log)')
    listed = IMAGES / 'saved_images.txt'
    saved = [r.split()[0] for r in listed.read_text().splitlines() if r.strip()] if listed.exists() else []
    saver = 'running' if unit_active('risers-imgsave') else 'stopped'
    lines += [f'  {tests}',
              f'  Images on the SSD: {len(saved)} of 7 (base, step 1000, final, step 2400, 3 grasp tests), '
              f'saver {saver}.',
              f'  {board_line()}']
    return '\n'.join(lines)


def main() -> None:
    seen: set[tuple[str, str]] = set()
    log_pos = {log: 0 for log in LOGS}
    base = episodes('op_pull')
    watched = [(f'step {step}', f'op_step{step}') for step in QUEUE] + TESTS + RELIABLE
    for _, run in watched:  # the episodes that ended before the start
        for path in episodes(run):
            seen.add((run, path))
    for log in LOGS:
        if log.exists():
            log_pos[log] = len(log.read_text(errors='replace').splitlines())
    print(time.strftime('%H:%M'), 'tracker of the local open tests (Ctrl+C to stop)', flush=True)
    print(tracker(), flush=True)
    while True:
        for log in LOGS:
            if not log.exists():
                continue
            lines = log.read_text(errors='replace').splitlines()
            for line in lines[log_pos[log]:]:
                if DATED.match(line):
                    print(f'  [{log.stem}] {line[11:200]}', flush=True)
            log_pos[log] = len(lines)
        new = False
        for label, run in watched:
            eps = episodes(run)
            for e in RELIABLE_SET if run.startswith('reliable_') else SET:
                x = eps.get(e['path'])
                if x is None or (run, e['path']) in seen:
                    continue
                seen.add((run, e['path']))
                res = f"OK {x['time']:.1f} s" if x['ok'] else 'no'
                if run.startswith('reliable_'):
                    ref = f"board v3: {'OK' if e['v3_ok'] else 'no'}, top 5: {e['top5_solved']}/5 solve"
                else:
                    old = base.get(e['path'])
                    ref = 'v4 + pull: ' + (('OK' if old['ok'] else 'no') if old else '-')
                print(f"\n{time.strftime('%H:%M')} {label}: #{e['board_index']} {e['task'][:60]} -> {res} ({ref})",
                      flush=True)
                new = True
        if new:
            print(tracker(), flush=True)
        time.sleep(20)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

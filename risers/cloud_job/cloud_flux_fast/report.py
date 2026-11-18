"""Report of the FLUX 3 Action test (cloud_job/cloud_flux.sh), against the earlier cloud runs of v3 on the same episodes.

Usage: ~/molmobot_src/venv/bin/python cloud_job/cloud_flux/report.py > tests_1108/results_cloud_flux.md
Reads the runs conc_fluxa24, conc_fluxv3 and conc_fluxa (12 Nov), conc_v3jpeg (11 Nov) and conc_v3 (10 Nov) in
~/evals, their timing reports (*.timing.txt), the server logs, the GPU log of the VM and the board results of v3.
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
J = P / 'cloud_job'
RUNS = P / 'competition_runs'
EVALS = Path(os.path.expanduser('~/evals'))
GROUPS = {'FrankaPickHardBench': 'Pick, hard', 'FrankaPickandPlaceDroidMiniBench': 'Pick and place, normal',
          'FrankaOpenDataGenConfig': 'Open, normal', 'FrankaOpenHardBench': 'Open, hard',
          'FrankaCloseDataGenConfig': 'Close, normal', 'FrankaCloseHardBench': 'Close, hard'}
IMAGES = [('FLUX, 24 GB', 'conc_fluxa24'), ('FLUX + v3 rules, 24 GB', 'conc_fluxv3'),
          ('FLUX, no cap (stopped early)', 'conc_fluxa'), ('v3 + JPEG (11 Nov, H100)', 'conc_v3jpeg'),
          ('v3 (10 Nov, L40S)', 'conc_v3')]
# The 24 GB slice of a competition run.
SLICE_MIB = 24192


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


def gpu_peaks() -> dict[str, tuple[int, int]]:
    """For each run of vm_flux24.sh: the peak GPU memory (MiB) of one CUDA process, and of the whole GPU."""
    log, vm = J / 'cloud_flux_gpu.log', J / 'cloud_flux_vm.log'
    if not log.exists() or not vm.exists():
        return {}
    marks = sorted((int(m[2]), m[1]) for m in re.finditer(r'\[(\w+)\] START: .*GPU log from here: line (\d+)', vm.read_text()))
    lines = log.read_text().splitlines()
    out = {}
    for i, (first, name) in enumerate(marks):
        last = marks[i + 1][0] if i + 1 < len(marks) else len(lines) + 1
        proc, total = 0, 0
        for line in lines[first - 1:last - 1]:
            used = re.search(r' (\d+) MiB,', line)
            total = max(total, int(used[1])) if used else total
            for app in re.findall(r'(\d+) MiB;', line.split('|', 1)[1] if '|' in line else ''):
                proc = max(proc, int(app))
        out[name] = (proc, total)
    return out


def main() -> None:
    summ = load('summarize', P / 'tests_1108' / 'summarize.py')
    board = load('board_by_set', RUNS / 'board_by_set.py')
    sets = json.loads((RUNS / 'episode_sets.json').read_text())
    ref = board.successes(str(RUNS / 'molmobot_img_v3' / 'result.json'), sets)[0]
    eps = json.loads((HERE / 'conc40.json').read_text())
    images = [(label, run) for label, run in IMAGES if glob.glob(str(EVALS / f't8_{run}_ps*'))]
    runs = {label: summ.episodes(run) for label, run in images}
    print('# FLUX 3 Action DROID in the 24 GB of a competition run, as published and with the v3 rules')
    print()
    print('12 Nov: cloud VM with an L40S GPU. The public image `positro/flux3-action` serves FLUX 3 Action DROID with '
          '4 eval processes at a time, as the board does, on the 40 episodes of the tests of 10 and 11 Nov. In the '
          '"24 GB" runs (13 Nov), the GPU memory of FLUX is capped at the 24192 MiB slice of a competition run, its '
          'text encoder stays on the CPU and encodes there, its DiT is packed in place (BFL\'s own packing needs about '
          '9 GB more and does not fit), and the container has 14 CPUs, as a competition run has. The published image '
          'keeps the text encoder on the GPU and uses about 27 GB. '
          '"FLUX, 24 GB" otherwise serves as published: `image.exterior` in both exterior slots, and each chunk of 32 '
          'actions played whole. "FLUX + v3 rules, 24 GB" adds the rules of v3: the left shoulder camera in both slots, '
          'the pick part of a pick-and-place task while the open arm is still for 3 calls, and the v3 schedule '
          '(0.77 s of each chunk, the next request 0.2 s before the end, the first 4 actions of later chunks dropped). '
          '"FLUX, no cap" is the published image with no cap; it was stopped early, when the cap was asked for. '
          'The v3 columns are MolmoBot v3 on the same episodes.')
    print()
    print('| Group | Episodes | ' + ' | '.join(label for label, _ in images) + ' | Board v3 |')
    print('|---|---|' + '---|' * (len(images) + 1))
    for group, name in list(GROUPS.items()) + [('All', '**All**')]:
        sel = [e for e in eps if group in ('All', e['group'])]
        cells = []
        for label, _ in images:
            done = [e for e in sel if e['path'] in runs[label]]
            ok = sum(runs[label][e['path']]['ok'] for e in done)
            cells.append(f'{ok}' + ('' if len(done) == len(sel) else f' ({len(done)} done)'))
        print(f'| {name} | {len(sel)} | ' + ' | '.join(cells) + f" | {sum(ref[e['board_index']] for e in sel)} |")
    print()
    print('## Time per model call')
    print()
    print('"Charged" is the time of a model call as the harness measures it: the robot waits this long.')
    print()
    print('| Image | Calls | Charged p50 per stream (ms) | Median of the streams (ms) | Median time of a success (s) |')
    print('|---|---|---|---|---|')
    for label, run in images:
        calls, p50 = charged(run)
        median = f'{statistics.median(p50):.0f}' if p50 else '-'
        times = [x['time'] for x in runs[label].values() if x['ok']]
        t = f'{statistics.median(times):.1f}' if times else '-'
        print(f'| {label} | {calls} | {", ".join(f"{x:.0f}" for x in p50) or "-"} | {median} | {t} |')
    print()
    print('## Rules of v3 in the FLUX server')
    print()
    log = EVALS / 'conc_fluxv3.server.log'
    text = log.read_text(errors='replace') if log.exists() else ''
    print(f"- Sessions where `image.exterior` was the left shoulder camera: {text.count('is the left shoulder camera')}; "
          f"the right: {text.count('is the right shoulder camera')}.")
    print(f"- Sessions where the still-arm rule gave the pick part of the task: {text.count('task now')}.")
    print()
    print('## GPU memory: does FLUX fit the 24 GB of a competition run?')
    print()
    vm = J / 'cloud_flux_vm.log'
    vm_text = vm.read_text(errors='replace') if vm.exists() else ''
    for line in vm_text.splitlines():
        if 'RESULT: FLUX' in line or 'did not start' in line or 'out-of-memory lines' in line:
            print(f'- {line[20:]}')
    print()
    print(f'A competition run gets {SLICE_MIB} MiB of GPU memory. The VM samples the memory every 2 s.')
    print()
    print('| Run | Peak of the FLUX process (MiB) | Peak of the whole GPU, with the simulators (MiB) |')
    print('|---|---|---|')
    for name, (proc, total) in gpu_peaks().items():
        print(f'| {name} | {proc} | {total} |')
    print()
    fit = [line.split('FIT: ', 1)[1] for line in vm_text.splitlines() if 'FIT: ' in line]
    if fit:
        print('The memory that the FLUX process reported (PyTorch):')
        print()
        for line in fit:
            print(f'- {line}')
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
              + f" | {'OK' if ref[e['board_index']] else 'no'} |")


if __name__ == '__main__':
    main()

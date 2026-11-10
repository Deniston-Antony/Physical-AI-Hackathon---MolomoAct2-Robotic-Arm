"""Compare the downloaded top-team replays with our board runs (v3, v4, v5), per episode set and per episode.

Usage: python3 -I competition_runs/board_videos/compare_top.py > competition_runs/board_videos/compare_top.md
It reads the replays that download_board.py saved on the SSD and our result.json files.
"""

import collections
import importlib.util
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent
REPLAYS = Path('/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/board_replays')
OUR_TAG = 'd2504d'
OURS = {'v3': 'molmobot_img_v3', 'v4': 'molmobot_img_v4', 'v5': 'molmobot_img_v5_openclose'}

spec = importlib.util.spec_from_file_location('board_by_set', RUNS / 'board_by_set.py')
bbs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bbs)
SETS = json.loads((RUNS / 'episode_sets.json').read_text())


def short(name: str) -> str:
    return name.removeprefix('Franka').removesuffix('Bench').removesuffix('Config')


def main() -> None:
    snapshot = json.loads(sorted(REPLAYS.glob('board_*.json'))[-1].read_text())
    rank = {r['submission_id']: r['rank'] for r in snapshot}
    teams = []
    for folder in REPLAYS.iterdir():
        if not (folder / 'replay.json').exists():
            continue
        tag, sub = folder.name.split('_')[-2:]
        data = json.loads((folder / 'replay.json').read_text())
        eps = data['episodes']
        assert [e['values']['task'] for e in eps] == [s['task'] for s in SETS], f'episode order differs: {folder}'
        ok = [e['values']['outcome'] == 'Success' for e in eps]
        teams.append({'name': folder.name.rsplit('_', 2)[0], 'tag': tag, 'rank': rank.get(sub, 99), 'ok': ok,
                      'time': [e['duration_s'] for e in eps]})
    teams.sort(key=lambda t: t['rank'])
    top = [t for t in teams if t['tag'] != OUR_TAG]
    ours = {}
    for label, run in OURS.items():
        ok, times = bbs.successes(str(RUNS / run / 'result.json'), SETS)
        ours[label] = {'ok': ok, 'time': times}
    replay_v3 = next(t for t in teams if t['tag'] == OUR_TAG)
    assert replay_v3['ok'] == ours['v3']['ok'], 'our v3 replay and result.json differ'

    groups = collections.defaultdict(list)
    for i, s in enumerate(SETS):
        groups[short(s['set'])].append(i)
    cols = [(f"#{t['rank']} {t['name'][:12]}", t) for t in top] + [(f'us {k}', v) for k, v in ours.items()]
    print(f'# Top {len(top)} teams vs our board runs (board snapshot {sorted(REPLAYS.glob("board_*.json"))[-1].name})')
    print()
    print('Successes per episode set. The last column is the gap between the top-5 mean and our best run (v3).')
    print()
    print('| Set | Episodes | ' + ' | '.join(c for c, _ in cols) + ' | top-5 mean - v3 |')
    print('|---|---' + '|---' * len(cols) + '|---|')
    for g, idx in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        vals = [sum(t['ok'][i] for i in idx) for _, t in cols]
        mean = statistics.mean(sum(t['ok'][i] for i in idx) for t in top)
        print(f'| {g} | {len(idx)} | ' + ' | '.join(map(str, vals)) + f' | {mean - vals[len(top)]:+.1f} |')
    tot = [sum(t['ok']) for _, t in cols]
    print(f'| **All** | {len(SETS)} | ' + ' | '.join(map(str, tot)) +
          f' | {statistics.mean(sum(t["ok"]) for t in top) - tot[len(top)]:+.1f} |')
    print()
    print('Median time of a success (s) per set:')
    print()
    print('| Set | top-5 median | us v3 median |')
    print('|---|---|---|')
    for g, idx in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        tt = [t['time'][i] for t in top for i in idx if t['ok'][i]]
        us = [ours['v3']['time'][i] for i in idx if ours['v3']['ok'][i]]
        print(f'| {g} | {statistics.median(tt):.1f} | {statistics.median(us) if us else float("nan"):.1f} |')
    print()
    print('## Episodes that all our runs (v3, v4, v5) fail and 3 or more of the top 5 solve')
    print()
    print('| Board # | Set | Task | Top 5 that solve | Their median time (s) |')
    print('|---|---|---|---|---|')
    rows = []
    for i, s in enumerate(SETS):
        if any(o['ok'][i] for o in ours.values()):
            continue
        n = sum(t['ok'][i] for t in top)
        if n >= 3:
            rows.append((short(s['set']), i, s['task'], n, statistics.median(t['time'][i] for t in top if t['ok'][i])))
    for g, i, task, n, med in sorted(rows):
        print(f'| {i} | {g} | {task} | {n} | {med:.1f} |')
    print()
    print(f'{len(rows)} episodes. Per set: ' + ', '.join(f'{g} {c}' for g, c in collections.Counter(r[0] for r in rows).most_common()))


if __name__ == '__main__':
    main()

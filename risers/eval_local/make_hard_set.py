"""Pick a fixed local test set from the two hard sets (FrankaPickHardBench, FrankaPickandPlaceHardBench).

Usage: python3 -I make_hard_set.py <competition episodes dir> <rankings.json> <our replay json> <out.json>
Most episodes are ones our board run failed and at least 6 of the 11 best teams solved (episodes a faster or
better policy can win); the rest are ones our board run solved (to catch losses). Outcomes come from the public
board replays; the episode order of a replay equals the order of the episodes dir (checked).
"""

import glob
import json
import random
import sys
import urllib.request
from pathlib import Path

SEED = 20261106
TAKE = {'FrankaPickHardBench': (12, 4), 'FrankaPickandPlaceHardBench': (9, 3)}  # (won by top teams, solved by us)


def outcomes(url: str) -> list[bool]:
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as f:
        return [e['values']['outcome'] == 'Success' for e in sorted(json.load(f)['episodes'], key=lambda e: e['index'])]


def main(episodes_dir: str, rankings: str, ours: str, out_path: str):
    static = [json.loads(Path(f).read_text()) for f in sorted(glob.glob(f'{episodes_dir}/*/*/static.json'))]
    top = [outcomes(r['replay']['data_url']) for r in json.loads(Path(rankings).read_text())['rankings'][:11]]
    mine = [e['values']['outcome'] == 'Success' for e in sorted(json.loads(Path(ours).read_text())['episodes'], key=lambda e: e['index'])]
    rng = random.Random(SEED)
    picked = []
    for cfg, (n_won, n_ours) in TAKE.items():
        idx = [i for i, s in enumerate(static) if s['molmo.task_config'] == cfg]
        won = [i for i in idx if not mine[i] and sum(t[i] for t in top) >= 6]
        solved = [i for i in idx if mine[i]]
        for group, i in [('top teams solve, we fail', i) for i in rng.sample(won, n_won)] + [
            ('we solve', i) for i in rng.sample(solved, n_ours)
        ]:
            s = static[i]
            bench = '/'.join(s[k] for k in ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark'))
            picked.append(dict(set=cfg, group=group, board_index=i, path=f"{bench}/{s['molmo.episode_index']}",
                               task=s['eval.task'], limit_s=s['eval.timeout'], top11_solved=sum(t[i] for t in top)))
    Path(out_path).write_text(json.dumps(picked, indent=1))
    for p in picked:
        print(f"{p['set'][5:22]:18s} {p['group']:25s} top {p['top11_solved']:2d}/11  {p['task'][:60]}")


if __name__ == '__main__':
    main(*sys.argv[1:5])

"""Pick a local practice set of competition episodes that keeps the task mix of the 320-episode board run.

Usage: python3 make_mixed_set.py <competition episodes dir> <out.json> [size]
The episodes dir holds the static.json files of one board run (here our MolmoAct2 run 2d30ed2cf955a93). Each set
(task_config) gets a share of `size` in proportion to its board count. The output lists the episode paths that
`--eval.episode_paths` takes, with the set size and the MolmoAct2 outcome of each episode.
"""

import glob
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

SEED = 20261105


def main(episodes_dir: str, out_path: str, size: int = 40):
    by_set = defaultdict(list)
    for f in sorted(glob.glob(f'{episodes_dir}/*/*/static.json')):
        s = json.loads(Path(f).read_text())
        bench = '/'.join(s[k] for k in ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark'))
        by_set[s['molmo.task_config']].append(
            dict(path=f"{bench}/{s['molmo.episode_index']}", task=s['eval.task'], molmoact2=bool(s.get('eval.success')))
        )
    total = sum(len(v) for v in by_set.values())
    quota = {k: size * len(v) / total for k, v in by_set.items()}
    take = {k: int(q) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: quota[k] - take[k], reverse=True)[: size - sum(take.values())]:
        take[k] += 1
    rng = random.Random(SEED)
    picked = []
    for k in sorted(by_set):
        for ep in rng.sample(by_set[k], take[k]):
            picked.append(dict(set=k, set_board_count=len(by_set[k]), **ep))
    Path(out_path).write_text(json.dumps(picked, indent=1))
    for k in sorted(by_set):
        print(f'{k:36s} board {len(by_set[k]):3d}  picked {take[k]}')
    print(len(picked), 'episodes')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4]))

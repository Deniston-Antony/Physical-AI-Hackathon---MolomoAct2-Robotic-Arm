"""Success by exterior camera side for one board submission, from its public replay.

Usage: python replay_camera_split.py <replay.json> <work dir>   (run with ~/molmobot_src/venv/bin/python -I)
Downloads the two exterior videos of each episode, judges the side of `image.exterior` with camera_side.py
(about 94% right on local runs), and prints the success rate per side and task type.
"""

import collections
import concurrent.futures as cf
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

_spec = importlib.util.spec_from_file_location('camera_side', Path(__file__).with_name('camera_side.py'))
camera_side = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(camera_side)


def kind(task: str) -> str:
    t = task.lower()
    if t.startswith('open'):
        return 'open'
    if t.startswith('close'):
        return 'close'
    if 'next to' in t:
        return 'next-to'
    if ' place ' in t or ' put ' in t:
        return 'pick+place'
    return 'pick'


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    return path


def judge(e: dict, work: Path) -> tuple[str, str, bool]:
    vids = {v['camera']: v['url'] for v in e['videos']}
    frames = [
        camera_side.first_frame(fetch(vids[c], work / f"{e['index']}_{c}.mp4")) for c in ('image.exterior', 'image.exterior_2')
    ]
    return camera_side.exterior_side(*frames), kind(e['values']['task']), e['values']['outcome'] == 'Success'


def main(replay: str, work: str):
    work_dir = Path(work)
    work_dir.mkdir(parents=True, exist_ok=True)
    episodes = json.loads(Path(replay).read_text())['episodes']
    with cf.ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(lambda e: judge(e, work_dir), episodes))
    tally = collections.defaultdict(lambda: [0, 0])
    for side, k, ok in rows:
        for key in ((side, 'ALL'), (side, k)):
            tally[key][0] += ok
            tally[key][1] += 1
    print(f"{'type':11s} {'left camera':>16s} {'right camera':>16s}")
    for k in ('ALL', 'pick', 'pick+place', 'next-to', 'open', 'close'):
        cells = []
        for side in ('left', 'right'):
            ok, n = tally[(side, k)]
            cells.append(f'{ok:3d}/{n:3d} {100 * ok / n if n else 0:4.0f}%')
        print(f'{k:11s} {cells[0]:>16s} {cells[1]:>16s}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

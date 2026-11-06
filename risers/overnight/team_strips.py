"""Picture strips of hard episodes that top teams solve and our board run failed, next to our own run.

Usage (with ~/molmobot_src/venv/bin/python -I): team_strips.py <rankings.json> <our replay.json> <out dir> [episodes]
For each picked episode of eval_local/hard28.json (group 'top teams solve, we fail'), the strip has one row per
team: the 3 best teams that solved it, then us. A row holds 6 exterior frames from the start to the end.
"""

import io
import json
import sys
import urllib.request
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parent.parent
FRAMES = 6


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
        return r.read()


def row(video: bytes, label: str) -> np.ndarray:
    with av.open(io.BytesIO(video)) as c:
        frames = [f.to_ndarray(format='rgb24') for f in c.decode(c.streams.video[0])]
    pick = [frames[i] for i in np.linspace(0, len(frames) - 1, FRAMES).round().astype(int)]
    img = Image.fromarray(np.concatenate(pick, axis=1))
    ImageDraw.Draw(img).text((8, 8), label, fill=(255, 255, 0))
    return np.asarray(img)


def main(rankings: str, ours: str, out_dir: str, count: int = 6):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    teams = json.loads(Path(rankings).read_text())['rankings'][:11]
    replays = {t['display_name']: sorted(json.loads(get(t['replay']['data_url']))['episodes'], key=lambda e: e['index'])
               for t in teams}
    mine = sorted(json.loads(Path(ours).read_text())['episodes'], key=lambda e: e['index'])
    picked = [e for e in json.loads((PROJECT / 'eval_local/hard28.json').read_text()) if e['group'] != 'we solve'][:count]
    for k, e in enumerate(picked):
        i = e['board_index']
        rows = []
        for name, eps in replays.items():
            ep = eps[i]
            if ep['values']['outcome'] == 'Success' and len(rows) < 3:
                url = {v['camera']: v['url'] for v in ep['videos']}['image.exterior']
                rows.append(row(get(url), f"{name}: success in {ep['duration_s']:.1f} s"))
        ep = mine[i]
        url = {v['camera']: v['url'] for v in ep['videos']}['image.exterior']
        rows.append(row(get(url), f"The Risers: {ep['values']['outcome']} after {ep['duration_s']:.1f} s"))
        img = Image.fromarray(np.concatenate(rows, axis=0))
        img.thumbnail((1800, 1800))
        img.save(out / f"{k:02d}.jpg")
        print(k, e['set'][5:], '|', e['task'], '|', len(rows) - 1, 'top teams shown')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], *(int(x) for x in sys.argv[4:5]))

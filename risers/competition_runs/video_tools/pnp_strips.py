"""Strips of our failed episodes: one row per camera, FRAMES frames from start to end, with the time on each frame."""
import io, json, sys, urllib.request
from pathlib import Path
import av
import numpy as np
from PIL import Image, ImageDraw

FRAMES = 8

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
        return r.read()

def frames(video, n=FRAMES):
    with av.open(io.BytesIO(video)) as c:
        count = sum(1 for _ in c.decode(c.streams.video[0]))
    want = np.linspace(0, count - 1, n).round().astype(int).tolist()
    out = {}
    with av.open(io.BytesIO(video)) as c:
        s = c.streams.video[0]
        for i, f in enumerate(c.decode(s)):
            if i in want:
                out[i] = (f.to_ndarray(format='rgb24'), float(f.time or 0))
    return [out[i] for i in want]

def main(d):
    d = Path(d)
    ours = sorted(json.loads((d / 'ours.json').read_text())['episodes'], key=lambda e: e['index'])
    rows_info = json.loads((d / 'fails.json').read_text())
    (d / 'strips').mkdir(exist_ok=True)
    for r in rows_info:
        ep = ours[r['i']]
        vids = {v['camera']: v['url'] for v in ep['videos']}
        rows = []
        for cam in ('image.exterior', 'image.exterior_2', 'image.wrist'):
            fr = frames(get(vids[cam]))
            imgs = []
            for a, t in fr:
                im = Image.fromarray(a)
                ImageDraw.Draw(im).text((8, 8), f'{t:.1f}s', fill=(255, 255, 0))
                imgs.append(np.asarray(im))
            rows.append(np.concatenate(imgs, axis=1))
        img = Image.fromarray(np.concatenate(rows, axis=0))
        img.thumbnail((2400, 2400))
        img.save(d / 'strips' / f"{r['i']:03d}.jpg", quality=85)
        print(r['i'], r['task'], ep['duration_s'], flush=True)

main(sys.argv[1])

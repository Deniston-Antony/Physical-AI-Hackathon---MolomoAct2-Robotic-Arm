"""A strip of one local episode: rows exterior, exterior_2, wrist; 8 frames from start to end.

Usage: local_strip.py <run prefix> <episode number> <out.jpg>
"""
import glob, json, os, sys
from pathlib import Path
import av, numpy as np
from PIL import Image, ImageDraw

files = sorted(glob.glob(os.path.expanduser(f'~/evals/{sys.argv[1]}_p*/*/*/static.json')))
d = Path(files[int(sys.argv[2])]).parent
rows = []
for cam in ('image.exterior', 'image.exterior_2', 'image.wrist'):
    with av.open(str(d / f'{cam}.mp4')) as c:
        frames = [f.to_ndarray(format='rgb24') for f in c.decode(video=0)]
    idx = np.linspace(0, len(frames) - 1, 8).round().astype(int)
    tiles = []
    for i in idx:
        im = Image.fromarray(frames[i]); ImageDraw.Draw(im).text((6, 6), f'{i / 15:.1f}s', fill=(255, 255, 0)); tiles.append(np.asarray(im))
    rows.append(np.concatenate(tiles, axis=1))
img = Image.fromarray(np.concatenate(rows, axis=0)); img.thumbnail((2400, 2400)); img.save(sys.argv[3], quality=85)
print(json.loads((d / 'static.json').read_text())['eval.task'])

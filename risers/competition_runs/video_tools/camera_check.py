"""Which shoulder camera the MolmoBot server picked in each board episode, and how much that camera sees.

Usage: camera_check.py <replay.json> <episode_sets.json> <out dir>
The replay is the rankings `data_url` of our best submission. The server picks the left shoulder camera from the
first frames (the rule of `exterior_side` in positronic/vendors/molmobot/policy.py, copied here). "Detail" is the
mean gradient of the grey first frame: a camera that faces a wall or a dark corner has little detail.
Writes cameras.json and a sheet of the first frames (picked camera left, other camera right) for the episodes where
the picked camera has the least detail.
"""

import concurrent.futures as cf
import io
import json
import sys
import urllib.request
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
        return r.read()


def first_frame(url: str) -> np.ndarray:
    with av.open(io.BytesIO(get(url))) as c:
        for f in c.decode(c.streams.video[0]):
            return f.to_ndarray(format='rgb24')
    raise ValueError(f'no frame in {url}')


def white_lean(img: np.ndarray) -> float:
    h, w, _ = img.shape
    rgb = np.asarray(img, dtype=np.int16)
    white = (rgb.min(axis=2) > 170) & (rgb.max(axis=2) - rgb.min(axis=2) < 30)
    lower = white[h // 2 :]
    return float(lower[:, 2 * w // 3 :].mean() - lower[:, : w // 3].mean())


def detail(img: np.ndarray) -> float:
    g = img.astype(np.float32).mean(axis=2)
    return float((np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean()) / 2)


def check(ep: dict) -> dict:
    urls = {v['camera']: v['url'] for v in ep['videos']}
    ext, ext2 = first_frame(urls['image.exterior']), first_frame(urls['image.exterior_2'])
    picked_is_ext2 = white_lean(ext) <= white_lean(ext2)  # exterior_side(ext, ext2) != 'left'
    picked, other = (ext2, ext) if picked_is_ext2 else (ext, ext2)
    return dict(
        index=ep['index'], task=ep['values']['task'], ok=ep['values']['outcome'] == 'Success',
        picked='image.exterior_2' if picked_is_ext2 else 'image.exterior',
        detail_picked=detail(picked), detail_other=detail(other),
        mean_picked=float(picked.mean()), mean_other=float(other.mean()),
        frames=(picked, other),
    )


def main(replay: str, sets_path: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    eps = sorted(json.loads(Path(replay).read_text())['episodes'], key=lambda e: e['index'])
    sets = [e['set'] for e in json.loads(Path(sets_path).read_text())]
    with cf.ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(check, eps))
    for r, s in zip(rows, sets, strict=True):
        r['set'] = s
    worst = sorted(rows, key=lambda r: r['detail_picked'])[:24]
    tiles = []
    for r in worst:
        pair = np.concatenate([np.asarray(Image.fromarray(f).resize((312, 176))) for f in r['frames']], axis=1)
        im = Image.fromarray(pair)
        ImageDraw.Draw(im).text((6, 6), f"#{r['index']} {'OK' if r['ok'] else 'FAIL'} {r['detail_picked']:.1f}/{r['detail_other']:.1f} "
                                         f"{r['task'][:40]}", fill=(255, 255, 0))
        tiles.append(np.asarray(im))
    sheet = np.concatenate([np.concatenate(tiles[i : i + 2], axis=1) for i in range(0, len(tiles), 2)], axis=0)
    Image.fromarray(sheet).save(out / 'lowest_detail.jpg', quality=85)
    for r in rows:
        del r['frames']
    (out / 'cameras.json').write_text(json.dumps(rows, indent=1))
    print('episodes', len(rows))


if __name__ == '__main__':
    main(*sys.argv[1:])

"""Frames of one episode from T0 to T1 seconds, every STEP seconds, for the given cameras, as one picture."""
import io, json, sys, urllib.request
from pathlib import Path
import av
import numpy as np
from PIL import Image, ImageDraw

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
        return r.read()

def main(replay, index, t0, t1, step, out, *cams):
    ep = sorted(json.loads(Path(replay).read_text())['episodes'], key=lambda e: e['index'])[int(index)]
    vids = {v['camera']: v['url'] for v in ep['videos']}
    times = np.arange(float(t0), float(t1) + 1e-6, float(step))
    rows = []
    for cam in cams:
        got, k = [], 0
        with av.open(io.BytesIO(get(vids[cam]))) as c:
            for f in c.decode(c.streams.video[0]):
                t = float(f.time or 0)
                if k < len(times) and t >= times[k] - 1e-3:
                    im = Image.fromarray(f.to_ndarray(format='rgb24'))
                    ImageDraw.Draw(im).text((8, 8), f'{t:.1f}s', fill=(255, 255, 0))
                    got.append(np.asarray(im)); k += 1
        rows.append(np.concatenate(got, axis=1))
    w = min(r.shape[1] for r in rows)
    img = Image.fromarray(np.concatenate([r[:, :w] for r in rows], axis=0))
    img.thumbnail((2400, 2400))
    img.save(out, quality=85)
    print(ep['values'], ep['duration_s'])

main(*sys.argv[1:])

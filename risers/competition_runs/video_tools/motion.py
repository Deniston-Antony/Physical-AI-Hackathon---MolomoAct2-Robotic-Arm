"""Wrist-camera motion per episode of a board replay: the time of the first clear motion, and the largest change."""
import concurrent.futures as cf, io, json, sys, urllib.request
from pathlib import Path
import av
import numpy as np

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
        return r.read()

def motion(ep):
    url = {v['camera']: v['url'] for v in ep['videos']}['image.wrist']
    small = []
    with av.open(io.BytesIO(get(url))) as c:
        s = c.streams.video[0]
        for i, f in enumerate(c.decode(s)):
            if i % 5 == 0:
                a = f.to_ndarray(format='gray')
                small.append((float(f.time or i / 15), a[::8, ::8].astype(np.float32)))
    # Change of the wrist view over 3 s windows, one window per second (samples are 1/3 s apart).
    win = [(small[k][0], float(np.abs(small[k][1] - small[k - 9][1]).mean())) for k in range(9, len(small), 3)]
    return dict(index=ep['index'], task=ep['values']['task'], ok=ep['values']['outcome'] == 'Success',
                dur=ep['duration_s'], win=win)

def main(replay, out):
    eps = json.loads(Path(replay).read_text())['episodes']
    with cf.ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(motion, eps))
    Path(out).write_text(json.dumps(sorted(rows, key=lambda r: r['index'])))
    print('done', len(rows))

main(sys.argv[1], sys.argv[2])

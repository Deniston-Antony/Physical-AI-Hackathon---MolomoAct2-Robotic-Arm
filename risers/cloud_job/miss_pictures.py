import glob, json, os, sys
import av, numpy as np, pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont
run, want = sys.argv[1], [int(x) for x in sys.argv[2].split(',')]
KEYS = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')
board = {e['path']: e['board_index'] for e in json.load(open(os.path.expanduser('~/Desktop/Deniston_projects/Competitions/Physical_AI_Competition/tests_1108/open30.json')))}
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
def ser(d, n):
    t = pq.read_table(f'{d}/{n}.parquet', columns=['ts.harness.world', 'value'])
    return np.asarray(t.column(0).to_pylist()) / 1e9, np.asarray(t.column(1).to_pylist(), dtype=float).ravel()
rows = []
for f in glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*/*/*/static.json')):
    s = json.load(open(f)); d = os.path.dirname(f)
    b = board.get('/'.join(str(s[k]) for k in KEYS))
    if b not in want: continue
    gt, g = ser(d, 'grip')
    # moments the gripper finishes a close on nothing: first sample >= 0.9 after a sample < 0.9
    ends = np.flatnonzero((g[1:] >= 0.9) & (g[:-1] < 0.9)) + 1
    wt = np.asarray(pq.read_table(f'{d}/image.wrist.frames.parquet', columns=['ts.harness.world']).column(0)) / 1e9
    with av.open(f'{d}/image.wrist.mp4') as c:
        imgs = [x.to_ndarray(format='rgb24') for x in c.decode(video=0)]
    tiles = []
    for i in ends[:4]:
        # the frame 0.5 s before the fingers end the close: the view while the fingers close
        k = min(np.searchsorted(wt, gt[i] - 0.5), len(imgs) - 1)
        im = Image.fromarray(imgs[k]).resize((320, 180)); dr = ImageDraw.Draw(im)
        dr.text((4, 4), f'#{b} close {len(tiles)+1} t={gt[i]-gt[0]:.1f}s', font=font, fill=(255, 255, 0))
        tiles.append(im)
    rows.append((b, s['eval.task'], tiles))
rows.sort(key=lambda r: want.index(r[0]))
W = Image.new('RGB', (4 * 320, len(rows) * 200), (0, 0, 0)); dr = ImageDraw.Draw(W)
for r, (b, task, tiles) in enumerate(rows):
    for c, im in enumerate(tiles): W.paste(im, (c * 320, r * 200 + 20))
    dr.text((4, r * 200 + 2), f'#{b} {task}  (wrist camera, the first 4 closes on nothing)', font=font, fill=(255, 255, 255))
W.save(sys.argv[3]); print('ok', len(rows))

"""Make one video of the finished local test episodes of a run: the left shoulder camera and the wrist camera side by
side, with the gripper command and the finger reading on each frame.

Usage: ~/molmobot_src/venv/bin/python cloud_job/episode_video.py <run, for example op_regrasp> [--open]
The video goes to cloud_job/videos/<run>.mp4. With --open, the video player of the desktop opens it.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont

P = Path(__file__).resolve().parent.parent
OUT = P / 'cloud_job' / 'videos'
KEYS = ('molmo.suite', 'molmo.scene_dataset', 'molmo.task_config', 'molmo.benchmark', 'molmo.episode_index')
SETS = [P / 'tests_1108' / name for name in ('open30.json', 'close15.json', 'closedatagen15.json')]
FPS = 15
FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
# Finger readings: below LOW the gripper is open; at or above HIGH it closed on nothing (the regrasp rule uses the same).
LOW, HIGH = 0.1, 0.9


def font(size: int) -> ImageFont.ImageFont:
    return ImageFont.truetype(FONT_FILE, size) if os.path.exists(FONT_FILE) else ImageFont.load_default()


def series(d: Path, name: str) -> tuple[np.ndarray, np.ndarray]:
    t = pq.read_table(d / f'{name}.parquet', columns=['ts.harness.world', 'value'])
    return np.asarray(t.column(0).to_pylist()) / 1e9, np.asarray(t.column(1).to_pylist())


def frames(d: Path, camera: str) -> tuple[np.ndarray, list[np.ndarray]]:
    times = np.asarray(pq.read_table(d / f'{camera}.frames.parquet', columns=['ts.harness.world']).column(0)) / 1e9
    with av.open(str(d / f'{camera}.mp4')) as c:
        images = [f.to_ndarray(format='rgb24') for f in c.decode(video=0)]
    return times[: len(images)], images


def reading(value: float) -> str:
    if value < LOW:
        return 'open'
    return 'CLOSED ON NOTHING' if value >= HIGH else 'ON SOMETHING (holding)'


def main() -> None:
    run = sys.argv[1]
    board = {}
    for path in SETS:
        if path.exists():
            board.update({e['path']: e['board_index'] for e in json.loads(path.read_text())})
    episodes = sorted(glob.glob(os.path.expanduser(f'~/evals/t8_{run}_p*/*/*/static.json')))
    if not episodes:
        sys.exit(f'no finished episodes for run {run}')
    OUT.mkdir(exist_ok=True)
    out_path = OUT / f'{run}.mp4'
    big, small = font(22), font(18)
    with av.open(str(out_path), 'w') as out:
        stream = out.add_stream('libx264', rate=FPS)
        stream.width, stream.height, stream.pix_fmt = 1248, 432, 'yuv420p'
        for n, f in enumerate(episodes, 1):
            d = Path(f).parent
            s = json.loads(Path(f).read_text())
            key = '/'.join(str(s[k]) for k in KEYS)
            sides = s.get('molmo.exterior_sides') or ['left', 'right']
            shoulder = 'image.exterior' if sides[0] == 'left' else 'image.exterior_2'
            st, shoulder_images = frames(d, shoulder)
            wt, wrist_images = frames(d, 'image.wrist')
            gt, grip = series(d, 'grip')
            tt, target = series(d, 'target_grip')
            result = 'SOLVED' if s.get('eval.success') else 'not solved'
            title = f"{run}  episode {n}/{len(episodes)}  board #{board.get(key, '?')}  \"{s['eval.task']}\"  -> {result}"
            for i, t in enumerate(st):
                canvas = Image.new('RGB', (1248, 432), (20, 20, 20))
                canvas.paste(Image.fromarray(shoulder_images[i]).resize((624, 352)), (0, 40))
                w = min(np.searchsorted(wt, t), len(wrist_images) - 1)
                canvas.paste(Image.fromarray(wrist_images[w]).resize((624, 352)), (624, 40))
                g = grip[min(np.searchsorted(gt, t), len(grip) - 1)]
                c = target[min(np.searchsorted(tt, t), len(target) - 1)]
                draw = ImageDraw.Draw(canvas)
                draw.text((8, 8), title, font=big, fill=(255, 255, 255))
                draw.text((8, 48), 'left shoulder', font=small, fill=(255, 255, 0))
                draw.text((632, 48), 'wrist', font=small, fill=(255, 255, 0))
                colour = (255, 90, 90) if g >= HIGH else (90, 255, 90) if g >= LOW else (220, 220, 220)
                draw.text((8, 400), f't = {t - st[0]:5.1f} s   gripper command: {"CLOSE" if c > 0.5 else "open"}',
                          font=big, fill=(255, 255, 255))
                draw.text((560, 400), f'fingers: {reading(g)} ({g:.2f})', font=big, fill=colour)
                frame = av.VideoFrame.from_ndarray(np.asarray(canvas), format='rgb24')
                for packet in stream.encode(frame):
                    out.mux(packet)
            print(f'{n}: board #{board.get(key, "?")} {s["eval.task"]} {result}, {len(st) / FPS:.0f} s')
        for packet in stream.encode():
            out.mux(packet)
    print(f'video: {out_path}')
    if '--open' in sys.argv:
        subprocess.Popen(['xdg-open', str(out_path)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    main()

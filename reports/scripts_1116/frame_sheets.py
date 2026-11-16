"""Make the example pictures of the README update of 16 November in reports_1116/images/.

Usage (a Python with av and pillow, for example the positronic environment):
  python reports_1116/frame_sheets.py <~/evals folder> <real-robot check folder check_2026-11-10>
Each episode sheet: 8 frames of the shoulder camera (top two rows) and 8 of the wrist camera (bottom two rows), evenly
spread over the episode. The camera sheet: the first frame of both shoulder cameras and the wrist camera of 6
real-robot episodes.
"""

import json
import sys
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / 'images'


def frames(path: Path, n: int | None = 8, size=(320, 240)) -> list[Image.Image]:
    with av.open(str(path)) as c:
        all_frames = [f.to_ndarray(format='rgb24') for f in c.decode(video=0)]
    idx = [0] if n is None else np.linspace(0, len(all_frames) - 1, n).astype(int)
    return [Image.fromarray(all_frames[i]).resize(size) for i in idx]


def episode_sheet(episode: Path, name: str) -> None:
    rows = [frames(episode / 'image.exterior.mp4'), frames(episode / 'image.wrist.mp4')]
    sheet = Image.new('RGB', (320 * 4, 240 * 4))
    for r, row in enumerate(rows):
        for i, im in enumerate(row):
            sheet.paste(im, ((i % 4) * 320, (r * 2 + i // 4) * 240))
    sheet.save(OUT / name, quality=80)


def find(evals: Path, pattern: str, task: str) -> Path:
    for f in sorted(evals.glob(pattern)):
        if json.loads(f.read_text()).get('eval.task') == task:
            return f.parent
    raise FileNotFoundError(f'{pattern} {task}')


def camera_sheet(check: Path) -> None:
    outcomes = [o for o in json.loads((check / 'real_robot' / 'outcomes.json').read_text()) if o['take'] == 1][:6]
    sheet = Image.new('RGB', (960, 260 * len(outcomes)), 'white')
    draw = ImageDraw.Draw(sheet)
    for r, o in enumerate(outcomes):
        d = check / 'real_robot' / o['episode']
        draw.text((5, r * 260 + 2), o['instruction'] + '   [exterior | exterior_2 | wrist]', fill='black')
        for i, name in enumerate(('image.exterior.mp4', 'image.exterior_2.mp4', 'image.wrist.mp4')):
            sheet.paste(frames(d / name, None)[0], (i * 320, r * 260 + 18))
    sheet.save(OUT / 'real_robot_cameras.jpg', quality=80)


def main() -> None:
    evals, check = Path(sys.argv[1]).expanduser(), Path(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    episode_sheet(evals / 't8_conc_v3_ps4_1/000000000000/000000000001', 'v3_open_miss_dresser422.jpg')
    episode_sheet(evals / 't8_conc_v3_ps3_1/000000000000/000000000005', 'v3_pick_stopwatch555.jpg')
    episode_sheet(find(evals, 'rl_v3jpeg_s*_p1/**/static.json', 'ButterAboveRaisinTask'), 'robolab_frozen_butter.jpg')
    episode_sheet(find(evals, 'rl_v3jpeg_s*_p1/**/static.json', 'StackYellowOnRedTask'), 'robolab_wrong_block.jpg')
    camera_sheet(check)


if __name__ == '__main__':
    main()

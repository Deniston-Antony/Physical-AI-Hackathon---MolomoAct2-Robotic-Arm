"""Show one board episode of all downloaded teams side by side: a video, or a picture of frames.

Usage: ~/molmobot_src/venv/bin/python competition_runs/board_videos/side_by_side.py <board #> [options]
  --camera exterior | exterior_2 | wrist   the camera (default exterior, the first shoulder camera)
  --sheet                                  a picture: 6 frames of each team, from the start to the end
  --open                                   open the result in the desktop viewer
The output goes to competition_runs/board_videos/compare/. Board # is the episode index of the board (0-319), as in
compare_top.md. The teams come from the replay folders on the SSD (download_board.py).
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPLAYS = Path('/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/board_replays')
OUT = Path(__file__).resolve().parent / 'compare'
OUR_TAG = 'd2504d'
FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
TILE_W, TILE_H, BAR = 416, 234, 26
COLS = 3


def font(size: int) -> ImageFont.ImageFont:
    return ImageFont.truetype(FONT_FILE, size) if os.path.exists(FONT_FILE) else ImageFont.load_default()


def teams() -> list[dict]:
    snapshot = json.loads(sorted(REPLAYS.glob('board_*.json'))[-1].read_text())
    rank = {r['submission_id']: r['rank'] for r in snapshot}
    out = []
    for folder in REPLAYS.iterdir():
        if (folder / 'replay.json').exists():
            tag, sub = folder.name.split('_')[-2:]
            out.append({'folder': folder, 'name': folder.name.rsplit('_', 2)[0].replace('_', ' '), 'tag': tag,
                        'rank': rank.get(sub, 99), 'eps': json.loads((folder / 'replay.json').read_text())['episodes']})
    return sorted(out, key=lambda t: t['rank'])


def frames(path: Path) -> list[np.ndarray]:
    with av.open(str(path)) as c:
        return [f.to_ndarray(format='rgb24') for f in c.decode(video=0)]


def label(t: dict, ep: dict) -> tuple[str, tuple[int, int, int]]:
    ok = ep['values']['outcome'] == 'Success'
    who = 'US (v3)' if t['tag'] == OUR_TAG else f"#{t['rank']} {t['name'][:16]}"
    return f"{who}: {'SOLVED' if ok else 'failed'} {ep['duration_s']:.1f} s", (90, 255, 90) if ok else (255, 90, 90)


def tile(img: np.ndarray, text: str, colour: tuple, small: ImageFont.ImageFont, faded: bool) -> Image.Image:
    im = Image.new('RGB', (TILE_W, TILE_H + BAR), (20, 20, 20))
    pic = Image.fromarray(img).resize((TILE_W, TILE_H))
    if faded:
        pic = Image.blend(pic, Image.new('RGB', pic.size, (0, 0, 0)), 0.5)
    im.paste(pic, (0, BAR))
    ImageDraw.Draw(im).text((4, 4), text, font=small, fill=colour)
    return im


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('index', type=int)
    p.add_argument('--camera', default='exterior', choices=['exterior', 'exterior_2', 'wrist'])
    p.add_argument('--sheet', action='store_true')
    p.add_argument('--open', action='store_true')
    a = p.parse_args()
    ts = teams()
    task = ts[0]['eps'][a.index]['values']['task']
    clips = [frames(t['folder'] / 'episodes' / str(a.index) / f'image.{a.camera}.mp4') for t in ts]
    labels = [label(t, t['eps'][a.index]) for t in ts]
    small, big = font(15), font(18)
    OUT.mkdir(exist_ok=True)
    title = f'board #{a.index}: "{task}"  camera {a.camera}'
    if a.sheet:
        n = 6
        sheet = Image.new('RGB', (n * TILE_W, 30 + len(ts) * (TILE_H + BAR)), (0, 0, 0))
        ImageDraw.Draw(sheet).text((6, 6), title + '  (columns: 0, 20, 40, 60, 80, 100 % of each episode)',
                                   font=big, fill=(255, 255, 255))
        for r, (clip, (text, colour)) in enumerate(zip(clips, labels)):
            for c in range(n):
                k = round(c * (len(clip) - 1) / (n - 1))
                sheet.paste(tile(clip[k], f'{text}  t={k / 15:.1f}', colour, small, False),
                            (c * TILE_W, 30 + r * (TILE_H + BAR)))
        out_path = OUT / f'board{a.index}_{a.camera}_sheet.png'
        sheet.save(out_path)
    else:
        rows = -(-len(ts) // COLS)
        w, h = COLS * TILE_W, 30 + rows * (TILE_H + BAR)
        out_path = OUT / f'board{a.index}_{a.camera}.mp4'
        with av.open(str(out_path), 'w') as out:
            stream = out.add_stream('libx264', rate=15)
            stream.width, stream.height, stream.pix_fmt = w, h, 'yuv420p'
            for k in range(max(len(c) for c in clips)):
                canvas = Image.new('RGB', (w, h), (0, 0, 0))
                ImageDraw.Draw(canvas).text((6, 6), f'{title}   t = {k / 15:4.1f} s', font=big, fill=(255, 255, 255))
                for i, (clip, (text, colour)) in enumerate(zip(clips, labels)):
                    canvas.paste(tile(clip[min(k, len(clip) - 1)], text, colour, small, k >= len(clip)),
                                 ((i % COLS) * TILE_W, 30 + (i // COLS) * (TILE_H + BAR)))
                for packet in stream.encode(av.VideoFrame.from_ndarray(np.asarray(canvas), format='rgb24')):
                    out.mux(packet)
            for packet in stream.encode():
                out.mux(packet)
    print(out_path)
    if a.open:
        subprocess.Popen(['xdg-open', str(out_path)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    main()

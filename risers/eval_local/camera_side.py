"""Tell the left shoulder camera from the right one by where the white robot base sits in the first frame.

The left shoulder camera sees the base in the lower right of the image, the right one in the lower left.
Each episode records both shoulder cameras, so the pair decides: the video whose base sits further right is the left
camera.
Usage:
  python camera_side.py check <local run dir>...   accuracy on local runs, which record `molmo.exterior_sides`
"""

import json
import sys
from pathlib import Path

import av
import numpy as np


def first_frame(path) -> np.ndarray:
    with av.open(str(path)) as c:
        return next(c.decode(c.streams.video[0])).to_ndarray(format='rgb24')


def white_share(img: np.ndarray) -> tuple[float, float]:
    """Share of near-white, grey-free pixels in the lower-left and the lower-right corners."""
    h, w, _ = img.shape
    rgb = img.astype(np.int16)
    white = (rgb.min(axis=2) > 170) & (rgb.max(axis=2) - rgb.min(axis=2) < 30)
    lower = white[h // 2 :]
    return float(lower[:, : w // 3].mean()), float(lower[:, 2 * w // 3 :].mean())


def exterior_side(exterior: np.ndarray, exterior_2: np.ndarray) -> str:
    """The side of the camera in ``exterior``, from the first frames of both exterior cameras."""
    def lean(img):
        left_corner, right_corner = white_share(img)
        return right_corner - left_corner
    return 'left' if lean(exterior) > lean(exterior_2) else 'right'


def check(runs: list[str]) -> None:
    ok = n = 0
    for run in runs:
        for st in Path(run).glob('*/*/static.json'):
            sides = json.loads(st.read_text()).get('molmo.exterior_sides')
            if not sides:
                continue
            guess = exterior_side(*(first_frame(st.parent / f'image.{c}.mp4') for c in ('exterior', 'exterior_2')))
            ok += guess == sides[0]
            n += 1
    print(f'{ok}/{n} correct')


if __name__ == '__main__':
    check(sys.argv[2:])

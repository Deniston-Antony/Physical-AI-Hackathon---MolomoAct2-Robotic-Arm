"""The rules of the MolmoBot image v3 that do not depend on the model, as `positronic.vendors.molmobot.policy` has them."""

import re

import numpy as np

# A pick-and-place task in any wording of the board: "on", "in or on" or "next to" the target.
_PLACE_TASK = re.compile(r'pick up the (?P<item>.+?) and place it (?:on|in or on|next to) the .+', re.IGNORECASE)


def _white_lean(img: np.ndarray) -> float:
    """How much more of the lower right than of the lower left is near-white: the robot base at the home pose."""
    h, w, _ = img.shape
    rgb = np.asarray(img, dtype=np.int16)
    white = (rgb.min(axis=2) > 170) & (rgb.max(axis=2) - rgb.min(axis=2) < 30)
    lower = white[h // 2 :]
    return float(lower[:, 2 * w // 3 :].mean() - lower[:, : w // 3].mean())


def exterior_side(exterior: np.ndarray, exterior_2: np.ndarray) -> str:
    """The shoulder of the camera in ``exterior``, from frames of both shoulder cameras at the home pose.

    The left shoulder camera sees the robot base in the lower right of its image.
    """
    return 'left' if _white_lean(exterior) > _white_lean(exterior_2) else 'right'


def pick_part(task: str) -> str | None:
    """The pick part of a pick-and-place task in the wording of a pick task, or None for other tasks."""
    match = _PLACE_TASK.fullmatch(task.strip())
    return None if match is None else f'pick up the {match["item"]}.'

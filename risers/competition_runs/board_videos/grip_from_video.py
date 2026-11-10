"""Read the gripper closure (0 open .. 1 closed) from the wrist camera video, for runs that have no gripper data.

The fingers are at a fixed place in the wrist image. A linear model of the finger area of the image gives the
closure. It learns from our own local runs, where the recorded `grip` signal gives the true closure.
  train:  ~/molmobot_src/venv/bin/python competition_runs/board_videos/grip_from_video.py train
          (fits on our local runs, checks on runs it did not see, saves grip_model.npz)
The functions `closure_series` and `grasp_events` read one wrist video with the saved model.
"""

import glob
import os
import sys
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
MODEL = HERE / 'grip_model.npz'
FPS = 500 / 33  # the frame rate of the board replay videos
# The finger area of a 624 x 352 wrist image: rows and columns.
ROWS, COLS, BLOCK = (170, 310), (200, 590), 10
TRAIN_RUNS = ['t8_op_pull', 't8_op_step2400', 't8_cl_push', 't8_cl_both', 't8_img_v4', 'molmobot_mixed40',
              'molmobot_nextto16b', 't8_mid1000_open']
CHECK_RUNS = ['t8_op_regrasp', 'molmobot_nextto16c', 't8_cl_cam']


def features(img: np.ndarray) -> np.ndarray:
    crop = img[ROWS[0]:ROWS[1], COLS[0]:COLS[1]].astype(np.float32).mean(axis=2)
    h, w = (ROWS[1] - ROWS[0]) // BLOCK, (COLS[1] - COLS[0]) // BLOCK
    blocks = crop[: h * BLOCK, : w * BLOCK].reshape(h, BLOCK, w, BLOCK)
    dark = (blocks < 45).mean(axis=(1, 3))
    gray = blocks.mean(axis=(1, 3)) / 255
    return np.concatenate([dark.ravel(), gray.ravel(), [1.0]]).astype(np.float32)


def video_features(path: Path, every: int = 1) -> np.ndarray:
    out = []
    with av.open(str(path)) as c:
        for k, frame in enumerate(c.decode(video=0)):
            if k % every == 0:
                out.append(features(frame.to_ndarray(format='rgb24')))
    return np.asarray(out)


def episode_samples(d: str, every: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Features, true closure and times (s from the start) of every `every`-th wrist frame of a local episode."""
    t = pq.read_table(d + 'grip.parquet', columns=['ts.harness.world', 'value'])
    gt = np.asarray(t.column(0).to_pylist()) / 1e9
    g = np.asarray(t.column(1).to_pylist(), dtype=np.float64).ravel()
    wt = np.asarray(pq.read_table(d + 'image.wrist.frames.parquet', columns=['ts.harness.world']).column(0)) / 1e9
    x = video_features(Path(d) / 'image.wrist.mp4', every)
    wt = wt[::every][: len(x)]
    y = g[np.clip(np.searchsorted(gt, wt), 0, len(g) - 1)]
    return x[: len(wt)], np.clip(y, 0, 1), wt - wt[0]


def episodes_of(runs: list[str]) -> list[str]:
    out = []
    for run in runs:
        out += sorted(os.path.dirname(f) + '/' for f in glob.glob(os.path.expanduser(f'~/evals/{run}*/*/*/static.json')))
    return out


def grasp_events(closure: np.ndarray, times: np.ndarray, hold: int = 8) -> dict:
    """Close events of a closure series: the median of 9 frames is above 0.5 for at least `hold` frames.

    The gripper opens again when the median falls below 0.25. A real close keeps the fingers closed for more than
    0.5 s, so a shorter one is noise of the video model.
    """
    pad = np.pad(closure, 4, mode='edge')
    smooth = np.median(np.lib.stride_tricks.sliding_window_view(pad, 9), axis=1)
    closes, k = [], 0
    while k < len(smooth):
        if smooth[k] > 0.5:
            end = k
            while end < len(smooth) and smooth[end] >= 0.25:
                end += 1
            if (smooth[k:end] > 0.5).sum() >= hold:
                closes.append(float(times[k]))
            k = end
        k += 1
    return {'first_close_s': closes[0] if closes else None, 'closes': len(closes), 'close_times': closes}


def closure_series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    w = np.load(MODEL)['w']
    x = video_features(path)
    return np.clip(x @ w, 0, 1), np.arange(len(x)) / FPS


def train() -> None:
    rng = np.random.default_rng(0)
    eps = episodes_of(TRAIN_RUNS)
    eps = list(rng.choice(eps, size=min(160, len(eps)), replace=False))
    xs, ys = [], []
    for n, d in enumerate(eps, 1):
        x, y, _ = episode_samples(d, every=4)
        xs.append(x)
        ys.append(y)
        if n % 40 == 0:
            print(f'  {n}/{len(eps)} training episodes read', flush=True)
    x, y = np.concatenate(xs), np.concatenate(ys)
    lam = 1.0
    w = np.linalg.solve(x.T @ x + lam * np.eye(x.shape[1], dtype=np.float32), x.T @ y.astype(np.float32))
    np.savez(MODEL, w=w)
    print(f'trained on {len(x)} frames of {len(eps)} episodes')
    # Check on runs that the model did not see: frame accuracy and the error of the first-close time.
    errs, acc, n_eps = [], [], 0
    for d in episodes_of(CHECK_RUNS):
        x, y, t = episode_samples(d, every=1)
        p = np.clip(x @ w, 0, 1)
        acc.append(((p > 0.5) == (y > 0.5)).mean())
        a, b = grasp_events(p, t), grasp_events(y, t)
        if a['first_close_s'] is not None and b['first_close_s'] is not None:
            errs.append(abs(a['first_close_s'] - b['first_close_s']))
        elif (a['first_close_s'] is None) != (b['first_close_s'] is None):
            errs.append(np.inf)
        n_eps += 1
    errs = np.asarray(errs)
    print(f'check on {n_eps} unseen episodes: frame accuracy {np.mean(acc):.3f}; first-close time error '
          f'median {np.median(errs[np.isfinite(errs)]):.2f} s, within 1 s in {np.mean(errs <= 1):.0%} of episodes, '
          f'missed or extra first close in {np.sum(~np.isfinite(errs))}')


if __name__ == '__main__':
    if sys.argv[1:] == ['train']:
        train()

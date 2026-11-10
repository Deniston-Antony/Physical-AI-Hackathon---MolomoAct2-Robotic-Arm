"""Arrange MolmoSpaces datagen output as MolmoBot training data: <dst>/train/house_*/ with *.h5 and *.mp4.

MolmoBot's loader finds the video of camera C of trajectory i at traj_i/obs/sensor_data/C, a 100-byte name. Our
datagen leaves that group empty, so this script writes the names. Trajectory traj_i of trajectories_<suffix>.h5 has
the video episode_<i:08d>_<camera>_<suffix>.mp4 (the frame counts match the trajectory lengths).

Each source h5 becomes two h5 copies: in one, the camera `risers_exo` is the left shoulder camera; in the other, it
is the right shoulder camera. `risers_wrist` is the wrist camera in both. The mp4 files are hard links (or symlinks
across file systems), so no video is copied.

The script also writes <dst>/train/valid_trajectory_index.json, which the loader needs, over all h5 files there.

Usage: python prep_train_data.py <datagen output dir of one config> <dst dataset dir> <tag>
"""

import json
import os
import shutil
import sys
from pathlib import Path

import h5py
import numpy as np

LEFT = ('droid_shoulder_light_randomization', 'exo_camera_1')
RIGHT = ('right_shoulder_camera',)
WRIST = ('wrist_camera_zed_mini', 'wrist_camera')


def first(names: tuple[str, ...], present) -> str:
    for name in names:
        if name in present:
            return name
    raise KeyError(f'none of {names} in {list(present)}')


def name_bytes(filename: str) -> np.ndarray:
    raw = filename.encode('utf-8')
    out = np.zeros(100, dtype=np.uint8)
    out[: len(raw)] = list(raw)
    return out


def link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        os.symlink(src.resolve(), dst)


def main() -> None:
    src_root, dst_root, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    houses = trajs = skipped = 0
    for house in sorted(src_root.glob('*/house_*')):
        h5s = sorted(house.glob('trajectories_*.h5'))
        if not h5s:
            continue
        out = dst_root / 'train' / f'{house.name}_{tag}_{house.parent.name}'
        out.mkdir(parents=True, exist_ok=True)
        for mp4 in house.glob('*.mp4'):
            link(mp4, out / mp4.name)
        for h5 in h5s:
            try:
                h5py.File(h5, 'r').close()
            except OSError:
                print(f'skip unreadable {h5} (a run stopped while it was written)')
                continue
            suffix = h5.stem.removeprefix('trajectories')
            for side, names in (('left', LEFT), ('right', RIGHT)):
                copy = out / f'{h5.stem}_{side}.h5'
                shutil.copyfile(h5, copy)
                with h5py.File(copy, 'r+') as f:
                    for key in [k for k in f.keys() if k.startswith('traj_')]:
                        i = int(key.removeprefix('traj_'))
                        obs = f[key]['obs']
                        cams = list(obs['sensor_param'].keys())
                        sensors = obs.require_group('sensor_data')
                        videos = {
                            alias: f'episode_{i:08d}_{first(cam_names, cams)}{suffix}.mp4'
                            for alias, cam_names in (('risers_exo', names), ('risers_wrist', WRIST))
                        }
                        if not all((house / v).exists() for v in videos.values()):
                            del f[key]
                            skipped += side == 'left'
                            continue
                        for alias, video in videos.items():
                            if alias in sensors:
                                del sensors[alias]
                            sensors.create_dataset(alias, data=name_bytes(video))
                        trajs += side == 'left'
        houses += 1
    print(f'{tag}: {houses} house folders, {trajs} demos (x2 views), {skipped} without videos -> {dst_root}/train')
    write_index(dst_root / 'train')


def write_index(train: Path) -> None:
    """Write valid_trajectory_index.json over every h5 in `train`: the successful trajectories and their lengths."""
    index: dict[str, dict[str, dict[str, int]]] = {}
    for h5 in sorted(train.glob('*/*.h5')):
        with h5py.File(h5, 'r') as f:
            lengths = {
                key: int(f[key]['actions']['joint_pos'].shape[0])
                for key in f.keys()
                if key.startswith('traj_') and bool(np.asarray(f[key]['success']).any())
            }
        if lengths:
            index.setdefault(h5.parent.name, {})[f'{h5.parent.name}/{h5.name}'] = lengths
    (train / 'valid_trajectory_index.json').write_text(json.dumps(index))
    print(f'index: {sum(len(t) for h in index.values() for t in h.values())} trajectories in {len(index)} houses')


if __name__ == '__main__':
    main()

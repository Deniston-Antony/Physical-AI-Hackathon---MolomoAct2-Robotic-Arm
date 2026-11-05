"""Download a random train / eval / test subset of the Franka part of allenai/molmobot-data.

The task mix follows the competition board (molmo.competition_v2) without open and close, because
molmobot-data has no Franka open or close data: pick 116, pick-and-place 112, color 16, next-to 16 of 260.
Each episode comes from a different house, and a house is in one split only.
Each episode is a successful trajectory whose robot and sensors are in the competition ranges (COMPETITION):
the franka_droid robot with an open gripper at the start, an arm start pose near DROID home, 624x352 images at a
66 ms step, and the wrist and left shoulder cameras of FrankaOmniPurposeCameraSystem with their pose and field
of view in the benchmark ranges. The episode keeps only the videos of these two cameras, because the competition
robot has no other camera. The right shoulder camera of the competition is a mirror of the left one, and
molmobot-data does not record it.
Each episode keeps its two videos and an h5 file that holds only its trajectory, in the
MolmoSpaces datagen layout that convert_to_positronic.py reads:
  <out>/<split>/<config>/<house>_b<batch>_t<traj>/trajectories_batch_<batch>.h5
  <out>/<split>/<config>/<house>_b<batch>_t<traj>/episode_<traj:08d>_<camera>_batch_<batch>.mp4
<out>/manifest.json lists every episode.

Run from the positronic repo:
  uv run --locked --with h5py --with zstandard python ../datagen/molmobot_subset.py --out ~/datasets/molmobot_franka_350
"""

import argparse
import base64
import io
import json
import pickle
import re
import tarfile
import threading
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import h5py
import numpy as np
import pyarrow.parquet as pq
import zstandard
from scipy.spatial.transform import Rotation

BASE = 'https://huggingface.co/datasets/allenai/molmobot-data/resolve/main'
# The robot and sensor ranges of the competition, measured over the 33,915 episodes of the 20 benchmark files
# that molmo.competition_v2 draws from (molmospaces-bench-v1 and -v2, FrankaDroidCameraSystem and
# FrankaOmniPurposeCameraSystem). Quaternions are wxyz. An episode matches when each value is in its range.
COMPETITION = dict(
    camera_system='FrankaOmniPurposeCameraSystem',
    robot='franka_droid',
    img_resolution=(624, 352),
    policy_dt_ms=66.0,
    wrist_camera='wrist_camera_zed_mini',
    wrist_fov=(48.0, 56.74),
    wrist_offset=((0.016, 0.063, 0.002), (0.046, 0.085, 0.042)),
    wrist_nominal_wxyz=(-0.006, -0.001, 0.986, 0.169),
    wrist_max_tilt_deg=9.745,
    shoulder_camera='droid_shoulder_light_randomization',
    shoulder_fov=(71.0, 71.0),
    shoulder_offset=((0.05, 0.52, 0.61), (0.15, 0.62, 0.71)),
    shoulder_nominal_wxyz=(-0.363, -0.124, 0.426, 0.819),
    shoulder_max_tilt_deg=13.701,
    arm=((-0.26, -1.045, -0.26, -2.616, -0.26, 1.311, -1.571), (0.26, -0.525, 0.26, -2.096, 0.26, 1.831, 1.571)),
    gripper_open_max=0.01,
)
KEEP_CAMERAS = (COMPETITION['shoulder_camera'], COMPETITION['wrist_camera'])
TOLERANCE = 1e-3
SAFE_PICKLE = {('numpy', 'ndarray'), ('numpy', 'dtype'), ('numpy.core.multiarray', '_reconstruct'),
               ('numpy._core.multiarray', '_reconstruct'), ('numpy.core.multiarray', 'scalar'),
               ('numpy._core.multiarray', 'scalar'), ('pathlib', 'PosixPath'), ('pathlib', 'Path')}
MIX = {  # episodes on the competition board, per molmobot-data config
    'FrankaPickOmniCamConfig': 116,
    'FrankaPickAndPlaceOmniCamConfig': 112,
    'FrankaPickAndPlaceColorOmniCamConfig': 16,
    'FrankaPickAndPlaceNextToOmniCamConfig': 16,
}
SPLITS = {'train': 200, 'eval': 50, 'test': 100}
KEEP_FILE = re.compile(r'(\.h5|_(' + '|'.join(KEEP_CAMERAS) + r')_batch_[^/]+\.mp4)$')
HOUSE = re.compile(r'_(house_\d+)\.tar\.zst$')


def allocate(total: int) -> dict[str, int]:
    """Episodes per config for a split of `total` episodes, by the largest remainder."""
    weight = sum(MIX.values())
    exact = {c: total * n / weight for c, n in MIX.items()}
    counts = {c: int(x) for c, x in exact.items()}
    for c in sorted(exact, key=lambda c: exact[c] - counts[c], reverse=True)[: total - sum(counts.values())]:
        counts[c] += 1
    return counts


def fetch(config: str, entry: dict, attempts: int = 4) -> bytes:
    url = f'{BASE}/{config}/train_shards/{entry["shard_id"]:05d}.tar'
    end = entry['offset'] + entry['size'] - 1
    req = urllib.request.Request(url, headers={'Range': f'bytes={entry["offset"]}-{end}'})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            if len(data) == entry['size']:
                return data
            error = OSError(f'{entry["path"]}: got {len(data)} bytes, expected {entry["size"]}')
        except OSError as e:
            error = e
        print(f'retry {attempt + 1} for {entry["path"]}: {error}', flush=True)
    raise error


def unpack(data: bytes) -> dict[str, bytes]:
    files = {}
    with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data)) as reader:
        with tarfile.open(fileobj=reader, mode='r|') as tar:
            for m in tar:
                if m.isfile() and KEEP_FILE.search(m.name):
                    files[m.name] = tar.extractfile(m).read()
    return files


class _Stub:
    """Stands in for each config class of the frozen config, which this script does not import."""

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        self.__dict__ = state.get('__dict__', state) if isinstance(state, dict) else {'state': state}


class _ConfigUnpickler(pickle.Unpickler):
    """Loads only numpy arrays and paths. Each other class becomes a stub with its name and fields."""

    def find_class(self, module, name):
        if (module, name) in SAFE_PICKLE:
            return super().find_class(module, name)
        return type(name, (_Stub,), {})


def _decode(datum) -> dict:
    return json.loads(datum.tobytes().decode('utf-8').rstrip('\x00'))


def episode_setup(traj) -> dict:
    """The robot and sensor settings that recorded one trajectory."""
    scene = json.loads(traj['obs_scene'][()].decode())
    config = _ConfigUnpickler(io.BytesIO(base64.b64decode(scene['frozen_config']))).load().__dict__
    system = config['camera_config']
    cameras = {c.__dict__['name']: c.__dict__ for c in system.__dict__['cameras']}
    qpos = _decode(traj['obs/agent/qpos'][0])
    return dict(camera_system=type(system).__name__, img_resolution=tuple(system.__dict__.get('img_resolution') or ()),
                robot=config['robot_config'].__dict__.get('name'), policy_dt_ms=scene.get('policy_dt_ms'),
                cameras=cameras, arm=qpos.get('arm'), gripper=qpos.get('gripper'))


def _in_box(value, low, high) -> bool:
    return value is not None and np.all(np.asarray(value) >= np.asarray(low) - TOLERANCE) and np.all(
        np.asarray(value) <= np.asarray(high) + TOLERANCE)


def _tilt_deg(wxyz, nominal_wxyz) -> float:
    rot = Rotation.from_quat(wxyz, scalar_first=True) * Rotation.from_quat(nominal_wxyz, scalar_first=True).inv()
    return float(np.degrees(rot.magnitude()))


def mismatches(setup: dict) -> list[str]:
    """The settings of `setup` that are outside the competition ranges."""
    c = COMPETITION
    bad = [k for k in ('camera_system', 'robot', 'policy_dt_ms') if setup[k] != c[k]]
    if setup['img_resolution'] != c['img_resolution']:
        bad.append('img_resolution')
    for role in ('wrist', 'shoulder'):
        cam = setup['cameras'].get(c[f'{role}_camera'])
        if cam is None:
            bad.append(f'{role}_camera')
            continue
        if not _in_box(cam['fov'], *c[f'{role}_fov']):
            bad.append(f'{role}_fov')
        if not _in_box(cam['camera_offset'], *c[f'{role}_offset']):
            bad.append(f'{role}_offset')
        if _tilt_deg(cam['camera_quaternion'], c[f'{role}_nominal_wxyz']) > c[f'{role}_max_tilt_deg'] + TOLERANCE:
            bad.append(f'{role}_tilt')
    if not _in_box(setup['arm'], *c['arm']):
        bad.append('arm_start')
    if setup['gripper'] is None or max(setup['gripper']) > c['gripper_open_max']:
        bad.append('gripper_start')
    return bad


def matching_trajectories(files: dict[str, bytes], rejected: Counter) -> list[tuple[str, int]]:
    """(h5 name, trajectory index) of each valid, successful trajectory that matches the competition setup."""
    found = []
    for name, raw in files.items():
        if not name.endswith('.h5'):
            continue
        with h5py.File(io.BytesIO(raw), 'r') as f:
            keys = sorted(int(k[5:]) for k in f if k.startswith('traj_'))
            mask = f['valid_traj_mask'][()] if 'valid_traj_mask' in f else [i in keys for i in range(max(keys) + 1)]
            for i in keys:
                if i >= len(mask) or not mask[i] or not f[f'traj_{i}/success'][()].any():
                    rejected['not_successful'] += 1
                    continue
                bad = mismatches(episode_setup(f[f'traj_{i}']))
                rejected.update(bad)
                if bad:
                    rejected['episodes_out_of_range'] += 1
                else:
                    found.append((name, i))
    return sorted(found)


def save_episode(files, h5_name, traj, dest: Path) -> dict:
    batch = re.search(r'_batch_(.+)\.h5$', h5_name).group(1)
    dest.mkdir(parents=True, exist_ok=True)
    with h5py.File(io.BytesIO(files[h5_name]), 'r') as src, h5py.File(dest / f'trajectories_batch_{batch}.h5', 'w') as out:
        src.copy(src[f'traj_{traj}'], out, name=f'traj_{traj}')
        out['valid_traj_mask'] = np.array([i == traj for i in range(traj + 1)])
        t = src[f'traj_{traj}']
        scene = json.loads(t['obs_scene'][()].decode())
        steps = len(t['success'])
        first_success = int(np.argmax(t['success'][()]))
        setup = episode_setup(t)
    prefix = f'episode_{traj:08d}_'
    videos = []
    for name, raw in files.items():
        base = name.split('/')[-1]
        if base.startswith(prefix) and base.endswith(f'_batch_{batch}.mp4'):
            (dest / base).write_bytes(raw)
            videos.append(base[len(prefix) : -len(f'_batch_{batch}.mp4')])
    if sorted(videos) != sorted(KEEP_CAMERAS):
        raise ValueError(f'{dest}: videos {videos}, expected {KEEP_CAMERAS}')
    sensors = {role: {k: np.round(np.asarray(cam[k], dtype=float), 4).tolist() for k in ('fov', 'camera_offset', 'camera_quaternion')}
               for role, cam in (('shoulder', setup['cameras'][COMPETITION['shoulder_camera']]),
                                 ('wrist', setup['cameras'][COMPETITION['wrist_camera']]))}
    return dict(task_type=scene.get('task_type'), task_description=scene.get('task_description'),
                steps=steps, first_success=first_success, cameras=sorted(videos), robot=setup['robot'],
                camera_system=setup['camera_system'], img_resolution=list(setup['img_resolution']),
                arm_start=np.round(setup['arm'], 4).tolist(), sensors=sensors)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--meta', type=Path, default=Path.home() / 'datasets/molmobot_raw/meta')
    p.add_argument('--seed', type=int, default=20261102)
    p.add_argument('--workers', type=int, default=6)
    args = p.parse_args()
    rng = np.random.default_rng(args.seed)
    plan = {s: allocate(n) for s, n in SPLITS.items()}
    print('plan:', json.dumps(plan))

    # Shuffle the houses of each config once. Each episode takes the next house of the queue that no other
    # episode used, in any config or split.
    queues = {}
    for config in MIX:
        rows = [r for r in pq.read_table(args.meta / f'{config}_train_pkgs.parquet').to_pylist() if HOUSE.search(r['path'])]
        queues[config] = [rows[i] for i in rng.permutation(len(rows))]
    used: set[str] = set()
    manifest = []
    rejected = Counter()
    lock = threading.Lock()

    def take(config, split):
        while queues[config]:
            entry = queues[config].pop()
            house = HOUSE.search(entry['path']).group(1)
            if house not in used:
                used.add(house)
                return entry, house
        raise RuntimeError(f'{config}: no houses left')

    def one(config, split, entry, house, seed):
        files = unpack(fetch(config, entry))
        mine = Counter()
        trajs = matching_trajectories(files, mine)
        with lock:
            rejected.update(mine)
        if not trajs:
            return None
        h5_name, traj = trajs[np.random.default_rng(seed).integers(len(trajs))]
        batch = re.search(r'_batch_(.+)\.h5$', h5_name).group(1)
        dest = args.out / split / config / f'{house}_b{batch}_t{traj}'
        info = save_episode(files, h5_name, traj, dest)
        return dict(split=split, config=config, house=house, part=entry['part'], shard_id=entry['shard_id'],
                    package=entry['path'], batch=batch, traj=traj, dir=str(dest.relative_to(args.out)), **info)

    with ThreadPoolExecutor(args.workers) as ex:
        for split, counts in plan.items():
            for config, want in counts.items():
                got = 0
                while got < want:
                    jobs = [ex.submit(one, config, split, *take(config, split), int(rng.integers(2**31)))
                            for _ in range(want - got)]
                    for j in as_completed(jobs):
                        r = j.result()
                        if r:
                            manifest.append(r)
                            got += 1
                    print(f'{split} {config}: {got}/{want}', flush=True)

    manifest.sort(key=lambda r: (r['split'], r['config'], r['dir']))
    (args.out / 'manifest.json').write_text(json.dumps(
        dict(seed=args.seed, plan=plan, competition=COMPETITION, rejected=dict(rejected), episodes=manifest), indent=1))
    print('rejected trajectories:', dict(rejected))
    print('wrote', len(manifest), 'episodes to', args.out)


if __name__ == '__main__':
    main()

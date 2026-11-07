"""Convert MolmoSpaces data-generation output into a Positronic dataset, laid out as the competition records.

Each successful trajectory becomes one Positronic episode with the signals the GR00T `droid_molmo` recipes read.
The episode ends SUCCESS_TAIL_STEPS after the first success, because the competition eval ends an episode there.
  robot_state.q          7 arm joint positions (measured)
  robot_state.dq         7 arm joint velocities (measured)
  robot_state.ee_pose    grasp-site pose in the fr3_link0 frame, [x, y, z, qw, qx, qy, qz], by MuJoCo forward
                         kinematics (matches the competition's recorded ee_pose to about 1 mm)
  grip                   measured closure in [0, 1]: first finger joint / 0.824033
  target_grip            commanded closure in [0, 1]: Robotiq command / 255
  image.exterior, image.exterior_2, image.wrist
                         the left and right shoulder cameras go to the two exterior slots in a random order,
                         as the competition eval does; `molmo.exterior_sides` records the order
  eval.instruction       the task text
Static items copy the robot description (URDF, meshes, ee_frames) of a competition-format recording.

Run from the positronic repo, with one or more datagen run folders:
  uv run --locked --with h5py python ../datagen/convert_to_positronic.py \
      --input ../datagen/output/RisersPick/20261031_174849 ../datagen/output/RisersOpen/20261101_043930 \
      --output ~/datasets/risers_datagen
"""

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

import av
import h5py
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from positronic.dataset.local_dataset import LocalDatasetWriter
from pimm.time import Time

GRIPPER_QPOS_CLOSED = 0.824033  # positronic.simulator.molmo_spaces.mapping.GRIPPER_QPOS_CLOSED
ROBOTIQ_CLOSED = 255.0  # positronic.simulator.molmo_spaces.mapping.ROBOTIQ_CLOSED
LEFT_CAMERA = 'exo_camera_1'
RIGHT_CAMERA = 'right_shoulder_camera'
WRIST_CAMERA = 'wrist_camera'
# MolmoBot-Data records FrankaOmniPurposeCameraSystem: no right shoulder camera, and other camera names.
MOLMOBOT_CAMERAS = dict(left='droid_shoulder_light_randomization', right=None, wrist='wrist_camera_zed_mini')
TIMELINE = 'harness.world'
SUCCESS_TAIL_STEPS = 15  # about 1 s at the 66 ms policy step
STATIC_FROM_TEMPLATE = ('joint_signals', 'urdf', 'meshes', 'joint_names', 'gripper')
HERE = Path(__file__).resolve().parent


class ForwardKinematics:
    """Grasp-site pose in the fr3_link0 frame, from the MolmoSpaces Franka DROID model."""

    def __init__(self, robot_xml: Path):
        self.model = mujoco.MjModel.from_xml_path(str(robot_xml))
        self.data = mujoco.MjData(self.model)
        self.site = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, 'gripper/grasp_site')
        self.link0 = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, 'fr3_link0')
        joints = [mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, f'fr3_joint{i}') for i in range(1, 8)]
        self.qadr = [self.model.jnt_qposadr[j] for j in joints]

    def __call__(self, q: np.ndarray) -> np.ndarray:
        self.data.qpos[:] = 0
        self.data.qpos[self.qadr] = q
        mujoco.mj_kinematics(self.model, self.data)
        base = np.eye(4)
        base[:3, :3] = self.data.xmat[self.link0].reshape(3, 3)
        base[:3, 3] = self.data.xpos[self.link0]
        site = np.eye(4)
        site[:3, :3] = self.data.site_xmat[self.site].reshape(3, 3)
        site[:3, 3] = self.data.site_xpos[self.site]
        pose = np.linalg.inv(base) @ site
        x, y, z, w = Rotation.from_matrix(pose[:3, :3]).as_quat()
        return np.array([*pose[:3, 3], w, x, y, z], dtype=np.float64)


def instruction(scene: dict, rng: np.random.Generator) -> str:
    """The task text in the competition's wording.

    MolmoSpaces' OpeningTask describes close tasks as "Open the X", so the verb follows `task_type`. The
    competition words open and close tasks as "close the drawer.", and pick tasks both as "pick up the tissue."
    and as "Pick up the pencil"; pick tasks get one of the two styles at random.
    """
    text = (scene.get('task_description') or '').strip().rstrip('.')
    task_type = scene.get('task_type')
    if task_type in ('open', 'close'):
        return re.sub(r'^(open|close)\b', task_type, text, flags=re.IGNORECASE).lower() + '.'
    if rng.random() < 0.5:
        return text[:1].lower() + text[1:] + '.'
    return text[:1].upper() + text[1:]


def decode(raw: np.ndarray):
    """A MolmoSpaces byte-encoded JSON value, or None for a padding-only row."""
    text = bytes(raw).rstrip(b'\x00').decode()
    return json.loads(text) if text else None


def read_frames(path: Path) -> list[np.ndarray]:
    with av.open(str(path)) as container:
        return [frame.to_ndarray(format='rgb24') for frame in container.decode(container.streams.video[0])]


def episode_video(house_dir: Path, episode: int, camera: str) -> Path:
    matches = sorted(house_dir.glob(f'episode_{episode:08d}_{camera}_batch_*.mp4'))
    if not matches:
        raise FileNotFoundError(f'no {camera} video for episode {episode} in {house_dir}')
    return matches[0]


def convert_trajectory(traj, house_dir, episode, fk, rng, writer, template, source, camera_names):
    """Write one trajectory; returns the number of steps written, or 0 when it is skipped.

    `camera_names` maps left, right and wrist to the recorded camera names. A right of None puts the left camera in
    both exterior slots.
    """
    success = np.asarray(traj['success'][:], dtype=bool)
    if not success.any():
        return 0
    scene = json.loads(traj['obs_scene'][()])
    task = instruction(scene, rng)
    policy_dt_ns = int(round(float(scene.get('policy_dt_ms', 66.0)) * 1e6))

    # State i pairs with action i + 1; the first action and the last state are not used (MolmoSpaces data_format.md).
    steps = min(len(success) - 1, int(np.argmax(success)) + SUCCESS_TAIL_STEPS + 1)
    qpos = [decode(traj['obs/agent/qpos'][i]) for i in range(steps)]
    qvel = [decode(traj['obs/agent/qvel'][i]) for i in range(steps)]
    commands = [decode(traj['actions/commanded_action'][i + 1]) for i in range(steps)]
    while steps and (commands[steps - 1] is None or 'arm' not in commands[steps - 1]):
        steps -= 1  # trailing `done` sentinel
    if steps < 5:
        return 0
    # The pick-and-place planners leave the gripper out of the command while it holds its position.
    gripper_commands = []
    for command in commands[:steps]:
        if 'gripper' in command:
            gripper_commands.append(command['gripper'][0])
        elif gripper_commands:
            gripper_commands.append(gripper_commands[-1])
        else:
            raise ValueError(f'{source}: the first command has no gripper value')

    roles = [role for role in ('left', 'right', 'wrist') if camera_names[role] is not None]
    cameras = {role: read_frames(episode_video(house_dir, episode, camera_names[role])) for role in roles}
    cameras.setdefault('right', cameras['left'])
    for name, frames in cameras.items():
        if len(frames) < steps:
            raise ValueError(f'{source}: {name} has {len(frames)} frames for {steps} steps')
    sides = ['left', 'right'] if rng.random() < 0.5 else ['right', 'left']
    by_side = {'left': cameras['left'], 'right': cameras['right']}

    with writer.new_episode() as ep:
        for i in range(steps):
            ts = Time(**{TIMELINE: i * policy_dt_ns})
            q = np.asarray(qpos[i]['arm'], dtype=np.float64)
            ep.append('robot_state.q', q, ts)
            ep.append('robot_state.dq', np.asarray(qvel[i]['arm'], dtype=np.float64), ts)
            ep.append('robot_state.ee_pose', fk(q), ts)
            ep.append('robot_state.status', 0, ts)
            ep.append('grip', float(np.clip(qpos[i]['gripper'][0] / GRIPPER_QPOS_CLOSED, 0.0, 1.0)), ts)
            ep.append('target_grip', float(np.clip(gripper_commands[i] / ROBOTIQ_CLOSED, 0.0, 1.0)), ts)
            ep.append('image.exterior', by_side[sides[0]][i], ts)
            ep.append('image.exterior_2', by_side[sides[1]][i], ts)
            ep.append('image.wrist', cameras['wrist'][i], ts)
            if i == 0:
                ep.append('eval.instruction', task, ts)
        for key in STATIC_FROM_TEMPLATE:
            ep.set_static(key, template[key])
        ep.set_static('pose_signals', ['robot_state.ee_pose'])
        ep.set_static('ee_frames', {'robot_state.ee_pose': template['ee_frames']['robot_state.ee_pose']})
        ep.set_static('task', task)
        ep.set_static('eval.task', task)
        ep.set_static('eval.success', True)
        ep.set_static('eval.universe', 'sim')
        ep.set_static('eval.embodiment', 'remote.molmo_spaces.droid')
        ep.set_static('molmo.exterior_sides', sides)
        ep.set_static('molmo.task_type', scene.get('task_type'))
        ep.set_static('datagen.task_description', scene.get('task_description'))
        ep.set_static('datagen.source', source)
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', type=Path, nargs='+', required=True, help='MolmoSpaces datagen run folders')
    parser.add_argument('--output', type=Path, required=True, help='Positronic dataset directory to write')
    parser.add_argument('--robot-xml', type=Path, default=Path.home() / 'molmospaces/assets/robots/franka_droid/model.xml')
    parser.add_argument('--template-static', type=Path, default=HERE / 'template_static.json')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--limit', type=int, default=None, help='stop after this many episodes')
    parser.add_argument('--molmobot', action='store_true',
                        help='read MolmoBot-Data camera names; the left shoulder camera fills both exterior slots')
    args = parser.parse_args()

    template = json.loads(args.template_static.read_text())
    fk = ForwardKinematics(args.robot_xml)
    rng = np.random.default_rng(args.seed)
    camera_names = MOLMOBOT_CAMERAS if args.molmobot else dict(left=LEFT_CAMERA, right=RIGHT_CAMERA, wrist=WRIST_CAMERA)
    inputs = [path.expanduser().resolve() for path in args.input]
    # Sources are named from the folder above the configs, so they read `RisersPick/<run>/house_0/...`.
    root = Path(os.path.commonpath([path.parent.parent for path in inputs]))
    # MolmoSpaces also writes trajectory files under `debug/`; those are not training data.
    files = sorted(path for i in inputs for path in i.rglob('trajectories_*.h5') if 'debug' not in path.parts)
    print(f'{len(files)} trajectory files under {len(inputs)} folders')
    written = skipped = 0
    per_config = Counter()
    with LocalDatasetWriter(args.output.expanduser()) as writer:
        for path in files:
            with h5py.File(path, 'r') as f:
                trajectories = sorted((k for k in f.keys() if k.startswith('traj_')), key=lambda k: int(k[5:]))
                valid = f['valid_traj_mask'][()] if 'valid_traj_mask' in f else None
                for name in trajectories:
                    episode = int(name[5:])
                    if valid is not None and (episode >= len(valid) or not valid[episode]):
                        skipped += 1
                        continue
                    source = f'{path.relative_to(root)}#{name}'
                    try:
                        steps = convert_trajectory(
                            f[name], path.parent, episode, fk, rng, writer, template, source, camera_names
                        )
                    except (FileNotFoundError, ValueError, KeyError) as error:
                        print(f'skip {source}: {error}')
                        steps = 0
                    if steps:
                        written += 1
                        per_config[path.relative_to(root).parts[0]] += 1
                    else:
                        skipped += 1
                    if args.limit and written >= args.limit:
                        break
            if args.limit and written >= args.limit:
                break
    print(f'wrote {written} episodes, skipped {skipped}, into {args.output}')
    for config, count in sorted(per_config.items()):
        print(f'  {config}: {count}')


if __name__ == '__main__':
    main()

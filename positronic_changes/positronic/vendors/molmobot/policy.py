import logging
import re
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import torch
from olmo.models.model_config import BaseModelConfig
from olmo.models.molmobot.inference_wrapper import SynthManipMolmoInferenceWrapper

from positronic.offboard.spec import Model
from positronic.policy import keys as policy_keys
from positronic.policy.base import Obs
from positronic.policy.codecs import ACTION
from positronic.simulator.molmo_spaces import mapping
from positronic.vendors import molmobot
from positronic.vendors.molmobot import arm

logger = logging.getLogger(__name__)

STATE_DIM = 8  # [joint_positions(7), grip(1)]
_NUM_JOINTS = 7
_IMAGE_SHAPE = (352, 624, 3)
# MolmoBot's FrankaState8ClampAbsPosConfig: the largest joint step per action, and the gripper command threshold.
_MAX_JOINT_STEP = 0.2
_GRIP_THRESHOLD = 128.0
# An observed grip above this is a gripper that is closed or closing: an open gripper reads 0.
_GRIP_CLOSED_OBS = 0.05
# The model logs its inference time once per this many calls.
_TIMING_LOG_CALLS = 100
# The exterior camera the model sees: the one in `image.exterior`, or the left or the right shoulder camera.
CAMERAS = ('exterior', 'left', 'right')
# A pick-and-place task in the board wording. MolmoBot's training data says "place it in or on the", with no full stop.
_BOARD_PLACE_TASK = re.compile(r'pick up the (?P<item>.+) and place it on the (?P<target>.+?)\.?', re.IGNORECASE)
# A pick-and-place task in any wording of the board: "on", "in or on" or "next to" the target.
_PLACE_TASK = re.compile(r'pick up the (?P<item>.+?) and place it (?:on|in or on|next to) the .+', re.IGNORECASE)
# An arm whose joints stay in a range this small (rad) over the observations of `still_calls` calls is still.
_STILL_RAD = 0.02
# A shoulder camera is blocked when its detail (mean grey gradient) is below this and the other camera has at least
# `_BLOCKED_RATIO` times as much.
_BLOCKED_DETAIL = 0.6
_BLOCKED_RATIO = 1.5
# Close tasks: the push starts when the gripper stays in this range (m) over the last `_SLOW_CALLS` + 1 observations.
_SLOW_M = 0.08
_SLOW_CALLS = 3
# Each push moves the closed gripper this far per action (m), for this many calls, then the model gets this many calls.
_PUSH_STEP_M = 0.008
_PUSH_CALLS = 3
_REST_CALLS = 4
_PUSH_ATTEMPTS = 3
# The gripper axis gives the push direction while its height part is below this; else the push goes away from the base,
# after a drop (m) into or in front of the open drawer, by attempt.
_STEEP_AXIS = 0.7
_DROP_M = (0.06, 0.10)
# An open task in the board wording.
_OPEN_TASK = re.compile(r'open the (?P<item>.+?)\.?', re.IGNORECASE)
# The tasks that get the action expert of `open_close_expert`, by the value of `open_close_expert_tasks`.
_EXPERT_TASKS = {
    'both': re.compile(r'(?:open|close) the ', re.IGNORECASE),
    'open': re.compile(r'open the ', re.IGNORECASE),
    'close': re.compile(r'close the ', re.IGNORECASE),
}
# The gripper holds something when its observed closure is in this range, it was above the low end one call earlier,
# and the previous chunk kept it closed. Fingers that close on nothing read above the range within 0.3 s.
_HOLD_GRIP = (0.1, 0.9)
# Each pull moves the closed gripper this far per action (m), for this many calls, then the model gets `_REST_CALLS`.
_PULL_STEP_M = 0.006
_PULL_CALLS = 2
_PULL_ATTEMPTS = 3
# A regrasp backs the open gripper off along its axis by this much (m), then moves it past the missed grasp point by
# `_REGRASP_DEEPER_M` and along the finger axis by the offset of the attempt (m).
_REGRASP_BACK_M = 0.03
_REGRASP_DEEPER_M = 0.03
_REGRASP_OFFSETS_M = (0.0, 0.03, -0.03)
# A touch grasp moves the open gripper in along its axis by this much per call (m). It stops after a call that moved
# it less than `_TOUCH_STOP_M` along the axis, or after `_TOUCH_CALLS` calls, and closes there.
_TOUCH_STEP_M = 0.03
_TOUCH_STOP_M = 0.01
_TOUCH_CALLS = 3
# The model's closes that start a touch grasp, in one session.
_TOUCH_STARTS = 2
# An open task whose handle is usually a horizontal bar: a touch grasp first turns the fingers to close vertically.
_BAR_TASK = re.compile(r'open the .*\b(?:drawer|dresser|desk|table|nightstand|chest)\b', re.IGNORECASE)


def warm_observation() -> dict[str, Any]:
    """Zero-filled inputs one inference can run on, so the model's first-call cost is paid before it serves."""
    return {
        molmobot.IMAGES: [np.zeros(_IMAGE_SHAPE, dtype=np.uint8) for _ in range(3)],
        molmobot.STATE: np.zeros(STATE_DIM, dtype=np.float32),
        molmobot.TASK: '',
    }


class _MmapCheckpointWrapper(SynthManipMolmoInferenceWrapper):
    """The upstream wrapper, with the float32 checkpoint read through a memory map into the bfloat16 model.

    The upstream load reads the whole 20 GB checkpoint into RAM first.
    """

    def _load_checkpoint(self) -> None:
        self.model_config = BaseModelConfig.load(str(Path(self.checkpoint_path) / 'config.yaml'), key='model')
        self.max_seq_len = self.model_config.llm.max_sequence_length
        self.action_horizon = self.model_config.action_horizon
        self.action_dim = self.model_config.action_dim
        self.n_obs_steps = self.model_config.n_obs_steps
        if self.num_flow_steps is None:
            self.num_flow_steps = self.model_config.flow_matching_num_steps
        if self.states_mode is not None:
            self.model_config.states_mode = self.states_mode
        with torch.device('meta'):
            self.model = self.model_config.build_model()
        self.model.to(torch.bfloat16)
        self.model.to_empty(device=self.device)
        state = torch.load(Path(self.checkpoint_path) / 'model.pt', map_location='cpu', weights_only=True, mmap=True)
        self.model.load_state_dict(state, strict=True)
        del state
        self.model.eval()


def _white_lean(img: np.ndarray) -> float:
    """How much more of the lower right than of the lower left is near-white: the robot base at the home pose."""
    h, w, _ = img.shape
    rgb = np.asarray(img, dtype=np.int16)
    white = (rgb.min(axis=2) > 170) & (rgb.max(axis=2) - rgb.min(axis=2) < 30)
    lower = white[h // 2 :]
    return float(lower[:, 2 * w // 3 :].mean() - lower[:, : w // 3].mean())


def exterior_side(exterior: np.ndarray, exterior_2: np.ndarray) -> str:
    """The shoulder of the camera in ``exterior``, from frames of both shoulder cameras at the home pose.

    The left shoulder camera sees the robot base in the lower right of its image. About 94% right on 119 local
    episodes.
    """
    return 'left' if _white_lean(exterior) > _white_lean(exterior_2) else 'right'


def training_wording(task: str) -> str:
    """The task in the wording of MolmoBot's pick-and-place training data, or the task as it is."""
    match = _BOARD_PLACE_TASK.fullmatch(task.strip())
    if match is None:
        return task
    return f'Pick up the {match["item"]} and place it in or on the {match["target"]}'


def detail(img: np.ndarray) -> float:
    """The mean grey gradient of an image: low for a camera that faces a wall or a dark corner."""
    grey = np.asarray(img, dtype=np.float32).mean(axis=2)
    return float((np.abs(np.diff(grey, axis=0)).mean() + np.abs(np.diff(grey, axis=1)).mean()) / 2)


def push_plan(joints: np.ndarray, attempt: int, horizon: int) -> list[np.ndarray]:
    """The gripper step (m per action, base frame) of each call of one push attempt.

    A level gripper pushes along its axis (away from the base on odd attempts). A gripper that points down first drops
    into or in front of the open drawer, then pushes away from the base.
    """
    pose = arm.gripper_pose(joints)
    axis, level = pose[:3, 2], pose[:3, 3].copy()
    steep = abs(axis[2]) >= _STEEP_AXIS
    if not steep and attempt % 2 == 0:
        level = axis.copy()
    level[2] = 0.0
    level /= max(float(np.linalg.norm(level)), 1e-6)
    push = [_PUSH_STEP_M * level] * _PUSH_CALLS
    if not steep:
        return push
    drop = _DROP_M[attempt % len(_DROP_M)]
    return [np.array([0.0, 0.0, -drop / horizon]), *push]


def pull_step(joints: np.ndarray) -> np.ndarray:
    """The gripper step (m per action, base frame) that pulls a held handle straight out.

    A level gripper pulls back along its axis. A gripper that points down pulls toward the base.
    """
    pose = arm.gripper_pose(joints)
    axis = pose[:3, 2]
    out = -(axis if abs(axis[2]) < _STEEP_AXIS else pose[:3, 3]).copy()
    out[2] = 0.0
    return _PULL_STEP_M * out / max(float(np.linalg.norm(out)), 1e-6)


def regrasp_plan(joints: np.ndarray, attempt: int, horizon: int) -> list[tuple[np.ndarray, float]]:
    """The gripper step (m per action, base frame) and the gripper closure of each call of one regrasp attempt.

    The open gripper backs off along its axis, then moves past the missed grasp point and along its finger axis by the
    offset of the attempt. Then it closes in place.
    """
    pose = arm.gripper_pose(joints)
    axis, fingers = pose[:3, 2], pose[:3, 1]
    moves = [
        (-_REGRASP_BACK_M * axis, 0.0),
        ((_REGRASP_BACK_M + _REGRASP_DEEPER_M) * axis + _REGRASP_OFFSETS_M[attempt] * fingers, 0.0),
        (np.zeros(3), 1.0),
    ]
    return [(move / horizon, closure) for move, closure in moves]


def straight_chunk(
    joints: np.ndarray, step: np.ndarray, closure: float, horizon: int, turn: np.ndarray | None = None
) -> np.ndarray:
    """``horizon`` actions that move the gripper by ``step`` (m, base frame) and ``turn`` (rad) each, at one closure."""
    moves = arm.straight_move(joints, step, horizon, turn=turn)
    return np.concatenate([moves, np.full((horizon, 1), closure)], axis=1).astype(np.float32)


def vertical_fingers_turn(joints: np.ndarray) -> np.ndarray:
    """The rotation (rad, base frame) about the gripper axis that makes the fingers close vertically."""
    pose = arm.gripper_pose(joints)
    axis, fingers = pose[:3, 2], pose[:3, 1]
    up = np.array([0.0, 0.0, 1.0]) - axis[2] * axis
    up /= max(float(np.linalg.norm(up)), 1e-6)
    if fingers @ up < 0:
        up = -up
    return float(np.arctan2(np.cross(fingers, up) @ axis, fingers @ up)) * axis


def is_level(joints: np.ndarray) -> bool:
    """True when the gripper axis is closer to horizontal than ``_STEEP_AXIS``."""
    return abs(arm.gripper_pose(joints)[2, 2]) < _STEEP_AXIS


def handle_task(task: str) -> str | None:
    """An open task in the wording of a pick task of the handle, or None for other tasks."""
    match = _OPEN_TASK.fullmatch(task.strip())
    return None if match is None else f'pick up the {match["item"]} handle.'


def pick_part(task: str) -> str | None:
    """The pick part of a pick-and-place task in the wording of a pick task, or None for other tasks."""
    match = _PLACE_TASK.fullmatch(task.strip())
    return None if match is None else f'pick up the {match["item"]}.'


def limit_chunk(chunk: np.ndarray, joints: np.ndarray) -> np.ndarray:
    """Scale each joint step to ``_MAX_JOINT_STEP`` and turn the gripper command into a closure of 0 or 1."""
    out = np.asarray(chunk, dtype=np.float32).copy()
    reference = np.asarray(joints, dtype=np.float32)
    for action in out:
        step = action[:_NUM_JOINTS] - reference
        scale = np.max(np.abs(step)) / _MAX_JOINT_STEP
        if scale > 1:
            step /= scale
        action[:_NUM_JOINTS] = reference + step
        action[_NUM_JOINTS] = 1.0 if action[_NUM_JOINTS] > _GRIP_THRESHOLD else 0.0
        reference = action[:_NUM_JOINTS]
    return out


def hold_grip(raw: np.ndarray, closed: bool, release_below: float) -> np.ndarray:
    """Gripper closures of 0 or 1: close above ``_GRIP_THRESHOLD``, and open again only below ``release_below``."""
    out = np.empty(len(raw), dtype=np.float32)
    for i, value in enumerate(raw):
        closed = bool(value > (release_below if closed else _GRIP_THRESHOLD))
        out[i] = float(closed)
    return out


class MolmoBotModel(Model):
    """MolmoBot on the GPU, with the previous call's camera frames kept per session.

    The observation holds both shoulder cameras and the wrist camera; the model sees one shoulder camera and the
    wrist camera. A checkpoint with ``n_obs_steps=2`` takes two frames per camera. The previous call is one
    executed chunk earlier, which is the frame gap the checkpoint trained on when a chunk executes
    ``obs_step_delta`` actions.
    """

    def __init__(
        self,
        checkpoint_dir: str,
        *,
        num_flow_steps: int | None = None,
        skip_actions: int = 0,
        camera: str = 'exterior',
        grip_release_below: float | None = None,
        training_wording: bool = False,
        still_calls: int | None = None,
        camera_fallback: bool = False,
        close_push_after: int | None = None,
        open_as_pick: bool = False,
        open_pull: bool = False,
        open_regrasp: bool = False,
        open_touch: bool = False,
        open_close_expert: str | None = None,
        open_close_expert_tasks: str = 'both',
        open_close_flow_steps: int | None = None,
    ):
        """``skip_actions`` drops that many actions from the start of each chunk after a session's first one.

        A schedule that requests the next chunk when the current one starts plays it one chunk after its
        observation, so the robot has passed the chunk's first actions by then. ``camera`` is one of ``CAMERAS``;
        a shoulder is picked once per session, from its first observation. With ``grip_release_below``, a closed
        gripper opens only when the model's gripper value is below it (the model's range is 0 to 255). With
        ``training_wording``, the model gets each task in the wording of its training data. With ``still_calls``,
        the model gets only the pick part of a pick-and-place task while the gripper is open, from the call where
        the arm has been still for ``still_calls`` calls. With ``camera_fallback``, a blocked shoulder camera gives
        way to the other one. With ``close_push_after``, a close task whose arm is slow after that many calls gets
        straight pushes of the closed gripper instead of model actions. With ``open_as_pick``, the model gets an open
        task as a pick of the handle. With ``open_pull``, an open task whose gripper holds something gets straight
        pulls of the closed gripper instead of model actions. With ``open_regrasp`` (needs ``open_pull``), a level
        gripper of an open task that closes on nothing grasps again near that point, and a gripper that stops on
        something stays closed. With ``open_touch`` (needs ``open_pull``), the model's close of a level, open gripper in
        an open task becomes a touch grasp: the open gripper moves in until it touches something and closes there; on
        a drawer-like task the fingers first turn to close vertically. A gripper that stops on something stays closed.
        With ``open_close_expert``, the
        file of an action expert
        state dict, the tasks of ``open_close_expert_tasks`` ('both', 'open' or 'close') get that action expert and all
        other tasks the checkpoint's own. Only the action expert in use stays on the GPU. With
        ``open_close_flow_steps``, the tasks of that action expert use that many flow steps.
        """
        if camera not in CAMERAS:
            raise ValueError(f'camera must be one of {CAMERAS}, got {camera!r}')
        if grip_release_below is not None and not 0 <= grip_release_below < _GRIP_THRESHOLD:
            raise ValueError(f'grip_release_below must be in [0, {_GRIP_THRESHOLD}), got {grip_release_below}')
        if still_calls is not None and still_calls < 1:
            raise ValueError(f'still_calls must be at least 1, got {still_calls}')
        if open_close_expert_tasks not in _EXPERT_TASKS:
            raise ValueError(
                f'open_close_expert_tasks must be one of {sorted(_EXPERT_TASKS)}, got {open_close_expert_tasks!r}'
            )
        if close_push_after is not None and close_push_after < _SLOW_CALLS:
            raise ValueError(f'close_push_after must be at least {_SLOW_CALLS}, got {close_push_after}')
        if open_regrasp and not open_pull:
            raise ValueError('open_regrasp needs open_pull')
        if open_touch and not open_pull:
            raise ValueError('open_touch needs open_pull')
        if open_close_flow_steps is not None and (open_close_expert is None or open_close_flow_steps < 1):
            raise ValueError(
                f'open_close_flow_steps needs open_close_expert and a value of 1 or more, got {open_close_flow_steps}'
            )
        if not torch.cuda.is_available():
            raise RuntimeError('MolmoBot found no CUDA GPU.')
        self._agent = _MmapCheckpointWrapper(checkpoint_dir, num_flow_steps=num_flow_steps, states_mode='cross_attn')
        if self._agent.n_obs_steps not in (1, 2):
            raise ValueError(
                f'MolmoBot serves 1 or 2 frames per camera, the checkpoint takes {self._agent.n_obs_steps}'
            )
        if not 0 <= skip_actions < self._agent.action_horizon:
            raise ValueError(f'skip_actions must be in [0, {self._agent.action_horizon}), got {skip_actions}')
        self._skip_actions = skip_actions
        self._camera = camera
        self._grip_release_below = grip_release_below
        self._training_wording = training_wording
        self._still_calls = still_calls
        self._recent_joints: dict[str, deque[np.ndarray]] = {}
        self._picking: set[str] = set()
        self._camera_fallback = camera_fallback
        self._close_push_after = close_push_after
        self._close: dict[str, _ClosePlan] = {}
        self._open_as_pick = open_as_pick
        self._open_pull = open_pull
        self._open_regrasp = open_regrasp
        self._open_touch = open_touch
        self._open: dict[str, _OpenPlan] = {}
        # The action expert of each task kind, keyed by "is an open or close task".
        self._experts: dict[bool, torch.nn.Module] = {}
        self._expert_tasks = _EXPERT_TASKS[open_close_expert_tasks]
        if open_close_expert is not None:
            self._experts = {False: self._agent.model.action_expert, True: self._load_expert(open_close_expert)}
        # The flow steps of each task kind, keyed like `_experts`.
        own_steps = self._agent.num_flow_steps
        self._flow_steps = {
            False: own_steps,
            True: own_steps if open_close_flow_steps is None else open_close_flow_steps,
        }
        self._infer_ms: list[float] = []
        self._use_exterior_2: dict[str, bool] = {}
        self._previous_images: dict[str, list[np.ndarray]] = {}
        name = Path(checkpoint_dir).name
        self._meta = {policy_keys.TYPE: 'molmobot', 'model_id': name, policy_keys.CHECKPOINT_ID: name}

    def __call__(self, obs: Obs, *, session_id: str) -> list[dict[str, Any]]:
        exterior, exterior_2, wrist = obs[molmobot.IMAGES]
        if session_id not in self._use_exterior_2:
            self._use_exterior_2[session_id] = self._pick_exterior_2(exterior, exterior_2, session_id)
        images = [exterior_2 if self._use_exterior_2[session_id] else exterior, wrist]
        previous = self._previous_images.get(session_id)
        self._previous_images[session_id] = images
        if self._agent.n_obs_steps == 2 and previous is not None:
            images = [frame for pair in zip(previous, images, strict=True) for frame in pair]
        state = np.asarray(obs[molmobot.STATE], dtype=np.float32)
        joints = state[:_NUM_JOINTS]
        model_state = np.append(joints, state[_NUM_JOINTS] * mapping.GRIPPER_QPOS_CLOSED).astype(np.float32)
        closed = state[_NUM_JOINTS] > _GRIP_CLOSED_OBS
        raw_task = obs.get(molmobot.TASK, '')
        if self._close_push_after is not None and raw_task.strip().lower().startswith('close the'):
            plan = self._close.setdefault(session_id, _ClosePlan(self._close_push_after))
            pushed = plan.next_chunk(joints, self._agent.action_horizon, session_id)
            if pushed is not None:
                if previous is not None:
                    pushed = pushed[self._skip_actions :]
                return [{ACTION: action} for action in pushed]
        if self._open_pull and _OPEN_TASK.fullmatch(raw_task.strip()):
            plan = self._open.setdefault(
                session_id, _OpenPlan(self._open_regrasp, self._open_touch, _BAR_TASK.search(raw_task) is not None)
            )
            pulled = plan.next_chunk(joints, float(state[_NUM_JOINTS]), self._agent.action_horizon, session_id)
            if pulled is not None:
                if previous is not None:
                    pulled = pulled[self._skip_actions :]
                return [{ACTION: action} for action in pulled]
        task = self._task(raw_task, joints, closed, session_id)
        self._use_expert(self._expert_tasks.match(raw_task.strip()) is not None, session_id)
        start = time.perf_counter()
        chunk = self._agent.get_action_chunk(images=images, task_description=task, state=model_state)
        self._log_timing((time.perf_counter() - start) * 1000)
        actions = limit_chunk(chunk, joints)
        if self._grip_release_below is not None:
            actions[:, _NUM_JOINTS] = hold_grip(chunk[:, _NUM_JOINTS], closed, self._grip_release_below)
        if previous is not None:
            actions = actions[self._skip_actions :]
        if session_id in self._open:
            plan = self._open[session_id]
            plan.note_chunk(actions[:, _NUM_JOINTS])
            grasp = plan.touch_chunk(
                actions[:, _NUM_JOINTS], joints, float(state[_NUM_JOINTS]), self._agent.action_horizon, session_id
            )
            if grasp is not None:
                actions = grasp[self._skip_actions :] if previous is not None else grasp
        return [{ACTION: action} for action in actions]

    def _load_expert(self, path: str) -> torch.nn.Module:
        """An action expert of the checkpoint's shape on the CPU, in bfloat16, with the weights in ``path``."""
        config = self._agent.model_config
        expert = config.action_expert.build(llm_dim=config.llm.d_model, device=torch.device('cpu'))
        expert.to(torch.bfloat16)
        expert.load_state_dict(torch.load(path, map_location='cpu', weights_only=True), strict=True)
        expert.eval()
        logger.info(f'Loaded the open/close action expert {path}')
        return expert

    def _use_expert(self, open_close: bool, session_id: str) -> None:
        """Give the model the action expert and the flow steps of the task kind, and put the other expert on the CPU."""
        if not self._experts:
            return
        self._agent.num_flow_steps = self._flow_steps[open_close]
        current = self._agent.model.action_expert
        wanted = self._experts[open_close]
        if wanted is current:
            return
        device = next(current.parameters()).device
        current.to('cpu')
        self._agent.model.action_expert = wanted.to(device)
        kind = 'open/close' if open_close else 'checkpoint'
        logger.info(f'Session {session_id}: the model uses the {kind} action expert')

    def _pick_exterior_2(self, exterior: np.ndarray, exterior_2: np.ndarray, session_id: str) -> bool:
        if self._camera == 'exterior':
            return False
        use_2 = exterior_side(exterior, exterior_2) != self._camera
        if self._camera_fallback:
            picked, other = (detail(exterior_2), detail(exterior)) if use_2 else (detail(exterior), detail(exterior_2))
            if picked < _BLOCKED_DETAIL and other > picked and other >= _BLOCKED_RATIO * picked:
                use_2 = not use_2
                logger.info(
                    f'Session {session_id}: the {self._camera} camera is blocked (detail {picked:.2f}, other '
                    f'{other:.2f}), the model uses the other shoulder camera'
                )
        return use_2

    def _task(self, task: str, joints: np.ndarray, closed: bool, session_id: str) -> str:
        handle = handle_task(task) if self._open_as_pick else None
        if handle is not None:
            return handle
        pick = pick_part(task) if self._still_calls is not None else None
        if pick is not None:
            recent = self._recent_joints.setdefault(session_id, deque(maxlen=self._still_calls + 1))
            recent.append(joints.copy())
            if closed:
                self._picking.discard(session_id)
            elif session_id not in self._picking and len(recent) == recent.maxlen:
                if np.ptp(np.stack(recent), axis=0).max() < _STILL_RAD:
                    self._picking.add(session_id)
                    logger.info(f'Session {session_id}: the arm is still and the gripper is open, task now {pick!r}')
            if session_id in self._picking:
                return pick
        return training_wording(task) if self._training_wording else task

    def _log_timing(self, ms: float) -> None:
        self._infer_ms.append(ms)
        if len(self._infer_ms) == _TIMING_LOG_CALLS:
            p50, p95 = np.percentile(self._infer_ms, [50, 95])
            logger.info(f'MolmoBot inference over {_TIMING_LOG_CALLS} calls: p50 {p50:.0f} ms, p95 {p95:.0f} ms')
            self._infer_ms.clear()

    def end_session(self, session_id: str) -> None:
        self._previous_images.pop(session_id, None)
        self._use_exterior_2.pop(session_id, None)
        self._recent_joints.pop(session_id, None)
        self._picking.discard(session_id)
        self._close.pop(session_id, None)
        self._open.pop(session_id, None)

    def meta(self) -> dict[str, Any]:
        return self._meta

    def close(self):
        if self._agent is not None:
            del self._agent
            self._agent = None
            torch.cuda.empty_cache()


class _ClosePlan:
    """The push schedule of one close-task session: model calls, then pushes when the arm is slow."""

    def __init__(self, push_after: int):
        self._push_after = push_after
        self._calls = 0
        self._recent: deque[np.ndarray] = deque(maxlen=_SLOW_CALLS + 1)
        self._steps: list[np.ndarray] = []
        self._rest_left = 0
        self._attempt = 0

    def next_chunk(self, joints: np.ndarray, horizon: int, session_id: str) -> np.ndarray | None:
        """The pushed actions (joints and a closed gripper) for this call, or None when the model acts."""
        self._calls += 1
        self._recent.append(arm.gripper_pose(joints)[:3, 3])
        if not self._steps:
            if self._rest_left > 0:
                self._rest_left -= 1
                return None
            slow = len(self._recent) == self._recent.maxlen and np.ptp(np.stack(self._recent), axis=0).max() < _SLOW_M
            if self._calls <= self._push_after or self._attempt >= _PUSH_ATTEMPTS or not slow:
                return None
            self._steps = push_plan(joints, self._attempt, horizon)
            self._attempt += 1
            logger.info(
                f'Session {session_id}: close push starts (attempt {self._attempt}, call {self._calls}, '
                f'steps {[np.round(step * horizon, 3).tolist() for step in self._steps]})'
            )
        step = self._steps.pop(0)
        if not self._steps:
            self._rest_left = _REST_CALLS
            self._recent.clear()
        return straight_chunk(joints, step, 1.0, horizon)


class _TouchGrasp:
    """One scripted grasp of an open task, one part per call.

    It can first turn the fingers to close vertically. Then the open gripper moves in along its axis until it touches
    something, and closes.
    """

    def __init__(self, turn: bool):
        self._parts = (['turn'] if turn else []) + ['touch']
        self._touches = 0
        self._previous: np.ndarray | None = None

    def next_chunk(self, joints: np.ndarray, horizon: int) -> np.ndarray | None:
        """The actions of this call, or None after the close."""
        if not self._parts:
            return None
        pose = arm.gripper_pose(joints)
        axis, position = pose[:3, 2], pose[:3, 3]
        part = self._parts.pop(0)
        if part == 'turn':
            return straight_chunk(joints, np.zeros(3), 0.0, horizon, turn=vertical_fingers_turn(joints) / horizon)
        stopped = self._previous is not None and float((position - self._previous) @ axis) < _TOUCH_STOP_M
        if stopped or self._touches >= _TOUCH_CALLS:
            return straight_chunk(joints, np.zeros(3), 1.0, horizon)
        self._parts.insert(0, 'touch')
        self._touches += 1
        self._previous = position
        return straight_chunk(joints, _TOUCH_STEP_M * axis / horizon, 0.0, horizon)


class _OpenPlan:
    """The pull schedule of one open-task session: model calls, then pulls while the gripper holds something.

    With ``regrasp`` or ``touch``, the gripper holds something when two observations in a row are in ``_HOLD_GRIP``,
    and after one such observation the gripper stays closed for a call. With ``regrasp``, a level gripper that closes on
    nothing grasps again near that point. With ``touch``, the model's close of a level, open gripper becomes a touch
    grasp. With ``bar``, a touch grasp first turns the fingers to close vertically.
    """

    def __init__(self, regrasp: bool, touch: bool, bar: bool):
        self._regrasp = regrasp
        self._touch = touch
        self._two_readings = regrasp or touch
        self._bar = bar
        self._previous_grip = 0.0
        self._kept_closed = False
        self._step = np.zeros(3)
        self._calls_left = 0
        self._rest_left = 0
        self._attempt = 0
        self._regrasp_steps: list[tuple[np.ndarray, float]] = []
        self._regrasps = 0
        self._grasp: _TouchGrasp | None = None
        self._touch_starts = 0

    def note_chunk(self, grips: np.ndarray) -> None:
        """Record the gripper closures of the chunk the model returned."""
        self._kept_closed = bool(len(grips) and (grips > 0.5).all())

    def touch_chunk(
        self, grips: np.ndarray, joints: np.ndarray, grip: float, horizon: int, session_id: str
    ) -> np.ndarray | None:
        """A touch grasp in place of a model chunk that closes an open, level gripper, or None to keep the chunk."""
        if not self._touch or self._grasp is not None or self._calls_left or self._attempt >= _PULL_ATTEMPTS:
            return None
        if grip >= _HOLD_GRIP[0] or not (grips > 0.5).any() or not is_level(joints):
            return None
        if self._touch_starts >= _TOUCH_STARTS:
            return None
        self._touch_starts += 1
        self._grasp = _TouchGrasp(turn=self._bar)
        logger.info(f'Session {session_id}: open touch grasp starts ({self._touch_starts}, finger turn {self._bar})')
        return self._grasp.next_chunk(joints, horizon)

    def next_chunk(self, joints: np.ndarray, grip: float, horizon: int, session_id: str) -> np.ndarray | None:
        """The pulled actions (joints and a closed gripper) for this call, or None when the model acts."""
        low, high = _HOLD_GRIP
        if self._two_readings:
            held = low < self._previous_grip < high and low < grip < high
        else:
            held = self._kept_closed and self._previous_grip > low and low < grip < high
        self._previous_grip = grip
        self._kept_closed = False
        if self._regrasp_steps:
            step, closure = self._regrasp_steps.pop(0)
            return straight_chunk(joints, step, closure, horizon)
        if self._grasp is not None:
            chunk = self._grasp.next_chunk(joints, horizon)
            if chunk is not None:
                return chunk
            self._grasp = None
        if self._calls_left == 0:
            if self._rest_left > 0:
                self._rest_left -= 1
                return None
            if self._attempt >= _PULL_ATTEMPTS:
                return None
            if not held:
                return self._grasp_chunk(joints, grip, horizon, session_id) if self._two_readings else None
            self._step = pull_step(joints)
            self._calls_left = _PULL_CALLS
            self._attempt += 1
            logger.info(
                f'Session {session_id}: open pull starts (attempt {self._attempt}, grip {grip:.2f}, '
                f'step {np.round(self._step * horizon, 3).tolist()})'
            )
        self._calls_left -= 1
        if self._calls_left == 0 and not self._two_readings:
            self._rest_left = _REST_CALLS
        return straight_chunk(joints, self._step, 1.0, horizon)

    def _grasp_chunk(self, joints: np.ndarray, grip: float, horizon: int, session_id: str) -> np.ndarray | None:
        """A closed gripper in place, the first call of a regrasp, or None when the model acts."""
        low, high = _HOLD_GRIP
        if low < grip < high:
            return straight_chunk(joints, np.zeros(3), 1.0, horizon)
        if not self._regrasp or grip < high or not is_level(joints) or self._regrasps >= len(_REGRASP_OFFSETS_M):
            return None
        attempt = self._regrasps
        self._regrasps += 1
        logger.info(
            f'Session {session_id}: open regrasp starts (attempt {self._regrasps}, grip {grip:.2f}, '
            f'finger offset {_REGRASP_OFFSETS_M[attempt]} m)'
        )
        self._regrasp_steps = regrasp_plan(joints, attempt, horizon)
        step, closure = self._regrasp_steps.pop(0)
        return straight_chunk(joints, step, closure, horizon)

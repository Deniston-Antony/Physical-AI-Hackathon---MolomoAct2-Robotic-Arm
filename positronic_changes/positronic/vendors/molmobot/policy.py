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
    ):
        """``skip_actions`` drops that many actions from the start of each chunk after a session's first one.

        A schedule that requests the next chunk when the current one starts plays it one chunk after its
        observation, so the robot has passed the chunk's first actions by then. ``camera`` is one of ``CAMERAS``;
        a shoulder is picked once per session, from its first observation. With ``grip_release_below``, a closed
        gripper opens only when the model's gripper value is below it (the model's range is 0 to 255). With
        ``training_wording``, the model gets each task in the wording of its training data. With ``still_calls``,
        the model gets only the pick part of a pick-and-place task while the gripper is open, from the call where
        the arm has been still for ``still_calls`` calls.
        """
        if camera not in CAMERAS:
            raise ValueError(f'camera must be one of {CAMERAS}, got {camera!r}')
        if grip_release_below is not None and not 0 <= grip_release_below < _GRIP_THRESHOLD:
            raise ValueError(f'grip_release_below must be in [0, {_GRIP_THRESHOLD}), got {grip_release_below}')
        if still_calls is not None and still_calls < 1:
            raise ValueError(f'still_calls must be at least 1, got {still_calls}')
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
        self._infer_ms: list[float] = []
        self._use_exterior_2: dict[str, bool] = {}
        self._previous_images: dict[str, list[np.ndarray]] = {}
        name = Path(checkpoint_dir).name
        self._meta = {policy_keys.TYPE: 'molmobot', 'model_id': name, policy_keys.CHECKPOINT_ID: name}

    def __call__(self, obs: Obs, *, session_id: str) -> list[dict[str, Any]]:
        exterior, exterior_2, wrist = obs[molmobot.IMAGES]
        if session_id not in self._use_exterior_2:
            self._use_exterior_2[session_id] = (
                self._camera != 'exterior' and exterior_side(exterior, exterior_2) != self._camera
            )
        images = [exterior_2 if self._use_exterior_2[session_id] else exterior, wrist]
        previous = self._previous_images.get(session_id)
        self._previous_images[session_id] = images
        if self._agent.n_obs_steps == 2 and previous is not None:
            images = [frame for pair in zip(previous, images, strict=True) for frame in pair]
        state = np.asarray(obs[molmobot.STATE], dtype=np.float32)
        joints = state[:_NUM_JOINTS]
        model_state = np.append(joints, state[_NUM_JOINTS] * mapping.GRIPPER_QPOS_CLOSED).astype(np.float32)
        closed = state[_NUM_JOINTS] > _GRIP_CLOSED_OBS
        task = self._task(obs.get(molmobot.TASK, ''), joints, closed, session_id)
        start = time.perf_counter()
        chunk = self._agent.get_action_chunk(images=images, task_description=task, state=model_state)
        self._log_timing((time.perf_counter() - start) * 1000)
        actions = limit_chunk(chunk, joints)
        if self._grip_release_below is not None:
            actions[:, _NUM_JOINTS] = hold_grip(chunk[:, _NUM_JOINTS], closed, self._grip_release_below)
        if previous is not None:
            actions = actions[self._skip_actions :]
        return [{ACTION: action} for action in actions]

    def _task(self, task: str, joints: np.ndarray, closed: bool, session_id: str) -> str:
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

    def meta(self) -> dict[str, Any]:
        return self._meta

    def close(self):
        if self._agent is not None:
            del self._agent
            self._agent = None
            torch.cuda.empty_cache()

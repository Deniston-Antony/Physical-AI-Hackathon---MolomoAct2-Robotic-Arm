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

STATE_DIM = 8  # [joint_positions(7), grip(1)]
_NUM_JOINTS = 7
_IMAGE_SHAPE = (352, 624, 3)
# MolmoBot's FrankaState8ClampAbsPosConfig: the largest joint step per action, and the gripper command threshold.
_MAX_JOINT_STEP = 0.2
_GRIP_THRESHOLD = 128.0
# The exterior camera the model sees: the one in `image.exterior`, or the left or the right shoulder camera.
CAMERAS = ('exterior', 'left', 'right')


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


class MolmoBotModel(Model):
    """MolmoBot on the GPU, with the previous call's camera frames kept per session.

    The observation holds both shoulder cameras and the wrist camera; the model sees one shoulder camera and the
    wrist camera. A checkpoint with ``n_obs_steps=2`` takes two frames per camera. The previous call is one
    executed chunk earlier, which is the frame gap the checkpoint trained on when a chunk executes
    ``obs_step_delta`` actions.
    """

    def __init__(
        self, checkpoint_dir: str, *, num_flow_steps: int | None = None, skip_actions: int = 0, camera: str = 'exterior'
    ):
        """``skip_actions`` drops that many actions from the start of each chunk after a session's first one.

        A schedule that requests the next chunk when the current one starts plays it one chunk after its
        observation, so the robot has passed the chunk's first actions by then. ``camera`` is one of ``CAMERAS``;
        a shoulder is picked once per session, from its first observation.
        """
        if camera not in CAMERAS:
            raise ValueError(f'camera must be one of {CAMERAS}, got {camera!r}')
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
        chunk = self._agent.get_action_chunk(
            images=images, task_description=obs.get(molmobot.TASK, ''), state=model_state
        )
        actions = limit_chunk(chunk, joints)
        if previous is not None:
            actions = actions[self._skip_actions :]
        return [{ACTION: action} for action in actions]

    def end_session(self, session_id: str) -> None:
        self._previous_images.pop(session_id, None)
        self._use_exterior_2.pop(session_id, None)

    def meta(self) -> dict[str, Any]:
        return self._meta

    def close(self):
        if self._agent is not None:
            del self._agent
            self._agent = None
            torch.cuda.empty_cache()

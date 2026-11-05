"""MolmoBot codec: both exterior cameras and the wrist camera, 8-D joint state, and the DROID joint action space."""

from typing import Any

import configuronic as cfn
import numpy as np

from positronic import keys
from positronic.cfg import codecs
from positronic.policy.codecs import Codec
from positronic.vendors import molmobot


def _image(key: str, inputs: dict[str, Any]) -> np.ndarray:
    frame = np.asarray(inputs[key])
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(f"Image '{key}' must be HWC with 3 channels, got {frame.shape}")
    return frame


class MolmoBotObservationCodec(Codec):
    """Encodes positronic observations into MolmoBot inputs.

    Emits the camera list ``[exterior, exterior_2, wrist]`` (uint8 HWC RGB), the 8-D state
    ``[joint_positions(7), grip(1)]`` and the language task. The model picks one exterior camera, keeps the earlier
    frames and converts the grip to its own units.
    """

    def __init__(
        self,
        exterior_camera: str = keys.EXTERIOR_IMAGE,
        exterior_camera_2: str = keys.EXTERIOR_IMAGE_2,
        wrist_camera: str = keys.WRIST_IMAGE,
        joint_key: str = keys.JOINTS,
        grip_key: str = keys.GRIP,
    ):
        self._cameras = (exterior_camera, exterior_camera_2, wrist_camera)
        self._joint_key = joint_key
        self._grip_key = grip_key

    def encode(self, inputs: dict[str, Any]) -> dict[str, Any]:
        joints = np.asarray(inputs[self._joint_key], dtype=np.float32).reshape(-1)
        grip = np.asarray(inputs[self._grip_key], dtype=np.float32).reshape(-1)
        return {
            molmobot.IMAGES: [_image(k, inputs) for k in self._cameras],
            molmobot.STATE: np.concatenate([joints, grip]).astype(np.float32),
            molmobot.TASK: inputs.get(keys.TASK, ''),
        }


molmobot_obs = cfn.Config(MolmoBotObservationCodec)

# The model returns absolute joint positions (7) and a grip closure of 0 or 1.
_action = codecs.absolute_joints_action.override(tgt_joints_key=keys.TARGET_JOINTS, tgt_grip_key=keys.TARGET_GRIP)

# MolmoBot-Data records at 66 ms per step.
droid = codecs.compose.override(
    obs=molmobot_obs, action=codecs.droid_execution.override(action=_action), training_fps=15.0
)

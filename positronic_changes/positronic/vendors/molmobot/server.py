import logging

import configuronic as cfn

from pimm.logging import init_logging
from positronic.offboard.server import serve
from positronic.offboard.server_utils import warmup
from positronic.offboard.spec import Model, PolicyDeployment
from positronic.policy import Codec, Sequential
from positronic.policy.codecs import ResizeMode, TransformImages
from positronic.policy.processors import ChunkedSchedule, ConstantDuration
from positronic.vendors.molmobot import codecs as molmobot_codecs
from positronic.vendors.molmobot.policy import MolmoBotModel, warm_observation

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_DIR = '/opt/molmobot/MolmoBot-DROID'


@cfn.config(checkpoint_dir=DEFAULT_CHECKPOINT_DIR, num_flow_steps=None, skip_actions=0, camera='exterior')
def molmobot_model(checkpoint_dir: str, num_flow_steps: int | None, skip_actions: int, camera: str) -> Model:
    """One MolmoBot checkpoint directory (``config.yaml`` and ``model.pt``), in process."""
    logger.info(f'Loading MolmoBot model {checkpoint_dir}')
    policy = MolmoBotModel(checkpoint_dir, num_flow_steps=num_flow_steps, skip_actions=skip_actions, camera=camera)
    warmup(policy, warm_observation())
    return policy


# The checkpoint predicts 16 steps; MolmoBot's own eval executes the first 8 of them, at 66 ms per step.
@cfn.config(codec=molmobot_codecs.droid)
def pipeline(
    codec: Codec,
    fps: float = 15.0,
    horizon_sec: float | None = 7.5 / 15,
    inference_lead_sec: float = 0.0,
    compress_images: bool = False,
):
    schedule = ChunkedSchedule(fps, horizon_sec, inference_lead=ConstantDuration(inference_lead_sec))
    return PolicyDeployment(
        Sequential(schedule, TransformImages(640, 640, mode=ResizeMode.BOUND)), codec, compress_images=compress_images
    )


droid = pipeline
# The next chunk is requested when the current one starts, so inference runs while the robot moves. That chunk
# starts one chunk (8 actions) after its observation, so the model drops its first 8 actions.
droid_overlap = pipeline.override(inference_lead_sec=1.0)
# The next chunk is requested 0.2 s before the current one ends. The control rounds come every 66 ms, so the
# request goes out in round 5 of the chunk, and the robot plays the chunk's last 4 actions after its observation.
droid_half_overlap = pipeline.override(inference_lead_sec=0.2)

COMMANDS = {
    **{k: serve.override(model=molmobot_model, pipeline=droid) for k in ('', 'serve', 'droid')},
    'droid_overlap': serve.override(model=molmobot_model.override(skip_actions=8), pipeline=droid_overlap),
    'droid_half_overlap': serve.override(model=molmobot_model.override(skip_actions=4), pipeline=droid_half_overlap),
}


if __name__ == '__main__':
    init_logging()
    cfn.cli(COMMANDS)

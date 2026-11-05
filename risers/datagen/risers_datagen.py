"""MolmoSpaces data-generation configs for The Risers.

Every config records the competition's camera layout: the wrist camera, the left shoulder camera
(`exo_camera_1`) and the right shoulder camera that Positronic adds to the competition eval.

Run one config with run_datagen.sh, for example:
    bash run_datagen.sh RisersCheckPick
Run the whole overnight set with run_overnight.sh.
"""

import os
from pathlib import Path

from molmo_spaces.configs.camera_configs import (
    CameraConfig,
    CameraSystemConfig,
    FrankaDroidCameraSystem,
    RobotMountedCameraConfig,
)
from molmo_spaces.configs.task_sampler_configs import BaseMujocoTaskSamplerConfig
from molmo_spaces.data_generation.config.object_manipulation_datagen_configs import (
    FrankaCloseDataGenConfig,
    FrankaOpenDataGenConfig,
    FrankaPickAndPlaceColorDroidDataGenConfig,
    FrankaPickAndPlaceDroidDataGenConfig,
    FrankaPickAndPlaceNextToDroidDataGenConfig,
    FrankaPickDroidDataGenConfig,
)
from molmo_spaces.data_generation.config_registry import register_config
from molmo_spaces.env.data_views import MlSpacesArticulationObject
from molmo_spaces.tasks.opening_task_samplers import OpenTaskSampler

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
WORKERS = int(os.environ.get("RISERS_WORKERS", "4"))
# Objaverse pick-and-place scenes are the largest. With 4 workers they used all 15 GB of memory, and the
# Ubuntu memory monitor (systemd-oomd) stopped the run.
OBJAVERSE_PLACE_WORKERS = min(WORKERS, 2)

# The right shoulder camera of the competition eval: Positronic's mirror_camera_pose of exo_camera_1
# (offset [0.1, 0.57, 0.66], wxyz [-0.3633, -0.1241, 0.4263, 0.8191]), with no jitter because
# FrankaDroidCameraSystem has no pose noise. The name matches positronic's RIGHT_SHOULDER_CAMERA.
RIGHT_SHOULDER = RobotMountedCameraConfig(
    name="right_shoulder_camera",
    reference_body_names=["robot_0/fr3_link0"],
    camera_offset=[0.1, -0.57, 0.66],
    camera_quaternion=[0.819082, 0.426291, -0.124097, -0.363292],
    fov=71.0,
    # The competition drops episodes whose right view is blocked, so robot placement must keep the task
    # objects in this camera's view too, as exo_camera_1 already requires.
    visibility_constraints={"__task_objects__": 0.001},
)

# iTHOR floor plans of the standard AI2-THOR training split: kitchens, living rooms, bedrooms, bathrooms.
ITHOR_TRAIN = [*range(1, 21), *range(201, 221), *range(301, 321), *range(401, 421)]


class RisersCameras(FrankaDroidCameraSystem):
    """Wrist + left shoulder (exo_camera_1) + mirrored right shoulder, as the competition records."""

    # The competition eval's frame size (Positronic's MolmoSpaces recordings are 624x352).
    img_resolution: tuple[int, int] = (624, 352)
    cameras: list[CameraConfig] = [*FrankaDroidCameraSystem().cameras, RIGHT_SHOULDER]


def _cameras() -> CameraSystemConfig:
    return RisersCameras()


class RisersOpenTaskSampler(OpenTaskSampler):
    """MolmoSpaces' open/close sampler, skipping candidates that have no joints instead of failing the house.

    Upstream `OpenTaskSampler._has_grasps` asserts that every candidate is articulated, but iTHOR rooms hold
    objects of articulation types without joints, and the assertion then ends the whole house.
    """

    def _has_grasps(self, pickup_obj, asset_uid: str):
        if not isinstance(pickup_obj, MlSpacesArticulationObject):
            return False
        return super()._has_grasps(pickup_obj, asset_uid)


def _sampler(parent: type, **changes) -> BaseMujocoTaskSamplerConfig:
    """The parent config's own task sampler, with only `changes` replaced, so its other settings stay."""
    return parent.model_fields["task_sampler_config"].default.model_copy(update=changes, deep=True)


# ---------------------------------------------------------------- quick check (about 10 minutes)


@register_config("RisersCheckPick")
class RisersCheckPick(FrankaPickDroidDataGenConfig):
    """4 workers, 4 houses, 2 pick demos each: checks the 3 cameras and memory use."""

    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaPickDroidDataGenConfig, house_inds=[0, 1, 2, 3], samples_per_house=2
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


@register_config("RisersCheckClose")
class RisersCheckClose(FrankaCloseDataGenConfig):
    """2 iTHOR rooms, 2 close demos each: checks the open/close generator with our cameras."""

    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaCloseDataGenConfig,
        task_sampler_class=RisersOpenTaskSampler,
        house_inds=[1, 201],
        samples_per_house=2,
    )
    num_workers: int = 2
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


# ---------------------------------------------------------------- overnight set (up to ~2,600 demos)
# Each config uses its own houses, so no house repeats across task types.


@register_config("RisersPick")
class RisersPick(FrankaPickDroidDataGenConfig):
    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaPickDroidDataGenConfig, house_inds=list(range(0, 100)), samples_per_house=4
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


@register_config("RisersPickObjaverse")
class RisersPickObjaverse(RisersPick):
    """Unusual Objaverse objects: the scenes where the submitted model scored 8-15%."""

    scene_dataset: str = "procthor-objaverse"


@register_config("RisersPickAndPlace")
class RisersPickAndPlace(FrankaPickAndPlaceDroidDataGenConfig):
    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaPickAndPlaceDroidDataGenConfig, house_inds=list(range(100, 200)), samples_per_house=4
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


@register_config("RisersPickAndPlaceObjaverse")
class RisersPickAndPlaceObjaverse(RisersPickAndPlace):
    scene_dataset: str = "procthor-objaverse"
    num_workers: int = OBJAVERSE_PLACE_WORKERS


@register_config("RisersNextTo")
class RisersNextTo(FrankaPickAndPlaceNextToDroidDataGenConfig):
    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaPickAndPlaceNextToDroidDataGenConfig,
        house_inds=list(range(200, 250)),
        samples_per_house=4,
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


@register_config("RisersColor")
class RisersColor(FrankaPickAndPlaceColorDroidDataGenConfig):
    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaPickAndPlaceColorDroidDataGenConfig,
        house_inds=list(range(250, 300)),
        samples_per_house=4,
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


@register_config("RisersOpen")
class RisersOpen(FrankaOpenDataGenConfig):
    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaOpenDataGenConfig,
        task_sampler_class=RisersOpenTaskSampler,
        house_inds=ITHOR_TRAIN,
        samples_per_house=3,
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR


@register_config("RisersClose")
class RisersClose(FrankaCloseDataGenConfig):
    camera_config: CameraSystemConfig | None = _cameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        FrankaCloseDataGenConfig,
        task_sampler_class=RisersOpenTaskSampler,
        house_inds=ITHOR_TRAIN,
        samples_per_house=3,
    )
    num_workers: int = WORKERS
    use_wandb: bool = False
    output_dir: Path = OUTPUT_DIR

"""MolmoSpaces data-generation configs for The Risers.

Every config records the competition's camera layout: the wrist camera, the left shoulder camera
(`exo_camera_1`) and the right shoulder camera that Positronic adds to the competition eval.

Run one config with run_datagen.sh, for example:
    bash run_datagen.sh RisersCheckPick
Run the whole overnight set with run_overnight.sh.
"""

import math
import os
from pathlib import Path

from pydantic import create_model

from molmo_spaces.configs.camera_configs import (
    CameraConfig,
    CameraSystemConfig,
    FrankaDroidCameraSystem,
    FrankaOmniPurposeCameraSystem,
    RobotMountedCameraConfig,
)
from molmo_spaces.configs.robot_configs import BaseRobotConfig, FrankaRobotConfig
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

# The iTHOR floor plans of the MolmoSpaces train split: kitchens, living rooms, bedrooms, bathrooms. Floor plans 13-24
# of each room type are the val split, which holds the board's iTHOR episodes.
ITHOR_TRAIN = [*range(1, 13), *range(201, 213), *range(301, 313), *range(401, 413)]


class RisersCameras(FrankaDroidCameraSystem):
    """Wrist + left shoulder (exo_camera_1) + mirrored right shoulder, as the competition records."""

    # The competition eval's frame size (Positronic's MolmoSpaces recordings are 624x352).
    img_resolution: tuple[int, int] = (624, 352)
    cameras: list[CameraConfig] = [*FrankaDroidCameraSystem().cameras, RIGHT_SHOULDER]


_OMNI = {camera.name: camera for camera in FrankaOmniPurposeCameraSystem().cameras}
_JITTERED_LEFT = _OMNI["droid_shoulder_light_randomization"]


class RisersHardCameras(CameraSystemConfig):
    """Jittered ZED Mini wrist + jittered left shoulder + jittered mirrored right shoulder, as the hard sets record.

    The board's hard episodes come from FrankaOmniPurposeCameraSystem, and the board shows only its wrist and left
    shoulder cameras. Positronic mirrors the left shoulder's nominal pose and jitters it with the same noise.
    """

    img_resolution: tuple[int, int] = (624, 352)
    cameras: list[CameraConfig] = [
        _OMNI["wrist_camera_zed_mini"].model_copy(update={"record_depth": False}),
        _JITTERED_LEFT,
        RIGHT_SHOULDER.model_copy(
            update={
                "pos_noise_range": _JITTERED_LEFT.pos_noise_range,
                "orientation_noise_degrees": _JITTERED_LEFT.orientation_noise_degrees,
            }
        ),
    ]


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


# ---------------------------------------------------------------- open/close training set (8 November)
# The board has 30 open and 30 close episodes. For each task, 15 are in iTHOR rooms with fixed DROID cameras (the
# normal set) and 15 are hard episodes (the hard set). The hard configs copy FrankaOpenHardBench and
# FrankaCloseHardBench: a random arm start, a robot base height of +/-0.25 m to the object, a base turn of +/-30
# degrees and jittered cameras. All houses are from the train split. The board's houses are in the val split.


@register_config("RisersOpenMore")
class RisersOpenMore(RisersOpen):
    """Normal open set: 12 demos per iTHOR train room."""

    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(RisersOpen, samples_per_house=12)


@register_config("RisersCloseMore")
class RisersCloseMore(RisersClose):
    """Normal close set: 20 demos per iTHOR train room."""

    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(RisersClose, samples_per_house=20)


HARD_ROBOT = FrankaRobotConfig(init_qpos_noise_range={"arm": [0.26] * 6 + [math.pi / 2]})
HARD_PLACEMENT = dict(
    task_sampler_class=RisersOpenTaskSampler,
    robot_object_z_offset_random_min=-0.25,
    robot_object_z_offset_random_max=0.25,
    robot_placement_rotation_range_rad=0.52,
)
# Hard scenes: config name part, scene dataset, train houses, open demos per house, close demos per house.
# The house counts follow the board's hard episodes: 6 iTHOR, 8 ProcTHOR, 5 ProcTHOR-Objaverse, 11 Holodeck of 30.
# The hard set runs on a cloud VM with 192 GB of memory, so the Objaverse scenes use all RISERS_WORKERS too.
HARD_SCENES = [
    ("Ithor", "ithor", ITHOR_TRAIN, 3, 4),
    ("Procthor", "procthor-10k", list(range(1000, 1100)), 2, 2),
    ("ProcObja", "procthor-objaverse", list(range(1000, 1070)), 2, 2),
    ("Holodeck", "holodeck-objaverse", list(range(0, 200)), 2, 2),
]

for _part, _scene, _houses, _open_n, _close_n in HARD_SCENES:
    for _parent, _name, _n in (
        (RisersOpen, f"RisersOpenHard{_part}", _open_n),
        (RisersClose, f"RisersCloseHard{_part}", _close_n),
    ):
        # The pipeline pickles the config, so the class must be a module attribute under its own name.
        globals()[_name] = register_config(_name)(
            create_model(
                _name,
                __base__=_parent,
                __module__=__name__,
                scene_dataset=(str, _scene),
                robot_config=(BaseRobotConfig, HARD_ROBOT),
                camera_config=(CameraSystemConfig | None, RisersHardCameras()),
                task_sampler_config=(
                    BaseMujocoTaskSamplerConfig,
                    _sampler(_parent, house_inds=_houses, samples_per_house=_n, **HARD_PLACEMENT),
                ),
            )
        )

# ---------------------------------------------------------------- hard-set check (about 15 minutes)


@register_config("RisersCheckOpenHard")
class RisersCheckOpenHard(RisersOpen):
    """4 Holodeck houses (the largest scenes), 2 hard open demos each: checks the hard settings and memory use."""

    scene_dataset: str = "holodeck-objaverse"
    robot_config: BaseRobotConfig = HARD_ROBOT
    camera_config: CameraSystemConfig | None = RisersHardCameras()
    task_sampler_config: BaseMujocoTaskSamplerConfig = _sampler(
        RisersOpen, house_inds=[0, 1, 2, 3], samples_per_house=2, **HARD_PLACEMENT
    )

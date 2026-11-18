"""Serve FLUX 3 Action with the rules of the MolmoBot image v3, or with its text encoder kept on the CPU.

`droid_v3` gives the policy the left shoulder camera in both exterior slots, and only the pick part of a
pick-and-place task while the open arm is still. It plays each chunk as v3 does: 0.77 s of it, with the next request
0.2 s before the end, and 4 actions dropped from each later chunk. `droid_fit` is the published `droid`. Both run
`backend_fit.py`: the text encoder stays on the CPU, and the GPU memory is capped at the 24192 MiB slice of a
competition run. `text_encode=cpu` encodes each instruction on the CPU, so the encoder never visits the GPU.

Usage
  python -m positronic.vendors.flux3_v3rules.server droid_v3 --model.model.flux_python=<BFL's python> \
      --model.model.checkpoint=<repository> --model.model.revision=<commit> --model.model.subfolder=variants/gd
  python -m positronic.vendors.flux3_v3rules.server droid_fit --model.flux_python=<BFL's python> ...
"""

import logging
import subprocess
from collections import deque
from functools import partial
from pathlib import Path
from typing import Any

import configuronic as cfn
import numpy as np
from platform_client.policy_container import WARMUP_DEADLINE_S

from pimm.logging import init_logging
from positronic.offboard.roboarena import RoboarenaClient
from positronic.offboard.server import serve
from positronic.offboard.server_utils import wait_for_subprocess_ready, warmup
from positronic.offboard.spec import Model, PolicyDeployment
from positronic.policy import Sequential
from positronic.policy import keys as policy_keys
from positronic.policy.base import Obs
from positronic.policy import codecs as policy_codecs
from positronic.policy.codecs import Codec, ResizeMode, TransformImages
from positronic.policy.processors import ChunkedSchedule, ConstantDuration, TrajectoryPlayer
from positronic.vendors import flux3_action
from positronic.vendors.flux3_action import codecs
from positronic.vendors.flux3_action import server as flux_server
from positronic.vendors.flux3_v3rules import arm
from positronic.vendors.flux3_v3rules.rules import exterior_side, pick_part

logger = logging.getLogger(__name__)

BACKENDS = {'published': flux_server.BACKEND_SCRIPT, 'fit': Path(__file__).with_name('backend_fit.py')}
# An observed grip above this is a gripper that is closed or closing: an open gripper reads 0.
_GRIP_CLOSED_OBS = 0.05
# An arm whose joints stay in a range this small (rad) over the observations of `still_calls` calls is still.
_STILL_RAD = 0.02


# The hybrid schedule: a pick task plays this many actions of a chunk; the schedule requests 0.9 s (13.5 actions)
# before the end of a chunk, which is about the delay of a FLUX call.
_HYBRID_PICK = 16
_HYBRID_LEAD = 13

# An observed grip at or above this is a gripper closed on nothing (one that holds something reads lower).
_EMPTY_GRIP = 0.95
# After a close on nothing: open and lift this far (m) over `_LIFT_ACTIONS`, then hold `_LIFT_HOLD` actions.
_LIFT_M = 0.05
_LIFT_ACTIONS = 6
_LIFT_HOLD = 4
# The next close near a miss (m: across, and up or down) changes: the 1st retry goes `_DEEPER_M` lower, the 2nd also
# turns the gripper `_TURN_RAD` about the vertical, over `_RETRY_ACTIONS` actions.
_MISS_NEAR_XY = 0.06
_MISS_NEAR_Z = 0.08
_DEEPER_M = 0.02
_TURN_RAD = 0.52
_RETRY_ACTIONS = 4

# The GPU memory of a competition run: one `1g.24gb` slice.
SLICE_MIB = 24192


@cfn.config(revision=None, subfolder=None, backend_port=9000, backend='fit', slice_mib=SLICE_MIB, text_encode='gpu', num_inference_steps=0)
def flux_model(
    checkpoint: str,
    revision: str | None,
    subfolder: str | None,
    flux_python: str,
    backend_port: int,
    backend: str,
    slice_mib: int,
    text_encode: str,
    num_inference_steps: int,
) -> Model:
    """`flux_server.flux3_action_model`, with the backend script named in `BACKENDS`.

    The `fit` backend takes `slice_mib` (0 sets no cap), `text_encode` and `num_inference_steps`.
    """
    command: list[str | Path] = [Path(flux_python), '-P', BACKENDS[backend], '--checkpoint', checkpoint]
    command += ['--port', str(backend_port)]
    if backend == 'fit':
        command += ['--slice-mib', str(slice_mib), '--text-encode', text_encode]
        if num_inference_steps > 0:
            command += ['--num-inference-steps', str(num_inference_steps)]
    for flag, value in (('--revision', revision), ('--subfolder', subfolder)):
        if value is not None:
            command += [flag, value]
    process = subprocess.Popen(command)
    meta = {policy_keys.CHECKPOINT_ID: checkpoint, policy_keys.TYPE: 'flux3_action', 'revision': revision}
    meta |= {'backend': backend, 'slice_mib': slice_mib, 'text_encode': text_encode}
    model = flux_server.Flux3ActionModel(process, backend_port, meta)
    try:
        probe = RoboarenaClient(port=backend_port)
        wait_for_subprocess_ready(
            lambda: probe.probe() is None,
            partial(flux_server._exit_status, process),
            'FLUX 3 Action backend',
            max_wait=WARMUP_DEADLINE_S,
        )
        warmup(model, flux_server._warm_observation())
    except Exception:
        model.close()
        raise
    return model


class V3RulesModel(Model):
    """A FLUX 3 Action model with the camera and task rules of v3, and the first actions of later chunks dropped."""

    def __init__(
        self,
        inner: Model,
        still_calls: int,
        skip_actions: int,
        camera: str = 'left',
        grip_close: float | None = None,
        grip_open: float = 0.1,
        hybrid: bool = False,
        lead_actions: int = _HYBRID_LEAD,
        approach_speed: float = 1.0,
        max_retries: int = 0,
    ):
        """`grip_close` makes the gripper command full: closed from a command of `grip_close` or more until a command
        of `grip_open` or less. `hybrid` plays a pick task as stop-and-think on a schedule that requests
        `_HYBRID_LEAD` actions before the end of a chunk: `_HYBRID_PICK` actions, then the last one held for the lead,
        so the arm is still at the next observation. Other tasks drop the lead from each later chunk."""
        assert camera in ('left', 'both'), camera
        """`lead_actions` is the lead of the hybrid schedule. `approach_speed` above 1 plays the chunks of a pick task
        that keep an open gripper open faster, by skipping actions. `max_retries` above 0: a close on nothing opens
        and lifts the gripper, and the next close near it goes deeper (and on the 2nd retry also turns)."""
        self._grip_close, self._grip_open, self._hybrid = grip_close, grip_open, hybrid
        self._lead, self._approach_speed, self._max_retries = lead_actions, approach_speed, max_retries
        self._misses: dict[str, list[np.ndarray]] = {}
        self._retries: dict[str, int] = {}
        self._counts = {'miss lifts': 0, 'changed closes': 0, 'fast chunks': 0}
        self._grip_closed: set[str] = set()
        self._inner = inner
        self._camera = camera
        self._still_calls = still_calls
        self._skip_actions = skip_actions
        self._use_exterior_2: dict[str, bool] = {}
        self._recent_joints: dict[str, deque] = {}
        self._picking: set[str] = set()

    def __call__(self, obs: Obs, *, session_id: str) -> list[dict[str, Any]]:
        first = session_id not in self._use_exterior_2
        if first:
            side = exterior_side(obs[flux3_action.EXTERIOR_IMAGE_1], obs[flux3_action.EXTERIOR_IMAGE_2])
            self._use_exterior_2[session_id] = side != 'left'
            logger.info(f'Session {session_id}: image.exterior is the {side} shoulder camera')
        view_key = flux3_action.EXTERIOR_IMAGE_2 if self._use_exterior_2[session_id] else flux3_action.EXTERIOR_IMAGE_1
        view = obs[view_key]
        views = {flux3_action.EXTERIOR_IMAGE_1: view, flux3_action.EXTERIOR_IMAGE_2: view} if self._camera == 'left' else {}
        joints = np.asarray(obs[flux3_action.JOINT_POSITION], dtype=np.float32).reshape(-1)
        grip = float(np.asarray(obs[flux3_action.GRIPPER_POSITION]).reshape(-1)[0])
        closed = grip > _GRIP_CLOSED_OBS
        raw_task = str(obs.get(flux3_action.PROMPT, '')).strip().lower()
        is_pick = raw_task.startswith('pick')
        if is_pick and self._missed(joints, grip, session_id):
            return self._lift(joints, session_id)
        task = self._task(str(obs.get(flux3_action.PROMPT, '')), joints, closed, session_id)
        request = {**obs, **views, flux3_action.PROMPT: task}
        actions = self._inner(request, session_id=session_id)
        if not self._hybrid:
            actions = actions if first else actions[self._skip_actions :]
        elif is_pick:
            actions = actions[:_HYBRID_PICK] + [actions[_HYBRID_PICK - 1]] * (self._lead + 1)
        else:
            actions = actions[: len(actions) - self._lead] if first else actions[self._lead :]
        if is_pick:
            actions = self._retry_close(actions, joints, session_id)
            if not closed:
                actions = self._fast(actions)
        return actions if self._grip_close is None else [self._full_grip(a, session_id) for a in actions]

    def _closing(self, action: dict[str, Any]) -> bool:
        threshold = 0.5 if self._grip_close is None else self._grip_close
        return float(np.asarray(action[policy_codecs.ACTION]).reshape(-1)[-1]) >= threshold

    def _missed(self, joints: np.ndarray, grip: float, session_id: str) -> bool:
        """True (once per close) when the commanded close shut the gripper on nothing and a retry is left."""
        if self._max_retries <= 0 or session_id not in self._grip_closed or grip < _EMPTY_GRIP:
            return False
        if self._retries.get(session_id, 0) >= self._max_retries:
            return False
        self._misses.setdefault(session_id, []).append(arm.gripper_pose(joints)[:3, 3].copy())
        return True

    def _lift(self, joints: np.ndarray, session_id: str) -> list[dict[str, Any]]:
        """Open the gripper and lift it, then hold still for a fresh look."""
        self._grip_closed.discard(session_id)
        self._counts['miss lifts'] += 1
        up = arm.straight_move(joints, np.array([0.0, 0.0, _LIFT_M / _LIFT_ACTIONS]), _LIFT_ACTIONS)
        path = np.concatenate([up, np.repeat(up[-1:], _LIFT_HOLD, axis=0)])
        logger.info(f'Session {session_id}: closed on nothing, open and lift {_LIFT_M * 100:.0f} cm')
        return [{policy_codecs.ACTION: np.concatenate([q, [0.0]]).astype(np.float32)} for q in path]

    def _retry_close(self, actions: list[dict[str, Any]], joints: np.ndarray, session_id: str) -> list[dict[str, Any]]:
        """Change the first close of a chunk that is near a miss: deeper, and on the 2nd retry also turned."""
        misses = self._misses.get(session_id)
        if not misses or session_id in self._grip_closed:
            return actions
        first = next((k for k, a in enumerate(actions) if self._closing(a)), None)
        if first is None:
            return actions
        values = np.stack([np.asarray(a[policy_codecs.ACTION], dtype=np.float64).reshape(-1) for a in actions])
        at = arm.gripper_pose(values[first, :7])[:3, 3]
        near = [k for k, m in enumerate(misses)
                if np.linalg.norm(at[:2] - m[:2]) < _MISS_NEAR_XY and abs(at[2] - m[2]) < _MISS_NEAR_Z]
        if not near:
            return actions
        misses.pop(near[0])
        retry = self._retries.get(session_id, 0) + 1
        self._retries[session_id] = retry
        self._counts['changed closes'] += 1
        before = values[first - 1, :7] if first > 0 else joints
        turn = np.array([0.0, 0.0, _TURN_RAD / _RETRY_ACTIONS]) if retry >= 2 else None
        move = arm.straight_move(before, np.array([0.0, 0.0, -_DEEPER_M / _RETRY_ACTIONS]), _RETRY_ACTIONS, turn=turn)
        count = min(_RETRY_ACTIONS, len(values) - first)
        values[first : first + count, :7] = move[:count]
        values[first : first + count, 7] = 0.0
        values[first + count :, :7] = move[count - 1]
        values[first + count :, 7] = 1.0
        logger.info(f'Session {session_id}: retry {retry} near a miss: {_DEEPER_M * 100:.0f} cm deeper'
                    + (f', turned {np.degrees(_TURN_RAD):.0f} deg' if turn is not None else ''))
        return [{**a, policy_codecs.ACTION: v.astype(np.float32)} for a, v in zip(actions, values, strict=True)]

    def _fast(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Skip actions of a chunk that keeps the gripper open, so the arm reaches faster."""
        if self._approach_speed <= 1.0 or any(self._closing(a) for a in actions):
            return actions
        self._counts['fast chunks'] += 1
        keep = np.unique(np.round(np.arange(0, len(actions), self._approach_speed)).astype(int))
        return [actions[k] for k in keep if k < len(actions)] + [actions[-1]]

    def _full_grip(self, action: dict[str, Any], session_id: str) -> dict[str, Any]:
        values = np.array(action[policy_codecs.ACTION], dtype=np.float32)
        if values[-1] >= self._grip_close:
            self._grip_closed.add(session_id)
        elif values[-1] <= self._grip_open:
            self._grip_closed.discard(session_id)
        values[-1] = 1.0 if session_id in self._grip_closed else 0.0
        return {**action, policy_codecs.ACTION: values}

    def _task(self, task: str, joints: np.ndarray, closed: bool, session_id: str) -> str:
        pick = pick_part(task)
        if pick is None:
            return task
        recent = self._recent_joints.setdefault(session_id, deque(maxlen=self._still_calls + 1))
        recent.append(joints.copy())
        if closed:
            self._picking.discard(session_id)
        elif session_id not in self._picking and len(recent) == recent.maxlen:
            if np.ptp(np.stack(recent), axis=0).max() < _STILL_RAD:
                self._picking.add(session_id)
                logger.info(f'Session {session_id}: the arm is still and the gripper is open, task now {pick!r}')
        return pick if session_id in self._picking else task

    def end_session(self, session_id: str) -> None:
        self._use_exterior_2.pop(session_id, None)
        self._recent_joints.pop(session_id, None)
        self._picking.discard(session_id)
        self._grip_closed.discard(session_id)
        self._misses.pop(session_id, None)
        self._retries.pop(session_id, None)
        logger.info(f'Rule counts so far: {self._counts}')
        self._inner.end_session(session_id)

    def meta(self) -> dict[str, Any]:
        rules = {'camera': self._camera, 'still_calls': self._still_calls, 'skip_actions': self._skip_actions}
        rules |= {'grip_close': self._grip_close, 'grip_open': self._grip_open, 'hybrid': self._hybrid}
        rules |= {'lead_actions': self._lead, 'approach_speed': self._approach_speed, 'max_retries': self._max_retries}
        return {**self._inner.meta(), 'v3_rules': rules}

    def close(self) -> None:
        self._inner.close()


@cfn.config(model=flux_model, still_calls=3, skip_actions=4, camera='left', grip_close=None, grip_open=0.1, hybrid=False,
            lead_actions=_HYBRID_LEAD, approach_speed=1.0, max_retries=0)
def v3_rules_model(
    model: Model,
    still_calls: int,
    skip_actions: int,
    camera: str,
    grip_close: float | None,
    grip_open: float,
    hybrid: bool,
    lead_actions: int,
    approach_speed: float,
    max_retries: int,
) -> Model:
    return V3RulesModel(model, still_calls, skip_actions, camera, grip_close, grip_open, hybrid,
                        lead_actions, approach_speed, max_retries)


# v3 plays 11.5 actions of each chunk at 15 fps, and requests the next chunk 0.2 s before the end.
@cfn.config(codec=codecs.droid_3cam, horizon_sec=0.7667, inference_lead_sec=0.2)
def v3_pipeline(codec: Codec, horizon_sec: float, inference_lead_sec: float) -> PolicyDeployment:
    schedule = ChunkedSchedule(codecs.FPS, horizon_sec, inference_lead=ConstantDuration(inference_lead_sec))
    return PolicyDeployment(
        Sequential(
            TrajectoryPlayer(replan_on_error=True), schedule, TransformImages(*codecs.VIEW_SIZE, mode=ResizeMode.BOUND)
        ),
        codec,
    )


_both_views = v3_rules_model.override(skip_actions=0, camera='both')

_both_views_2step = _both_views.override(model=flux_model.override(num_inference_steps=2))
_both_views_1step = _both_views.override(model=flux_model.override(num_inference_steps=1))

COMMANDS = {
    'droid_v3': serve.override(model=v3_rules_model, pipeline=v3_pipeline),
    'droid_fit': serve.override(model=flux_model, pipeline=flux_server.pipeline),
    # The v3 rules with a schedule for the delay of a FLUX call (about 0.85 s): the next request goes 0.9 s before
    # the end of a chunk, each chunk plays 18.5 actions (1.23 s), and a later chunk starts 13 actions (0.87 s) in,
    # where the arm is when the answer starts to play.
    # Both exterior views, as the policy learned from them, and a request at the end of a chunk: the arm is still
    # at each observation, so each chunk starts where the arm is. `droid_cam2` plays each chunk whole, as BFL's DROID
    # settings do; `droid_cam2_short` plays 15.5 actions (1.03 s) of it. Both keep the pick-part rule of v3.
    'droid_cam2': serve.override(model=_both_views, pipeline=flux_server.pipeline.override(codec=codecs.droid_3cam)),
    'droid_cam2_short': serve.override(
        model=_both_views, pipeline=v3_pipeline.override(horizon_sec=1.0333, inference_lead_sec=0.0)
    ),
    # `droid_cam2_short` with a full gripper command: the policy commands a part-closed gripper most of the time,
    # and the object slips. `droid_hybrid` adds the hybrid schedule: stop-and-think for a pick task, no stop for others.
    'droid_grip': serve.override(
        model=_both_views.override(grip_close=0.35),
        pipeline=v3_pipeline.override(horizon_sec=1.0333, inference_lead_sec=0.0),
    ),
    'droid_hybrid': serve.override(
        model=_both_views.override(grip_close=0.35, hybrid=True),
        pipeline=v3_pipeline.override(horizon_sec=2.2, inference_lead_sec=0.9),
    ),
    'droid_v3fix': serve.override(
        model=v3_rules_model.override(skip_actions=13),
        pipeline=v3_pipeline.override(horizon_sec=1.2333, inference_lead_sec=0.9),
    ),
    # Fewer denoising steps: the GD model at 2 steps and 1 step (default is 4). Both cameras, hybrid schedule.
    'droid_hybrid_2step': serve.override(
        model=_both_views_2step.override(grip_close=0.35, hybrid=True),
        pipeline=v3_pipeline.override(horizon_sec=2.2, inference_lead_sec=0.9),
    ),
    'droid_hybrid_1step': serve.override(
        model=_both_views_1step.override(grip_close=0.35, hybrid=True),
        pipeline=v3_pipeline.override(horizon_sec=2.2, inference_lead_sec=0.9),
    ),
    # 1 step, faster: the lead fits a 1-step call (5 actions, 0.33 s), and an open gripper on a pick task reaches
    # 1.25x faster. `droid_retry_1step` adds the retry after a close on nothing (at most 2 per episode).
    'droid_fast_1step': serve.override(
        model=_both_views_1step.override(grip_close=0.35, hybrid=True, lead_actions=5, approach_speed=1.25),
        pipeline=v3_pipeline.override(horizon_sec=2.2, inference_lead_sec=0.35),
    ),
    'droid_retry_1step': serve.override(
        model=_both_views_1step.override(
            grip_close=0.35, hybrid=True, lead_actions=5, approach_speed=1.25, max_retries=2
        ),
        pipeline=v3_pipeline.override(horizon_sec=2.2, inference_lead_sec=0.35),
    ),
    # 2 steps without hybrid (stop-and-think for all tasks): if 2 steps is fast enough, no need for hybrid.
    'droid_cam2_2step': serve.override(
        model=_both_views_2step,
        pipeline=v3_pipeline.override(horizon_sec=1.0333, inference_lead_sec=0.0),
    ),
}


if __name__ == '__main__':
    init_logging()
    cfn.cli(COMMANDS)

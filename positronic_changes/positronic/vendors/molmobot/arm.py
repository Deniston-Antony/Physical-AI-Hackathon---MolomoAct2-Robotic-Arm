"""Kinematics of the Franka FR3 arm of `franka_droid`: the gripper pose and straight gripper moves in joint space."""

import numpy as np

# Modified DH parameters (a, d, alpha) of joints 1-7, then the flange.
_DH = (
    (0.0, 0.333, 0.0),
    (0.0, 0.0, -np.pi / 2),
    (0.0, 0.316, np.pi / 2),
    (0.0825, 0.0, np.pi / 2),
    (-0.0825, 0.384, -np.pi / 2),
    (0.0, 0.0, np.pi / 2),
    (0.088, 0.0, np.pi / 2),
)
_FLANGE_D = 0.107
# The `gripper` site of franka_droid is this far along the flange z axis (checked against recorded ee poses).
_GRIPPER_D = 0.155
JOINT_LIMITS = np.array([
    (-2.7437, 2.7437),
    (-1.7837, 1.7837),
    (-2.9007, 2.9007),
    (-3.0421, -0.1518),
    (-2.8065, 2.8065),
    (0.5445, 4.5169),
    (-3.0159, 3.0159),
])


def _dh(a: float, d: float, alpha: float, theta: float) -> np.ndarray:
    ca, sa, ct, st = np.cos(alpha), np.sin(alpha), np.cos(theta), np.sin(theta)
    return np.array([[ct, -st, 0, a], [st * ca, ct * ca, -sa, -d * sa], [st * sa, ct * sa, ca, d * ca], [0, 0, 0, 1]])


def gripper_pose(joints: np.ndarray) -> np.ndarray:
    """The 4x4 pose of the gripper site in the robot base frame. Its z axis points from the wrist to the fingers."""
    pose = np.eye(4)
    for (a, d, alpha), theta in zip(_DH, np.asarray(joints, dtype=np.float64), strict=True):
        pose = pose @ _dh(a, d, alpha, theta)
    return pose @ _dh(0.0, _FLANGE_D + _GRIPPER_D, 0.0, 0.0)


def _jacobian(joints: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """6x7: the gripper's linear velocity and its rotation (small-angle vector) per joint."""
    base = gripper_pose(joints)
    jac = np.zeros((6, 7))
    for i in range(7):
        q = np.array(joints, dtype=np.float64)
        q[i] += eps
        moved = gripper_pose(q)
        jac[:3, i] = (moved[:3, 3] - base[:3, 3]) / eps
        rot = moved[:3, :3] @ base[:3, :3].T
        jac[3:, i] = np.array([rot[2, 1] - rot[1, 2], rot[0, 2] - rot[2, 0], rot[1, 0] - rot[0, 1]]) / (2 * eps)
    return jac


def straight_move(
    joints: np.ndarray, step: np.ndarray, count: int, damping: float = 0.02, turn: np.ndarray | None = None
) -> np.ndarray:
    """``count`` joint positions that move the gripper by ``step`` (m, base frame) each.

    The gripper turns by ``turn`` (a rotation vector in rad, base frame) each, or keeps its rotation.
    """
    q = np.array(joints, dtype=np.float64)
    out = np.empty((count, 7))
    turn = np.zeros(3) if turn is None else np.asarray(turn, dtype=np.float64)
    twist = np.concatenate([np.asarray(step, dtype=np.float64), turn])
    for k in range(count):
        jac = _jacobian(q)
        dq = jac.T @ np.linalg.solve(jac @ jac.T + damping**2 * np.eye(6), twist)
        q = np.clip(q + dq, JOINT_LIMITS[:, 0], JOINT_LIMITS[:, 1])
        out[k] = q
    return out

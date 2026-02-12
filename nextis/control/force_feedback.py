"""Force feedback from follower motors to leader arms.

Gripper force feedback: follower gripper torque → leader gripper current
ceiling via EMA filter + dead zone + linear ramp + saturation.

Joint force feedback: position error between leader and follower →
virtual spring via CURRENT_POSITION mode on Dynamixel motors.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class GripperForceFeedback:
    """Maps follower gripper torque to leader gripper Goal_Current.

    Uses EMA-filtered absolute torque with dead zone, linear ramp,
    and saturation to produce a current ceiling for the leader gripper.

    Args:
        alpha: EMA smoothing factor (higher = faster response).
        baseline_current: Minimum current (mA) for light spring feel.
        max_current: Maximum current (mA) at saturation.
        torque_threshold: Dead zone (Nm) below which baseline is used.
        torque_saturation: Torque (Nm) at which max current is reached.
    """

    def __init__(
        self,
        alpha: float = 0.3,
        baseline_current: int = 60,
        max_current: int = 1750,
        torque_threshold: float = 0.2,
        torque_saturation: float = 2.0,
    ) -> None:
        self.alpha = alpha
        self.baseline_current = baseline_current
        self.max_current = max_current
        self.torque_threshold = torque_threshold
        self.torque_saturation = torque_saturation
        self._filtered_torque: float = 0.0

    def update(self, raw_torque: float) -> int:
        """Process a new torque reading and return the goal current.

        Args:
            raw_torque: Raw gripper torque from follower (Nm, signed).

        Returns:
            Goal current (mA) for the leader gripper motor.
        """
        torque_mag = abs(raw_torque)

        # EMA filter (tau ~ 55ms at 60Hz with alpha=0.3)
        self._filtered_torque = self.alpha * torque_mag + (1 - self.alpha) * self._filtered_torque

        # Dead zone → linear ramp → saturation
        if self._filtered_torque <= self.torque_threshold:
            goal_current = self.baseline_current
        elif self._filtered_torque >= self.torque_saturation:
            goal_current = self.max_current
        else:
            t = (self._filtered_torque - self.torque_threshold) / (
                self.torque_saturation - self.torque_threshold
            )
            goal_current = int(
                self.baseline_current + t * (self.max_current - self.baseline_current)
            )

        return max(self.baseline_current, min(self.max_current, goal_current))

    @property
    def filtered_torque(self) -> float:
        """Current EMA-filtered torque magnitude (Nm)."""
        return self._filtered_torque

    def reset(self) -> None:
        """Reset the EMA filter state."""
        self._filtered_torque = 0.0


class JointForceFeedback:
    """Virtual spring force feedback for a single joint.

    Uses Dynamixel CURRENT_POSITION mode: sets Goal_Position to follower's
    actual position and Goal_Current proportional to position error.
    This creates a spring pulling the leader toward the follower.

    Args:
        k_spring: Spring stiffness (mA/rad).
        deadzone: Position error (rad) below which current is zero.
        max_current: Maximum current (mA).
        min_force: Minimum current (mA) when outside deadzone.
    """

    def __init__(
        self,
        k_spring: float = 15000.0,
        deadzone: float = 0.10,
        max_current: int = 1750,
        min_force: int = 100,
    ) -> None:
        self.k_spring = k_spring
        self.deadzone = deadzone
        self.max_current = max_current
        self.min_force = min_force

    def compute_spring(
        self,
        leader_pos: float,
        follower_pos: float,
        homing_offset: int = 0,
    ) -> tuple[int, int]:
        """Compute Goal_Position and Goal_Current for virtual spring.

        Args:
            leader_pos: Leader joint position (radians).
            follower_pos: Follower joint position (radians).
            homing_offset: Dynamixel software homing offset (ticks).

        Returns:
            Tuple of (goal_position_raw_ticks, goal_current_mA).
        """
        pos_error = abs(leader_pos - follower_pos)

        # Goal_Current: spring force proportional to error
        if pos_error > self.deadzone:
            excess = pos_error - self.deadzone
            goal_current = min(
                int(max(self.k_spring * excess, self.min_force)),
                self.max_current,
            )
        else:
            goal_current = 0  # Completely limp during normal tracking

        # Goal_Position: follower position converted to raw Dynamixel ticks
        homed_ticks = int((follower_pos + np.pi) / (2 * np.pi) * 4096)
        raw_ticks = homed_ticks - homing_offset

        return raw_ticks, goal_current

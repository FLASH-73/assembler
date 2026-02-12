"""Human intervention detection for human-in-the-loop (HIL) control.

Detects when a human operator takes over from an autonomous policy by
monitoring leader arm velocity. Uses position-delta velocity estimation
filtered by policy-relevant arms.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InterventionDetector:
    """Detects human intervention on the leader arm during autonomous execution.

    Tracks leader arm position changes to estimate velocity. When velocity
    exceeds a threshold, the human is considered to have taken over control.

    Args:
        move_threshold: Velocity threshold for human detection.
        idle_timeout: Seconds of no movement before reverting to autonomous.
        inference_hz: Policy inference rate (used to scale position deltas).
    """

    def __init__(
        self,
        move_threshold: float = 0.5,
        idle_timeout: float = 2.0,
        inference_hz: float = 30.0,
    ) -> None:
        self.move_threshold = move_threshold
        self.idle_timeout = idle_timeout
        self.inference_hz = inference_hz

        self._last_leader_pos: dict[str, float] | None = None
        self._last_human_move_time: float = 0.0

    def get_leader_velocity(
        self,
        leader: Any,
        policy_arms: list[str] | None = None,
    ) -> float:
        """Estimate leader arm velocity from position deltas.

        Only checks arms that the policy was trained on. For a left-arm-only
        policy, only left arm movement triggers intervention.

        Args:
            leader: Connected leader arm with get_action() method.
            policy_arms: List of arm prefixes the policy controls
                (e.g., ["left", "right"]). None means all arms.

        Returns:
            Maximum velocity magnitude across relevant joints, scaled by
            inference rate.
        """
        if not leader:
            return 0.0

        try:
            current_pos = leader.get_action()
            if not current_pos:
                return 0.0

            # Initialize on first call
            if self._last_leader_pos is None:
                self._last_leader_pos = current_pos.copy()
                return 0.0

            if policy_arms is None:
                policy_arms = ["left", "right"]

            # Compute max position delta across relevant motors
            max_delta = 0.0
            for key, val in current_pos.items():
                is_relevant = False
                if "left" in policy_arms and key.startswith("left_"):
                    is_relevant = True
                if "right" in policy_arms and key.startswith("right_"):
                    is_relevant = True
                # Non-prefixed keys (e.g., "gripper") are always relevant
                if not key.startswith("left_") and not key.startswith("right_"):
                    is_relevant = True

                if is_relevant and key in self._last_leader_pos:
                    delta = abs(float(val) - float(self._last_leader_pos[key]))
                    max_delta = max(max_delta, delta)

            self._last_leader_pos = current_pos.copy()

            # Scale by loop rate to get velocity estimate
            velocity = max_delta * self.inference_hz
            return velocity

        except Exception as e:
            msg = str(e)
            # Suppress known spam errors from uncalibrated motors
            if "has no calibration registered" not in msg and "Failed to sync read" not in msg:
                logger.debug("Error reading leader velocity: %s", e)
            return 0.0

    def check(
        self,
        leader: Any,
        policy_arms: list[str] | None = None,
    ) -> bool:
        """Check whether a human has taken over from the autonomous policy.

        Returns True if the leader velocity exceeds the move threshold
        (indicating active human input). Also tracks the last time human
        movement was detected for idle timeout logic.

        Args:
            leader: Connected leader arm with get_action() method.
            policy_arms: List of arm prefixes the policy controls.

        Returns:
            True if human intervention is detected.
        """
        velocity = self.get_leader_velocity(leader, policy_arms)

        if velocity > self.move_threshold:
            self._last_human_move_time = time.time()
            return True

        # Check idle timeout — if human moved recently, still intervening
        if self._last_human_move_time > 0:
            idle_time = time.time() - self._last_human_move_time
            if idle_time < self.idle_timeout:
                return True

        return False

    def reset(self) -> None:
        """Reset the detector state (e.g., when starting a new episode)."""
        self._last_leader_pos = None
        self._last_human_move_time = 0.0

    @property
    def time_since_last_move(self) -> float:
        """Seconds since the last detected human movement."""
        if self._last_human_move_time == 0.0:
            return float("inf")
        return time.time() - self._last_human_move_time

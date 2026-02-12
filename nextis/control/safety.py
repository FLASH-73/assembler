"""Safety layer for motor torque and load monitoring.

Provides real-time safety checks for both Feetech (load-based) and Damiao
(torque-based) motors. Triggers emergency stop on sustained violations.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from nextis.errors import SafetyError

logger = logging.getLogger(__name__)

# Damiao motor torque limits (Nm) — conservative defaults for testing.
# Actual limits come from robot.get_torque_limits() at runtime.
DAMIAO_TORQUE_LIMITS = {
    "J8009P": 3.5,  # 10% of 35Nm max
    "J4340P": 0.8,  # 10% of 8Nm max
    "J4310": 0.4,  # 10% of 4Nm max
}


class SafetyLayer:
    """Motor safety monitor with debounced violation detection.

    Checks motor loads/torques on a round-robin schedule to minimize
    lock-holding time. Triggers emergency stop after consecutive
    violations exceed the limit.

    Args:
        robot_lock: Threading lock for robot bus access.
        load_threshold: Feetech load threshold (0-1000 scale, 1000 = 100%).
        violation_limit: Consecutive violations before emergency stop.
    """

    def __init__(
        self,
        robot_lock: Any,
        load_threshold: int = 500,
        violation_limit: int = 3,
    ) -> None:
        self.lock = robot_lock
        self.load_threshold = load_threshold
        self.violation_limit = violation_limit
        self.violation_counts: dict[str, int] = {}
        self.latest_loads: dict[str, float] = {}
        self.latest_torques: dict[str, float] = {}
        self.monitored_motors: list[tuple] = []
        self.current_motor_index: int = 0
        self._is_damiao_robot: bool | None = None

    def check_limits(self, robot: Any) -> bool:
        """Check Feetech motor load limits (round-robin, one motor per call).

        Args:
            robot: Connected robot instance with motor buses.

        Returns:
            True if safe, False if emergency stop was triggered.
        """
        if not robot or not robot.is_connected:
            return True

        try:
            if not self.monitored_motors:
                self._discover_motors(robot)
                if not self.monitored_motors:
                    return True

            # Check one motor per call to minimize bus contention
            self.current_motor_index = (self.current_motor_index + 1) % len(self.monitored_motors)
            bus, motor = self.monitored_motors[self.current_motor_index]

            try:
                load_val = bus.read("Present_Load", motor, normalize=False)
                magnitude = load_val % 1024
                self.latest_loads[motor] = magnitude

                if magnitude > self.load_threshold:
                    self.violation_counts[motor] = self.violation_counts.get(motor, 0) + 1
                    logger.warning(
                        "Motor %s load %d/%d (violation %d)",
                        motor,
                        magnitude,
                        self.load_threshold,
                        self.violation_counts[motor],
                    )
                else:
                    self.violation_counts[motor] = 0

                if self.violation_counts.get(motor, 0) >= self.violation_limit:
                    logger.error("Motor %s overloaded — triggering E-STOP", motor)
                    self.emergency_stop(robot)
                    return False
            except Exception:
                pass  # Silently skip single read errors for robustness

            return True
        except Exception as e:
            logger.error("Safety check failed: %s", e)
            return True

    def check_damiao_limits(self, robot: Any) -> bool:
        """Check Damiao motor torque limits.

        Damiao motors report torque in Nm. Checks against per-motor limits
        from robot.get_torque_limits().

        Args:
            robot: Connected robot with get_torques()/get_torque_limits() methods.

        Returns:
            True if safe, False if emergency stop was triggered.
        """
        if not robot or not robot.is_connected:
            return True

        if not hasattr(robot, "get_torques") or not hasattr(robot, "get_torque_limits"):
            return True

        try:
            torques = robot.get_torques()
            limits = robot.get_torque_limits()

            for motor_name, torque in torques.items():
                self.latest_torques[motor_name] = torque
                limit = limits.get(motor_name, 10.0)

                if abs(torque) > limit:
                    self.violation_counts[motor_name] = self.violation_counts.get(motor_name, 0) + 1
                    logger.warning(
                        "Damiao %s torque %.2fNm > %.1fNm (violation %d)",
                        motor_name,
                        torque,
                        limit,
                        self.violation_counts[motor_name],
                    )
                    if self.violation_counts.get(motor_name, 0) >= self.violation_limit:
                        logger.error("Damiao %s overloaded — E-STOP", motor_name)
                        self.emergency_stop(robot)
                        return False
                else:
                    self.violation_counts[motor_name] = 0

            return True
        except Exception as e:
            logger.error("Damiao safety check failed: %s", e)
            return True  # Don't block on check errors

    def check_all_limits(self, robot: Any) -> bool:
        """Check all applicable safety limits for the robot.

        Automatically detects robot type and applies appropriate checks.

        Args:
            robot: Connected robot instance.

        Returns:
            True if safe, False if emergency stop was triggered.
        """
        if not self.check_limits(robot):
            return False
        return not (hasattr(robot, "get_torques") and not self.check_damiao_limits(robot))

    def emergency_stop(self, robot: Any) -> None:
        """Cut power to all motors immediately.

        Args:
            robot: Connected robot instance.

        Raises:
            SafetyError: Always raised after disconnecting.
        """
        logger.critical("!!! EMERGENCY STOP TRIGGERED !!!")
        if not robot:
            raise SafetyError("Emergency stop — no robot to disconnect")

        try:
            timestamp = time.strftime("%H:%M:%S")
            logger.critical("Cutting power at %s", timestamp)
            robot.disconnect()
        except Exception as e:
            logger.error("E-Stop failed to disconnect cleanly: %s", e)

        raise SafetyError("Emergency stop triggered — motors disabled")

    def _discover_motors(self, robot: Any) -> None:
        """Build list of Feetech motors to monitor (skips Damiao buses)."""
        buses: list = []
        if hasattr(robot, "left_arm"):
            buses.append(robot.left_arm.bus)
        if hasattr(robot, "right_arm"):
            buses.append(robot.right_arm.bus)
        if hasattr(robot, "bus"):
            buses.append(robot.bus)

        for bus in buses:
            # Skip Damiao CAN buses — they use check_damiao_limits()
            try:
                from lerobot.motors.damiao.damiao import DamiaoMotorsBus

                if isinstance(bus, DamiaoMotorsBus):
                    continue
            except ImportError:
                pass
            for motor_name in bus.motors:
                self.monitored_motors.append((bus, motor_name))

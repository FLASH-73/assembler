"""Safe return-to-home-position for Damiao arms.

Uses the MIT rate limiter in DamiaoMotorsBus.sync_write() for smooth
movement. Disables motors when done.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def homing_loop(
    robot: Any,
    home_pos: dict[str, float],
    duration: float = 10.0,
    homing_vel: float = 0.05,
    cancel_check: Any | None = None,
) -> None:
    """Move robot to home position over duration, then disable motors.

    Uses the existing MIT rate limiter in sync_write() for smooth movement.
    At homing_vel=0.15: J8009P ~1 rad/s, J4340P ~0.8 rad/s.

    Args:
        robot: Connected Damiao follower robot.
        home_pos: Target joint positions {motor_name: radians}.
        duration: Maximum time to reach home (seconds).
        homing_vel: Velocity limit during homing (rad/s per motor).
        cancel_check: Optional callable returning True to cancel homing.
    """
    try:
        from lerobot.motors.damiao.damiao import DamiaoMotorsBus
    except ImportError:
        logger.warning("lerobot not available — skipping homing")
        return

    bus = getattr(robot, "bus", None)
    if not bus or not isinstance(bus, DamiaoMotorsBus):
        logger.warning("Robot has no Damiao bus — skipping homing")
        return

    old_vel = bus.velocity_limit
    bus.velocity_limit = homing_vel
    logger.info("Homing started (vel=%.3f, duration=%.1fs)", homing_vel, duration)

    try:
        start = time.time()
        while time.time() - start < duration:
            if cancel_check and cancel_check():
                logger.info("Homing cancelled")
                break
            bus.sync_write("Goal_Position", home_pos)
            time.sleep(1.0 / 30)  # 30Hz control

        bus.velocity_limit = old_vel
    except Exception as e:
        logger.error("Homing error: %s", e)
    finally:
        # Always disable motors when done
        try:
            bus = getattr(robot, "bus", None)
            if bus and isinstance(bus, DamiaoMotorsBus):
                for motor in bus._motors.values():
                    bus._control.disable(motor)
                logger.info("Homing complete — motors disabled")
        except Exception:
            pass

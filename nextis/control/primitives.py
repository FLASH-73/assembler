"""Parameterized motion primitives for assembly execution.

Each primitive is an async function that takes a robot instance + parameters,
executes a motion using impedance control, and returns success/failure based
on force/position criteria. Currently stubs -- interfaces are locked so the
sequencer and policy router can call them, but no real hardware motion occurs.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from nextis.errors import AssemblyError

logger = logging.getLogger(__name__)


@dataclass
class PrimitiveResult:
    """Result from executing a motion primitive.

    Attributes:
        success: Whether the primitive completed successfully.
        actual_force: Measured force at completion (Nm).
        actual_position: End-effector position at completion.
        duration_ms: Execution time in milliseconds.
        error_message: Description of failure, if any.
    """

    success: bool
    actual_force: float = 0.0
    actual_position: list[float] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Primitive functions (stubs)
# ---------------------------------------------------------------------------


async def move_to(
    robot: Any,
    target_pose: list[float] | None = None,
    velocity: float = 0.5,
    timeout: float = 10.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Move end-effector to a target pose.

    Args:
        robot: Connected follower robot instance.
        target_pose: 6-DOF target [x, y, z, rx, ry, rz].
        velocity: Movement velocity (0.0 to 1.0 scale).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with success and actual position.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    target_pose = target_pose or []
    logger.info("move_to: target=%s velocity=%.2f", target_pose, velocity)
    start = time.monotonic()
    await asyncio.sleep(min(1.0, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("move_to: complete in %.0fms", duration)
    return PrimitiveResult(success=True, actual_position=target_pose, duration_ms=duration)


async def pick(
    robot: Any,
    grasp_pose: list[float] | None = None,
    approach_height: float = 0.05,
    force_threshold: float = 0.5,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Pick a part using the gripper.

    Args:
        robot: Connected follower robot instance.
        grasp_pose: 6-DOF grasp pose.
        approach_height: Height above grasp pose for approach (meters).
        force_threshold: Gripper force to confirm grasp (Nm).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with success and measured grip force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    logger.info(
        "pick: grasp_pose=%s approach=%.3fm threshold=%.2fNm",
        grasp_pose,
        approach_height,
        force_threshold,
    )
    start = time.monotonic()
    await asyncio.sleep(min(1.5, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("pick: complete in %.0fms", duration)
    return PrimitiveResult(
        success=True,
        actual_force=force_threshold,
        actual_position=grasp_pose or [],
        duration_ms=duration,
    )


async def place(
    robot: Any,
    target_pose: list[float] | None = None,
    approach_height: float = 0.05,
    release_force: float = 0.2,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Place a part at the target pose and release.

    Args:
        robot: Connected follower robot instance.
        target_pose: 6-DOF placement pose.
        approach_height: Height above target for approach (meters).
        release_force: Gripper force for release trigger (Nm).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with success and actual position.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    target_pose = target_pose or []
    logger.info("place: target=%s approach=%.3fm", target_pose, approach_height)
    start = time.monotonic()
    await asyncio.sleep(min(1.5, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("place: complete in %.0fms", duration)
    return PrimitiveResult(success=True, actual_position=target_pose, duration_ms=duration)


async def guarded_move(
    robot: Any,
    direction: list[float] | None = None,
    force_threshold: float = 5.0,
    max_distance: float = 0.1,
    timeout: float = 10.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Move in a direction until force threshold is hit.

    Args:
        robot: Connected follower robot instance.
        direction: 3D movement direction vector.
        force_threshold: Force to stop at (Nm).
        max_distance: Maximum travel distance (meters).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with measured contact force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    direction = direction or [0, 0, -1]
    logger.info(
        "guarded_move: dir=%s threshold=%.1fNm max=%.3fm",
        direction,
        force_threshold,
        max_distance,
    )
    start = time.monotonic()
    await asyncio.sleep(min(1.0, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("guarded_move: contact at %.1fNm in %.0fms", force_threshold, duration)
    return PrimitiveResult(
        success=True,
        actual_force=force_threshold,
        duration_ms=duration,
    )


async def linear_insert(
    robot: Any,
    target_pose: list[float] | None = None,
    force_limit: float = 10.0,
    compliance_axes: list[bool] | None = None,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Insert a part along a linear path with force limiting.

    Args:
        robot: Connected follower robot instance.
        target_pose: 6-DOF insertion target.
        force_limit: Maximum allowed insertion force (Nm).
        compliance_axes: Per-axis compliance flags [x, y, z, rx, ry, rz].
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with final position and force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    target_pose = target_pose or []
    logger.info("linear_insert: target=%s force_limit=%.1fNm", target_pose, force_limit)
    start = time.monotonic()
    await asyncio.sleep(min(2.0, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("linear_insert: complete in %.0fms", duration)
    return PrimitiveResult(
        success=True,
        actual_force=force_limit * 0.6,
        actual_position=target_pose,
        duration_ms=duration,
    )


async def screw(
    robot: Any,
    target_pose: list[float] | None = None,
    torque_limit: float = 2.0,
    rotations: float = 3.0,
    timeout: float = 20.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Screw operation with torque-based termination.

    Args:
        robot: Connected follower robot instance.
        target_pose: 6-DOF screw axis pose.
        torque_limit: Maximum allowed torque (Nm).
        rotations: Number of full rotations.
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with final torque reading.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    logger.info("screw: rotations=%.1f torque_limit=%.1fNm", rotations, torque_limit)
    start = time.monotonic()
    await asyncio.sleep(min(2.0, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("screw: complete in %.0fms", duration)
    return PrimitiveResult(success=True, actual_force=torque_limit * 0.8, duration_ms=duration)


async def press_fit(
    robot: Any,
    direction: list[float] | None = None,
    force_target: float = 15.0,
    max_distance: float = 0.02,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Press-fit with target force termination.

    Args:
        robot: Connected follower robot instance.
        direction: 3D press direction vector.
        force_target: Target pressing force (Nm).
        max_distance: Maximum travel distance (meters).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with achieved pressing force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    direction = direction or [0, 0, -1]
    logger.info(
        "press_fit: dir=%s target=%.1fNm max=%.3fm",
        direction,
        force_target,
        max_distance,
    )
    start = time.monotonic()
    await asyncio.sleep(min(1.5, timeout) * speed)
    duration = (time.monotonic() - start) * 1000
    logger.info("press_fit: complete at %.1fNm in %.0fms", force_target, duration)
    return PrimitiveResult(success=True, actual_force=force_target, duration_ms=duration)


# ---------------------------------------------------------------------------
# Primitive library — registry and dispatcher
# ---------------------------------------------------------------------------

PrimitiveFn = Callable[..., Awaitable[PrimitiveResult]]


class PrimitiveLibrary:
    """Registry and dispatcher for motion primitives.

    Registers primitive functions by name and dispatches assembly step
    parameters to the appropriate primitive.
    """

    def __init__(self, speed_factor: float = 1.0) -> None:
        self._primitives: dict[str, PrimitiveFn] = {}
        self._speed = speed_factor
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in primitives."""
        self.register("move_to", move_to)
        self.register("pick", pick)
        self.register("place", place)
        self.register("guarded_move", guarded_move)
        self.register("linear_insert", linear_insert)
        self.register("screw", screw)
        self.register("press_fit", press_fit)

    def register(self, name: str, fn: PrimitiveFn) -> None:
        """Register a primitive function by name.

        Args:
            name: Primitive identifier (e.g., "pick").
            fn: Async callable implementing the primitive.
        """
        self._primitives[name] = fn
        logger.debug("Registered primitive: %s", name)

    async def run(
        self,
        name: str,
        robot: Any,
        params: dict | None = None,
    ) -> PrimitiveResult:
        """Execute a primitive by name with given parameters.

        Args:
            name: Primitive name (e.g., "pick", "place").
            robot: Connected follower robot.
            params: Parameters passed as keyword arguments to the primitive.

        Returns:
            PrimitiveResult from the primitive execution.

        Raises:
            AssemblyError: If the primitive name is not registered.
        """
        fn = self._primitives.get(name)
        if fn is None:
            raise AssemblyError(f"Unknown primitive: {name}")
        params = params or {}
        params["_speed_factor"] = self._speed
        logger.info("Dispatching primitive '%s' with params: %s", name, params)
        return await fn(robot=robot, **params)

    @property
    def available(self) -> list[str]:
        """List registered primitive names."""
        return list(self._primitives.keys())

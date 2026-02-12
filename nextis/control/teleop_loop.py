"""60Hz teleoperation control loop.

Composes safety, joint mapping, force feedback, and leader assist into
a single threaded control loop that reads the leader arm, maps joints,
blends startup, sends commands to the follower, and applies safety checks.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import numpy as np

from nextis.control.force_feedback import GripperForceFeedback, JointForceFeedback
from nextis.control.joint_mapping import JointMapper
from nextis.control.leader_assist import LeaderAssistService
from nextis.control.safety import SafetyLayer

logger = logging.getLogger(__name__)

# Try to import precise_sleep from lerobot, fallback to time.sleep
try:
    from lerobot.utils.robot_utils import precise_sleep
except ImportError:

    def precise_sleep(dt: float) -> None:
        time.sleep(max(0, dt))


class TeleopLoop:
    """Threaded 60Hz teleoperation control loop.

    Reads leader arm positions, maps joints to the follower, applies
    startup blending, sends commands, and runs safety / force feedback.

    Args:
        robot: Connected follower robot instance.
        leader: Connected leader arm instance.
        safety: SafetyLayer for motor monitoring.
        joint_mapper: JointMapper with pre-computed mappings.
        leader_assists: Dict of arm_key -> LeaderAssistService instances.
        gripper_ff: Optional GripperForceFeedback controller.
        joint_ff: Optional JointForceFeedback controller.
        frequency: Control loop frequency (Hz).
        blend_duration: Startup blend ramp time (seconds).
    """

    def __init__(
        self,
        robot: Any,
        leader: Any,
        safety: SafetyLayer,
        joint_mapper: JointMapper,
        leader_assists: dict[str, LeaderAssistService] | None = None,
        gripper_ff: GripperForceFeedback | None = None,
        joint_ff: JointForceFeedback | None = None,
        frequency: int = 60,
        blend_duration: float = 2.0,
    ) -> None:
        self.robot = robot
        self.leader = leader
        self.safety = safety
        self.joint_mapper = joint_mapper
        self.leader_assists = leader_assists or {}
        self.gripper_ff = gripper_ff
        self.joint_ff = joint_ff

        self.frequency = frequency
        self.dt = 1.0 / frequency
        self._blend_duration = blend_duration

        # Thread control
        self.is_running = False
        self._thread: threading.Thread | None = None

        # Loop state
        self._blend_start_time: float | None = None
        self._follower_start_pos: dict[str, float] = {}
        self._leader_start_rad: dict[str, float] = {}
        self._rad_to_percent_scale: dict[str, float] = {}
        self.loop_count: int = 0

        # Leader assist state
        self.assist_enabled = False
        self.assist_groups: dict[str, list[str]] = {}
        self._last_leader_pos: dict[str, float] = {}
        self._leader_vel_filtered: dict[str, float] = {}
        self._alpha_vel: float = 0.2

        # Force feedback options
        self.force_feedback_enabled = True
        self.joint_ff_enabled = True

        # Shared action state (for external consumers like recording)
        self._latest_action: dict[str, float] = {}
        self._action_lock = threading.Lock()

    def start(self) -> None:
        """Start the teleoperation loop in a background thread."""
        if self.is_running:
            logger.warning("Teleop loop already running")
            return

        self.is_running = True
        self._blend_start_time = None
        self._follower_start_pos = {}
        self._leader_start_rad = {}
        self._rad_to_percent_scale = {}
        self.loop_count = 0

        self._thread = threading.Thread(target=self._loop, daemon=True, name="TeleopLoop")
        self._thread.start()
        logger.info("Teleop loop started at %dHz", self.frequency)

    def stop(self) -> None:
        """Stop the teleoperation loop and wait for thread to exit."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Teleop loop stopped")

    @property
    def latest_action(self) -> dict[str, float]:
        """Thread-safe copy of the latest follower action dict."""
        with self._action_lock:
            return self._latest_action.copy()

    # ── Main Loop ──────────────────────────────────────────────────

    def _loop(self) -> None:
        """Core 60Hz control loop."""
        logger.info("Control loop running at %dHz", self.frequency)
        self._blend_start_time = time.time()

        perf_start = time.time()

        try:
            while self.is_running:
                loop_start = time.perf_counter()

                # 1. Read leader state
                obs = self._read_leader()
                if obs is None:
                    continue

                # 2. Apply leader assist (gravity comp, friction, haptics)
                if self.leader_assists and self.assist_enabled:
                    self._apply_leader_assist(obs)

                # 3. Map leader joints → follower joints
                leader_action = self._map_joints(obs)

                if self.loop_count == 0:
                    logger.debug(
                        "First frame: %d mapped joints from %d obs keys",
                        len(leader_action),
                        len(obs),
                    )

                # 4. Startup blend: ramp from follower's current position
                if self._blend_start_time and leader_action:
                    leader_action = self._apply_startup_blend(leader_action, obs)

                # 5. Send action to follower
                if leader_action and self.robot:
                    self._send_action(leader_action)

                # 6. Safety checks
                if leader_action and self.robot:
                    if not self._check_safety():
                        break

                    # 7. Force feedback
                    if self.force_feedback_enabled and obs:
                        self._apply_force_feedback(obs)

                # 8. Cache latest action for external consumers
                if leader_action:
                    with self._action_lock:
                        self._latest_action = leader_action.copy()

                # 9. Performance logging (every 1s)
                self.loop_count += 1
                if self.loop_count % self.frequency == 0:
                    now = time.time()
                    real_hz = self.frequency / (now - perf_start)
                    logger.info("Teleop rate: %.1fHz", real_hz)
                    perf_start = now

                # 10. Sleep for remaining frame time
                elapsed = time.perf_counter() - loop_start
                precise_sleep(self.dt - elapsed)

            logger.info("Teleop loop exited normally")

        except OSError as e:
            if e.errno == 5:
                logger.error("Hardware disconnected: %s", e)
            else:
                logger.error("OSError in teleop loop: %s", e)
        except Exception as e:
            logger.error("Teleop loop failed: %s", e, exc_info=True)
        finally:
            self.is_running = False
            logger.info("Teleop loop cleanup complete")

    # ── Leader Read ────────────────────────────────────────────────

    def _read_leader(self, attempts: int = 3) -> dict[str, float] | None:
        """Read leader arm positions with retry on transient errors.

        Args:
            attempts: Maximum read attempts before giving up.

        Returns:
            Observation dict {joint_key: value} or None on failure.
        """
        if not self.leader:
            return None

        for attempt in range(attempts):
            try:
                obs = self.leader.get_action()
                if obs:
                    return obs
            except (OSError, ConnectionError) as e:
                error_str = str(e)
                is_transient = (
                    "Incorrect status packet" in error_str or "Port is in use" in error_str
                )
                if is_transient and attempt < attempts - 1:
                    time.sleep(0.005)
                    continue
                if attempt == attempts - 1 and self.loop_count % 60 == 0:
                    logger.warning("Leader read failed after %d attempts: %s", attempts, e)
                elif not is_transient:
                    logger.error("Leader read error: %s", e)
                    break

        return None

    # ── Joint Mapping ──────────────────────────────────────────────

    def _map_joints(self, obs: dict[str, float]) -> dict[str, float]:
        """Map leader observation to follower action using JointMapper.

        Args:
            obs: Leader observation dict.

        Returns:
            Follower action dict {follower_key: converted_value}.
        """
        action: dict[str, float] = {}
        mapper = self.joint_mapper

        for l_key, f_key in mapper.joint_mapping.items():
            if l_key in obs:
                action[f_key] = mapper.convert_value(
                    value=obs[l_key],
                    follower_key=f_key,
                    leader_key=l_key,
                    leader_start_rad=self._leader_start_rad,
                    follower_start_pos=self._follower_start_pos,
                    rad_to_percent_scale=self._rad_to_percent_scale,
                )

        return action

    # ── Startup Blend ──────────────────────────────────────────────

    def _apply_startup_blend(
        self,
        leader_action: dict[str, float],
        obs: dict[str, float],
    ) -> dict[str, float]:
        """Ramp from follower's current position to leader target.

        Captures follower start position on first frame, then linearly
        blends from start to leader target over blend_duration seconds.

        Args:
            leader_action: Mapped follower action dict.
            obs: Raw leader observation (for delta-tracking capture).

        Returns:
            Blended action dict.
        """
        mapper = self.joint_mapper

        # First frame: capture leader start positions for delta tracking
        if not self._leader_start_rad and mapper.value_mode.value == "rad_to_percent" and obs:
            self._leader_start_rad = {
                l_key: obs[l_key] for l_key in mapper.joint_mapping if l_key in obs
            }
            logger.info(
                "Delta tracking: captured %d leader start positions",
                len(self._leader_start_rad),
            )

        # First frame: capture follower's actual position
        if not self._follower_start_pos and self.robot:
            try:
                fobs = self.robot.get_observation()
                self._follower_start_pos = {k: v for k, v in fobs.items() if k.endswith(".pos")}
                logger.info(
                    "Startup blend: captured %d follower positions",
                    len(self._follower_start_pos),
                )
            except Exception as e:
                logger.warning("Startup blend capture failed: %s", e)
                # Fallback: use last known positions from bus
                if hasattr(self.robot, "bus") and hasattr(self.robot.bus, "_last_positions"):
                    lp = self.robot.bus._last_positions
                    self._follower_start_pos = {f"{k}.pos": v for k, v in lp.items()}
                    logger.info(
                        "Startup blend: using bus fallback (%d joints)",
                        len(self._follower_start_pos),
                    )

        # Compute per-joint rad→percent scale factors from follower calibration
        if (
            not self._rad_to_percent_scale
            and mapper.value_mode.value == "rad_to_percent"
            and hasattr(self.robot, "calibration")
            and self.robot.calibration
        ):
            for _l_key, f_key in mapper.joint_mapping.items():
                motor_name = f_key.replace(".pos", "")
                if "gripper" in motor_name:
                    continue
                cal = self.robot.calibration.get(motor_name)
                if cal:
                    tick_range = cal.range_max - cal.range_min
                    if tick_range > 0:
                        self._rad_to_percent_scale[f_key] = 4096.0 * 100.0 / (np.pi * tick_range)
            logger.info(
                "Per-joint scales: %s",
                {k: f"{v:.1f}" for k, v in self._rad_to_percent_scale.items()},
            )

        # Compute blend alpha
        elapsed = time.time() - self._blend_start_time
        alpha = min(1.0, elapsed / self._blend_duration)

        if alpha < 1.0 and self._follower_start_pos:
            blended = {}
            for key, target in leader_action.items():
                if key in self._follower_start_pos:
                    start = self._follower_start_pos[key]
                    blended[key] = start + alpha * (target - start)
                else:
                    blended[key] = target
            return blended

        # Blend complete — clear blend state
        if alpha >= 1.0 and self._blend_start_time:
            self._blend_start_time = None
            logger.info("Startup blend complete")

        return leader_action

    # ── Send Action ────────────────────────────────────────────────

    def _send_action(self, action: dict[str, float]) -> None:
        """Send mapped action to the follower robot.

        Args:
            action: Follower action dict {joint_key: value}.
        """
        try:
            self.robot.send_action(action)
        except Exception as e:
            if self.loop_count % 60 == 0:
                logger.error("Send action failed: %s", e)

    # ── Safety ─────────────────────────────────────────────────────

    def _check_safety(self) -> bool:
        """Run safety checks. Returns False if loop should stop.

        Checks:
        - CAN bus death (every frame)
        - Damiao torque limits (every 6th frame ≈ 10Hz)
        """
        # CAN bus death detection
        if hasattr(self.robot, "bus") and getattr(self.robot.bus, "_can_bus_dead", False):
            logger.error("CAN bus failure detected — emergency stop")
            self.is_running = False
            return False

        # Damiao torque limits (every 6th frame to keep within frame budget)
        if self.joint_mapper.has_damiao_follower and self.loop_count % 6 == 3:
            try:
                if not self.safety.check_damiao_limits(self.robot):
                    logger.error("Damiao torque limit exceeded — emergency stop")
                    self.is_running = False
                    return False
            except Exception as e:
                if self.loop_count % 60 == 0:
                    logger.warning("Safety check error (non-fatal): %s", e)

        return True

    # ── Force Feedback ─────────────────────────────────────────────

    def _apply_force_feedback(self, obs: dict[str, float]) -> None:
        """Apply gripper and joint force feedback to the leader arm.

        Args:
            obs: Leader observation dict (for joint positions).
        """
        if not self.joint_mapper.has_damiao_follower:
            return
        if not self.leader or self.loop_count == 0:
            return

        # Gripper force feedback
        if self.gripper_ff:
            try:
                torques = self.robot.get_torques()
                raw_torque = torques.get("gripper", 0.0)
                goal_current = self.gripper_ff.update(raw_torque)

                self.leader.bus.write("Goal_Current", "gripper", goal_current, normalize=False)

                if self.loop_count % 60 == 0:
                    logger.debug(
                        "Gripper FF: torque=%.2fNm filtered=%.2fNm current=%dmA",
                        raw_torque,
                        self.gripper_ff.filtered_torque,
                        goal_current,
                    )
            except Exception as e:
                if self.loop_count % 60 == 0:
                    logger.warning("Gripper force feedback error: %s", e)

        # Joint force feedback (virtual spring)
        if self.joint_ff and self.joint_ff_enabled:
            try:
                cached = self.robot.get_cached_positions()
                follower_pos = cached.get("link3")
                leader_pos = obs.get("joint_4.pos")

                if follower_pos is not None and leader_pos is not None:
                    # Get homing offset for ticks conversion
                    j4_id = self.leader.bus.motors["joint_4"].id
                    homing_offset = self.leader.bus._software_homing_offsets.get(j4_id, 0)

                    raw_ticks, goal_current = self.joint_ff.compute_spring(
                        leader_pos, follower_pos, homing_offset
                    )

                    self.leader.bus.write(
                        "Goal_Position", "joint_4", int(raw_ticks), normalize=False
                    )
                    self.leader.bus.write("Goal_Current", "joint_4", goal_current, normalize=False)

                    if self.loop_count % 60 == 0:
                        logger.debug(
                            "Joint FF: leader=%.3f follower=%.3f error=%.3frad current=%dmA",
                            leader_pos,
                            follower_pos,
                            abs(leader_pos - follower_pos),
                            goal_current,
                        )
            except Exception as e:
                if self.loop_count % 60 == 0:
                    logger.warning("Joint force feedback error: %s", e)

    # ── Leader Assist ──────────────────────────────────────────────

    def _apply_leader_assist(self, obs: dict[str, float]) -> None:
        """Apply gravity compensation and friction assist to leader arm.

        Iterates over pre-computed assist groups, estimates velocity via
        EMA filtering, and writes PWM values to the leader bus.

        Args:
            obs: Leader observation dict.
        """
        for arm_key, joint_names in self.assist_groups.items():
            service = self.leader_assists.get(arm_key)
            if not service:
                continue

            positions: list[float] = []
            velocities: list[float] = []
            valid = True

            for fullname in joint_names:
                pos_key = f"{fullname}.pos"
                if pos_key not in obs:
                    valid = False
                    break

                deg = obs[pos_key]
                positions.append(deg)

                # EMA velocity estimate
                raw_vel = 0.0
                if fullname in self._last_leader_pos:
                    delta = deg - self._last_leader_pos[fullname]
                    raw_vel = delta / self.dt

                prev_vel = self._leader_vel_filtered.get(fullname, 0.0)
                filtered_vel = self._alpha_vel * raw_vel + (1 - self._alpha_vel) * prev_vel
                self._leader_vel_filtered[fullname] = filtered_vel
                velocities.append(filtered_vel)
                self._last_leader_pos[fullname] = deg

            if not valid:
                continue

            try:
                # Compute haptic forces from follower loads
                haptic_forces: dict[str, float] = {}
                # (Haptics require follower gravity models — skipped in v2 MVP)

                pwm_dict = service.compute_assist_torque(
                    joint_names,
                    positions,
                    velocities,
                    follower_torques=haptic_forces,
                )

                if pwm_dict:
                    self._write_leader_pwm(arm_key, pwm_dict)

            except Exception as e:
                logger.error("Leader assist error (%s): %s", arm_key, e)

    def _write_leader_pwm(self, arm_key: str, pwm_dict: dict[str, int]) -> None:
        """Write PWM values to the leader arm bus.

        Handles bi-manual (left/right) and single-arm leaders by stripping
        the arm prefix before writing.

        Args:
            arm_key: Arm identifier ("left", "right", or "default").
            pwm_dict: Joint name -> PWM value mapping.
        """
        if arm_key == "left" and hasattr(self.leader, "left_arm"):
            local_pwm = {k.replace("left_", ""): v for k, v in pwm_dict.items()}
            self.leader.left_arm.bus.write_pwm(local_pwm)
        elif arm_key == "right" and hasattr(self.leader, "right_arm"):
            local_pwm = {k.replace("right_", ""): v for k, v in pwm_dict.items()}
            self.leader.right_arm.bus.write_pwm(local_pwm)
        else:
            self.leader.bus.write_pwm(pwm_dict)

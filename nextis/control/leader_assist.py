"""Leader arm gravity compensation, friction assist, and haptic feedback.

Implements a linear regression-based gravity model with four additive
control terms: gravity compensation, friction assistance, haptic
reflection, and viscous damping. Calibration data stored as JSON.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Default calibration directory (relative to project root)
_DEFAULT_CALIBRATION_DIR = Path("configs/calibration")


class LeaderAssistService:
    """Leader arm transparency and assistance controller.

    Computes per-joint PWM values that combine:
    - Gravity compensation from a calibrated linear model
    - Friction assistance (negative damping via tanh)
    - Haptic feedback from follower external forces
    - Viscous damping for stability

    Args:
        arm_id: Identifier for this arm (used in calibration filename).
        calibration_path: Explicit path to gravity calibration JSON.
            If None, uses configs/calibration/gravity_{arm_id}.json.
    """

    def __init__(
        self,
        arm_id: str = "default",
        calibration_path: Path | str | None = None,
    ) -> None:
        self.arm_id = arm_id

        calibration_dir = _DEFAULT_CALIBRATION_DIR
        calibration_dir.mkdir(parents=True, exist_ok=True)

        if calibration_path is None:
            self.calibration_path = calibration_dir / f"gravity_{arm_id}.json"
        else:
            self.calibration_path = Path(calibration_path)

        self.gravity_weights: dict[str, list[float]] = {}
        self.is_calibrated: bool = False
        self.load_calibration()

        # Tunable gains
        self.k_assist: float = 0.5  # Friction assistance
        self.v_threshold: float = 2.0  # Velocity scaling for tanh
        self.vel_deadband: float = 1.0  # Ignore velocity noise below this
        self.k_haptic: float = 0.0  # Haptic reflection (disabled by default)
        self.k_gravity: float = 1.0  # Gravity model scaling
        self.k_damping: float = 0.5  # Viscous damping
        self.max_pwm: int = 400  # Safety cap (40% of 1000)

        # Calibration state
        self.calibration_mode: bool = False
        self.calibration_data: list[tuple[list[float], list[float]]] = []

    def update_gains(
        self,
        k_gravity: float | None = None,
        k_assist: float | None = None,
        k_haptic: float | None = None,
        v_threshold: float | None = None,
        k_damping: float | None = None,
    ) -> None:
        """Update control gains at runtime.

        Args:
            k_gravity: Gravity compensation scaling.
            k_assist: Friction assistance gain.
            k_haptic: Haptic reflection gain.
            v_threshold: Velocity threshold for tanh scaling.
            k_damping: Viscous damping gain.
        """
        if k_gravity is not None:
            self.k_gravity = float(k_gravity)
        if k_assist is not None:
            self.k_assist = float(k_assist)
        if k_haptic is not None:
            self.k_haptic = float(k_haptic)
        if v_threshold is not None:
            self.v_threshold = float(v_threshold)
        if k_damping is not None:
            self.k_damping = float(k_damping)
        logger.info(
            "Updated gains: G=%.2f, F=%.2f, H=%.2f, D=%.2f",
            self.k_gravity,
            self.k_assist,
            self.k_haptic,
            self.k_damping,
        )

    def load_calibration(self) -> None:
        """Load gravity calibration weights from JSON file."""
        if self.calibration_path.exists():
            try:
                with open(self.calibration_path) as f:
                    self.gravity_weights = json.load(f)
                self.is_calibrated = True
                logger.info("Loaded gravity calibration from %s", self.calibration_path)
            except Exception as e:
                logger.error("Failed to load calibration: %s", e)
        else:
            logger.warning("No gravity calibration found for %s", self.arm_id)

    def save_calibration(self) -> None:
        """Save gravity calibration weights to JSON file."""
        try:
            self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.calibration_path, "w") as f:
                json.dump(self.gravity_weights, f)
            self.is_calibrated = True
            logger.info("Saved gravity calibration to %s", self.calibration_path)
        except Exception as e:
            logger.error("Failed to save calibration: %s", e)

    def _compute_features(self, q_deg: list[float]) -> np.ndarray:
        """Compute regression features from joint positions.

        Independent joint approximation: [1, sin(q), cos(q)] per joint.

        Args:
            q_deg: Joint angles in degrees.

        Returns:
            Feature vector (1 + 2*n_joints,).
        """
        q = [math.radians(x) for x in q_deg]
        feats = [1.0]  # Bias term
        for val in q:
            feats.append(math.sin(val))
            feats.append(math.cos(val))
        return np.array(feats)

    # --- Calibration Routine ---

    def start_calibration(self) -> None:
        """Enter calibration mode and clear samples."""
        logger.info("Starting gravity calibration for %s", self.arm_id)
        self.calibration_mode = True
        self.calibration_data = []

    def record_sample(self, positions_deg: list[float], loads_raw: list[float]) -> None:
        """Record a calibration sample (position + measured load).

        Args:
            positions_deg: Joint angles in degrees.
            loads_raw: Current loads (PWM to hold position against gravity).
        """
        if not self.calibration_mode:
            return
        self.calibration_data.append((positions_deg, loads_raw))
        logger.info("Recorded calibration sample %d", len(self.calibration_data))

    def compute_weights(self) -> None:
        """Fit per-joint linear regression: W * features = load.

        Uses ridge regression (lambda=1e-3) for numerical stability.
        """
        if not self.calibration_data:
            logger.error("No calibration data to fit")
            return

        logger.info("Computing gravity weights from %d samples", len(self.calibration_data))

        num_joints = len(self.calibration_data[0][1])
        X: list[np.ndarray] = []
        Y: list[list[float]] = [[] for _ in range(num_joints)]

        for q, load in self.calibration_data:
            feat = self._compute_features(q)
            X.append(feat)
            for i in range(num_joints):
                Y[i].append(load[i])

        X_mat = np.array(X)
        self.gravity_weights = {}

        try:
            lambda_reg = 1e-3
            for i in range(num_joints):
                y_vec = np.array(Y[i])
                # Ridge regression: W = (X^T X + lambda*I)^-1 X^T y
                w = (
                    np.linalg.inv(X_mat.T @ X_mat + lambda_reg * np.eye(X_mat.shape[1]))
                    @ X_mat.T
                    @ y_vec
                )
                self.gravity_weights[f"joint_{i}"] = w.tolist()

            self.save_calibration()
            self.calibration_mode = False
            logger.info("Gravity calibration complete")
        except Exception as e:
            logger.error("Calibration failed: %s", e)

    # --- Runtime Control ---

    def predict_gravity(self, positions_deg: list[float]) -> list[float]:
        """Predict gravity torque (PWM) for given joint positions.

        Args:
            positions_deg: Joint angles in degrees.

        Returns:
            Per-joint gravity compensation PWM values.
        """
        features = self._compute_features(positions_deg)
        gravity_pwm: list[float] = []

        for i in range(len(positions_deg)):
            w_key = f"joint_{i}"
            val = 0.0
            if self.is_calibrated and w_key in self.gravity_weights:
                w = np.array(self.gravity_weights[w_key])
                val = float(np.dot(w, features))
            gravity_pwm.append(val)

        return gravity_pwm

    def compute_assist_torque(
        self,
        joint_names: list[str],
        positions_deg: list[float],
        velocities_deg: list[float],
        follower_torques: dict[str, float] | list[float] | None = None,
    ) -> dict[str, int]:
        """Compute total assist torque (PWM) for each joint.

        Combines gravity compensation + friction assist + haptic feedback
        + viscous damping. Output clamped to +/-max_pwm.

        Args:
            joint_names: Joint name for each index.
            positions_deg: Current joint angles in degrees.
            velocities_deg: Current joint velocities in deg/s.
            follower_torques: External forces from follower arm (for haptics).

        Returns:
            Dict mapping joint_name -> integer PWM value.
        """
        pwm_values: dict[str, int] = {}
        features = self._compute_features(positions_deg)

        for i, name in enumerate(joint_names):
            total_pwm = 0.0

            # 1. Gravity compensation
            w_key = f"joint_{i}"
            if self.is_calibrated and w_key in self.gravity_weights:
                w = np.array(self.gravity_weights[w_key])
                total_pwm += float(np.dot(w, features)) * self.k_gravity

            # 2. Friction assistance (negative damping)
            vel = velocities_deg[i]
            if abs(vel) > self.vel_deadband and self.k_assist > 0:
                total_pwm += self.k_assist * math.tanh(vel / self.v_threshold) * 100.0

            # 3. Haptic feedback (inverted — resist external force)
            if follower_torques:
                f_load = 0.0
                if isinstance(follower_torques, dict):
                    if name in follower_torques:
                        f_load = follower_torques[name]
                elif i < len(follower_torques):
                    f_load = follower_torques[i]
                total_pwm -= f_load * self.k_haptic

            # 4. Viscous damping
            total_pwm -= vel * self.k_damping

            # Clamp to safety limit
            total_pwm = max(-self.max_pwm, min(self.max_pwm, total_pwm))
            pwm_values[name] = int(total_pwm)

        return pwm_values

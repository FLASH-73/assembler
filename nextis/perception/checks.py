"""Step verification checkers — four pure functions for assembly step validation.

Each checker takes an AssemblyStep and ExecutionData, and returns a
VerificationResult indicating whether the step met its success criteria.

Checkers:
    check_position — Euclidean distance to target pose.
    check_force_threshold — Peak force exceeds threshold.
    check_force_signature — Pattern matching on force time-series.
    check_classifier — PyTorch image classifier inference.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from nextis.assembly.models import AssemblyStep
from nextis.perception.types import ExecutionData, VerificationResult

logger = logging.getLogger(__name__)

# Default position tolerance in mm.
_DEFAULT_POSITION_TOLERANCE_MM = 2.0


# ------------------------------------------------------------------
# 1. Position check
# ------------------------------------------------------------------


def check_position(step: AssemblyStep, data: ExecutionData) -> VerificationResult:
    """Check if final position is within tolerance of the target pose.

    Target is extracted from ``step.primitive_params["target_pose"]`` (first 3
    elements = xyz). Tolerance comes from ``step.success_criteria.threshold``
    or defaults to 2.0 mm.

    Args:
        step: Assembly step with primitive_params containing target_pose.
        data: Execution telemetry with final_position.

    Returns:
        VerificationResult with distance as measured_value.
    """
    params = step.primitive_params or {}
    target_pose = params.get("target_pose")
    if target_pose is None or len(target_pose) < 3:
        return VerificationResult(
            passed=True,
            confidence=0.3,
            detail="No target_pose in primitive_params — skipping position check",
        )

    if len(data.final_position) < 3:
        return VerificationResult(
            passed=False,
            confidence=0.8,
            detail="No final position data available for verification",
        )

    target_xyz = np.array(target_pose[:3], dtype=np.float64)
    actual_xyz = np.array(data.final_position[:3], dtype=np.float64)
    distance = float(np.linalg.norm(target_xyz - actual_xyz))

    tolerance = step.success_criteria.threshold or _DEFAULT_POSITION_TOLERANCE_MM

    passed = distance <= tolerance
    return VerificationResult(
        passed=passed,
        confidence=0.9 if passed else 0.85,
        detail=f"Position error: {distance:.2f}mm (tolerance: {tolerance:.2f}mm)",
        measured_value=distance,
        threshold=tolerance,
    )


# ------------------------------------------------------------------
# 2. Force threshold check
# ------------------------------------------------------------------


def check_force_threshold(step: AssemblyStep, data: ExecutionData) -> VerificationResult:
    """Check if peak force exceeded the required threshold.

    Args:
        step: Assembly step with success_criteria.threshold (N).
        data: Execution telemetry with peak_force.

    Returns:
        VerificationResult with peak_force as measured_value.
    """
    threshold = step.success_criteria.threshold
    if threshold is None:
        return VerificationResult(
            passed=True,
            confidence=0.3,
            detail="No force threshold defined — skipping",
        )

    passed = data.peak_force >= threshold
    return VerificationResult(
        passed=passed,
        confidence=0.95 if passed else 0.9,
        detail=f"Peak force: {data.peak_force:.2f}N (threshold: {threshold:.2f}N)",
        measured_value=data.peak_force,
        threshold=threshold,
    )


# ------------------------------------------------------------------
# 3. Force signature check
# ------------------------------------------------------------------


def _detect_snap_fit(force: np.ndarray, threshold: float | None) -> VerificationResult:
    """Snap-fit: peak followed by sharp drop (>50%) within 5 samples, then hold."""
    if len(force) < 10:
        return VerificationResult(
            passed=False, confidence=0.4, detail="Force history too short for snap-fit detection"
        )

    peak_idx = int(np.argmax(force))
    peak_val = float(force[peak_idx])

    if peak_val < 0.1:
        return VerificationResult(
            passed=False, confidence=0.7, detail=f"Peak force too low for snap-fit: {peak_val:.2f}N"
        )

    # Look for >50% drop within next 5 samples after peak
    window_end = min(peak_idx + 6, len(force))
    post_peak = force[peak_idx + 1 : window_end]
    if len(post_peak) == 0:
        return VerificationResult(
            passed=False, confidence=0.5, detail="Peak at end of force history — no drop detected"
        )

    min_after_peak = float(np.min(post_peak))
    drop_ratio = (peak_val - min_after_peak) / peak_val if peak_val > 0 else 0

    passed = drop_ratio > 0.5
    return VerificationResult(
        passed=passed,
        confidence=0.85 if passed else 0.7,
        detail=f"Snap-fit: peak={peak_val:.2f}N, drop={drop_ratio:.0%}",
        measured_value=peak_val,
        threshold=threshold,
    )


def _detect_meshing(force: np.ndarray, threshold: float | None) -> VerificationResult:
    """Meshing (gears): detect oscillations with >=3 local peaks."""
    if len(force) < 10:
        return VerificationResult(
            passed=False, confidence=0.4, detail="Force history too short for meshing detection"
        )

    # Simple peak detection: a point higher than both neighbors
    peaks = []
    for i in range(1, len(force) - 1):
        if force[i] > force[i - 1] and force[i] > force[i + 1]:
            peaks.append(i)

    # Filter out noise — peaks must be above 10% of max
    max_force = float(np.max(force))
    noise_floor = max_force * 0.1
    significant_peaks = [p for p in peaks if force[p] > noise_floor]

    passed = len(significant_peaks) >= 3
    return VerificationResult(
        passed=passed,
        confidence=0.8 if passed else 0.6,
        detail=f"Meshing: {len(significant_peaks)} oscillation peaks detected (need >=3)",
        measured_value=float(len(significant_peaks)),
        threshold=3.0,
    )


def _detect_press_fit(force: np.ndarray, threshold: float | None) -> VerificationResult:
    """Press-fit: monotonic-ish rise to target force."""
    if len(force) < 5:
        return VerificationResult(
            passed=False, confidence=0.4, detail="Force history too short for press-fit detection"
        )

    # Check monotonicity: allow small dips (gradient mostly positive)
    gradient = np.diff(force)
    positive_ratio = float(np.sum(gradient >= -0.1) / len(gradient))

    final_force = float(force[-1])
    target = threshold or 0.0

    monotonic = positive_ratio >= 0.7
    reached_target = final_force >= target if target > 0 else True

    passed = monotonic and reached_target
    return VerificationResult(
        passed=passed,
        confidence=0.85 if passed else 0.65,
        detail=(
            f"Press-fit: final={final_force:.2f}N, "
            f"monotonicity={positive_ratio:.0%}, target={target:.2f}N"
        ),
        measured_value=final_force,
        threshold=target,
    )


def check_force_signature(step: AssemblyStep, data: ExecutionData) -> VerificationResult:
    """Pattern-match on force history for snap-fit, meshing, or press-fit.

    Dispatches on ``step.success_criteria.pattern``.

    Args:
        step: Assembly step with success_criteria.pattern and optional threshold.
        data: Execution telemetry with force_history.

    Returns:
        VerificationResult from the appropriate sub-detector.
    """
    pattern = step.success_criteria.pattern
    if not pattern:
        return VerificationResult(
            passed=True,
            confidence=0.3,
            detail="No force signature pattern defined — skipping",
        )

    if not data.force_history:
        return VerificationResult(
            passed=False, confidence=0.6, detail="No force history data for signature analysis"
        )

    force = np.array(data.force_history, dtype=np.float64)
    threshold = step.success_criteria.threshold

    detectors = {
        "snap_fit": _detect_snap_fit,
        "meshing": _detect_meshing,
        "press_fit": _detect_press_fit,
    }

    detector = detectors.get(pattern)
    if detector is None:
        return VerificationResult(
            passed=True,
            confidence=0.3,
            detail=f"Unknown force signature pattern: {pattern}",
        )

    return detector(force, threshold)


# ------------------------------------------------------------------
# 4. Classifier check
# ------------------------------------------------------------------


def check_classifier(step: AssemblyStep, data: ExecutionData) -> VerificationResult:
    """Run a trained image classifier to verify step completion.

    Looks for a PyTorch model at
    ``data/classifiers/{assembly_id}/{step_id}/model.pt`` where assembly_id
    is extracted from the step ID prefix (convention: ``{assembly}_step_NNN``).

    Args:
        step: Assembly step with success_criteria.model pointing to classifier.
        data: Execution telemetry with camera_frame.

    Returns:
        VerificationResult from classifier inference, or pass-with-low-confidence
        if no model or camera frame is available.
    """
    # Determine model path from success_criteria.model or convention
    model_path_str = step.success_criteria.model
    if model_path_str:
        model_path = Path(model_path_str)
    else:
        # No explicit model path — skip
        return VerificationResult(
            passed=True,
            confidence=0.5,
            detail="No classifier model path defined — skipping",
        )

    if not model_path.exists():
        return VerificationResult(
            passed=True,
            confidence=0.5,
            detail=f"Classifier not found at {model_path} — skipping",
        )

    if data.camera_frame is None:
        return VerificationResult(
            passed=False,
            confidence=0.4,
            detail="No camera frame available for classifier verification",
        )

    try:
        import torch
    except ImportError:
        logger.warning("torch not available — skipping classifier verification")
        return VerificationResult(
            passed=True, confidence=0.3, detail="PyTorch not available — skipping classifier"
        )

    try:
        model = torch.load(str(model_path), map_location="cpu", weights_only=False)
        model.eval()

        # Resize to 224x224 and normalize
        frame = data.camera_frame
        if frame.shape[:2] != (224, 224):
            # Simple resize via nearest-neighbor (no PIL dependency)
            h, w = frame.shape[:2]
            y_indices = (np.arange(224) * h / 224).astype(int)
            x_indices = (np.arange(224) * w / 224).astype(int)
            frame = frame[np.ix_(y_indices, x_indices)]

        # HWC uint8 → CHW float32 normalized to [0, 1]
        tensor = torch.tensor(frame, dtype=torch.float32).permute(2, 0, 1) / 255.0
        tensor = tensor.unsqueeze(0)  # Add batch dim

        with torch.no_grad():
            output = model(tensor)

        # Binary classifier: sigmoid output, threshold at 0.5
        if output.shape[-1] == 1:
            prob = float(torch.sigmoid(output[0, 0]))
        else:
            prob = float(torch.softmax(output[0], dim=0)[1])

        passed = prob >= 0.5
        return VerificationResult(
            passed=passed,
            confidence=prob if passed else 1.0 - prob,
            detail=f"Classifier confidence: {prob:.2%}",
            measured_value=prob,
            threshold=0.5,
        )

    except Exception as e:
        logger.error("Classifier inference failed: %s", e, exc_info=True)
        return VerificationResult(
            passed=True,
            confidence=0.3,
            detail=f"Classifier error: {e}",
        )

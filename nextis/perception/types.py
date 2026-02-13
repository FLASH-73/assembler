"""Perception layer type definitions.

Shared types for step verification checkers and the StepVerifier dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ExecutionData:
    """Telemetry snapshot captured after step dispatch.

    Attributes:
        final_position: End-effector position at step completion (xyz + optional orientation).
        force_history: Time-series of force magnitudes during execution (N).
        peak_force: Maximum force observed during execution (N).
        final_force: Force at step completion (N).
        camera_frame: RGB image from workspace camera (H, W, 3) uint8, or None.
        duration_ms: Step execution time in milliseconds.
    """

    final_position: list[float] = field(default_factory=list)
    force_history: list[float] = field(default_factory=list)
    peak_force: float = 0.0
    final_force: float = 0.0
    camera_frame: np.ndarray | None = None
    duration_ms: float = 0.0


@dataclass
class VerificationResult:
    """Output from a verification checker.

    Attributes:
        passed: Whether the step met its success criteria.
        confidence: Confidence in the result (0.0–1.0).
        detail: Human-readable description of the check outcome.
        measured_value: The measured metric (distance, force, etc.), if applicable.
        threshold: The threshold compared against, if applicable.
    """

    passed: bool
    confidence: float
    detail: str
    measured_value: float | None = None
    threshold: float | None = None

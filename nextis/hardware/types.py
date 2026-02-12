"""Hardware type definitions.

Data models for arm configuration, motor types, and arm pairings.
These are pure data -- no hardware communication logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MotorType(str, Enum):  # noqa: UP042
    """Supported motor types with their connection protocols."""

    STS3215 = "sts3215"  # Feetech STS3215 — UART TTL
    DAMIAO = "damiao"  # Damiao J-series — CAN-to-serial
    DYNAMIXEL_XL330 = "dynamixel_xl330"  # Dynamixel XL330 — Waveshare USB
    DYNAMIXEL_XL430 = "dynamixel_xl430"  # Dynamixel XL430


class ArmRole(str, Enum):  # noqa: UP042
    """Role of an arm in the system."""

    LEADER = "leader"
    FOLLOWER = "follower"


class ConnectionStatus(str, Enum):  # noqa: UP042
    """Connection state of an arm."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ArmDefinition:
    """Configuration for a single robotic arm.

    Attributes:
        id: Unique arm identifier (e.g., "left_follower").
        name: Human-readable name.
        role: Whether this arm is a leader (human-operated) or follower.
        motor_type: Type of motors in this arm.
        port: Serial port or CAN interface (e.g., "/dev/ttyUSB0", "can0").
        enabled: Whether this arm is active in the system.
        structural_design: Mechanical design variant (e.g., "damiao_7dof", "umbra_7dof").
        config: Motor-type-specific configuration (velocity_limit, etc.).
        calibrated: Whether calibration has been performed.
    """

    id: str
    name: str
    role: ArmRole
    motor_type: MotorType
    port: str
    enabled: bool = True
    structural_design: str | None = None
    config: dict = field(default_factory=dict)
    calibrated: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "motor_type": self.motor_type.value,
            "port": self.port,
            "enabled": self.enabled,
            "structural_design": self.structural_design,
            "config": self.config,
            "calibrated": self.calibrated,
        }


@dataclass
class Pairing:
    """A leader-follower arm pairing for teleoperation.

    Attributes:
        leader_id: ArmDefinition ID for the leader arm.
        follower_id: ArmDefinition ID for the follower arm.
        name: Human-readable pairing name.
    """

    leader_id: str
    follower_id: str
    name: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "leader_id": self.leader_id,
            "follower_id": self.follower_id,
            "name": self.name,
        }

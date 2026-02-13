"""Integration tests for the full training pipeline.

Verifies the end-to-end data path: synthetic HDF5 creation -> dataset build ->
ACT training -> checkpoint save -> policy load -> inference -> policy router
dispatch.  All without GPU or real hardware.
"""

from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np
import pytest
import torch

from nextis.assembly.models import AssemblyStep
from nextis.execution.policy_router import PolicyRouter
from nextis.learning.dataset import DatasetInfo, StepDataset
from nextis.learning.policy_loader import PolicyLoader
from nextis.learning.trainer import MinimalACT, PolicyTrainer, TrainingConfig, TrainingProgress

logger = logging.getLogger(__name__)

ASSEMBLY_ID = "test_pipe"
STEP_ID = "step_001"
NUM_FRAMES = 100
JOINT_KEYS = sorted(["base", "gripper", "link1", "link2", "link3", "link4", "link5"])
NUM_JOINTS = len(JOINT_KEYS)


# ---------------------------------------------------------------------------
# Fixture: synthetic HDF5 demos matching DemoRecorder output schema
# ---------------------------------------------------------------------------


@pytest.fixture()
def demo_dir(tmp_path: Path) -> Path:
    """Create 2 synthetic HDF5 demos matching DemoRecorder output schema."""
    demo_path = tmp_path / "demos" / ASSEMBLY_ID / STEP_ID
    demo_path.mkdir(parents=True)

    for demo_idx in range(2):
        fname = demo_path / f"demo_{demo_idx:03d}.hdf5"
        with h5py.File(str(fname), "w") as f:
            # File-level attributes
            f.attrs["assembly_id"] = ASSEMBLY_ID
            f.attrs["step_id"] = STEP_ID
            f.attrs["demo_id"] = f"demo_{demo_idx:03d}"
            f.attrs["num_frames"] = NUM_FRAMES
            f.attrs["recording_hz"] = 50
            f.attrs["timestamp"] = 1700000000.0 + demo_idx

            f.create_dataset("timestamps", data=np.linspace(0, 2.0, NUM_FRAMES))

            # Observation group
            obs_grp = f.create_group("observation")
            t = np.linspace(0, 2 * np.pi, NUM_FRAMES)
            jp = np.column_stack([np.sin(t + i * 0.5) * 0.3 for i in range(NUM_JOINTS)]).astype(
                np.float32
            )
            obs_grp.create_dataset("joint_positions", data=jp)
            obs_grp.attrs["joint_keys"] = JOINT_KEYS

            obs_grp.create_dataset(
                "gripper_state",
                data=np.zeros(NUM_FRAMES, dtype=np.float32),
            )
            obs_grp.create_dataset(
                "force_torque",
                data=np.zeros((NUM_FRAMES, NUM_JOINTS), dtype=np.float32),
            )

            # Action group
            act_grp = f.create_group("action")
            ap = np.column_stack(
                [np.sin(t + i * 0.5 + 0.1) * 0.3 for i in range(NUM_JOINTS)]
            ).astype(np.float32)
            act_grp.create_dataset("joint_positions", data=ap)
            act_grp.attrs["joint_keys"] = JOINT_KEYS

    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_dataset(demo_dir: Path) -> DatasetInfo:
    """Build the dataset from the synthetic demos."""
    return StepDataset(ASSEMBLY_ID, STEP_ID, data_dir=str(demo_dir)).build()


async def _train_policy(demo_dir: Path, chunk_size: int = 4, num_epochs: int = 5) -> tuple:
    """Build dataset + train, returning (dataset_info, training_result, policies_dir)."""
    info = _build_dataset(demo_dir)
    policies_dir = demo_dir / "policies"
    trainer = PolicyTrainer(policies_dir=str(policies_dir))
    config = TrainingConfig(
        num_epochs=num_epochs, batch_size=16, chunk_size=chunk_size, hidden_dim=32
    )
    result = await trainer.train(info, config=config)
    return info, result, policies_dir


# ---------------------------------------------------------------------------
# Test 1: Synthetic HDF5 schema validation
# ---------------------------------------------------------------------------


def test_demo_hdf5_schema(demo_dir: Path) -> None:
    """Synthetic HDF5 files match DemoRecorder output schema."""
    demo_files = sorted((demo_dir / "demos" / ASSEMBLY_ID / STEP_ID).glob("*.hdf5"))
    assert len(demo_files) == 2

    with h5py.File(str(demo_files[0]), "r") as f:
        assert f.attrs["assembly_id"] == ASSEMBLY_ID
        assert f.attrs["step_id"] == STEP_ID
        assert f.attrs["num_frames"] == NUM_FRAMES
        assert f.attrs["recording_hz"] == 50

        assert f["observation/joint_positions"].shape == (NUM_FRAMES, NUM_JOINTS)
        assert f["observation/gripper_state"].shape == (NUM_FRAMES,)
        assert f["observation/force_torque"].shape == (NUM_FRAMES, NUM_JOINTS)
        assert f["action/joint_positions"].shape == (NUM_FRAMES, NUM_JOINTS)

        obs_keys = list(f["observation"].attrs["joint_keys"])
        assert len(obs_keys) == NUM_JOINTS
        assert obs_keys == JOINT_KEYS

        act_keys = list(f["action"].attrs["joint_keys"])
        assert act_keys == JOINT_KEYS


# ---------------------------------------------------------------------------
# Test 2: Dataset build
# ---------------------------------------------------------------------------


def test_dataset_build(demo_dir: Path) -> None:
    """StepDataset.build() merges HDF5 demos and reads joint_keys."""
    info = _build_dataset(demo_dir)

    assert info.assembly_id == ASSEMBLY_ID
    assert info.step_id == STEP_ID
    assert info.obs_dim == NUM_JOINTS
    assert info.action_dim == NUM_JOINTS
    total_frames = NUM_FRAMES * 2  # 2 demos
    assert info.train_frames + info.val_frames == total_frames
    assert info.train_frames == int(total_frames * 0.8)
    assert info.val_frames == total_frames - info.train_frames

    assert len(info.joint_keys) == NUM_JOINTS
    assert info.joint_keys == JOINT_KEYS

    # Verify numpy files exist and have correct shapes
    assert (info.output_dir / "train_obs.npy").exists()
    assert (info.output_dir / "train_act.npy").exists()
    assert (info.output_dir / "val_obs.npy").exists()
    assert (info.output_dir / "val_act.npy").exists()

    train_obs = np.load(info.output_dir / "train_obs.npy")
    train_act = np.load(info.output_dir / "train_act.npy")
    assert train_obs.shape == (info.train_frames, NUM_JOINTS)
    assert train_act.shape == (info.train_frames, NUM_JOINTS)


# ---------------------------------------------------------------------------
# Test 3: Training produces checkpoint with decreasing loss
# ---------------------------------------------------------------------------


async def test_training_loss_decreases(demo_dir: Path) -> None:
    """Training for 5 epochs produces a checkpoint with decreasing loss."""
    info = _build_dataset(demo_dir)
    policies_dir = demo_dir / "policies"
    trainer = PolicyTrainer(policies_dir=str(policies_dir))
    config = TrainingConfig(num_epochs=5, batch_size=16, chunk_size=4, hidden_dim=32)

    losses: list[float] = []

    def on_progress(p: TrainingProgress) -> None:
        losses.append(p.loss)

    result = await trainer.train(info, config=config, on_progress=on_progress)

    assert result.checkpoint_path.exists()
    assert result.epochs_trained == 5
    assert result.final_loss > 0
    assert len(losses) == 5
    # Loss should decrease over 5 epochs (at least last < first)
    assert losses[-1] < losses[0], f"Loss did not decrease: {losses}"


# ---------------------------------------------------------------------------
# Test 4: PolicyLoader.load() and PolicyLoader.exists()
# ---------------------------------------------------------------------------


async def test_policy_load_and_exists(demo_dir: Path) -> None:
    """PolicyLoader loads a trained checkpoint and exists() works."""
    _, _, policies_dir = await _train_policy(demo_dir, chunk_size=4, num_epochs=3)
    loader = PolicyLoader(policies_dir=policies_dir)

    # exists() should return True for trained step, False for non-existent
    assert loader.exists(ASSEMBLY_ID, STEP_ID)
    assert not loader.exists(ASSEMBLY_ID, "step_999")

    policy = loader.load(ASSEMBLY_ID, STEP_ID)
    assert policy is not None
    assert policy.obs_dim == NUM_JOINTS
    assert policy.action_dim == NUM_JOINTS
    assert policy.chunk_size == 4
    assert len(policy.joint_keys) == NUM_JOINTS
    assert policy.joint_keys == JOINT_KEYS


# ---------------------------------------------------------------------------
# Test 5: Policy.predict() returns correct shape with finite values
# ---------------------------------------------------------------------------


async def test_policy_predict_shape(demo_dir: Path) -> None:
    """Policy.predict() returns (chunk_size, action_dim) finite array."""
    _, _, policies_dir = await _train_policy(demo_dir, chunk_size=4, num_epochs=3)
    loader = PolicyLoader(policies_dir=policies_dir)
    policy = loader.load(ASSEMBLY_ID, STEP_ID)
    assert policy is not None

    obs = {
        "base": 0.1,
        "gripper": 0.0,
        "link1": 0.2,
        "link2": 0.3,
        "link3": 0.4,
        "link4": 0.5,
        "link5": 0.6,
    }
    actions = policy.predict(obs)
    assert actions.shape == (4, NUM_JOINTS)
    assert np.all(np.isfinite(actions))


# ---------------------------------------------------------------------------
# Test 6: PolicyRouter end-to-end dispatch with tracking mock robot
# ---------------------------------------------------------------------------


class _TrackingRobot:
    """Mock robot that tracks get_observation/send_action calls."""

    def __init__(self, obs: dict[str, float]) -> None:
        self._obs = obs
        self.sent_actions: list[dict[str, float]] = []

    def get_observation(self) -> dict[str, float]:
        return dict(self._obs)

    def send_action(self, action: dict[str, float]) -> None:
        self.sent_actions.append(dict(action))


async def test_policy_router_dispatch(demo_dir: Path) -> None:
    """PolicyRouter dispatches a policy step end-to-end with a tracking mock."""
    _, _, policies_dir = await _train_policy(demo_dir, chunk_size=4, num_epochs=3)

    obs = {
        "base": 0.1,
        "gripper": 0.0,
        "link1": 0.2,
        "link2": 0.3,
        "link3": 0.4,
        "link4": 0.5,
        "link5": 0.6,
    }
    robot = _TrackingRobot(obs)
    loader = PolicyLoader(policies_dir=policies_dir)
    router = PolicyRouter(
        robot=robot,
        policy_loader=loader,
        assembly_id=ASSEMBLY_ID,
    )

    step = AssemblyStep(id=STEP_ID, name="Test policy step", handler="policy")
    result = await router.dispatch(step)

    assert result.success, f"Dispatch failed: {result.error_message}"
    assert result.handler_used == "policy"
    assert result.duration_ms > 0
    assert result.error_message is None

    # Robot should have received chunk_size action dicts
    assert len(robot.sent_actions) == 4
    for action_dict in robot.sent_actions:
        assert sorted(action_dict.keys()) == JOINT_KEYS
        assert all(np.isfinite(v) for v in action_dict.values())


# ---------------------------------------------------------------------------
# Test 7: Backward compatibility — old checkpoint without joint_keys
# ---------------------------------------------------------------------------


async def test_backward_compat_no_joint_keys(demo_dir: Path) -> None:
    """Policy.predict() falls back to sorted(obs.keys()) for old checkpoints."""
    # Create a checkpoint WITHOUT joint_keys (simulating old format)
    policies_dir = demo_dir / "policies"
    ckpt_dir = policies_dir / ASSEMBLY_ID / "step_old"
    ckpt_dir.mkdir(parents=True)

    model = MinimalACT(obs_dim=NUM_JOINTS, action_dim=NUM_JOINTS, chunk_size=4, hidden_dim=32)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": {
                "obs_dim": NUM_JOINTS,
                "action_dim": NUM_JOINTS,
                "chunk_size": 4,
                "hidden_dim": 32,
                "architecture": "act",
                # No joint_keys field
            },
        },
        str(ckpt_dir / "policy.pt"),
    )

    loader = PolicyLoader(policies_dir=policies_dir)
    policy = loader.load(ASSEMBLY_ID, "step_old")
    assert policy is not None
    assert policy.joint_keys == []  # No keys stored

    obs = {
        "base": 0.1,
        "gripper": 0.0,
        "link1": 0.2,
        "link2": 0.3,
        "link3": 0.4,
        "link4": 0.5,
        "link5": 0.6,
    }
    # Should still work via sorted(obs.keys()) fallback
    actions = policy.predict(obs)
    assert actions.shape == (4, NUM_JOINTS)
    assert np.all(np.isfinite(actions))

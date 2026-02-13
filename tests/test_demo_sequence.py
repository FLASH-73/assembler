"""Integration test: full AURA demo loop running in-process.

Exercises the complete pipeline without an HTTP server:
  load assembly -> execute (step_004 fails) -> record demo -> human completes
  -> train policy -> re-execute (step_004 succeeds via policy) -> complete.

All file I/O uses tmp_path for automatic cleanup.
"""

from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path

from nextis.analytics.store import AnalyticsStore
from nextis.api.schemas import ExecutionState
from nextis.assembly.models import AssemblyGraph
from nextis.control.primitives import PrimitiveLibrary
from nextis.execution.policy_router import PolicyRouter
from nextis.execution.sequencer import Sequencer, SequencerState
from nextis.hardware.mock import MOCK_JOINT_NAMES
from nextis.learning.dataset import StepDataset
from nextis.learning.policy_loader import PolicyLoader
from nextis.learning.recorder import DemoRecorder
from nextis.learning.trainer import PolicyTrainer, TrainingConfig

ASSEMBLY_ID = "bearing_housing_v1"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _sinusoidal_joints(offset: float = 0.0) -> dict[str, float]:
    """Return a 7-joint dict with sinusoidal values that vary over time."""
    t = time.monotonic()
    return {
        f"{name}.pos": math.sin(t * 0.5 + i * 0.7 + offset) * 0.3
        for i, name in enumerate(MOCK_JOINT_NAMES)
    }


async def _wait_for(event: asyncio.Event, timeout: float = 30.0) -> None:
    """Await an event with a timeout."""
    await asyncio.wait_for(event.wait(), timeout=timeout)


# ------------------------------------------------------------------
# Full demo loop
# ------------------------------------------------------------------


async def test_full_demo_loop(
    tmp_path: Path,
    bearing_housing_graph: AssemblyGraph,
) -> None:
    """Run the complete AURA demo loop in-process.

    Phases:
        a) Load bearing_housing_v1 fixture.
        b) First execution: primitives succeed, step_004 fails -> WAITING_FOR_HUMAN.
        c) Record mock demo for step_004.
        d) Complete human step -> step_005 -> COMPLETE.
        e) Train policy from recorded demo.
        f) Second execution: step_004 succeeds via trained policy.
    """
    graph = bearing_housing_graph
    analytics_dir = tmp_path / "analytics"
    analytics_dir.mkdir()

    # ------------------------------------------------------------------
    # b) First execution run
    # ------------------------------------------------------------------
    waiting_event = asyncio.Event()
    done_event = asyncio.Event()
    states_1: list[ExecutionState] = []

    def on_change_1(state: ExecutionState) -> None:
        states_1.append(state)
        if state.phase == "teaching":
            waiting_event.set()
        if state.phase in ("complete", "error"):
            done_event.set()

    primitives = PrimitiveLibrary()
    router_1 = PolicyRouter(primitive_library=primitives, robot=None)
    analytics = AnalyticsStore(root=analytics_dir)

    seq = Sequencer(
        graph=graph,
        on_state_change=on_change_1,
        router=router_1,
        analytics=analytics,
    )
    await seq.start()

    # Wait until step_004 exhausts retries and enters teaching phase
    await _wait_for(waiting_event, timeout=30.0)

    assert seq.state == SequencerState.WAITING_FOR_HUMAN

    # Steps 001-003 should have succeeded
    state = seq.get_execution_state()
    for sid in ["step_001", "step_002", "step_003"]:
        assert state.step_states[sid].status == "success", f"{sid} should succeed"

    # Step 004 should be waiting for human
    assert state.step_states["step_004"].status == "human"

    # ------------------------------------------------------------------
    # c) Record mock demo for step_004
    # ------------------------------------------------------------------
    demo_dir = tmp_path / "demos"
    recorder = DemoRecorder(
        assembly_id=ASSEMBLY_ID,
        step_id="step_004",
        data_dir=demo_dir,
    )

    recorder.start(
        robot_state_fn=lambda: _sinusoidal_joints(offset=0.0),
        action_fn=lambda: _sinusoidal_joints(offset=1.0),
    )

    # Let the recorder capture ~25 frames at 50Hz
    await asyncio.sleep(0.6)

    metadata = recorder.stop()
    assert metadata.num_frames >= 20, f"Expected >= 20 frames, got {metadata.num_frames}"
    assert metadata.file_path.exists()

    # ------------------------------------------------------------------
    # d) Complete human step -> step_005 -> COMPLETE
    # ------------------------------------------------------------------
    done_event.clear()
    await seq.complete_human_step(success=True)

    await _wait_for(done_event, timeout=15.0)

    assert seq.state == SequencerState.COMPLETE
    final_1 = seq.get_execution_state()
    assert final_1.step_states["step_005"].status == "success"

    # ------------------------------------------------------------------
    # e) Build dataset and train policy
    # ------------------------------------------------------------------
    dataset = StepDataset(
        assembly_id=ASSEMBLY_ID,
        step_id="step_004",
        data_dir=str(tmp_path),
    )
    info = dataset.build()
    assert info.obs_dim == 7
    assert info.action_dim == 7
    assert info.train_frames >= 16

    trainer = PolicyTrainer(policies_dir=str(tmp_path / "policies"))
    config = TrainingConfig(num_epochs=5, batch_size=8)
    result = await trainer.train(info, config=config)
    assert result.checkpoint_path.exists()
    assert result.epochs_trained == 5

    # ------------------------------------------------------------------
    # f) Second execution with trained policy
    # ------------------------------------------------------------------
    loader = PolicyLoader(policies_dir=tmp_path / "policies")

    # robot=None keeps primitives as stubs (skip force checks).
    # PolicyRouter._run_policy creates a MockRobot internally for inference.
    router_2 = PolicyRouter(
        primitive_library=PrimitiveLibrary(),
        robot=None,
        policy_loader=loader,
        assembly_id=ASSEMBLY_ID,
    )

    done_event_2 = asyncio.Event()
    states_2: list[ExecutionState] = []

    def on_change_2(state: ExecutionState) -> None:
        states_2.append(state)
        if state.phase in ("complete", "error"):
            done_event_2.set()

    seq2 = Sequencer(
        graph=graph,
        on_state_change=on_change_2,
        router=router_2,
        analytics=analytics,
    )
    await seq2.start()

    await _wait_for(done_event_2, timeout=30.0)

    assert seq2.state == SequencerState.COMPLETE

    final_2 = seq2.get_execution_state()
    for sid in graph.step_order:
        assert final_2.step_states[sid].status == "success", (
            f"Second run: {sid} should succeed, got {final_2.step_states[sid].status}"
        )


# ------------------------------------------------------------------
# Isolated sub-tests for recording and dataset
# ------------------------------------------------------------------


async def test_mock_recording_produces_valid_hdf5(tmp_path: Path) -> None:
    """Mock recording at 50Hz produces a non-degenerate HDF5 file."""
    import h5py

    recorder = DemoRecorder(
        assembly_id="test",
        step_id="step_001",
        data_dir=tmp_path / "demos",
    )
    recorder.start(
        robot_state_fn=lambda: _sinusoidal_joints(0.0),
        action_fn=lambda: _sinusoidal_joints(1.0),
    )
    await asyncio.sleep(0.5)
    meta = recorder.stop()

    assert meta.num_frames >= 20
    assert meta.file_path.exists()

    with h5py.File(str(meta.file_path), "r") as f:
        obs = f["observation/joint_positions"][:]
        act = f["action/joint_positions"][:]

        assert obs.shape[1] == 7, f"Expected 7 obs columns, got {obs.shape[1]}"
        assert act.shape[1] == 7, f"Expected 7 action columns, got {act.shape[1]}"

        # Values should vary (not all zeros or constants)
        obs_range = obs.max() - obs.min()
        assert obs_range > 0.01, f"Observation data is degenerate: range={obs_range}"


async def test_dataset_builds_from_mock_demo(tmp_path: Path) -> None:
    """StepDataset.build() succeeds on mock HDF5 data."""
    recorder = DemoRecorder(
        assembly_id="test",
        step_id="step_001",
        data_dir=tmp_path / "demos",
    )
    recorder.start(
        robot_state_fn=lambda: _sinusoidal_joints(0.0),
        action_fn=lambda: _sinusoidal_joints(1.0),
    )
    await asyncio.sleep(0.5)
    recorder.stop()

    dataset = StepDataset("test", "step_001", data_dir=str(tmp_path))
    info = dataset.build()

    assert info.obs_dim == 7
    assert info.action_dim == 7
    assert info.train_frames >= 16

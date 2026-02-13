"""End-to-end AURA demo sequence driven via HTTP API calls.

Demonstrates the full pipeline:
  Phase 1: Load assembly
  Phase 2: First execution (step_004 fails -> human intervention)
  Phase 3: Record demonstration + complete human step
  Phase 4: Train policy from recorded demo
  Phase 5: Second execution (step_004 succeeds via trained policy)
  Phase 6: Print analytics summary

Usage:
    python scripts/demo_sequence.py
    python scripts/demo_sequence.py --base-url http://host:port

Requires the AURA API server to be running (python scripts/run_api.py).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo")

ASSEMBLY_ID = "bearing_housing_v1"
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "configs" / "assemblies"
TIMEOUT = 10.0


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


class DemoError(Exception):
    """Raised when a demo phase fails."""


async def _get(client: httpx.AsyncClient, path: str) -> dict:
    """GET with timeout and error handling."""
    resp = await client.get(path, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise DemoError(f"GET {path} returned {resp.status_code}: {resp.text}")
    return resp.json()


async def _post(
    client: httpx.AsyncClient,
    path: str,
    body: dict | None = None,
    *,
    params: dict | None = None,
) -> dict:
    """POST with timeout and error handling."""
    resp = await client.post(path, json=body or {}, params=params, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise DemoError(f"POST {path} returned {resp.status_code}: {resp.text}")
    return resp.json()


async def _poll_execution(
    client: httpx.AsyncClient,
    target_phase: str,
    *,
    max_wait: float = 60.0,
) -> dict:
    """Poll execution state until the target phase is reached.

    Args:
        client: HTTP client.
        target_phase: Phase to wait for (e.g. "teaching", "complete").
        max_wait: Maximum seconds to wait before giving up.

    Returns:
        The execution state dict when the target phase is reached.
    """
    deadline = time.monotonic() + max_wait
    last_step = ""

    while time.monotonic() < deadline:
        state = await _get(client, "/execution/state")
        phase = state.get("phase", "idle")

        # Log step transitions
        current = state.get("currentStepId", "")
        if current and current != last_step:
            step_states = state.get("stepStates", {})
            step_info = step_states.get(current, {})
            status = step_info.get("status", "?")
            duration = step_info.get("durationMs")
            dur_str = f", duration={duration:.0f}ms" if duration else ""
            logger.info(
                "[Execution] Step %s: status=%s%s",
                current,
                status,
                dur_str,
            )
            last_step = current

        if phase == target_phase:
            return state
        if phase == "error":
            raise DemoError(f"Execution entered error state: {state}")

        await asyncio.sleep(0.5)

    raise DemoError(f"Timed out waiting for phase='{target_phase}' (waited {max_wait}s)")


# ------------------------------------------------------------------
# Phases
# ------------------------------------------------------------------


async def phase_1_load(client: httpx.AsyncClient) -> None:
    """Phase 1: Ensure assembly is loaded."""
    logger.info("[Phase 1] Loading assembly %s", ASSEMBLY_ID)

    assemblies = await _get(client, "/assemblies")
    ids = [a["id"] for a in assemblies]

    if ASSEMBLY_ID not in ids:
        logger.info("[Phase 1] Assembly not found, creating from fixture")
        fixture_file = FIXTURE_PATH / f"{ASSEMBLY_ID}.json"
        if not fixture_file.exists():
            raise DemoError(f"Fixture file not found: {fixture_file}")
        data = json.loads(fixture_file.read_text())
        await _post(client, "/assemblies", body=data)

    assembly = await _get(client, f"/assemblies/{ASSEMBLY_ID}")
    steps = assembly.get("steps", {})
    step_order = assembly.get("stepOrder", [])
    logger.info("[Phase 1] Assembly loaded: %d steps, order=%s", len(steps), step_order)

    if len(step_order) != 5:
        raise DemoError(f"Expected 5 steps, got {len(step_order)}")


async def phase_2_first_execution(client: httpx.AsyncClient) -> None:
    """Phase 2: Run execution until step_004 triggers human intervention."""
    logger.info("[Phase 2] Starting first execution run")

    await _post(client, "/execution/start", {"assemblyId": ASSEMBLY_ID})

    state = await _poll_execution(client, "teaching", max_wait=60.0)
    current = state.get("currentStepId", "")
    logger.info(
        "[Phase 2] Step %s failed after retries. Sequencer awaiting human demonstration.",
        current,
    )


async def phase_3_demonstrate(client: httpx.AsyncClient) -> None:
    """Phase 3: Record mock demo and complete the human step."""
    logger.info("[Phase 3] Starting mock teleoperation")
    await _post(client, "/teleop/start", body={}, params={"mock": "true"})

    logger.info("[Phase 3] Starting recording for step_004")
    await _post(
        client,
        "/recording/step/step_004/start",
        body={"assemblyId": ASSEMBLY_ID},
    )

    logger.info("[Phase 3] Recording for 2 seconds (mock demonstration)")
    await asyncio.sleep(2.0)

    demo_info = await _post(client, "/recording/stop")
    logger.info(
        "[Phase 3] Recording stopped: %d frames, %.1fs",
        demo_info.get("numFrames", 0),
        demo_info.get("durationS", 0),
    )

    await _post(client, "/teleop/stop")

    # Verify demo exists
    demos = await _get(client, f"/recording/demos/{ASSEMBLY_ID}/step_004")
    if not demos:
        raise DemoError("No demos found after recording")
    logger.info("[Phase 3] Verified %d demo(s) for step_004", len(demos))

    # Signal human completed the step
    logger.info("[Phase 3] Sending human intervention signal")
    await _post(client, "/execution/intervene")

    # Wait for remaining steps to finish
    await _poll_execution(client, "complete", max_wait=30.0)
    logger.info("[Phase 3] First execution run complete (with human assistance)")


async def phase_4_train(client: httpx.AsyncClient) -> str:
    """Phase 4: Train policy for step_004.

    Returns:
        The training job ID.
    """
    logger.info("[Phase 4] Launching training for step_004")
    job = await _post(
        client,
        "/training/step/step_004/train",
        body={"assemblyId": ASSEMBLY_ID, "numSteps": 1000},
    )
    job_id = job.get("jobId", "")
    logger.info("[Phase 4] Training job created: %s", job_id)

    # Poll until completed
    deadline = time.monotonic() + 120.0
    while time.monotonic() < deadline:
        status = await _get(client, f"/training/jobs/{job_id}")
        progress = status.get("progress", 0)
        job_status = status.get("status", "pending")

        if job_status == "completed":
            checkpoint = status.get("checkpointPath", "")
            logger.info(
                "[Phase 4] Training complete: checkpoint=%s, progress=%.0f%%",
                checkpoint,
                progress * 100,
            )
            return job_id

        if job_status == "failed":
            raise DemoError(f"Training failed: {status.get('error', 'unknown')}")

        await asyncio.sleep(1.0)

    raise DemoError("Training timed out after 120s")


async def phase_5_second_execution(client: httpx.AsyncClient) -> None:
    """Phase 5: Re-execute assembly. Step_004 should succeed via trained policy."""
    logger.info("[Phase 5] Starting second execution run (with trained policy)")

    await _post(client, "/execution/start", {"assemblyId": ASSEMBLY_ID})

    state = await _poll_execution(client, "complete", max_wait=60.0)

    # Verify all steps succeeded
    step_states = state.get("stepStates", {})
    for sid in ["step_001", "step_002", "step_003", "step_004", "step_005"]:
        status = step_states.get(sid, {}).get("status", "?")
        if status != "success":
            raise DemoError(f"Step {sid} status={status}, expected success")

    logger.info("[Phase 5] Assembly completed successfully. All 5 steps passed.")


async def phase_6_summary(client: httpx.AsyncClient, total_start: float) -> None:
    """Phase 6: Print analytics summary."""
    logger.info("[Phase 6] Fetching analytics")

    metrics = await _get(client, f"/analytics/{ASSEMBLY_ID}/steps")

    # Print table header
    header = f"{'step_id':<12} {'success_rate':>12} {'avg_ms':>10} {'attempts':>10}"
    logger.info("[Phase 6] %s", header)
    logger.info("[Phase 6] %s", "-" * len(header))

    for m in metrics:
        sid = m.get("stepId", "?")
        rate = m.get("successRate", 0)
        avg_ms = m.get("avgDurationMs", 0)
        attempts = m.get("totalAttempts", 0)
        logger.info(
            "[Phase 6] %-12s %11.0f%% %9.0fms %10d",
            sid,
            rate * 100,
            avg_ms,
            attempts,
        )

    elapsed = time.monotonic() - total_start
    logger.info("[Phase 6] Total demo elapsed time: %.1fs", elapsed)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


async def main() -> None:
    """Run all demo phases sequentially."""
    parser = argparse.ArgumentParser(description="AURA end-to-end demo sequence")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="AURA API base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    total_start = time.monotonic()

    async with httpx.AsyncClient(base_url=args.base_url) as client:
        try:
            # Quick health check
            health = await _get(client, "/health")
            if health.get("status") != "ok":
                raise DemoError(f"Health check failed: {health}")
            logger.info("Connected to AURA API at %s", args.base_url)

            await phase_1_load(client)
            await phase_2_first_execution(client)
            await phase_3_demonstrate(client)
            await phase_4_train(client)
            await phase_5_second_execution(client)
            await phase_6_summary(client, total_start)

            logger.info("Demo sequence completed successfully.")

        except DemoError as e:
            logger.error("Demo failed: %s", e)
            sys.exit(1)
        except httpx.ConnectError:
            logger.error(
                "Cannot connect to %s. Is the API server running? "
                "(python scripts/run_api.py)",
                args.base_url,
            )
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

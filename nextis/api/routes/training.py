"""Training routes — per-step policy training with real ACT pipeline.

Launches background training tasks that build datasets from HDF5 demos,
train a MinimalACT policy, and save checkpoints. Job progress is tracked
in-memory and queryable via GET endpoints.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException

from nextis.api.schemas import TrainingJobState, TrainRequest
from nextis.errors import TrainingError
from nextis.learning.dataset import StepDataset
from nextis.learning.trainer import PolicyTrainer, TrainingConfig, TrainingProgress

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job registry.
_jobs: dict[str, TrainingJobState] = {}


async def _run_training(job: TrainingJobState, step_id: str, request: TrainRequest) -> None:
    """Background coroutine that runs the full training pipeline.

    Updates the job object in-place with progress, status, and result.
    """
    try:
        job.status = "running"
        job.progress = 0.0

        # Build dataset from recorded demos
        logger.info("Building dataset for %s/%s", request.assembly_id, step_id)
        dataset = StepDataset(request.assembly_id, step_id)
        info = dataset.build()

        # Map num_steps to epochs (rough heuristic: 1 epoch ≈ 100 steps)
        num_epochs = max(10, request.num_steps // 100)

        config = TrainingConfig(num_epochs=num_epochs)

        def on_progress(p: TrainingProgress) -> None:
            job.progress = (p.epoch + 1) / p.total_epochs

        # Train
        logger.info("Starting training: %d epochs", num_epochs)
        trainer = PolicyTrainer()
        result = await trainer.train(info, config=config, on_progress=on_progress)

        job.status = "completed"
        job.progress = 1.0
        job.checkpoint_path = str(result.checkpoint_path)
        logger.info("Training complete: %s (loss=%.6f)", result.checkpoint_path, result.final_loss)

    except TrainingError as e:
        logger.error("Training failed for %s/%s: %s", request.assembly_id, step_id, e)
        job.status = "failed"
        job.error = str(e)

    except Exception as e:
        logger.error("Unexpected training error: %s", e, exc_info=True)
        job.status = "failed"
        job.error = str(e)


@router.post("/step/{step_id}/train")
async def start_training(step_id: str, request: TrainRequest) -> TrainingJobState:
    """Launch a training job for a specific assembly step.

    Builds a dataset from recorded HDF5 demos, trains a MinimalACT policy,
    and saves the checkpoint. Training runs as a background task.

    Args:
        step_id: Assembly step to train a policy for.
        request: Training configuration (architecture, num_steps, assembly_id).
    """
    job_id = str(uuid.uuid4())[:8]

    job = TrainingJobState(
        job_id=job_id,
        step_id=step_id,
        status="pending",
        progress=0.0,
    )
    _jobs[job_id] = job

    logger.info(
        "Training job created: job=%s step=%s arch=%s steps=%d assembly=%s",
        job_id,
        step_id,
        request.architecture,
        request.num_steps,
        request.assembly_id,
    )

    # Launch training in background
    asyncio.create_task(_run_training(job, step_id, request))

    return job


@router.get("/jobs/{job_id}")
async def get_training_job(job_id: str) -> TrainingJobState:
    """Get the status of a training job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")
    return job


@router.get("/jobs", response_model=list[TrainingJobState])
async def list_training_jobs() -> list[TrainingJobState]:
    """List all training jobs."""
    return list(_jobs.values())

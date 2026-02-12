"""Policy router — dispatches assembly steps to primitives or learned policies.

For primitive-type steps, calls the appropriate function from PrimitiveLibrary.
For policy-type steps, currently stubs out with a failure since no policies
are trained yet.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from nextis.assembly.models import AssemblyStep
from nextis.control.primitives import PrimitiveLibrary
from nextis.execution.types import StepResult

logger = logging.getLogger(__name__)


class PolicyRouter:
    """Routes assembly steps to the appropriate execution handler.

    Args:
        primitive_library: PrimitiveLibrary for dispatching primitive steps.
        robot: Connected follower robot instance (passed to primitives).
    """

    def __init__(
        self,
        primitive_library: PrimitiveLibrary | None = None,
        robot: Any = None,
    ) -> None:
        self._primitives = primitive_library or PrimitiveLibrary()
        self._robot = robot

    async def dispatch(self, step: AssemblyStep) -> StepResult:
        """Dispatch a step to the appropriate handler.

        Args:
            step: The assembly step to execute.

        Returns:
            StepResult with success/failure and timing.
        """
        start_ms = time.monotonic() * 1000

        if step.handler == "primitive":
            return await self._run_primitive(step, start_ms)
        if step.handler == "policy":
            return await self._run_policy(step, start_ms)

        logger.error("Unknown handler type '%s' for step %s", step.handler, step.id)
        return StepResult(
            success=False,
            duration_ms=time.monotonic() * 1000 - start_ms,
            handler_used=step.handler,
            error_message=f"Unknown handler: {step.handler}",
        )

    async def _run_primitive(self, step: AssemblyStep, start_ms: float) -> StepResult:
        """Execute a primitive-type step."""
        if not step.primitive_type:
            return StepResult(
                success=False,
                duration_ms=time.monotonic() * 1000 - start_ms,
                handler_used="primitive",
                error_message=f"Step {step.id} has no primitive_type set",
            )

        try:
            result = await self._primitives.run(
                name=step.primitive_type,
                robot=self._robot,
                params=step.primitive_params,
            )
            return StepResult(
                success=result.success,
                duration_ms=result.duration_ms,
                handler_used="primitive",
                error_message=result.error_message,
            )
        except Exception as e:
            logger.error("Primitive '%s' failed on step %s: %s", step.primitive_type, step.id, e)
            return StepResult(
                success=False,
                duration_ms=time.monotonic() * 1000 - start_ms,
                handler_used="primitive",
                error_message=str(e),
            )

    async def _run_policy(self, step: AssemblyStep, start_ms: float) -> StepResult:
        """Execute a policy-type step (stub — always fails)."""
        logger.warning(
            "Policy execution not implemented. Step '%s' (policy_id=%s) will fail.",
            step.id,
            step.policy_id,
        )
        return StepResult(
            success=False,
            duration_ms=time.monotonic() * 1000 - start_ms,
            handler_used="policy",
            error_message="Policy execution not yet implemented",
        )

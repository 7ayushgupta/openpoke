"""Coordinate execution agents and batch their results for the interaction agent."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .runtime import ExecutionAgentRuntime, ExecutionResult
from ...logging_config import logger
from ...services.admin import get_admin_status_service


@dataclass
class PendingExecution:
    """Track a pending execution request."""

    request_id: str
    agent_name: str
    instructions: str
    batch_id: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class _BatchState:
    """Collect results for a single interaction-agent turn."""

    batch_id: str
    created_at: datetime = field(default_factory=datetime.now)
    pending: int = 0
    results: List[ExecutionResult] = field(default_factory=list)


class ExecutionBatchManager:
    """Run execution agents and deliver their combined outcome."""

    # Initialize batch manager with timeout and coordination state for execution agents
    def __init__(self, timeout_seconds: int = 90) -> None:
        self.timeout_seconds = timeout_seconds
        self._pending: Dict[str, PendingExecution] = {}
        self._batch_lock = asyncio.Lock()
        self._batch_state: Optional[_BatchState] = None

    # Run execution agent with timeout handling and batch coordination for interaction agent
    async def execute_agent(
        self,
        agent_name: str,
        instructions: str,
        request_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute an agent asynchronously and buffer the result for batch dispatch."""

        if not request_id:
            request_id = str(uuid.uuid4())

        # Record agent spawn
        admin_service = get_admin_status_service()
        admin_service.record_execution_agent_spawned()
        logger.info(f"[BATCH] Spawning execution agent '{agent_name}' with instructions: {instructions[:150]}{'...' if len(instructions) > 150 else ''}")

        batch_id = await self._register_pending_execution(agent_name, instructions, request_id)

        try:
            logger.info(f"[{agent_name}] Execution started")
            runtime = ExecutionAgentRuntime(agent_name=agent_name)
            result = await asyncio.wait_for(
                runtime.execute(instructions),
                timeout=self.timeout_seconds,
            )
            status = "SUCCESS" if result.success else "FAILED"
            logger.info(f"[{agent_name}] Execution finished: {status}")
            if result.success:
                logger.info(f"[{agent_name}] Final response: {result.response[:200]}{'...' if len(result.response) > 200 else ''}")
            else:
                logger.warning(f"[{agent_name}] Execution failed with error: {result.error}")
        except asyncio.TimeoutError:
            logger.error(f"[{agent_name}] Execution timed out after {self.timeout_seconds}s")
            result = ExecutionResult(
                agent_name=agent_name,
                success=False,
                response=f"Execution timed out after {self.timeout_seconds} seconds",
                error="Timeout",
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(f"[{agent_name}] Execution failed unexpectedly")
            result = ExecutionResult(
                agent_name=agent_name,
                success=False,
                response=f"Execution failed: {exc}",
                error=str(exc),
            )
        finally:
            self._pending.pop(request_id, None)
            # Record completion (success or failure)
            admin_service.record_execution_agent_completed(result.success)
            logger.info(f"[BATCH] Agent '{agent_name}' completed. Success: {result.success}, Total pending: {len(self._pending)}")

        await self._complete_execution(batch_id, result, agent_name)
        return result

    # Add execution request to current batch or create new batch if none exists
    async def _register_pending_execution(
        self,
        agent_name: str,
        instructions: str,
        request_id: str,
    ) -> str:
        """Attach a new execution to the active batch, opening one when required."""

        async with self._batch_lock:
            if self._batch_state is None:
                batch_id = str(uuid.uuid4())
                self._batch_state = _BatchState(batch_id=batch_id)
            else:
                batch_id = self._batch_state.batch_id

            self._batch_state.pending += 1
            self._pending[request_id] = PendingExecution(
                request_id=request_id,
                agent_name=agent_name,
                instructions=instructions,
                batch_id=batch_id,
            )

            return batch_id

    # Store execution result and send combined batch to interaction agent when complete
    async def _complete_execution(
        self,
        batch_id: str,
        result: ExecutionResult,
        agent_name: str,
    ) -> None:
        """Record the execution result and dispatch when the batch drains."""

        dispatch_payload: Optional[str] = None

        logger.info(f"[EXECUTION_BATCH] Completing execution for agent: {agent_name}")
        logger.info(f"[EXECUTION_BATCH] Result success: {result.success}")
        if result.success:
            logger.info(f"[EXECUTION_BATCH] Agent {agent_name} response: {result.response[:200]}{'...' if len(result.response) > 200 else ''}")
        else:
            logger.warning(f"[EXECUTION_BATCH] Agent {agent_name} failed: {result.error}")

        async with self._batch_lock:
            state = self._batch_state
            if state is None or state.batch_id != batch_id:
                logger.warning(f"[{agent_name}] Dropping result for unknown batch")
                return

            state.results.append(result)
            state.pending -= 1
            logger.info(f"[EXECUTION_BATCH] Added result for {agent_name}. Pending: {state.pending}")

            if state.pending == 0:
                dispatch_payload = self._format_batch_payload(state.results)
                agent_names = [entry.agent_name for entry in state.results]
                logger.info(f"[EXECUTION_BATCH] Execution batch completed: {', '.join(agent_names)}")
                logger.info(f"[EXECUTION_BATCH] Batch payload: {dispatch_payload[:300]}{'...' if len(dispatch_payload) > 300 else ''}")
                self._batch_state = None

        if dispatch_payload:
            logger.info(f"[EXECUTION_BATCH] Dispatching to interaction agent")
            await self._dispatch_to_interaction_agent(dispatch_payload)

    # Return list of currently pending execution requests for monitoring purposes
    def get_pending_executions(self) -> List[Dict[str, str]]:
        """Expose pending executions for observability."""

        return [
            {
                "request_id": pending.request_id,
                "agent_name": pending.agent_name,
                "batch_id": pending.batch_id,
                "created_at": pending.created_at.isoformat(),
                "elapsed_seconds": (datetime.now() - pending.created_at).total_seconds(),
            }
            for pending in self._pending.values()
        ]

    # Clean up all pending executions and batch state on shutdown
    async def shutdown(self) -> None:
        """Clear pending bookkeeping and kill all running execution agents."""
        logger.info(f"[BATCH] Shutting down batch manager with {len(self._pending)} running agents")
        
        # Clear all pending executions (kills running agents)
        self._pending.clear()
        
        # Clear batch state
        async with self._batch_lock:
            self._batch_state = None
        
        logger.info("[BATCH] All execution agents killed and batch manager shutdown complete")

    # Format multiple execution results into single message for interaction agent
    def _format_batch_payload(self, results: List[ExecutionResult]) -> str:
        """Render execution results into the interaction-agent format."""

        entries: List[str] = []
        for result in results:
            status = "SUCCESS" if result.success else "FAILED"
            response_text = (result.response or "(no response provided)").strip()
            entries.append(f"[{status}] {result.agent_name}: {response_text}")
        return "\n".join(entries)

    # Forward combined execution results to interaction agent for user response generation
    async def _dispatch_to_interaction_agent(self, payload: str) -> None:
        """Send the aggregated execution summary to the interaction agent."""

        from ..interaction_agent.runtime import InteractionAgentRuntime

        runtime = InteractionAgentRuntime()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(runtime.handle_agent_message(payload))
            return

        loop.create_task(runtime.handle_agent_message(payload))

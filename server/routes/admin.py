"""Admin API routes for dashboard status."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..services.admin import get_admin_status_service
from ..services.execution.roster import get_agent_roster
from ..agents.execution_agent.batch_manager import ExecutionBatchManager
from ..logging_config import logger

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
async def get_admin_status():
    """Get admin dashboard status including interaction and execution agent statistics."""
    try:
        admin_service = get_admin_status_service()
        
        # Get interaction agent status
        interaction_status = admin_service.get_interaction_agent_status()
        
        # Get execution agent roster
        roster = get_agent_roster()
        roster.load()
        all_agents = roster.get_agents()
        
        # Get currently running execution agents from batch manager
        batch_manager = ExecutionBatchManager()
        pending_executions = batch_manager.get_pending_executions()
        
        # Format running agents data
        running_agents = []
        for execution in pending_executions:
            running_agents.append({
                "name": execution["agent_name"],
                "started_at": execution["created_at"],
                "instructions": "Processing...",  # Could be enhanced to store actual instructions
                "elapsed_seconds": execution["elapsed_seconds"]
            })
        
        # Get execution agent statistics
        execution_stats = admin_service.get_execution_agent_statistics()
        
        response = {
            "interaction_agent": interaction_status,
            "execution_agents": {
                "currently_running": len(pending_executions),
                "running_agents": running_agents,
                "statistics": execution_stats,
                "roster": all_agents
            }
        }
        
        logger.debug("Admin status requested", extra={
            "interaction_status": interaction_status["status"],
            "running_count": len(pending_executions),
            "total_roster": len(all_agents)
        })
        
        return JSONResponse(content=response)
        
    except Exception as exc:
        logger.error("Failed to get admin status", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to retrieve admin status")

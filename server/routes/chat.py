from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..models import ChatHistoryClearResponse, ChatHistoryResponse, ChatRequest
from ..models.auth import User
from ..middleware.auth import get_current_user
from ..services import get_conversation_log, get_trigger_service, handle_chat_request

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_class=JSONResponse, summary="Submit a chat message and receive a completion")
# Handle incoming chat messages and route them to the interaction agent
async def chat_send(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    return await handle_chat_request(payload, user_id=current_user.id)


@router.get("/history", response_model=ChatHistoryResponse)
# Retrieve the conversation history from the log
def chat_history(current_user: User = Depends(get_current_user)) -> ChatHistoryResponse:
    log = get_conversation_log(current_user.id)
    return ChatHistoryResponse(messages=log.to_chat_messages())


@router.delete("/history", response_model=ChatHistoryClearResponse)
def clear_history(current_user: User = Depends(get_current_user)) -> ChatHistoryClearResponse:
    from ..services import get_execution_agent_logs, get_agent_roster
    from ..agents.execution_agent.batch_manager import ExecutionBatchManager
    from ..logging_config import logger

    # Get current running agents count before clearing
    batch_manager = ExecutionBatchManager()
    pending_executions = batch_manager.get_pending_executions()
    running_count = len(pending_executions)
    
    logger.info(f"[CLEAR_HISTORY] Starting clear operation for user {current_user.id} with {running_count} running execution agents")

    # Clear conversation log
    log = get_conversation_log(current_user.id)
    log.clear()

    # Clear execution agent logs
    execution_logs = get_execution_agent_logs(current_user.id)
    execution_logs.clear_all()

    # Clear agent roster
    roster = get_agent_roster(current_user.id)
    roster.clear()

    # Clear stored triggers
    trigger_service = get_trigger_service(current_user.id)
    trigger_service.clear_all()

    # Kill all running execution agents
    if running_count > 0:
        logger.info(f"[CLEAR_HISTORY] Killing {running_count} running execution agents")
        # Clear pending executions (this effectively "kills" them)
        batch_manager._pending.clear()
        batch_manager._batch_state = None
        logger.info("[CLEAR_HISTORY] All running execution agents killed")
    else:
        logger.info("[CLEAR_HISTORY] No running execution agents to kill")

    logger.info("[CLEAR_HISTORY] Clear operation completed successfully")
    return ChatHistoryClearResponse()


__all__ = ["router"]

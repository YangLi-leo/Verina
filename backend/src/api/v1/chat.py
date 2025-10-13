"""Chat API Endpoints (matches search.py pattern)."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.dependencies import get_chat_service
from src.chat import ChatRequest as ChatRequestModel, ChatResponse
from src.services.chat_service import ChatService

logger = logging.getLogger(__name__)
router = APIRouter()




@router.post("/stream")
async def chat_stream(
    request: ChatRequestModel,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Streaming chat endpoint - returns SSE stream with real-time thinking steps and answer.

    Frontend receives events in this order:
    1. thinking_step events: Each tool execution as it happens
    2. chunk events: Answer text chunks (for typing effect)
    3. complete event: Final ChatResponse with all metadata

    Event types:
    - {"type": "thinking_step", "data": {...ThinkingStep...}}
    - {"type": "chunk", "data": "text chunk"}
    - {"type": "complete", "data": {...ChatResponse...}}
    - {"type": "error", "message": "error description"}
    """
    try:
        user_id = "anonymous"  # No authentication required
        logger.info(f"Streaming chat from user {user_id}: {request.message[:50]}...")

        async def event_generator():
            """Generate SSE events from ChatService stream"""
            try:
                async for event in chat_service.process_message_stream(
                    message=request.message,
                    session_id=request.session_id,
                    user_id=user_id,
                    mode=request.mode if request.mode else "chat",
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Stream generator error: {e}", exc_info=True)
                error_event = {"type": "error", "message": str(e)}
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except Exception as e:
        logger.error(f"Stream setup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequestModel,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Send a chat message and get response.

    Frontend receives ChatResponse with:
    - assistant_message: Final response
    - thinking_steps: Step-by-step reasoning process
    - sources: Citation sources for [1][2] references
    - session_id: Session identifier
    - metadata: used_tools, has_code, has_web_results, total_time_ms
    """
    try:
        user_id = "anonymous"  # No authentication required
        logger.info(f"Chat message from user {user_id}: {request.message[:50]}...")

        response = await chat_service.process_message(
            message=request.message,
            session_id=request.session_id,
            user_id=user_id,
            mode=request.mode if request.mode else "chat",
        )

        return response

    except Exception as e:
        logger.error(f"Send message error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(
    limit: int = Query(default=20, ge=1, le=100),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get user's chat sessions for history sidebar.

    Returns list of session summaries:
    - session_id
    - first_message (preview)
    - message_count
    - created_at, updated_at

    Note: Without authentication, returns empty list.
    """
    try:
        user_id = "anonymous"
        history = await chat_service.get_user_chat_sessions(
            user_id=user_id, limit=limit
        )
        return {"sessions": history}

    except Exception as e:
        logger.error(f"Get history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get history")


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get full conversation history for a specific session (public access via session_id).

    Used for restoring conversation on page refresh.
    Note: session_id itself acts as access token (UUID is hard to guess)
    """
    try:
        session_data = await chat_service.get_conversation_history_public(
            session_id=session_id
        )

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        return session_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get session")


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Delete a chat session (public access via session_id).

    Note: session_id itself acts as access token (UUID is hard to guess).
    """
    try:
        user_id = "anonymous"
        success = await chat_service.delete_session(
            session_id=session_id, user_id=user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.post("/session/{session_id}/clear")
async def clear_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Clear conversation history but keep session alive (public access via session_id).

    Note: session_id itself acts as access token (UUID is hard to guess).
    """
    try:
        user_id = "anonymous"
        success = await chat_service.clear_session_conversation(
            session_id=session_id, user_id=user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Conversation cleared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear session")


@router.post("/session/{session_id}/stop")
async def stop_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Stop active chat session (user clicks stop button).

    This sets a cancellation flag that the streaming loop checks.
    The stream will stop at the next iteration checkpoint.

    Works for both Chat Mode and Agent Mode.

    Note: session_id itself acts as access token (UUID is hard to guess).
    """
    try:
        chat_service.cancel_session(session_id)
        logger.info(f"Stop requested for session {session_id}")
        return {"message": "Cancellation requested", "session_id": session_id}

    except Exception as e:
        logger.error(f"Stop session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to stop session")
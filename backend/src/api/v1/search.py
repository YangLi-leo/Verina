"""
Search API Endpoints
"""

import logging
from typing import Optional

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.dependencies import get_search_service
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model for SearchAgent V1"""

    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    deep_thinking: bool = Field(default=False, description="Enable deep thinking mode for complex queries")




@router.post("/stream")
async def search_stream(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
):
    """
    Streaming search endpoint - returns SSE stream

    Frontend receives:
    1. metadata event: candidates, queries, related_searches
    2. chunk events: answer chunks (typing effect)
    3. done event: completion signal
    """
    try:
        user_id = "anonymous"  # For local open source, no authentication
        mode = "deep" if request.deep_thinking else "standard"
        logger.info(f"[API] Search request from user {user_id}, mode={mode}, query: {request.query[:50]}...")

        async def event_generator():
            """Generate SSE events"""
            try:
                async for event in search_service.search(
                    user_id=user_id,
                    query=request.query,
                    deep_thinking=request.deep_thinking
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                error_event = {"type": "error", "message": str(e)}
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        logger.error(f"Stream setup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_search_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Get user's search history
    """
    try:
        user_id = "anonymous"  # For local open source, no authentication
        history = await search_service.get_user_search_history(
            user_id=user_id, limit=limit
        )
        return history
    except Exception as e:
        logger.error(f"Get history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get history")


@router.get("/record/{search_id}")
async def get_search_record(
    search_id: str,
    search_service: SearchService = Depends(get_search_service),
):
    """
    Get a specific search record for history restoration (public access via search_id)

    Note: No authentication required - search_id itself acts as access token
    """
    try:
        record = await search_service.get_search_record_public(search_id=search_id)
        if not record:
            raise HTTPException(status_code=404, detail="Search not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get record error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get search record")



"""
Verina Backend Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.v1 import search
from src.core.config import Config
from src.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Verina backend...")
    # Startup code here (e.g., database connections, cache initialization)
    yield
    # Shutdown code here
    logger.info("Shutting down Verina backend...")


# Create FastAPI app
app = FastAPI(
    title="Verina API",
    description="AI-powered search engine API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if Config.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if Config.ENVIRONMENT == "development" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat module is still evolving; make it optional so search can run independently
try:
    from src.api.v1 import chat  # type: ignore
    _chat_router = chat.router
except Exception as exc:  # pragma: no cover - defensive guard for unfinished module
    _chat_router = None
    logger.warning("Chat routes disabled: %s", exc)

# Include API routers
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])

if _chat_router is not None:
    app.include_router(_chat_router, prefix="/api/v1/chat", tags=["Chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Verina API",
        "version": "1.0.0",
        "docs": "/api/docs" if Config.ENVIRONMENT == "development" else None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "verina-backend", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.ENVIRONMENT == "development",
    )

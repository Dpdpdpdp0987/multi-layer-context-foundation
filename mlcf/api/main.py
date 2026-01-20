"""
FastAPI REST API - Main application entry point.
"""

from typing import Optional
from contextlib import asynccontextmanager
import time
from loguru import logger

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from mlcf.api.routes import (
    context_router,
    search_router,
    graph_router,
    admin_router,
    health_router
)
from mlcf.api.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware
)
from mlcf.api.exceptions import (
    MLCFException,
    handle_mlcf_exception,
    handle_validation_error,
    handle_http_exception,
    handle_generic_exception
)
from mlcf.api.config import get_settings
from mlcf.core.orchestrator import ContextOrchestrator
from mlcf.storage.vector_store import QdrantVectorStore
from mlcf.graph.neo4j_store import Neo4jStore


# Application state
class AppState:
    """Application state container."""
    orchestrator: Optional[ContextOrchestrator] = None
    vector_store: Optional[QdrantVectorStore] = None
    graph_store: Optional[Neo4jStore] = None
    start_time: float = 0


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    logger.info("Starting MLCF API server...")
    
    app_state.start_time = time.time()
    
    try:
        # Initialize orchestrator
        app_state.orchestrator = ContextOrchestrator()
        logger.info("Context orchestrator initialized")
        
        # Initialize vector store if enabled
        if settings.ENABLE_VECTOR_SEARCH:
            try:
                app_state.vector_store = QdrantVectorStore(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    collection_name=settings.QDRANT_COLLECTION
                )
                logger.info("Vector store initialized")
            except Exception as e:
                logger.warning(f"Vector store init failed: {e}")
        
        # Initialize graph store if enabled
        if settings.ENABLE_GRAPH_SEARCH:
            try:
                app_state.graph_store = Neo4jStore(
                    uri=settings.NEO4J_URI,
                    user=settings.NEO4J_USER,
                    password=settings.NEO4J_PASSWORD
                )
                logger.info("Graph store initialized")
            except Exception as e:
                logger.warning(f"Graph store init failed: {e}")
        
        logger.info("MLCF API server started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MLCF API server...")
    
    if app_state.graph_store:
        app_state.graph_store.close()
        logger.info("Graph store closed")
    
    logger.info("MLCF API server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Multi-Layer Context Foundation API",
    description="REST API for intelligent context management with multi-layer storage",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Configure CORS
settings = get_settings()
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

if settings.ENABLE_RATE_LIMITING:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )


# Exception handlers
app.add_exception_handler(MLCFException, handle_mlcf_exception)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(StarletteHTTPException, handle_http_exception)
app.add_exception_handler(Exception, handle_generic_exception)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(context_router, prefix="/api/v1/context", tags=["Context"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
app.include_router(graph_router, prefix="/api/v1/graph", tags=["Knowledge Graph"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multi-Layer Context Foundation API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


# Make app_state accessible to routes
app.state.mlcf = app_state


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "mlcf.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import settings
from database import init_database, close_database
from models.responses import HealthResponse, ErrorResponse
from routers import programs, review


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()


# Create FastAPI app
app = FastAPI(
    title="Graduate Admissions API",
    description="API for graduate admissions requirements data collection and analysis",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:19006", # Expo dev server
        "https://*.vercel.app",   # Vercel deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    if settings.debug:
        import traceback
        detail = f"{str(exc)}\n\n{traceback.format_exc()}"
    else:
        detail = "Internal server error"

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=detail
        ).model_dump()
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint."""
    from database import db

    # Test database connection
    db_healthy = False
    try:
        await db.execute_one("SELECT 1")
        db_healthy = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        timestamp=asyncio.get_event_loop().time(),
        version="0.1.0",
        database=db_healthy
    )


# API status endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Graduate Admissions API",
        "version": "0.1.0",
        "description": "API for graduate admissions requirements data collection and analysis",
        "docs_url": "/docs" if settings.debug else None,
        "status": "running"
    }


# Include routers
app.include_router(programs.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")


# Rate limiting middleware (simple in-memory implementation)
import time
from collections import defaultdict
from typing import Dict

request_counts: Dict[str, list] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware."""
    if not settings.debug and "/api/" in str(request.url):
        client_ip = request.client.host
        current_time = time.time()

        # Clean old requests (older than 1 minute)
        request_counts[client_ip] = [
            req_time for req_time in request_counts[client_ip]
            if current_time - req_time < 60
        ]

        # Check rate limit
        if len(request_counts[client_ip]) >= settings.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error="Rate Limit Exceeded",
                    detail=f"Maximum {settings.requests_per_minute} requests per minute exceeded"
                ).model_dump()
            )

        # Add current request
        request_counts[client_ip].append(current_time)

    response = await call_next(request)
    return response


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
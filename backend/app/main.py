"""
Main FastAPI Application entrypoint for The Lenny Growth Assistant.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.middleware.trace import TraceMiddleware
from app.routers import artifacts, chat, config, health, sessions

# Initialize structured logging
setup_logging()

app = FastAPI(
    title="The Lenny Growth Assistant API",
    description="Backend API providing grounded growth intelligence and session persistence.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Tracing & CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)


# ---------------------------------------------------------------------------
# Include Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(config.router)
app.include_router(chat.router)
app.include_router(artifacts.router)


@app.get("/", tags=["Root"])
def read_root():
    return {
        "name": "The Lenny Growth Assistant API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }

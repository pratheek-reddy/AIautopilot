"""
API Router Configuration Module.

This module serves as the central routing configuration for the AI Autopilot API.
It aggregates and organizes different route collections (core and specialized endpoints)
into a unified router structure. The module uses FastAPI's APIRouter for route management
and organization.

The routing structure is organized as follows:
- Core endpoints: Basic task management and execution endpoints
- Writer endpoints: Specialized endpoints for content generation and management
"""

from fastapi import APIRouter
from app.api.endpoints import router as core_router
from app.api.endpoints.writer import router as writer_router

# Initialize the main API router that will contain all sub-routers
api_router = APIRouter()

# Mount the core router containing primary task management endpoints
# These endpoints handle task execution, plan approval, and status checks
api_router.include_router(core_router, tags=["core"])

# Mount the writer router with a '/writer' prefix for content-related endpoints
# These endpoints handle specialized content generation and formatting tasks
api_router.include_router(writer_router, prefix="/writer", tags=["writer"]) 
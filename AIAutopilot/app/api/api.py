from fastapi import APIRouter
from app.api.endpoints.writer import router as writer_router

api_router = APIRouter()

# Only include the writer router for now
api_router.include_router(writer_router, prefix="/writer", tags=["writer"]) 
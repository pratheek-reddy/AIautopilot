"""
Main FastAPI application module that initializes and configures the AI Autopilot API.

This module sets up the FastAPI application with necessary middleware, logging configuration,
and environment variable validation. It serves as the entry point for the application and
handles the core API routing setup.

Key responsibilities:
- Application initialization and configuration
- Logging setup
- Environment variable validation
- CORS middleware configuration
- API router integration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv
from app.api.api import api_router

# Configure logging with both file and console handlers for comprehensive debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autopilot.log"),  # Persistent log file for historical tracking
        logging.StreamHandler()                # Console output for immediate feedback
    ]
)

# Load environment variables from .env file if present
load_dotenv()

# Validate critical environment variables
# These are required for the OpenAI integration used by various agents
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
if not OPENAI_MODEL:
    raise ValueError("OPENAI_MODEL environment variable is not set")

# Initialize FastAPI application with metadata
app = FastAPI(
    title="AI Autopilot API",
    description="API for automating tasks using AI agents",
    version="1.0.0"
)

# Configure CORS middleware to allow cross-origin requests
# This is particularly important for web clients accessing the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Allow all origins for development
    allow_credentials=True,  # Allow credentials (cookies, authorization headers)
    allow_methods=["*"],     # Allow all HTTP methods
    allow_headers=["*"],     # Allow all headers
)

# Mount the API router with version prefix
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """
    Root endpoint that serves as a basic health check and welcome message.

    Returns:
        dict: A simple welcome message indicating the API is running.
    """
    return {"message": "Hello World"}

"""
Application Configuration Module.

This module manages the application's configuration settings using Pydantic's
BaseSettings for type-safe configuration management. It handles loading of
environment variables and provides default values for essential settings.

Key features:
- Environment variable loading from .env files
- Type validation for configuration values
- Default value management
- Support for multiple AI model providers
- Database configuration
"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings management class.

    This class uses Pydantic's BaseSettings to handle configuration
    with environment variable support and type validation. It manages
    API keys, model selections, and database connections.

    Attributes:
        OPENAI_API_KEY: API key for OpenAI services
        OPENAI_MODEL: Selected OpenAI model (default: gpt-4)
        DATABASE_URL: Database connection string
        GEMINI_API_KEY: API key for Google's Gemini AI services

    Environment Variables:
        The following environment variables can be set to override defaults:
        - OPENAI_API_KEY: OpenAI API key
        - OPENAI_MODEL: OpenAI model name
        - DATABASE_URL: Database connection URL
        - GEMINI_API_KEY: Gemini API key
    """
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./autopilot.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        """
        Pydantic configuration class.

        Configures the behavior of the settings class, including
        environment file loading and extra field handling.
        """
        env_file = ".env"
        extra = "allow"  # Allow extra fields in the environment

# Create singleton settings instance
settings = Settings()

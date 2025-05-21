"""
Writer Agent Module.

This module implements an AI-powered writing agent that formats and structures content
using specialized DSPy modules. It supports multiple content types including emails,
Standard Operating Procedures (SOPs), and summaries, with customizable formatting options.

Key features:
- Multiple content type support (email, SOP, summary)
- DSPy-powered content generation
- Customizable formatting and styling
- Metadata tracking and generation
- Error handling with graceful fallback
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models import Output
from .writer.dspy_modules import EmailGenerator, SOPGenerator, SummaryGenerator
import json
import re
from app.core.config import settings

class WriterAgent:
    """
    An AI agent specialized in content generation and formatting.

    This agent uses DSPy modules to generate and format different types of content,
    including emails, SOPs, and summaries. Each content type has its own specialized
    generator with configurable parameters for customization.

    Key capabilities:
    - Email generation with customizable tone and audience
    - SOP creation with variable complexity levels
    - Content summarization with adjustable length
    - Metadata generation for each content type
    - Error handling with informative feedback
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the writer agent with specialized DSPy modules.

        Args:
            api_key: Optional API key (currently unused, maintained for consistency)
        """
        # Initialize specialized DSPy modules for each content type
        self.email_generator = EmailGenerator()
        self.sop_generator = SOPGenerator()
        self.summary_generator = SummaryGenerator()

    def run(self, content: str, format: str = "markdown", content_type: str = "email", **kwargs) -> Output:
        """
        Format and structure content using appropriate DSPy modules.

        This method processes input content through specialized DSPy modules based on
        the content type. It handles various formatting options and generates appropriate
        metadata for each content type.

        Args:
            content: The raw content to be processed
            format: Output format (default: "markdown")
            content_type: Type of content to generate ("email", "sop", or "summary")
            **kwargs: Additional arguments specific to each content type:
                For email:
                    - audience: Target audience (default: "general")
                    - tone: Email tone (default: "professional")
                For SOP:
                    - target_audience: Intended readers (default: "general")
                    - complexity_level: Detail level (default: "medium")
                For summary:
                    - target_length: Desired length (default: "medium")
                    - key_points: List of points to focus on

        Returns:
            Output object containing:
            - summary: Brief overview of the content
            - details: Formatted main content
            - recommendations: List of suggestions or next steps
            - format: Output format used
            - metadata: Content-specific metadata

        Raises:
            ValueError: If an unsupported content type is specified
        """
        try:
            if content_type == "email":
                # Generate email using DSPy EmailGenerator
                result = self.email_generator.forward(
                    meeting_notes=content,
                    audience=kwargs.get("audience", "general"),
                    tone=kwargs.get("tone", "professional")
                )
                return Output(
                    summary=result.subject,
                    details=f"{result.greeting}\n\n{result.body}\n\n{result.closing}\n{result.email_signature}",
                    recommendations=[],
                    format=format,
                    metadata={
                        "type": "email",
                        "subject": result.subject,
                        "audience": kwargs.get("audience", "general"),
                        "tone": kwargs.get("tone", "professional")
                    }
                )
            elif content_type == "sop":
                # Generate SOP using DSPy SOPGenerator
                result = self.sop_generator.forward(
                    process_description=content,
                    target_audience=kwargs.get("target_audience", "general"),
                    complexity_level=kwargs.get("complexity_level", "medium")
                )
                return Output(
                    summary=result.title,
                    details=f"Purpose: {result.purpose}\nPrerequisites: {', '.join(result.prerequisites or [])}\nSteps: {', '.join(result.steps or [])}",
                    recommendations=result.warnings or [],
                    format=format,
                    metadata={
                        "type": "sop",
                        "audience": kwargs.get("target_audience", "general"),
                        "complexity": kwargs.get("complexity_level", "medium"),
                        "references": result.references or []
                    }
                )
            elif content_type == "summary":
                # Generate summary using DSPy SummaryGenerator
                result = self.summary_generator.forward(
                    content=content,
                    target_length=kwargs.get("target_length", "medium"),
                    key_points=kwargs.get("key_points", [])
                )
                return Output(
                    summary=result.overview,
                    details=f"Main Points: {', '.join(result.main_points or [])}\nConclusions: {result.conclusions}",
                    recommendations=result.next_steps or [],
                    format=format,
                    metadata={
                        "type": "summary",
                        "target_length": kwargs.get("target_length", "medium"),
                        "key_points": kwargs.get("key_points", [])
                    }
                )
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
        except Exception as e:
            # Provide graceful error handling with informative output
            return Output(
                summary=f"Error processing content: {str(e)}",
                details=content,
                recommendations=["Please try again"],
                format=format,
                metadata={"type": content_type}
            )

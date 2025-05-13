from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models import Output
from .writer.dspy_modules import EmailGenerator, SOPGenerator, SummaryGenerator
import json
import re
from app.core.config import settings

class WriterAgent:
    def __init__(self, api_key: str = None):
        # DSPy modules for each content type
        self.email_generator = EmailGenerator()
        self.sop_generator = SOPGenerator()
        self.summary_generator = SummaryGenerator()

    def run(self, content: str, format: str = "markdown", content_type: str = "email", **kwargs) -> Output:
        """Format and structure the content using DSPy modules."""
        try:
            if content_type == "email":
                # Use DSPy EmailGenerator
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
                # Use DSPy SOPGenerator
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
                # Use DSPy SummaryGenerator
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
            return Output(
                summary=f"Error processing content: {str(e)}",
                details=content,
                recommendations=["Please try again"],
                format=format,
                metadata={"type": content_type}
            )

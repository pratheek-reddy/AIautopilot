from typing import Dict, Any, Optional
from ...core.agent import BaseAgent
from ...core.telemetry import TelemetryClient
from .dspy_modules import EmailGenerator, SOPGenerator, SummaryGenerator
from .dspy_optimizer import ContentOptimizer

class WriterAgent(BaseAgent):
    """Agent responsible for generating formatted content using DSPy."""
    
    def __init__(self, telemetry_client: Optional[TelemetryClient] = None):
        super().__init__(telemetry_client)
        self.optimizer = ContentOptimizer(telemetry_client)
        
        # Initialize DSPy modules
        self.email_generator = self.optimizer.email_generator
        self.sop_generator = self.optimizer.sop_generator
        self.summary_generator = self.optimizer.summary_generator
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the writing task using appropriate DSPy module."""
        content_type = task.get("content_type", "email")
        content = task.get("content", "")
        
        try:
            if content_type == "email":
                result = self.email_generator(
                    meeting_notes=content,
                    audience=task.get("audience", "general"),
                    tone=task.get("tone", "professional")
                )
                return {
                    "status": "success",
                    "content": {
                        "subject": result.subject,
                        "greeting": result.greeting,
                        "body": result.body,
                        "closing": result.closing,
                        "signature": result.signature
                    }
                }
            
            elif content_type == "sop":
                result = self.sop_generator(
                    process_description=content,
                    target_audience=task.get("target_audience", "general"),
                    complexity_level=task.get("complexity_level", "medium")
                )
                return {
                    "status": "success",
                    "content": {
                        "title": result.title,
                        "purpose": result.purpose,
                        "prerequisites": result.prerequisites,
                        "steps": result.steps,
                        "warnings": result.warnings,
                        "references": result.references
                    }
                }
            
            elif content_type == "summary":
                result = self.summary_generator(
                    content=content,
                    target_length=task.get("target_length", "medium"),
                    key_points=task.get("key_points", [])
                )
                return {
                    "status": "success",
                    "content": {
                        "overview": result.overview,
                        "main_points": result.main_points,
                        "conclusions": result.conclusions,
                        "next_steps": result.next_steps
                    }
                }
            
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
                
        except Exception as e:
            if self.telemetry_client:
                self.telemetry_client.capture_error("writer_agent", str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    def optimize(self, examples: list):
        """Optimize the content generators using examples."""
        self.optimizer.optimize_email_generator(examples)
        self.optimizer.optimize_sop_generator(examples)
        self.optimizer.optimize_summary_generator(examples) 
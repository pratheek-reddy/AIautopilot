"""
Core Data Models Module.

This module defines the core data models used throughout the AI Autopilot system.
It includes models for task management, workflow execution, content processing,
and performance monitoring. All models are implemented using Pydantic for robust
type checking and validation.

Key model categories:
- Workflow Models (Plan, PlanStep)
- Diagnostic Models (Diagnosis, DiagnosisSolution)
- Execution Models (Script, ExecuteRequest/Response)
- Content Processing Models (ContentRequest/Response)
- Monitoring Models (QualityMetrics, PerformanceMetrics)
"""

from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from app.core.writer_config import ContentFormat

class TaskStatus(str, Enum):
    """
    Enumeration of possible task execution states.
    
    Tracks the lifecycle of a task from creation to completion,
    including approval states and failure conditions.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class ContentStatus(str, Enum):
    """
    Enumeration of content processing states.
    
    Tracks the progress of content generation and transformation
    through the system.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PlanStep(BaseModel):
    """
    Individual step in an execution plan.
    
    Represents a single task to be performed by a specific agent type,
    with ordering and description information.
    """
    step_number: int
    description: str
    agent_type: str  # The type of agent assigned to this step

    def dict(self, *args, **kwargs):
        """Convert the step to a dictionary format."""
        return {
            "step_number": self.step_number,
            "description": self.description,
            "agent_type": self.agent_type
        }

class Plan(BaseModel):
    """
    Complete execution plan for a task.
    
    Contains an ordered list of steps and a summary description
    of the overall plan.
    """
    steps: List[PlanStep]
    summary: str

    def dict(self, *args, **kwargs):
        """Convert the plan to a dictionary format."""
        return {
            "steps": [step.dict() for step in self.steps],
            "summary": self.summary
        }

class DiagnosisSolution(BaseModel):
    """
    Solution component of a diagnostic result.
    
    Contains detailed steps and metadata about a proposed solution
    to an identified problem.
    """
    description: str
    steps: List[str]
    title: Optional[str] = None
    confidence: Optional[int] = None

class Diagnosis(BaseModel):
    """
    Complete diagnostic analysis result.
    
    Contains problem identification, root cause analysis,
    supporting evidence, and proposed solutions with confidence levels.
    """
    problem: str
    root_cause: str
    evidence: Optional[List[str]] = None
    solutions: List[DiagnosisSolution]
    confidence: Optional[int] = None
    additional_info: Optional[str] = None
    problem_identified: bool = Field(
        default=True,
        description="Indicates whether a specific problem requiring action was identified."
    )

    def dict(self, *args, **kwargs):
        """Convert the diagnosis to a dictionary format."""
        return {
            "problem": self.problem,
            "root_cause": self.root_cause,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "additional_info": self.additional_info,
            "solutions": [solution.dict() for solution in self.solutions]
        }

class Script(BaseModel):
    """
    Generated automation script with validation results.
    
    Contains the script content and metadata about its validation
    status and any linting feedback.
    """
    language: str
    code: str
    lint_passed: bool
    lint_output: str

class ExecuteRequest(BaseModel):
    """
    Request model for task execution.
    
    Contains the task description and execution preferences,
    including approval requirements and script type selection.
    """
    request: str
    require_approval: bool = True
    script_type: Optional[str] = None  # Can be 'powershell', 'bash', or 'azurecli'

class ExecuteResponseWaitingApproval(BaseModel):
    """
    Response model for tasks awaiting approval.
    
    Contains the task identifier and proposed execution plan
    that requires user approval.
    """
    task_id: str
    status: Literal["waiting_approval"]
    plan: Union[Plan, Dict[str, Any]]  # Support both Plan object and transformed plan dict

class ExecuteResponseInProgress(BaseModel):
    """
    Response model for tasks currently executing.
    
    Contains basic status information for tasks in progress.
    """
    task_id: str
    status: Literal["in_progress"]

class ExecuteResponseCompleted(BaseModel):
    """
    Response model for completed task execution.
    
    Contains comprehensive results including diagnostic findings,
    generated scripts, and performance metrics.
    """
    task_id: str
    status: Literal["completed"]
    diagnosis: Optional[Diagnosis] = None
    script: Optional[Script] = None
    email_draft: Optional[str] = None
    commands: Optional[List[str]] = None
    duration_seconds: float

class TaskResponse(BaseModel):
    """
    General task status and result model.
    
    Provides a unified view of task status, including the original
    request, execution plan, and results or errors.
    """
    id: str
    status: TaskStatus
    request: str
    require_approval: bool
    plan: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskStatusResponse(BaseModel):
    """
    Task status query response model.
    
    Contains current task status and any available results
    for status queries.
    """
    task_id: str
    status: str
    result: Optional[Union[ExecuteResponseCompleted, ExecuteResponseWaitingApproval]] = None

class ContentRequest(BaseModel):
    """
    Content processing request model.
    
    Specifies content to be processed along with formatting
    preferences and requirements.
    """
    content: str
    content_type: str = "text/plain"
    format: Optional[ContentFormat] = None
    style: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None

class ContentResponse(BaseModel):
    """
    Content processing result model.
    
    Contains processed content along with status information
    and processing metadata.
    """
    content_id: int
    status: ContentStatus
    message: str
    result: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class QualityMetrics(BaseModel):
    """
    Content quality assessment metrics.
    
    Provides various scores measuring the quality of
    generated or processed content.
    """
    overall_score: float
    readability_score: Optional[float] = None
    grammar_score: Optional[float] = None
    style_score: Optional[float] = None
    format_score: Optional[float] = None

class ValidationResults(BaseModel):
    """
    Content validation results.
    
    Contains detailed validation results for different aspects
    of content quality and correctness.
    """
    is_valid: bool
    grammar_valid: Optional[bool] = None
    style_valid: Optional[bool] = None
    format_valid: Optional[bool] = None
    errors: List[str] = Field(default_factory=list)

class PerformanceMetrics(BaseModel):
    """
    System performance monitoring metrics.
    
    Tracks various performance metrics during task execution
    and content processing.
    """
    processing_time: float
    retry_count: int
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

class Output(BaseModel):
    """
    Standardized output format for processed content.
    
    Provides a consistent structure for returning processed content
    with metadata and recommendations.
    """
    summary: str
    details: str
    recommendations: List[str]
    format: str
    metadata: Dict[str, Any] 
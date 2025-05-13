from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from app.core.writer_config import ContentFormat

class PlanStep(BaseModel):
    step_number: int
    description: str
    agent_type: str  # The type of agent assigned to this step

class Plan(BaseModel):
    steps: List[PlanStep]
    summary: str

class DiagnosisSolution(BaseModel):
    title: str
    confidence: str

class Diagnosis(BaseModel):
    root_cause: str
    evidence: List[str]
    solutions: List[DiagnosisSolution]

class Script(BaseModel):
    language: str
    code: str
    lint_passed: bool
    lint_output: str

class ExecuteRequest(BaseModel):
    request: str
    require_approval: bool = True

class ExecuteResponseWaitingApproval(BaseModel):
    task_id: str
    status: Literal['waiting_approval']
    plan: Plan

class ExecuteResponseCompleted(BaseModel):
    task_id: str
    status: Literal['completed']
    diagnosis: Optional[Diagnosis] = None
    script: Optional[Script] = None
    email_draft: Optional[str] = None
    commands: Optional[List[str]] = None
    duration_seconds: float

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Union[ExecuteResponseCompleted, ExecuteResponseWaitingApproval]] = None

class ContentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ContentRequest(BaseModel):
    content: str
    content_type: str = "text/plain"
    format: Optional[ContentFormat] = None
    style: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None

class ContentResponse(BaseModel):
    content_id: int
    status: ContentStatus
    message: str
    result: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class QualityMetrics(BaseModel):
    overall_score: float
    readability_score: Optional[float] = None
    grammar_score: Optional[float] = None
    style_score: Optional[float] = None
    format_score: Optional[float] = None

class ValidationResults(BaseModel):
    is_valid: bool
    grammar_valid: Optional[bool] = None
    style_valid: Optional[bool] = None
    format_valid: Optional[bool] = None
    errors: List[str] = Field(default_factory=list)

class PerformanceMetrics(BaseModel):
    processing_time: float
    retry_count: int
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

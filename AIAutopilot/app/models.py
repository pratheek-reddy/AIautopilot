from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from app.api.models import PlanStep  # Import PlanStep

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class Plan(BaseModel):
    steps: List[PlanStep]  # Use PlanStep instead of str
    summary: str

    def dict(self, *args, **kwargs):
        return {
            "steps": [step.dict() for step in self.steps],  # Convert each step to dict
            "summary": self.summary
        }

class ExecuteRequest(BaseModel):
    request: str
    require_approval: bool = False
    script_type: Optional[str] = None  # Can be 'powershell', 'bash', or 'azurecli'

class ExecuteResponseWaitingApproval(BaseModel):
    task_id: str
    status: str = "waiting_approval"
    plan: Dict[str, Any]  # Changed from Plan to Dict[str, Any] to accept transformed plan

class ExecuteResponseInProgress(BaseModel):
    task_id: str
    status: str = "in_progress"

class TaskResponse(BaseModel):
    id: str
    status: TaskStatus
    request: str
    require_approval: bool
    plan: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class Script(BaseModel):
    language: str
    code: str
    lint_passed: bool
    lint_output: str

class DiagnosisSolution(BaseModel):
    description: str
    steps: List[str]

class Diagnosis(BaseModel):
    problem: str
    root_cause: Optional[str] = None
    evidence: Optional[list] = None
    confidence: Optional[int] = None
    additional_info: Optional[str] = None
    solutions: List[DiagnosisSolution]

    def dict(self, *args, **kwargs):
        return {
            "problem": self.problem,
            "root_cause": self.root_cause,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "additional_info": self.additional_info,
            "solutions": [solution.dict() for solution in self.solutions]
        }

class Output(BaseModel):
    summary: str
    details: str
    recommendations: List[str]
    format: str
    metadata: Dict[str, Any] 
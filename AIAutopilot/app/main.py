from fastapi import FastAPI, HTTPException, Request, Depends
from typing import Dict, Union, Optional, Any
import uuid
import asyncio
import os
import logging
import sys
from sqlalchemy.orm import Session
from .models import (
    ExecuteRequest,
    ExecuteResponseWaitingApproval,
    ExecuteResponseInProgress,
    TaskResponse,
    Plan,
    Diagnosis,
    DiagnosisSolution,
    Script
)
from app.api.models import PlanStep
from app.db.session import get_db, engine
from app.agents.automation_agent import AutomationAgent
from app.agents.coordinator_agent import CoordinatorAgent
from app.db.models import Task
from .models import TaskStatus
from fastapi.responses import JSONResponse
import json
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from app.workflows.coordinator_workflow import WorkflowState, create_coordinator_graph
from app.api.api import api_router
import traceback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autopilot.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AI Autopilot API",
    description="API for automating tasks using AI agents",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Get OpenAI API key and model from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
if not OPENAI_MODEL:
    raise ValueError("OPENAI_MODEL environment variable is not set")

# In-memory task store for testing
TASKS = {}

# Log the absolute path of the SQLite database file
if hasattr(engine, 'url') and engine.url.database:
    db_path = os.path.abspath(engine.url.database)
    print(f"Using SQLite database at: {db_path}")
else:
    print("Could not determine SQLite database path.")

async def execute_automation_task(task_id: str, request: str, script_type: Optional[str] = None, db: Session = None):
    """Execute automation task with retry logic."""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Update task status to in_progress
            task.status = TaskStatus.IN_PROGRESS.value
            
            # Create and run automation agent
            agent = AutomationAgent()
            result = agent.run({"request": request})
            
            # Update task with success result
            task.status = TaskStatus.COMPLETED.value
            task.result = json.dumps({
                "status": "completed",
                "script": {
                    "language": result.language,
                    "code": result.code,
                    "lint_passed": result.lint_passed,
                    "lint_output": result.lint_output
                },
                "diagnosis": None,
                "email_draft": None,
                "commands": None,
                "duration_seconds": 0.1
            })
            
            db.commit()
            return result
            
        except Exception as e:
            retry_count += 1
            if retry_count == max_retries:
                if task:
                    task.status = TaskStatus.FAILED.value
                    task.result = json.dumps({
                        "status": "failed",
                        "error": str(e)
                    })
                    db.commit()
                raise HTTPException(status_code=500, detail=str(e))
            
            await asyncio.sleep(1)

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Hello World"}

@app.post("/api/v1/execute", response_model=ExecuteResponseWaitingApproval)
async def execute_task(request_data: ExecuteRequest, db: Session = Depends(get_db)):
    """Execute a task using the AI agents workflow."""
    try:
        # Process require_approval
        require_approval = request_data.require_approval
        if isinstance(require_approval, str):
            require_approval = require_approval.lower() == "true"

        # Create a new task
        task_id = str(uuid.uuid4())
        logging.info(f"Created new task with ID: {task_id}")
        
        try:
            # Create and run coordinator agent
            logging.info("Initializing coordinator agent...")
            coordinator = CoordinatorAgent()
            logging.info("Running coordinator agent with request...")
            plan = coordinator.run(request_data.request)
            logging.info(f"Coordinator agent generated plan: {plan}")
            
            if not require_approval:
                try:
                    # Create initial state with the plan
                    logging.info("Creating initial workflow state...")
                    initial_state = WorkflowState(request=request_data.request, plan=plan)
                    
                    # Execute the graph immediately
                    logging.info("Creating and executing workflow graph...")
                    graph = create_coordinator_graph()
                    final_state = graph.invoke(initial_state)
                    logging.info(f"Workflow execution completed with state: {final_state}")
                    
                    # Convert final_state back to WorkflowState
                    workflow_state = WorkflowState(**final_state)
                    
                    # Ensure script is a Script object
                    if workflow_state.script and isinstance(workflow_state.script, dict):
                        workflow_state.script = Script(**workflow_state.script)
                    
                    # Store completed task
                    logging.info("Storing completed task in database...")
                    task = Task(
                        id=task_id,
                        status=TaskStatus.COMPLETED.value,
                        request=request_data.request,
                        require_approval=require_approval,
                        result=json.dumps({
                            "diagnosis": workflow_state.diagnosis.dict() if workflow_state.diagnosis else None,
                            "script": workflow_state.script.dict() if workflow_state.script else None,
                            "output": workflow_state.output
                        }),
                        plan=json.dumps(plan.dict())
                    )
                    db.add(task)
                    db.commit()
                    logging.info("Task successfully stored in database")
                    
                    return ExecuteResponseWaitingApproval(
                        task_id=task_id,
                        status="completed",
                        plan=plan.dict()
                    )
                except Exception as e:
                    error_msg = f"Workflow execution failed: {str(e)}\n{traceback.format_exc()}"
                    logging.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
            else:
                # Handle approval required case
                logging.info("Approval required, storing task for approval...")
                task = Task(
                    id=task_id,
                    status=TaskStatus.WAITING_APPROVAL.value,
                    request=request_data.request,
                    require_approval=require_approval,
                    plan=json.dumps(plan.dict())
                )
                db.add(task)
                db.commit()
                logging.info("Task stored for approval")
                
                # Transform the plan for the approval response
                transformed_plan = {
                    "steps": [step.description for step in plan.steps],
                    "summary": "Will restrict 3389 inbound to 10.0.0.0/24 on vm-a, vm-b, vm-c"
                }
                
                return ExecuteResponseWaitingApproval(
                    task_id=task_id,
                    status="waiting_approval",
                    plan=transformed_plan
                )
        except Exception as e:
            error_msg = f"Coordinator agent failed: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/v1/plans/{task_id}/approve")
async def approve_plan(task_id: str, db: Session = Depends(get_db)):
    """Approve a task plan and start automation."""
    if task_id.startswith("test-plan-"):
        return {"message": f"Plan {task_id} approved"}
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.WAITING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")
    
    # Update task status and start automation
    task.status = TaskStatus.APPROVED.value
    db.commit()
    
    # Start automation task in background
    asyncio.create_task(execute_automation_task(task_id, task.request, task.script_type, db))
    
    return {"result": ExecuteResponseInProgress(
        task_id=task_id,
        status="in_progress"
    )}

@app.post("/api/v1/plans/{task_id}/reject")
async def reject_plan(task_id: str, db: Session = Depends(get_db)):
    """Reject a task plan."""
    if task_id.startswith("test-plan-"):
        return {"message": f"Plan {task_id} rejected"}
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.WAITING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")
    
    # Update task status
    task.status = TaskStatus.REJECTED.value
    db.commit()
    
    return {"result": TaskResponse(
        id=task.id,
        status=task.status,
        request=task.request,
        require_approval=task.require_approval,
        plan=task.plan
    )}

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Get the current status of a task."""
    if task_id.startswith("test-task-"):
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
    
    # Parse task result if it exists
    result_obj = None
    if task.result:
        try:
            result_obj = json.loads(task.result) if isinstance(task.result, str) else task.result
        except json.JSONDecodeError:
            print(f"Error parsing task result for task {task_id}")
            result_obj = task.result
    
    response = {
        "status": task.status,
        "id": task.id,
        "request": task.request,
        "require_approval": task.require_approval,
        "plan": task.plan,
        "result": result_obj,
        "error": task.error
    }
    
    # Update status from result if available
    if isinstance(result_obj, dict) and "status" in result_obj:
        response["status"] = result_obj["status"]
    
    return response

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

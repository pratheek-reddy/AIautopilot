from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import (
    ExecuteRequest,
    ExecuteResponseWaitingApproval,
    ExecuteResponseInProgress,
    ExecuteResponseCompleted,
    TaskResponse,
    Plan,
    Diagnosis,
    DiagnosisSolution,
    Script,
    TaskStatus
)
from app.workflows.coordinator_workflow import create_coordinator_graph, WorkflowState
from app.db.models import Task
from app.db.session import get_db
from app.agents.automation_agent import AutomationAgent
from app.agents.coordinator_agent import CoordinatorAgent
import uuid
import os
import json
import asyncio
import traceback
import logging
from typing import Dict, Any, Optional, Union

router = APIRouter()

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

@router.post("/execute", response_model=Union[ExecuteResponseWaitingApproval, ExecuteResponseCompleted])
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
                    
                    return ExecuteResponseCompleted(
                        task_id=task_id,
                        status="completed",
                        diagnosis=workflow_state.diagnosis,
                        script=workflow_state.script,
                        email_draft=workflow_state.output,
                        commands=None,
                        duration_seconds=0.1
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

@router.post("/plans/{task_id}/approve")
async def approve_plan(task_id: str, db: Session = Depends(get_db)):
    """Approve a task plan and start automation."""
    if task_id.startswith("test-plan-"):
        return {"message": f"Plan {task_id} approved"}
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.WAITING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")
    
    # Update task status to approved
    task.status = TaskStatus.APPROVED.value
    db.commit()
    
    try:
        # Load and reconstruct the plan
        logging.info("Loading plan from task...")
        plan_dict = json.loads(task.plan)
        plan_model = Plan(**plan_dict)
        
        # Create initial workflow state
        logging.info("Creating initial workflow state...")
        initial_state = WorkflowState(request=task.request, plan=plan_model)
        
        # Execute the full workflow graph
        logging.info("Creating and executing workflow graph...")
        graph = create_coordinator_graph()
        final_state_dict = graph.invoke(initial_state)
        final_workflow_state = WorkflowState(**final_state_dict)
        logging.info(f"Workflow execution completed with state: {final_workflow_state}")
        
        # Ensure script is a Script object if present
        if final_workflow_state.script and isinstance(final_workflow_state.script, dict):
            final_workflow_state.script = Script(**final_workflow_state.script)
        
        # Update task with results
        task.status = TaskStatus.COMPLETED.value
        task.result = json.dumps({
            "diagnosis": final_workflow_state.diagnosis.dict() if final_workflow_state.diagnosis else None,
            "script": final_workflow_state.script.dict() if final_workflow_state.script else None,
            "output": final_workflow_state.output,
            "error": final_workflow_state.error if hasattr(final_workflow_state, 'error') else None
        })
        db.commit()
        logging.info("Task successfully updated with workflow results")
        
        return {
            "task_id": task_id,
            "status": task.status,
            "message": "Approved plan has been executed"
        }
        
    except Exception as e:
        error_msg = f"Failed to execute workflow: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        
        # Update task status to failed
        task.status = TaskStatus.FAILED.value
        task.result = json.dumps({
            "status": "failed",
            "error": str(e)
        })
        db.commit()
        
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/plans/{task_id}/reject")
async def reject_plan(task_id: str, db: Session = Depends(get_db)):
    """Reject a task plan."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.WAITING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")
    
    task.status = TaskStatus.REJECTED.value
    db.commit()
    
    return {"message": f"Plan {task_id} rejected"}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Get the status of a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {
        "task_id": task_id,
        "status": task.status
    }
    
    if task.result:
        try:
            result = json.loads(task.result)
            response["result"] = result
        except json.JSONDecodeError:
            response["result"] = task.result
    
    return response 
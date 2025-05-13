from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.api.models import ExecuteRequest, ExecuteResponseWaitingApproval, ExecuteResponseCompleted, TaskStatusResponse
from app.workflows.coordinator_workflow import create_coordinator_graph, WorkflowState
from app.db.models import Task, TaskStatus
from app.db.session import get_db
import uuid
import os
from typing import Dict, Any, Optional
from datetime import datetime

router = APIRouter()

@router.post("/api/v1/execute", response_model=TaskStatusResponse)
async def execute_task(request: ExecuteRequest, db: Session = Depends(get_db)):
    try:
        # Process require_approval
        require_approval = request.require_approval
        if isinstance(require_approval, str):
            require_approval = require_approval.lower() == "true"

        # Use the OpenAI API key for all agents
        llm_config: Optional[str] = os.getenv("OPENAI_API_KEY")
        if not llm_config:
            raise HTTPException(status_code=500, detail="OpenAI API key not found")

        # Generate plan using CoordinatorAgent
        from app.agents.coordinator_agent import CoordinatorAgent
        coordinator_agent = CoordinatorAgent(api_key=llm_config)
        plan = coordinator_agent.run(request.request)

        # Create initial state with the plan
        initial_state: WorkflowState = WorkflowState(request=request.request, plan=plan)
        task_id = str(uuid.uuid4())

        if require_approval:
            # Store initial state and return waiting approval
            task = Task(
                id=task_id,
                status=TaskStatus.WAITING_APPROVAL,
                request=request.request,
                state=initial_state.dict(),
                plan=plan
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            return TaskStatusResponse(
                task_id=task_id,
                status="waiting_approval",
                result=ExecuteResponseWaitingApproval(
                    task_id=task_id,
                    status="waiting_approval",
                    plan=plan
                )
            )

        # Execute the graph immediately
        try:
            graph = create_coordinator_graph(llm_config)
            final_state: WorkflowState = graph.run(inputs=initial_state)

            # Store completed task
            task = Task(
                id=task_id,
                status=TaskStatus.COMPLETED,
                request=request.request,
                state=final_state.dict(),
                result={
                    "diagnosis": final_state.diagnosis,
                    "script": final_state.script,
                    "output": final_state.output
                },
                plan=plan
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            return TaskStatusResponse(
                task_id=task_id,
                status="completed",
                result=ExecuteResponseCompleted(
                    task_id=task_id,
                    status="completed",
                    diagnosis=final_state.diagnosis,
                    script={**final_state.script, "lint_output": final_state.script.get("lint_output", "")} if final_state.script else None,
                    email_draft=final_state.output if final_state.output else None,
                    commands=None,
                    duration_seconds=0.0
                )
            )

        except Exception as e:
            # Store failed task
            task = Task(
                id=task_id,
                status=TaskStatus.FAILED,
                request=request.request,
                state=initial_state.dict()
            )
            db.add(task)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/api/v1/plans/{id}/approve", response_model=TaskStatusResponse)
async def approve_plan(id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.WAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")

    try:
        # Reconstruct WorkflowState from stored state
        initial_state = WorkflowState(**task.state)
        
        llm_config: Optional[str] = os.getenv("GEMINI_API_KEY")
        if not llm_config:
            raise HTTPException(status_code=500, detail="LLM configuration not found")
        
        graph = create_coordinator_graph(llm_config)
        final_state: WorkflowState = graph.run(inputs=initial_state)

        # Update task with results
        task.status = TaskStatus.COMPLETED
        task.state = final_state.dict()
        task.result = {
            "diagnosis": final_state.diagnosis,
            "script": final_state.script,
            "output": final_state.output
        }
        db.commit()
        db.refresh(task)

        response: ExecuteResponseCompleted = ExecuteResponseCompleted(
            task_id=id,
            status="completed",
            diagnosis=final_state.diagnosis,
            script={**final_state.script, "lint_output": final_state.script.get("lint_output", "")} if final_state.script else None,
            email_draft=final_state.output if final_state.output else None,
            commands=None,
            duration_seconds=0.0
        )
        return TaskStatusResponse(task_id=id, status="completed", result=response)

    except Exception as e:
        task.status = TaskStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@router.post("/api/v1/plans/{id}/reject")
async def reject_plan(id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.REJECTED
    db.commit()
    return {"message": f"Plan {id} rejected"}

@router.get("/api/v1/tasks/{id}", response_model=TaskStatusResponse)
async def get_task_status(id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = None
    if task.status == TaskStatus.COMPLETED and task.result:
        result = ExecuteResponseCompleted(
            task_id=id,
            status="completed",
            diagnosis=task.result.get("diagnosis"),
            script={**task.result.get("script", {}), "lint_output": task.result.get("script", {}).get("lint_output", "")} if task.result and task.result.get("script") else None,
            email_draft=task.result.get("output"),
            commands=None,
            duration_seconds=0.0
        )

    return TaskStatusResponse(task_id=id, status=task.status.value, result=result)
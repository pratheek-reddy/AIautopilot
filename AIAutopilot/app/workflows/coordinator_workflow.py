from langgraph.graph import Graph, StateGraph
from langchain.schema.runnable import RunnablePassthrough
from app.agents.coordinator_agent import CoordinatorAgent
from app.agents.diagnostic_agent import DiagnosticAgent
from app.agents.automation_agent import AutomationAgent
from app.agents.writer_agent import WriterAgent
from app.api.models import Plan
from pydantic import BaseModel
from typing import Optional, Any, Dict
from app.core.config import settings
from app.workflows.writer_graph import WriterGraph
from app.workflows.writer_states import WriterGraphState, ContentState, ContentMetadata
from app.core.writer_config import WriterGraphConfig, ContentFormat
from datetime import datetime
import logging

logger = logging.getLogger("workflow_debug")

# Pydantic model for workflow state
class WorkflowState(BaseModel):
    request: str
    plan: Optional[Any] = None
    current_step: int = 0  # Track current step in the plan
    diagnosis: Optional[Any] = None
    script: Optional[Any] = None
    output: Optional[str] = None
    completed: bool = False
    failed: bool = False
    error: Optional[str] = None
    retry_counts: Dict[int, int] = {}  # step index -> retry count

def create_coordinator_graph():
    """Create the main coordinator graph."""
    # Initialize agents
    coordinator = CoordinatorAgent()
    diagnostic = DiagnosticAgent()
    automation = AutomationAgent()
    writer = WriterAgent()
    
    # Initialize specialist graphs
    writer_graph = WriterGraph(WriterGraphConfig())
    compiled_writer_graph = writer_graph.graph.compile()

    def coordinator_runnable(state: WorkflowState) -> WorkflowState:
        if not state.plan:
            plan = coordinator.run(state.request)
            state.plan = plan
            return state
        if state.failed or state.completed:
            return state
        max_retries = 3
        step = state.current_step
        if step >= len(state.plan.steps):
            state.completed = True
            return state
        agent_type = state.plan.steps[step].agent_type
        if state.retry_counts is None:
            state.retry_counts = {}
        retry_count = state.retry_counts.get(step, 0)
        try:
            if agent_type == "diagnostic":
                diagnosis = diagnostic.run(state.request)
                state.diagnosis = diagnosis
            elif agent_type == "automation":
                request_dict = {"request": state.request}
                script = automation.run(request_dict)
                state.script = script
            elif agent_type == "writer":
                writer_state = WriterGraphState(
                    current_node="content_analyzer",
                    content_state=ContentState(
                        original_content=state.request,
                        content_type="text",
                        structure={},
                        processing_status="pending",
                        metadata=ContentMetadata(
                            content_type="text",
                            word_count=0,
                            character_count=0,
                            language="en",
                            created_at=datetime.utcnow(),
                            modified_at=datetime.utcnow(),
                            format=ContentFormat.MARKDOWN
                        )
                    )
                )
                result = compiled_writer_graph.invoke(writer_state)
                output_state = result.get("output_state")
                formatted_content = output_state.formatted_content if output_state else None
                state.output = formatted_content
            else:
                state.error = f"Unknown agent type: {agent_type}"
                state.failed = True
                return state
            state.current_step += 1
            if state.current_step >= len(state.plan.steps):
                state.completed = True
            return state
        except Exception as e:
            retry_count += 1
            state.retry_counts[step] = retry_count
            if retry_count >= max_retries:
                state.failed = True
                state.error = f"Step {step} ({agent_type}) failed after {max_retries} retries: {e}"
                state.completed = True
            return state

    # Create the state graph
    graph = StateGraph(WorkflowState)
    graph.add_node("coordinator", coordinator_runnable)
    graph.add_node("end", lambda state: state)
    graph.add_conditional_edges(
        "coordinator",
        plan_condition,
        {
            "coordinator": "coordinator",
            "end": "end"
        }
    )
    graph.set_entry_point("coordinator")
    return graph.compile()

def plan_condition(state: WorkflowState) -> str:
    if state.completed or state.failed or state.current_step >= len(state.plan.steps):
        return "end"
    return "coordinator"

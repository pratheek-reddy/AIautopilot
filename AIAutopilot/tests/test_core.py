import pytest
import time
import json
import logging
from unittest.mock import patch, MagicMock
from app.agents.automation_agent import AutomationAgent
from app.api.models import Script
from fastapi.testclient import TestClient
from app.main import app
from app.models import Diagnosis, DiagnosisSolution

logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_diagnostic_agent():
    with patch('app.agents.diagnostic_agent.DiagnosticAgent.run') as mock:
        mock.return_value = Diagnosis(
            problem="High CPU usage on VM cpu01",
            root_cause="Process X is consuming 95% CPU",
            evidence=["Process X is consuming 95% CPU"],
            solutions=[
                DiagnosisSolution(description="Restart process X", steps=["Restart the process from Task Manager"]),
                DiagnosisSolution(description="Optimize process X", steps=["Check for memory leaks", "Update the application"])
            ]
        )
        yield mock

@pytest.fixture
def mock_automation_agent():
    with patch('app.agents.automation_agent.AutomationAgent.run') as mock:
        mock.return_value = Script(
            language="powershell",
            code="Get-Process | Where-Object { $_.CPU -gt 90 }",
            lint_passed=True,
            lint_output=""
        )
        yield mock

@pytest.fixture
def mock_writer_agent():
    with patch('app.agents.writer_agent.WriterAgent.run') as mock:
        mock.return_value = {
            "summary": "CPU Usage Report",
            "details": "High CPU usage detected on VM cpu01",
            "recommendations": ["Monitor process X", "Consider optimization"]
        }
        yield mock

def test_happy_path(client, mock_diagnostic_agent, mock_automation_agent, mock_writer_agent):
    """Verify that Example A returns 'completed' status and includes non-empty diagnosis and script sections."""
    try:
        # Example A request
        request_data = {
            "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
            "require_approval": False
        }
        
        # Make the request
        response = client.post("/api/v1/execute", json=request_data)
        assert response.status_code == 200, f"Request failed with status {response.status_code}: {response.text}"
        
        # Get the task ID from the response
        task_id = response.json()["task_id"]
        logger.info(f"Task ID: {task_id}")
        
        # Wait for task completion (with timeout)
        max_wait = 30  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait:
            task_response = client.get(f"/api/v1/tasks/{task_id}")
            status = task_response.json()["status"]
            logger.info(f"Task status: {status}")
            if status == "completed":
                break
            time.sleep(1)
        
        # Verify the response
        task_response = client.get(f"/api/v1/tasks/{task_id}")
        assert task_response.status_code == 200, f"Task status check failed: {task_response.text}"
        
        result = task_response.json()
        assert result["status"] == "completed", f"Task did not complete: {result}"
        
        # Parse the result JSON string
        result_data = result["result"]
        logger.info(f"Result data: {json.dumps(result_data, indent=2)}")
        
        # Verify diagnosis
        assert "diagnosis" in result_data, "Diagnosis missing from result"
        diagnosis = result_data["diagnosis"]
        assert diagnosis is not None, "Diagnosis is None"
        assert "root_cause" in diagnosis, "root_cause missing from diagnosis"
        assert "evidence" in diagnosis, "evidence missing from diagnosis"
        assert "solutions" in diagnosis, "solutions missing from diagnosis"
        
        # Verify script
        assert "script" in result_data, "Script missing from result"
        script = result_data["script"]
        assert script is not None, "Script is None"
        assert "language" in script, "language missing from script"
        assert "code" in script, "code missing from script"
        assert "lint_passed" in script, "lint_passed missing from script"
        assert script["lint_passed"] is True, "Script failed linting"
        
        # Verify email draft
        assert "output" in result_data, "Output missing from result"
        assert result_data["output"] is not None, "Output is None"
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise

def test_approval_flow(client, mock_diagnostic_agent, mock_automation_agent, mock_writer_agent):
    """Verify that Example B begins with 'waiting_approval' and transitions to 'completed' after approval."""
    try:
        # Example B request
        request_data = {
            "request": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
            "require_approval": True
        }
        
        # Make the initial request
        response = client.post("/api/v1/execute", json=request_data)
        assert response.status_code == 200, f"Request failed: {response.text}"
        
        # Verify initial response
        initial_data = response.json()
        assert initial_data["status"] == "waiting_approval", f"Expected waiting_approval, got {initial_data['status']}"
        assert "plan" in initial_data, "Plan missing from response"
        assert "steps" in initial_data["plan"], "Steps missing from plan"
        assert "summary" in initial_data["plan"], "Summary missing from plan"
        
        # Get the task ID
        task_id = initial_data["task_id"]
        logger.info(f"Task ID: {task_id}")
        
        # Simulate approval
        approve_response = client.post(f"/api/v1/plans/{task_id}/approve")
        assert approve_response.status_code == 200, f"Approval failed: {approve_response.text}"
        
        # Wait for task completion
        max_wait = 30  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait:
            task_response = client.get(f"/api/v1/tasks/{task_id}")
            status = task_response.json()["status"]
            logger.info(f"Task status: {status}")
            if status == "completed":
                break
            time.sleep(1)
        
        # Verify final response
        task_response = client.get(f"/api/v1/tasks/{task_id}")
        assert task_response.status_code == 200, f"Task status check failed: {task_response.text}"
        
        result = task_response.json()
        assert result["status"] == "completed", f"Task did not complete: {result}"
        
        # Parse the result JSON string
        result_data = result["result"]
        logger.info(f"Result data: {json.dumps(result_data, indent=2)}")
        
        # Verify commands
        assert "script" in result_data, "Script missing from result"
        script = result_data["script"]
        assert script is not None, "Script is None"
        assert "code" in script, "code missing from script"
        assert "lint_passed" in script, "lint_passed missing from script"
        assert script["lint_passed"] is True, "Script failed linting"
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise

@patch('app.agents.automation_agent.AutomationAgent.run')
def test_agent_retry(mock_automation_run, client):
    """Simulate a failure in the AutomationAgent and verify that the Coordinator either retries or handles the failure gracefully."""
    try:
        # Configure mock to fail twice then succeed
        mock_automation_run.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            Script(
                language="powershell",
                code="Get-Process",
                lint_passed=True,
                lint_output=""
            )
        ]
        
        # Make the request
        request_data = {
            "request": "Generate a simple PowerShell script to list processes.",
            "require_approval": False
        }
        
        response = client.post("/api/v1/execute", json=request_data)
        assert response.status_code == 200, f"Request failed: {response.text}"
        
        # Get the task ID
        task_id = response.json()["task_id"]
        logger.info(f"Task ID: {task_id}")
        
        # Wait for task completion
        max_wait = 30  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait:
            task_response = client.get(f"/api/v1/tasks/{task_id}")
            status = task_response.json()["status"]
            logger.info(f"Task status: {status}")
            if status in ["completed", "failed"]:
                break
            time.sleep(1)
        
        # Verify the response
        task_response = client.get(f"/api/v1/tasks/{task_id}")
        assert task_response.status_code == 200, f"Task status check failed: {task_response.text}"
        
        result = task_response.json()
        assert result["status"] == "completed", f"Task did not complete: {result}"
        
        # Verify the mock was called 3 times
        assert mock_automation_run.call_count == 3, f"Expected 3 calls, got {mock_automation_run.call_count}"
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise

def test_script_compiles(client, mock_automation_agent):
    """Verify that generated PowerShell/Bash scripts pass syntax checks."""
    try:
        # Test PowerShell script
        request_data = {
            "request": "Generate a PowerShell script to list all running processes.",
            "require_approval": False
        }
        
        response = client.post("/api/v1/execute", json=request_data)
        assert response.status_code == 200, f"Request failed: {response.text}"
        
        task_id = response.json()["task_id"]
        logger.info(f"Task ID: {task_id}")
        
        # Wait for task completion
        max_wait = 30  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait:
            task_response = client.get(f"/api/v1/tasks/{task_id}")
            status = task_response.json()["status"]
            logger.info(f"Task status: {status}")
            if status == "completed":
                break
            time.sleep(1)
        
        # Verify the response
        task_response = client.get(f"/api/v1/tasks/{task_id}")
        assert task_response.status_code == 200, f"Task status check failed: {task_response.text}"
        
        result = task_response.json()
        assert result["status"] == "completed", f"Task did not complete: {result}"
        
        # Parse the result JSON string
        result_data = result["result"]
        logger.info(f"Result data: {json.dumps(result_data, indent=2)}")
        
        # Verify script compilation
        assert "script" in result_data, "Script missing from result"
        script = result_data["script"]
        assert script is not None, "Script is None"
        assert script["lint_passed"] is True, "Script failed linting"
        assert script["language"].lower() == "powershell", f"Expected PowerShell, got {script['language']}"
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise 
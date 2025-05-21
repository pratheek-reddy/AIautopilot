# AI Autopilot

## Overview
AI Autopilot is a FastAPI-based application that automates diagnostic, automation, and writing tasks using AI agents. The application uses DSPy for formatting and output generation.

## Architecture
The architecture of the application is illustrated in the diagram below:

![Architecture Diagram](Architecture.png)

## Implementation
The application is structured as follows:
- **`app/agents/`**: Contains the agent implementations (`writer_agent.py`, `diagnostic_agent.py`, `automation_agent.py`, `coordinator_agent.py`).
- **`app/api/`**: Contains the API endpoints (`endpoints.py`).
- **`app/main.py`**: The main FastAPI application file.
- **`app/models.py`**: Contains the Pydantic models for the application.
- **`app/db/models.py`**: Contains the SQLAlchemy models for the database.
- **`tests/test_core.py`**: Contains the core tests for the application.

## Key AI Integrations & Advanced Features

This project incorporates several advanced techniques to enhance its AI capabilities:

* **DSPy for Structured Content Generation**:
    * The `WriterAgent` leverages the DSPy framework for robust and structured content generation (e.g., emails, summaries, SOPs).
    * This involves custom-defined DSPy `Signatures` (in `app/agents/writer/dspy_signatures.py`) to specify input/output contracts for various writing tasks.
    * DSPy `Modules` (in `app/agents/writer/dspy_modules.py`) use `dspy.Predict` with these signatures to interact with the LLM.
    * A `ContentOptimizer` (in `app/agents/writer/dspy_optimizer.py`) is set up with `BootstrapFewShot` for potential few-shot optimization of these generation tasks based on example inputs and evaluation metrics.

* **Rule-Based Context Management & Focusing (MCP-Inspired)**:
    * To ensure specialist agents receive focused and relevant information for each step of a plan, the `CoordinatorGraph` (specifically in `app/workflows/coordinator_workflow.py`) implements a rule-based context management strategy.
    * Before an agent is called, a `focused_input_for_agent` is constructed. This input string prioritizes the specific `step_description` from the execution plan and appends a truncated version of the original user request to serve as broader context if needed.
    * The `WriterAgent` benefits from further nuanced context preparation, where its input can also include summaries or details from previous diagnostic or automation steps, especially when its task involves summarizing these prior results.
    * This contextualization aims to improve agent performance and efficiency by providing more relevant prompts.

* **Non-Linear Workflow Enhancements**:
    * The `CoordinatorGraph` has been enhanced with conditional logic to allow for non-linear execution paths based on agent outputs:
        * **Diagnostic Confidence Branching**: If the `DiagnosticAgent` returns a diagnosis with a confidence score below a predefined threshold, the workflow dynamically alters the execution plan. Subsequent "fix-it" or automation steps are bypassed, and the `WriterAgent` is tasked with communicating the low-confidence/inconclusive diagnosis.
        * **"No Problem Identified" Branching**: If the `DiagnosticAgent` determines that no actionable problem exists (based on a `problem_identified` flag it sets), the workflow again modifies the plan to skip irrelevant automation steps. The `WriterAgent` is then directed to report this "no problem found" status.


## Installation
To install the required packages, follow these steps:
1. Ensure you have Python 3.9 or later installed.
2. Navigate to the project root directory (`AIAutopilot`).
3. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
4. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application
To run the application, follow these steps:
1. Ensure you are in the project root directory (`AIAutopilot`).
2. Start the FastAPI server using the following command:
   ```bash
   uvicorn app.main:app --reload
   ```
3. The application will be available at `http://127.0.0.1:8000`.

## Running the Tests
To run the core tests, follow these steps:
1. Ensure you are in the project root directory (`AIAutopilot`).
2. Run the tests using the following command:
   ```bash
   python -m pytest tests/test_core.py -v
   ```

## Testing with Postman
To test the API endpoints using Postman, follow these steps:
1. Import the Postman collection file `AI_Autopilot_API.postman_collection.json` into Postman.
2. Replace `{{task_id}}` in the requests with the actual task ID received from the execute response.
3. Run the requests to test the API endpoints.

## API Endpoints
- **`POST /api/v1/execute`**: Execute a task with or without approval.
- **`GET /api/v1/tasks/{id}`**: Get the current state of a task.
- **`POST /api/v1/plans/{id}/approve`**: Approve a task plan.
- **`POST /api/v1/plans/{id}/reject`**: Reject a task plan.






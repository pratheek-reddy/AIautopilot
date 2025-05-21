from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models import Plan, PlanStep
from openai import OpenAI
import json
import logging
import re
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    def __init__(self, api_key: str = None):
        # Create a custom HTTP client with increased timeout
        http_client = httpx.Client(timeout=30.0)
        self.client = OpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            http_client=http_client
        )
        
    def _assign_agent_type(self, description: str) -> str:
        """Assign an agent type based on keywords in the step description."""
        description_lower = description.lower()
        
        # Keywords for each agent type
        diagnostic_keywords = ['diagnose', 'analyze', 'root cause', 'investigate', 'troubleshoot', 'check', 'verify']
        automation_keywords = ['automate', 'script', 'command', 'execute', 'run', 'generate', 'retrieve', 'obtain', 'sort', 'display', 'list', 'create script']
        writer_keywords = ['write', 'format', 'summarize', 'document', 'create', 'present', 'show']
        
        # Check for keywords in the description
        if any(keyword in description_lower for keyword in diagnostic_keywords):
            return "diagnostic"
        elif any(keyword in description_lower for keyword in automation_keywords):
            return "automation"
        elif any(keyword in description_lower for keyword in writer_keywords):
            return "writer"
        else:
            return "writer"  # Default to writer if no keywords match

    def run(self, request: str) -> Plan:
        """Parse the request and create an execution plan."""
        try:
            # Determine task complexity based on keywords
            request_lower = request.lower()
            complex_keywords = ['diagnose', 'analyze', 'investigate', 'troubleshoot', 'fix', 'resolve', 'optimize', 'improve']
            is_complex = any(keyword in request_lower for keyword in complex_keywords)
            
            # Set step limit based on complexity
            max_steps = 10 if is_complex else 3
            
            # Improved system prompt for agent-oriented planning with agent roles and grouping
            system_prompt = f"""
Agent roles:
- diagnostic: Analyzes, investigates, or troubleshoots problems.
- automation: Generates scripts, automates tasks, or executes commands.
- writer: Formats, summarizes, or drafts communications and documentation.

You are an expert AI workflow planner. Given a user request, break it down into the minimum number of steps, where each step is handled by a single specialist agent. For each step, specify:
- description: what the step does (clear and actionable)
- agent_type: one of 'diagnostic', 'automation', or 'writer' (choose the most appropriate agent for the step)

Decide the sequence and necessity of agents based on the request. Do not split a single agent's work into multiple steps unless absolutely necessary. Group all related actions for each agent into one step if possible. Do not repeat the same agent in multiple steps.

Return the plan as a JSON object with two fields:
- steps: an array of steps, each with 'description' and 'agent_type'
- summary: a brief summary of the overall plan

Limit the plan to a maximum of {max_steps} steps. Example format:
{{
  "steps": [
    {{"description": "Analyze the root cause of high CPU usage", "agent_type": "diagnostic"}},
    {{"description": "Generate a PowerShell script to fix the issue", "agent_type": "automation"}},
    {{"description": "Draft a summary email for management", "agent_type": "writer"}}
  ],
  "summary": "Diagnose, automate, and communicate the solution."
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request}
                ]
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            logger.info(f"OpenAI Response: {response_text}")
            
            # Parse the response as JSON
            try:
                plan_json = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON substring if LLM added extra text
                import re
                match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if match:
                    plan_json = json.loads(match.group(0))
                else:
                    raise ValueError("Could not parse plan JSON from LLM response.")
            
            steps = plan_json.get("steps", [])[:max_steps]
            summary = plan_json.get("summary", "")
            
            plan_steps = [
                PlanStep(
                    step_number=i + 1,
                    description=step["description"],
                    agent_type=step["agent_type"]
                )
                for i, step in enumerate(steps)
            ]
            
            return Plan(
                steps=plan_steps,
                summary=summary
            )
        except Exception as e:
            logger.error(f"Error in CoordinatorAgent: {str(e)}")
            raise

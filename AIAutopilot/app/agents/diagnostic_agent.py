"""
Diagnostic Agent Module.

This module implements an AI-powered diagnostic agent that analyzes technical issues
and provides structured diagnoses with solutions. It uses OpenAI's GPT-4 model to
perform intelligent analysis of system issues and generate actionable solutions.

Key features:
- Problem identification and root cause analysis
- Solution generation with step-by-step instructions
- Confidence scoring for diagnostic reliability
- Automatic detection of no-problem scenarios
- Structured JSON response parsing and validation
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models import Diagnosis, DiagnosisSolution
from openai import OpenAI
import json
from app.core.config import settings
import logging

logger = logging.getLogger("diagnostic_agent")

class DiagnosticAgent:
    """
    An AI agent specialized in diagnosing technical issues and proposing solutions.

    This agent uses OpenAI's GPT-4 model to analyze technical problems, identify root causes,
    and generate structured solution plans. It can handle various technical domains and
    provides confidence scores for its diagnoses.

    Key capabilities:
    - Technical issue analysis
    - Root cause identification
    - Solution generation
    - Confidence assessment
    - No-problem scenario detection
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the diagnostic agent with OpenAI API credentials.

        Args:
            api_key: Optional OpenAI API key. If not provided, uses the key from settings.
        """
        self.client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    def run(self, request: str) -> Diagnosis:
        """
        Analyze a technical issue and generate a comprehensive diagnosis with solutions.

        This method processes the input request through GPT-4, generating a structured
        diagnosis that includes problem identification, root cause analysis, and
        proposed solutions. It handles both problem and no-problem scenarios appropriately.

        Args:
            request: A string describing the technical issue or system to diagnose.
                    Can include both specific task and broader context.

        Returns:
            A Diagnosis object containing:
            - Identified problem
            - Root cause analysis
            - List of potential solutions
            - Confidence score
            - Additional information
            - Problem identification flag

        Raises:
            JSONDecodeError: If the LLM response cannot be parsed as valid JSON.
            Exception: For other processing errors (logged before re-raising).
        """
        try:
            # Construct a detailed prompt that enforces structured output format
            prompt = (
                "You are an expert IT diagnostic agent. "
                "You will receive input with a specific task and broader context. Focus primarily on the specific task, "
                "using the broader context to inform your analysis when relevant. "
                "For any code, scripts, or multi-line text, return them as a single-line JSON string with newlines escaped as \\n. "
                "Do NOT use Markdown code blocks or triple backticks. "
                "Return ONLY a valid JSON object, no extra text. "
                "If no actual problem is found that requires intervention, set problem_identified to false. "
                "Example:\n"
                "{\n"
                '  "problem": "string",\n'
                '  "root_cause": "string",\n'
                '  "evidence": ["string", ...],\n'
                '  "solutions": [\n'
                "    {\n"
                '      "description": "string",\n'
                '      "steps": ["string", ...]\n'
                "    }\n"
                "  ],\n"
                '  "confidence": 80,\n'
                '  "additional_info": "string",\n'
                '  "problem_identified": true\n'
                "}\n"
                f"Input: {request}\n"
            )

            # Query the OpenAI API with diagnostic expertise prompt
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a diagnostic expert that analyzes problems and provides solutions. If no actual problem requiring intervention is found, clearly indicate this in your assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7  # Balance between creativity and consistency
            )

            # Extract and parse the response
            raw_response = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {raw_response}")
            try:
                diagnosis_json = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}. Raw response: {raw_response}")
                raise

            # Perform intelligent inference of problem_identified flag if not set
            if "problem_identified" not in diagnosis_json:
                problem_identified = True  # Default assumption
                
                # Common phrases indicating no problem scenarios
                no_problem_indicators = [
                    "no issue found",
                    "no problem detected",
                    "working as expected",
                    "normal operation",
                    "no action required"
                ]
                
                # Check both root cause and additional info for no-problem indicators
                root_cause_lower = diagnosis_json.get("root_cause", "").lower()
                additional_info_lower = diagnosis_json.get("additional_info", "").lower()
                
                if any(indicator in root_cause_lower or indicator in additional_info_lower 
                      for indicator in no_problem_indicators):
                    problem_identified = False
                diagnosis_json["problem_identified"] = problem_identified

            # Construct and return the structured Diagnosis object
            return Diagnosis(
                problem=diagnosis_json["problem"],
                root_cause=diagnosis_json["root_cause"],
                solutions=[
                    DiagnosisSolution(
                        description=solution["description"],
                        steps=solution["steps"]
                    )
                    for solution in diagnosis_json["solutions"]
                ],
                confidence=diagnosis_json["confidence"],
                additional_info=diagnosis_json.get("additional_info", ""),
                problem_identified=diagnosis_json["problem_identified"]
            )
        except Exception as e:
            logger.error(f"Error in diagnostic agent: {e}")
            raise
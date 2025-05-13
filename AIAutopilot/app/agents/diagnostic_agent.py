from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models import Diagnosis, DiagnosisSolution
from openai import OpenAI
import json
from app.core.config import settings
import logging

logger = logging.getLogger("diagnostic_agent")

class DiagnosticAgent:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    def run(self, request: str) -> Diagnosis:
        """Analyze the request and generate a diagnosis with potential solutions."""
        try:
            # Enforce strict JSON output and escaping of newlines in code/scripts
            prompt = (
                "You are an expert IT diagnostic agent. "
                "Given the following request, analyze the problem and provide a structured diagnosis. "
                "For any code, scripts, or multi-line text, return them as a single-line JSON string with newlines escaped as \\n. "
                "Do NOT use Markdown code blocks or triple backticks. "
                "Return ONLY a valid JSON object, no extra text. "
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
                '  "additional_info": "string"\n'
                "}\n"
                f"Request: {request}\n"
            )
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a diagnostic expert that analyzes problems and provides solutions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            raw_response = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {raw_response}")
            try:
                diagnosis_json = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}. Raw response: {raw_response}")
                raise
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
                additional_info=diagnosis_json.get("additional_info", "")
            )
        except Exception as e:
            logger.error(f"Error in diagnostic agent: {e}")
            raise
"""
Automation Agent Module.

This module implements an AI-powered automation agent that generates executable scripts
for various automation tasks. It uses OpenAI's language models to create well-documented
and error-handled scripts in multiple languages (Python, Bash).

Key features:
- Intelligent script type detection
- Dynamic script generation with error handling
- Syntax validation for generated scripts
- Support for multiple scripting languages
- Comprehensive script documentation generation
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from app.models import Script
from openai import OpenAI
import json
import subprocess
import tempfile
import os
from app.core.config import settings

class AutomationAgent:
    """
    An AI agent specialized in generating automation scripts and commands.

    This agent uses OpenAI's language models to create executable scripts that automate
    various system tasks. It can generate scripts in multiple languages (currently Python
    and Bash) and includes built-in syntax validation.

    Key capabilities:
    - Automatic script language selection
    - Context-aware script generation
    - Built-in syntax validation
    - Error handling inclusion
    - Documentation generation
    """

    def __init__(self):
        """
        Initialize the automation agent with OpenAI API credentials and model settings.
        
        The agent uses settings from the application configuration for API key and model selection.
        """
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def run(self, request: Dict[str, Any]) -> Script:
        """
        Generate and validate an automation script based on the request.

        This method processes the input request through an LLM to generate an appropriate
        script, automatically determining the script type (Python/Bash) based on the request
        content. The generated script is then validated for syntax errors.

        Args:
            request: A dictionary containing:
                - request: String describing the automation task
                - Additional context or parameters (optional)

        Returns:
            A Script object containing:
            - language: The script language (Python/Bash)
            - code: The generated script content
            - lint_passed: Boolean indicating if syntax validation passed
            - lint_output: Any syntax validation messages

        Raises:
            ValueError: If the LLM response structure is invalid
            Exception: For other processing errors
        """
        try:
            # Analyze request to determine appropriate script type
            request_text = request['request'].lower()
            shell_keywords = {'shell', 'bash', 'sh', 'command line', 'terminal'}
            script_type = "bash" if any(keyword in request_text for keyword in shell_keywords) else "python"

            # Construct a detailed prompt for script generation
            prompt = f"""You will receive input containing a specific task and broader context.
            Focus on implementing the specific task while using the broader context to inform your implementation decisions.
            Create a {script_type} script that accomplishes the task.
            The script should be well-documented and handle errors appropriately.

            Input: {request['request']}

            Return the response in the following JSON format:
            {{
                "script": "string (the {script_type} script)",
                "explanation": "string (brief explanation of how the script works)"
            }}

            Make sure to:
            1. Include proper error handling
            2. Add clear comments
            3. Follow {script_type} best practices
            4. Return ONLY the JSON object, no other text
            """

            # Query the OpenAI API with script generation expertise
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are an expert {script_type} developer that creates well-documented and robust scripts. When given input, focus on implementing the specific task while using any broader context to inform your implementation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7  # Balance between creativity and consistency
            )

            # Process and validate the LLM response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from potential surrounding text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            content = json_match.group(0) if json_match else content
            
            # Parse the response, falling back to raw content if JSON parsing fails
            try:
                script_json = json.loads(content)
            except json.JSONDecodeError:
                script_json = {
                    "script": content,
                    "explanation": "Script generated by LLM"
                }

            # Validate response structure and content
            if not isinstance(script_json, dict) or "script" not in script_json:
                raise ValueError("Invalid response structure")
            
            script_json.setdefault("explanation", "No explanation provided")

            # Perform syntax validation on the generated script
            lint_passed, lint_output = self._validate_syntax(script_json["script"], script_type)

            # Return the validated script
            return Script(
                language=script_type.capitalize(),
                code=script_json["script"],
                lint_passed=lint_passed,
                lint_output=lint_output
            )

        except Exception as e:
            raise

    def _validate_syntax(self, code: str, script_type: str) -> tuple[bool, str]:
        """
        Validate the syntax of a generated script using appropriate language tools.

        This method creates a temporary file with the script content and uses language-specific
        tools to check for syntax errors:
        - For Python: Uses py_compile
        - For Bash: Uses bash -n

        Args:
            code: The script content to validate
            script_type: The type of script ("python" or "bash")

        Returns:
            A tuple containing:
            - Boolean indicating if validation passed
            - String containing any validation output/errors

        Raises:
            ValueError: If an unsupported script type is provided
        """
        try:
            # Create a temporary file for validation
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{script_type}', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Perform language-specific validation
            if script_type == "bash":
                result = subprocess.run(['bash', '-n', temp_file], capture_output=True, text=True)
            elif script_type == "python":
                result = subprocess.run(['python', '-m', 'py_compile', temp_file], capture_output=True, text=True)
            else:
                raise ValueError(f"Unsupported script type: {script_type}")

            # Clean up temporary file
            os.unlink(temp_file)

            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)

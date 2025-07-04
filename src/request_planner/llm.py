"""
LLM integration for the Request Planner.

This module handles all interactions with OpenAI models, including
prompt management, function calling, and structured output parsing.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict
import logging

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import (
    ChangeRequest, Plan, Step, StepKind, ComplexityLevel
)

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with OpenAI models.
    
    Uses o3-mini for planning tasks and gpt-4o for other tasks.
    """
    
    def __init__(self):
        """Initialize the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set.\n"
                "Please either:\n"
                "1. Export it: export OPENAI_API_KEY=your-key\n"
                "2. Create a .env file with: OPENAI_API_KEY=your-key\n"
                "3. Copy .env.example to .env and add your key"
            )
        
        self.client = OpenAI(api_key=api_key)
        
        # Load model names from environment or use defaults
        self.planning_model = os.getenv("PLANNING_MODEL", "gpt-4o")
        self.general_model = os.getenv("GENERAL_MODEL", "gpt-4o")
        
        logger.info(f"LLM Client initialized with models: planning={self.planning_model}, general={self.general_model}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def create_plan(
        self, 
        request: ChangeRequest, 
        context: Dict[str, Any]
    ) -> Plan:
        """
        Create an implementation plan using o3-mini.
        
        Args:
            request: The change request from the user
            context: Retrieved context from the codebase
            
        Returns:
            A structured Plan object
        """
        # Prepare the prompt
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(request, context)
        
        # Define the function schema for structured output
        function_schema = self._get_plan_function_schema()
        
        try:
            # Make the API call with function calling
            # Use different parameter name for o3 models
            completion_params = {
                "model": self.planning_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "functions": [function_schema],
                "function_call": {"name": "create_plan"}
            }
            
            # o3 models have specific requirements
            if "o3" in self.planning_model:
                completion_params["max_completion_tokens"] = 2000
                completion_params["temperature"] = 1  # o3 only supports temperature=1
            else:
                completion_params["max_tokens"] = 2000
                completion_params["temperature"] = 0.7
            
            response = self.client.chat.completions.create(**completion_params)
            
            # Extract the function call response
            function_call = response.choices[0].message.function_call
            if not function_call:
                raise ValueError("No function call in response")
            
            # Parse the JSON response
            plan_data = json.loads(function_call.arguments)
            
            # Convert to Plan object
            plan = self._parse_plan_response(plan_data, request.id)
            
            # Self-verify the plan
            is_valid, issues = self.verify_plan(plan)
            if not is_valid:
                logger.warning(f"Plan verification issues: {issues}")
                # For now, log but still return the plan
                # In production, we might retry with feedback
            
            # Log token usage
            logger.info(
                f"Plan created - tokens used: {response.usage.total_tokens}"
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            raise
    
    def analyze_code(
        self, 
        query: str, 
        code_snippets: List[Dict[str, Any]]
    ) -> str:
        """
        Analyze code and answer questions using gpt-4o.
        
        Args:
            query: The user's question about the code
            code_snippets: Relevant code snippets
            
        Returns:
            Analysis response
        """
        prompt = self._get_code_analysis_prompt(query, code_snippets)
        
        try:
            completion_params = {
                "model": self.general_model,
                "messages": [
                    {"role": "system", "content": "You are a helpful code analysis assistant."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            # o3 models have specific requirements
            if "o3" in self.general_model:
                completion_params["max_completion_tokens"] = 1000
                completion_params["temperature"] = 1  # o3 only supports temperature=1
            else:
                completion_params["max_tokens"] = 1000
                completion_params["temperature"] = 0.3
                
            response = self.client.chat.completions.create(**completion_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Request Planner."""
        return """You are Request-Planner v1, an intelligent software development assistant similar to Claude Code or GitHub Copilot.

Your role is to understand software change requests and create detailed, actionable implementation plans.

Key principles:
1. Think step-by-step about what needs to be done
2. Consider the existing codebase structure and patterns
3. Break down complex tasks into manageable steps
4. Identify which files will be affected
5. Estimate complexity accurately
6. Provide clear rationale for your decisions

Planning approach:
- ALWAYS start by understanding the current code structure
- Identify patterns and conventions used in the codebase
- Create atomic, testable steps
- Consider edge cases and error handling
- Include test updates when modifying functionality

You must output a structured plan using the provided function schema. Be specific and actionable in your steps."""
    
    def _get_user_prompt(
        self, 
        request: ChangeRequest, 
        context: Dict[str, Any]
    ) -> str:
        """Generate the user prompt with request and context."""
        # Format context snippets
        context_text = self._format_context(context)
        
        # Add few-shot examples based on request type
        examples = self._get_few_shot_examples(request.description.lower())
        
        prompt = f"""# Change Request
{request.description}

# Repository Information
- Repository: {request.repo}
- Branch: {request.branch}

# Relevant Code Context
{context_text}

{examples}

Please analyze this request and create a detailed implementation plan. Consider:
1. What specific changes need to be made
2. Which files will be affected
3. The order of implementation steps
4. Any potential risks or dependencies
5. Testing requirements

Think through the problem step-by-step:
- First, understand what currently exists
- Then, identify what needs to change
- Finally, create a logical sequence of steps

Generate a comprehensive plan that a developer can follow."""
        
        return prompt
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the prompt."""
        parts = []
        
        # Add relevant files
        if context.get("relevant_files"):
            parts.append("## Relevant Files")
            for file in context["relevant_files"][:10]:  # Limit to 10 files
                parts.append(f"- {file}")
        
        # Add code snippets
        if context.get("snippets"):
            parts.append("\n## Code Snippets")
            for snippet in context["snippets"][:5]:  # Limit to 5 snippets
                parts.append(f"\n### {snippet['file']}:{snippet['line']}")
                parts.append(f"```python\n{snippet['content']}\n```")
        
        # Add similar patterns if found
        if context.get("similar_features"):
            parts.append("\n## Similar Patterns Found")
            for pattern in context["similar_features"][:3]:
                parts.append(
                    f"- {pattern['name']} in {pattern['file']} "
                    f"(similarity: {pattern['similarity']:.0%})"
                )
        
        return "\n".join(parts)
    
    def _get_plan_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for structured plan output."""
        return {
            "name": "create_plan",
            "description": "Create a structured implementation plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "description": "List of implementation steps",
                        "items": {
                            "type": "object",
                            "properties": {
                                "order": {
                                    "type": "integer",
                                    "description": "Step execution order"
                                },
                                "goal": {
                                    "type": "string",
                                    "description": "What this step accomplishes"
                                },
                                "kind": {
                                    "type": "string",
                                    "enum": ["edit", "add", "remove", "refactor", "test", "review"],
                                    "description": "Type of action"
                                },
                                "hints": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Implementation hints"
                                }
                            },
                            "required": ["order", "goal", "kind"]
                        }
                    },
                    "rationale": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Reasoning behind the plan"
                    },
                    "affected_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files that will be modified"
                    },
                    "complexity_label": {
                        "type": "string",
                        "enum": ["trivial", "moderate", "complex"],
                        "description": "Overall complexity assessment"
                    },
                    "estimated_tokens": {
                        "type": "integer",
                        "description": "Estimated tokens for implementation"
                    }
                },
                "required": ["steps", "rationale", "affected_paths", "complexity_label"]
            }
        }
    
    def _parse_plan_response(
        self, 
        plan_data: Dict[str, Any], 
        request_id: str
    ) -> Plan:
        """Parse the LLM response into a Plan object."""
        import uuid
        
        # Parse steps
        steps = []
        for step_data in plan_data["steps"]:
            step = Step(
                order=step_data["order"],
                goal=step_data["goal"],
                kind=StepKind(step_data["kind"]),
                hints=step_data.get("hints", [])
            )
            steps.append(step)
        
        # Create plan
        plan = Plan(
            id=str(uuid.uuid4()),
            parent_request_id=request_id,
            steps=steps,
            rationale=plan_data["rationale"],
            affected_paths=plan_data["affected_paths"],
            complexity_label=ComplexityLevel(plan_data["complexity_label"]),
            estimated_tokens=plan_data.get("estimated_tokens", 0)
        )
        
        return plan
    
    def _get_code_analysis_prompt(
        self, 
        query: str, 
        code_snippets: List[Dict[str, Any]]
    ) -> str:
        """Generate prompt for code analysis."""
        snippets_text = []
        for snippet in code_snippets[:10]:  # Limit snippets
            snippets_text.append(
                f"File: {snippet['file']}:{snippet['line']}\n"
                f"```\n{snippet['content']}\n```\n"
            )
        
        return f"""Question: {query}

Relevant code from the repository:

{''.join(snippets_text)}

Please provide a clear, helpful answer based on the code above."""
    
    def _get_few_shot_examples(self, description: str) -> str:
        """Get relevant few-shot examples based on request type."""
        examples = []
        
        # Detect request type and add relevant examples
        if any(word in description for word in ["bug", "fix", "error", "issue"]):
            examples.append("""## Example: Bug Fix
Request: "Fix null pointer exception in user service"
Good plan:
1. IDENTIFY the exact location of the null pointer exception
2. ANALYZE the root cause (missing validation, race condition, etc.)
3. ADD null checks or proper initialization
4. UPDATE unit tests to cover the edge case
5. VERIFY no other code paths are affected""")
        
        if any(word in description for word in ["add", "feature", "implement", "create"]):
            examples.append("""## Example: Feature Addition
Request: "Add retry logic to API client"
Good plan:
1. REVIEW existing API client implementation
2. DESIGN retry strategy (exponential backoff, max attempts)
3. CREATE retry decorator or utility function
4. INTEGRATE retry logic into API calls
5. ADD configuration for retry parameters
6. WRITE tests for retry scenarios
7. UPDATE documentation""")
        
        if any(word in description for word in ["refactor", "clean", "improve", "optimize"]):
            examples.append("""## Example: Refactoring
Request: "Refactor database connection handling"
Good plan:
1. ANALYZE current connection patterns
2. IDENTIFY code duplication and issues
3. DESIGN connection pool or manager class
4. EXTRACT common connection logic
5. UPDATE all database operations to use new pattern
6. ENSURE backward compatibility
7. RUN integration tests
8. REMOVE deprecated code""")
        
        return "\n".join(examples) if examples else ""
    
    def verify_plan(self, plan: Plan) -> Tuple[bool, List[str]]:
        """
        Self-verify the generated plan for completeness and correctness.
        
        Args:
            plan: The generated plan to verify
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        # Check for empty or minimal plans
        if len(plan.steps) < 2:
            issues.append("Plan has too few steps - likely missing important details")
        
        # Check for affected paths
        if not plan.affected_paths:
            issues.append("No affected files identified - plan needs file targets")
        
        # Check step ordering
        seen_orders = set()
        for step in plan.steps:
            if step.order in seen_orders:
                issues.append(f"Duplicate step order: {step.order}")
            seen_orders.add(step.order)
        
        # Check for test steps when modifying code
        has_code_change = any(
            step.kind in [StepKind.EDIT, StepKind.ADD, StepKind.REFACTOR] 
            for step in plan.steps
        )
        has_test_step = any(step.kind == StepKind.TEST for step in plan.steps)
        
        if has_code_change and not has_test_step:
            issues.append("Code changes detected but no test step included")
        
        # Check rationale
        if len(plan.rationale) < 2:
            issues.append("Insufficient rationale provided")
        
        # Verify complexity matches step count
        if plan.complexity_label == ComplexityLevel.TRIVIAL and len(plan.steps) > 3:
            issues.append("Many steps but marked as trivial - complexity mismatch")
        elif plan.complexity_label == ComplexityLevel.COMPLEX and len(plan.steps) < 5:
            issues.append("Few steps but marked as complex - complexity mismatch")
        
        is_valid = len(issues) == 0
        return is_valid, issues
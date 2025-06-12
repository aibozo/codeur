#!/usr/bin/env python3
"""
Test script for LLM integration.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.request_planner.models import ChangeRequest
from src.request_planner.planner import RequestPlanner
from src.core.logging import setup_logging
import logging

# Set up logging
setup_logging(logging.DEBUG)

def test_llm_planning():
    """Test LLM-based planning."""
    print("\n=== Testing LLM Planning ===\n")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        print("Please run: export OPENAI_API_KEY=your-key")
        return
    
    # Initialize planner
    planner = RequestPlanner(use_llm=True)
    
    # Test requests
    test_requests = [
        "Add retry logic to the fetch_data function with exponential backoff",
        "Fix the bug where users can't log in with email addresses containing plus signs",
        "Refactor the authentication module to use dependency injection"
    ]
    
    for request_text in test_requests:
        print(f"\nRequest: {request_text}")
        print("-" * 50)
        
        # Create change request
        request = ChangeRequest(
            description=request_text,
            repo=".",
            branch="main"
        )
        
        try:
            # Create plan
            plan = planner.create_plan(request)
            
            # Display plan
            print(f"Plan ID: {plan.id}")
            print(f"Complexity: {plan.complexity_label}")
            print(f"Estimated tokens: {plan.estimated_tokens}")
            print(f"\nSteps:")
            for step in plan.steps:
                print(f"  {step.order}. {step.goal} ({step.kind})")
                if step.hints:
                    for hint in step.hints:
                        print(f"     - {hint}")
            
            print(f"\nRationale:")
            for point in plan.rationale:
                print(f"  - {point}")
                
            print(f"\nAffected files: {', '.join(plan.affected_paths)}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

def test_code_analysis():
    """Test LLM-based code analysis."""
    print("\n\n=== Testing Code Analysis ===\n")
    
    planner = RequestPlanner(use_llm=True)
    
    questions = [
        "How does the Request Planner work?",
        "What is the purpose of the context retriever?",
        "How are plans structured in this system?"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        print("-" * 50)
        
        try:
            answer = planner.analyze_code(question)
            print(answer)
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_llm_planning()
    test_code_analysis()
#!/usr/bin/env python3
"""
E2E Test Runner
==============

This script runs the comprehensive end-to-end integration tests with proper
environment setup and reporting.

Usage:
    python run_e2e_tests.py [options]
    
Options:
    --with-llm     Run tests with real LLM calls (requires API keys)
    --fast         Skip slow tests
    --verbose      Show detailed output
    --coverage     Generate coverage report
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import json
from datetime import datetime


def check_environment():
    """Check test environment and dependencies."""
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ required")
        
    # Check required packages
    try:
        import pytest
    except ImportError:
        issues.append("pytest not installed")
        
    try:
        import pytest_asyncio
    except ImportError:
        issues.append("pytest-asyncio not installed")
        
    # Check for git
    if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
        issues.append("git not found")
        
    return issues


def check_api_keys():
    """Check if API keys are configured."""
    keys = {
        "OpenAI": os.getenv("OPENAI_API_KEY"),
        "Anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "Google": os.getenv("GOOGLE_API_KEY")
    }
    
    configured = {k: bool(v and v != "your-" + k.lower() + "-api-key-here") 
                  for k, v in keys.items()}
    
    return configured


def setup_test_env():
    """Set up test environment variables."""
    # Load test environment
    test_env_file = Path(__file__).parent / ".env.test"
    if test_env_file.exists():
        with open(test_env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
                    
    # Ensure test mode
    os.environ["AGENT_TEST_MODE"] = "true"
    
    
def run_tests(args):
    """Run the E2E tests."""
    # Build pytest command
    cmd = ["pytest", "tests/test_e2e_full_integration.py"]
    
    # Add markers
    markers = []
    if args.fast:
        markers.append("not slow")
    if not args.with_llm:
        markers.append("not requires_llm")
        
    if markers:
        cmd.extend(["-m", " and ".join(markers)])
        
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
        cmd.append("-s")
    else:
        cmd.append("-v")
        
    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
        
    # Add output options
    cmd.extend([
        "--tb=short",
        f"--junit-xml=test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    ])
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


def print_summary(args):
    """Print test summary."""
    print("\n" + "="*60)
    print("E2E TEST SUMMARY")
    print("="*60)
    
    # Check API keys
    api_keys = check_api_keys()
    print("\nAPI Keys Configured:")
    for service, configured in api_keys.items():
        status = "✓" if configured else "✗"
        print(f"  {status} {service}")
        
    if not any(api_keys.values()) and args.with_llm:
        print("\n⚠️  WARNING: No API keys configured, tests will use mocks")
        
    print(f"\nTest Mode: {'Real LLM' if args.with_llm else 'Mocked LLM'}")
    print(f"Speed: {'Fast (skipping slow tests)' if args.fast else 'Full'}")
    
    if args.coverage:
        print(f"Coverage: Enabled (see htmlcov/index.html)")
        
    print("="*60)
    

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run E2E integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Run tests with real LLM calls (requires API keys)"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    # Check environment
    issues = check_environment()
    if issues:
        print("Environment issues found:")
        for issue in issues:
            print(f"  ✗ {issue}")
        return 1
        
    # Setup environment
    setup_test_env()
    
    # Print summary
    print_summary(args)
    
    # Run tests
    return run_tests(args)
    

if __name__ == "__main__":
    sys.exit(main())
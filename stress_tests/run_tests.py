#!/usr/bin/env python3
"""
Stress test runner for the AI coding agent system.
Executes tests in order of increasing complexity.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append('/home/riley/Programming/agent')
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class StressTestRunner:
    """Manages execution of stress tests."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = []
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "total_duration": 0,
            "total_tokens": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_all_tests(self, phase_filter: int = None):
        """Run all available stress tests."""
        print(f"\n{'='*80}")
        print("AI AGENT STRESS TEST SUITE")
        print(f"{'='*80}\n")
        
        # Find all test files
        test_files = sorted(self.test_dir.glob("test_*.py"))
        test_files = [f for f in test_files if f.name != "test_template.py"]
        
        print(f"Found {len(test_files)} tests")
        
        for test_file in test_files:
            # Import and run the test
            module_name = test_file.stem
            
            try:
                # Dynamic import
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, test_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Check if we should run this test based on phase
                if hasattr(module, 'TEST_SPEC'):
                    test_phase = module.TEST_SPEC.get('phase', 1)
                    if phase_filter and test_phase != phase_filter:
                        continue
                    
                    print(f"\nRunning: {module.TEST_SPEC['name']} (Phase {test_phase})")
                
                # Find and run the test function
                test_functions = [
                    func for func in dir(module)
                    if func.startswith('run_') and callable(getattr(module, func))
                ]
                
                if test_functions:
                    test_func = getattr(module, test_functions[0])
                    result = await test_func()
                    
                    self.results.append(result)
                    self.summary["total_tests"] += 1
                    
                    if result.get("success"):
                        self.summary["passed"] += 1
                    else:
                        self.summary["failed"] += 1
                    
                    self.summary["total_duration"] += result.get("duration_seconds", 0)
                    self.summary["total_tokens"] += result.get("tokens_used", 0)
                
            except Exception as e:
                print(f"✗ Failed to run {module_name}: {e}")
                self.summary["failed"] += 1
    
    def save_results(self):
        """Save test results to file."""
        results_file = self.test_dir / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "summary": self.summary,
                "results": self.results
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {self.summary['total_tests']}")
        print(f"Passed: {self.summary['passed']}")
        print(f"Failed: {self.summary['failed']}")
        print(f"Success Rate: {self.summary['passed'] / max(1, self.summary['total_tests']) * 100:.1f}%")
        print(f"Total Duration: {self.summary['total_duration']:.2f} seconds")
        print(f"Total Tokens: {self.summary['total_tokens']:,}")
        
        if self.summary['total_tokens'] > 0:
            # Estimate cost (rough approximation)
            cost_per_million = 0.15  # Gemini 2.5 Flash input cost
            estimated_cost = (self.summary['total_tokens'] / 1_000_000) * cost_per_million
            print(f"Estimated Cost: ${estimated_cost:.4f}")
        
        print(f"{'='*80}\n")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run AI agent stress tests")
    parser.add_argument(
        "--phase",
        type=int,
        help="Run only tests from a specific phase (1-5)"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Run a specific test file (e.g., test_todo_list.py)"
    )
    
    args = parser.parse_args()
    
    runner = StressTestRunner()
    
    if args.test:
        # Run specific test
        print(f"Running single test: {args.test}")
        # TODO: Implement single test execution
    else:
        # Run all tests or phase-filtered tests
        await runner.run_all_tests(phase_filter=args.phase)
    
    runner.print_summary()
    runner.save_results()


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Comprehensive test suite for the enhanced coding agent with tool support.
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging
import logging


class ComprehensiveCodingAgentTest:
    """Comprehensive test suite for the coding agent."""
    
    def __init__(self, repo_path: Path, use_fast_model: bool = True):
        self.repo_path = repo_path
        self.use_fast_model = use_fast_model
        self.results = []
        
        # Setup logging
        setup_logging(logging.INFO)
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize RAG, LLM, and Coding Agent."""
        print("🔧 Initializing components...")
        
        # RAG Service
        rag_dir = self.repo_path / ".rag"
        self.rag_service = RAGService(persist_directory=str(rag_dir))
        
        # Index all Python files
        print("📚 Indexing repository...")
        python_files = list(self.repo_path.glob("**/*.py"))
        for py_file in python_files:
            if ".rag" not in str(py_file):
                self.rag_service.index_file(str(py_file))
        
        self.rag_client = RAGClient(service=self.rag_service)
        
        # LLM Client - use gpt-4o for faster testing unless specified
        model = "gpt-4o" if self.use_fast_model else "o3"
        self.llm_client = LLMClient(model=model)
        print(f"✓ Using model: {self.llm_client.model}")
        
        # Create Coding Agent
        self.coding_agent = CodingAgent(
            repo_path=str(self.repo_path),
            rag_client=self.rag_client,
            llm_client=self.llm_client,
            max_retries=2
        )
    
    def cleanup_branches(self):
        """Clean up any existing test branches."""
        try:
            subprocess.run(["git", "checkout", "master"], cwd=self.repo_path, capture_output=True)
            branches = subprocess.run(["git", "branch"], cwd=self.repo_path, capture_output=True, text=True)
            for line in branches.stdout.split('\n'):
                if 'coding/' in line:
                    branch = line.strip().replace('* ', '')
                    subprocess.run(["git", "branch", "-D", branch], cwd=self.repo_path, capture_output=True)
        except:
            pass
    
    def get_base_commit(self) -> str:
        """Get the current HEAD commit."""
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        ).stdout.strip()
    
    def create_task(self, task_id: str, goal: str, paths: list, complexity=None) -> messages_pb2.CodingTask:
        """Create a coding task."""
        task = messages_pb2.CodingTask()
        task.id = task_id
        task.parent_plan_id = "test-plan-001"
        task.step_number = 1
        task.goal = goal
        for path in paths:
            task.paths.append(path)
        task.complexity_label = complexity or messages_pb2.COMPLEXITY_MODERATE
        task.estimated_tokens = 1000
        task.base_commit_sha = self.get_base_commit()
        return task
    
    def run_test(self, test_name: str, task: messages_pb2.CodingTask, expected_checks: list):
        """Run a single test case."""
        print(f"\n{'='*60}")
        print(f"🧪 Test: {test_name}")
        print(f"{'='*60}")
        print(f"Goal: {task.goal}")
        print(f"Files: {', '.join(task.paths)}")
        
        start_time = time.time()
        
        try:
            # Process the task
            result = self.coding_agent.process_task(task)
            
            elapsed = time.time() - start_time
            
            # Record result
            test_result = {
                "name": test_name,
                "task_id": task.id,
                "status": result.status.name,
                "elapsed_time": elapsed,
                "retries": result.retries,
                "tokens_used": result.llm_tokens_used,
                "notes": result.notes,
                "checks": {}
            }
            
            print(f"\n📊 Result:")
            print(f"  Status: {result.status.name}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Retries: {result.retries}")
            print(f"  Tokens: {result.llm_tokens_used}")
            
            if result.notes:
                print("\n📝 Process notes:")
                for note in result.notes[-5:]:  # Show last 5 notes
                    print(f"  - {note}")
            
            if result.status.name == "SUCCESS":
                # Show the diff
                print(f"\n✅ Success! Commit: {result.commit_sha[:8]}")
                
                # Show changes
                diff = subprocess.run(
                    ["git", "show", "--stat", result.commit_sha],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                print("\n📄 Change summary:")
                print(diff.stdout)
                
                # Run verification checks
                print("\n🔍 Verification:")
                for check_name, check_func in expected_checks:
                    check_result = check_func(self.repo_path)
                    test_result["checks"][check_name] = check_result
                    print(f"  {'✓' if check_result else '✗'} {check_name}")
                
                # Reset to master for next test
                subprocess.run(["git", "checkout", "master"], cwd=self.repo_path, capture_output=True)
            else:
                print(f"\n❌ Failed: {result.status.name}")
                test_result["checks"] = {name: False for name, _ in expected_checks}
            
            self.results.append(test_result)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results.append({
                "name": test_name,
                "task_id": task.id,
                "status": "ERROR",
                "error": str(e),
                "elapsed_time": time.time() - start_time
            })
    
    def run_all_tests(self):
        """Run all test scenarios."""
        print("\n" + "="*60)
        print("🚀 Running Comprehensive Coding Agent Tests")
        print("="*60)
        
        self.cleanup_branches()
        
        # Test 1: Simple error handling
        task1 = self.create_task(
            "test-001",
            "Add error handling to the get_user method in src/api_client.py. It should catch requests.exceptions.RequestException and return None with a log message when the request fails.",
            ["src/api_client.py"]
        )
        
        def check_error_handling(repo_path):
            content = (repo_path / "src/api_client.py").read_text()
            return all([
                "import logging" in content,
                "try:" in content,
                "except" in content,
                "RequestException" in content,
                "return None" in content
            ])
        
        self.run_test(
            "Error Handling Addition", 
            task1,
            [
                ("Has error handling", check_error_handling),
                ("Imports logging", lambda p: "import logging" in (p / "src/api_client.py").read_text()),
                ("Has try/except", lambda p: "try:" in (p / "src/api_client.py").read_text())
            ]
        )
        
        # Test 2: Method refactoring
        task2 = self.create_task(
            "test-002",
            "Refactor the calculate_total method in src/calculator.py to handle empty lists gracefully by returning 0.",
            ["src/calculator.py"]
        )
        
        def check_empty_list_handling(repo_path):
            content = (repo_path / "src/calculator.py").read_text()
            return "if not" in content or "len(" in content or "== []" in content
        
        self.run_test(
            "Empty List Handling",
            task2,
            [
                ("Handles empty lists", check_empty_list_handling),
                ("Still has calculate_total", lambda p: "def calculate_total" in (p / "src/calculator.py").read_text())
            ]
        )
        
        # Test 3: Adding type hints
        task3 = self.create_task(
            "test-003",
            "Add type hints to all methods in src/data_processor.py",
            ["src/data_processor.py"],
            messages_pb2.COMPLEXITY_SIMPLE
        )
        
        def check_type_hints(repo_path):
            content = (repo_path / "src/data_processor.py").read_text()
            return "->" in content and ":" in content
        
        self.run_test(
            "Type Hints Addition",
            task3,
            [
                ("Has type hints", check_type_hints),
                ("Has return types", lambda p: "->" in (p / "src/data_processor.py").read_text())
            ]
        )
        
        # Test 4: Multi-file change
        task4 = self.create_task(
            "test-004",
            "Add a new method 'get_version()' to src/utils.py that returns '1.0.0', and update src/main.py to import and print this version on startup.",
            ["src/utils.py", "src/main.py"],
            messages_pb2.COMPLEXITY_MODERATE
        )
        
        def check_version_method(repo_path):
            utils = (repo_path / "src/utils.py").read_text()
            main = (repo_path / "src/main.py").read_text()
            return "def get_version" in utils and "1.0.0" in utils
        
        def check_main_uses_version(repo_path):
            main = (repo_path / "src/main.py").read_text()
            return "get_version" in main or "version" in main.lower()
        
        self.run_test(
            "Multi-file Feature Addition",
            task4,
            [
                ("Added version method", check_version_method),
                ("Main uses version", check_main_uses_version)
            ]
        )
        
        # Test 5: Complex refactoring with context understanding
        task5 = self.create_task(
            "test-005",
            "Create a new file src/config.py with a Config class that has a method get_setting(key: str) -> str. Update src/api_client.py to use this Config class for the base_url instead of hardcoding it.",
            ["src/config.py", "src/api_client.py"],
            messages_pb2.COMPLEXITY_COMPLEX
        )
        
        def check_config_file(repo_path):
            config_path = repo_path / "src/config.py"
            if not config_path.exists():
                return False
            content = config_path.read_text()
            return "class Config" in content and "def get_setting" in content
        
        def check_api_uses_config(repo_path):
            api_content = (repo_path / "src/api_client.py").read_text()
            return "Config" in api_content or "config" in api_content.lower()
        
        self.run_test(
            "New File Creation with Integration",
            task5,
            [
                ("Created config.py", check_config_file),
                ("API uses Config", check_api_uses_config)
            ]
        )
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("status") == "SUCCESS")
        failed = total - passed
        
        print(f"\nTotal tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        print("\n📈 Performance Stats:")
        total_time = sum(r.get("elapsed_time", 0) for r in self.results)
        total_tokens = sum(r.get("tokens_used", 0) for r in self.results)
        print(f"Total time: {total_time:.2f}s")
        print(f"Total tokens: {total_tokens}")
        
        print("\n📋 Detailed Results:")
        for result in self.results:
            status_icon = "✅" if result.get("status") == "SUCCESS" else "❌"
            print(f"\n{status_icon} {result['name']}:")
            print(f"   Status: {result.get('status', 'ERROR')}")
            print(f"   Time: {result.get('elapsed_time', 0):.2f}s")
            if "checks" in result:
                checks_passed = sum(1 for v in result["checks"].values() if v)
                print(f"   Checks: {checks_passed}/{len(result['checks'])} passed")
        
        # Save results to file
        results_file = Path(__file__).parent / "test_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to: {results_file}")


def main():
    """Run the comprehensive test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Coding Agent Test Suite")
    parser.add_argument("--repo", default="test_repo", help="Repository path to test")
    parser.add_argument("--use-o3", action="store_true", help="Use o3 model instead of gpt-4o")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per test in seconds")
    
    args = parser.parse_args()
    
    repo_path = Path(__file__).parent / args.repo
    
    if not repo_path.exists():
        print(f"❌ Repository not found: {repo_path}")
        print("Please run setup_test_repo.py first")
        return
    
    # Create and run test suite
    test_suite = ComprehensiveCodingAgentTest(
        repo_path=repo_path,
        use_fast_model=not args.use_o3
    )
    
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
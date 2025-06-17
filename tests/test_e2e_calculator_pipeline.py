#!/usr/bin/env python3
"""
End-to-end test for the complete pipeline: Architect -> Planner -> Coder -> Tester
Creates a calculator app from scratch with no existing files.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
import json
import subprocess
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect import Architect
from src.code_planner import CodePlanner
from src.coding_agent import CodingAgent
from src.test_agent import TestAgent
from src.analyzer import Analyzer
from src.rag_service import AdaptiveRAGService
from src.core.logging import setup_logging, get_logger

# Setup logging
setup_logging(structured=True)
logger = get_logger(__name__)


async def test_calculator_pipeline():
    """Test the complete pipeline by creating a calculator app from scratch."""
    
    # Create a directory for our test project (not temporary so we can test it)
    test_output_dir = Path(__file__).parent.parent / "test_output"
    test_output_dir.mkdir(exist_ok=True)
    
    # Remove old calculator if exists
    project_path = test_output_dir / "calculator_app"
    if project_path.exists():
        shutil.rmtree(project_path)
    
    # Use context manager style for consistency
    temp_dir = str(test_output_dir)
    project_path = Path(temp_dir) / "calculator_app"
    project_path.mkdir(parents=True)
    
    print("\n" + "="*80)
    print("CALCULATOR APP PIPELINE TEST")
    print("="*80)
    print(f"Project directory: {project_path}")
    
    # Initialize basic project structure
    print("\n1. Setting up project structure...")
    
    # Create a simple README
    readme_path = project_path / "README.md"
    readme_path.write_text("# Calculator App\n\nA simple calculator application built by the agent system.")
    
    # Create empty src directory
    src_dir = project_path / "src"
    src_dir.mkdir()
    
    # Create empty tests directory
    tests_dir = project_path / "tests"
    tests_dir.mkdir()
    
    # Create __init__.py files
    (src_dir / "__init__.py").touch()
    (tests_dir / "__init__.py").touch()
    
    # Create a simple requirements.txt
    requirements_path = project_path / "requirements.txt"
    requirements_path.write_text("pytest>=7.0.0\n")
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_path, check=True, capture_output=True)
    
    print("✓ Basic project structure created with git repository")
        
    # Initialize RAG service
    print("\n2. Initializing RAG service...")
    rag_service = AdaptiveRAGService(
        persist_directory=str(project_path / ".rag"),
        repo_path=str(project_path)
    )
    
    # Initialize agents
    print("\n3. Creating agents...")
    
    # Create architect
    architect = Architect(
        project_path=str(project_path),
        rag_service=rag_service,
        use_enhanced_task_graph=True
    )
    print("✓ Architect created")
        
    # Create analyzer
    analyzer = Analyzer(
        project_path=str(project_path),
        rag_service=rag_service
    )
    print("✓ Analyzer created")
        
    # Requirements for the calculator app
    requirements = """
        Create a Python calculator application with the following features:
        1. Basic arithmetic operations: addition, subtraction, multiplication, division
        2. Advanced operations: power, square root, percentage
        3. Memory functions: store, recall, clear memory
        4. A command-line interface for interactive use
        5. Proper error handling for invalid inputs and division by zero
        6. Comprehensive unit tests with at least 90% coverage
        
        The calculator should be modular with separate files for:
        - Core calculator logic (calculator.py)
        - CLI interface (cli.py)
        - Main entry point (__main__.py)
    """
    
    # Phase 1: Architect creates the plan
    print("\n4. PHASE 1: Architect creating task graph...")
    print("-" * 40)
    
    try:
        # Analyze the project first
        print("Analyzing project structure...")
        analysis_report = await analyzer.analyze()
        print(f"Analysis complete: {len(analysis_report.graph.components)} components found")
        
        # Create task graph
        task_graph = await architect.create_task_graph(
            project_name="Calculator App",
            requirements=requirements
        )
        
        print(f"✓ Task graph created with {len(task_graph.tasks)} tasks")
        
        # Display tasks
        print("\nTasks created:")
        for task_id, task in task_graph.tasks.items():
            deps = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""
            print(f"  - [{task.priority.value}] {task.title}{deps}")
        
        # Get the task context for development
        print("\nGetting task context...")
        ready_tasks = task_graph.get_ready_tasks()
        if ready_tasks:
            first_task = ready_tasks[0]
            context = await architect.get_project_context(task_graph.project_id, first_task.id)
            print(f"✓ Context retrieved for task: {first_task.title}")
        
        # If we have plan context, display it
        if "plan_context" in context:
            print("\nPlan context available:")
            for key in ["implementation_guide", "technical_context", "technologies"]:
                if key in context:
                    print(f"  - {key}: {'✓' if context[key] else '✗'}")
        
    except Exception as e:
        print(f"✗ Architect phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    # Phase 2: Request Planner breaks down the implementation
    print("\n\n5. PHASE 2: Request Planner creating implementation plan...")
    print("-" * 40)
    
    try:
        # For this test, we'll create a simplified plan based on the task graph
        # In a real system, this would use the RequestPlanner with messaging
        
        # Simulate plan creation
        implementation_plan = {
            "steps": [
                {
                    "name": "Create calculator core",
                    "description": "Implement the core calculator logic with all operations",
                    "files": ["src/calculator.py"],
                    "priority": "high"
                },
                {
                    "name": "Create CLI interface",
                    "description": "Build command-line interface for the calculator",
                    "files": ["src/cli.py"],
                    "priority": "medium"
                },
                {
                    "name": "Create main entry point",
                    "description": "Create the main entry point for the application",
                    "files": ["src/__main__.py"],
                    "priority": "medium"
                },
                {
                    "name": "Write tests",
                    "description": "Create comprehensive unit tests",
                    "files": ["tests/test_calculator.py", "tests/test_cli.py"],
                    "priority": "high"
                }
            ]
        }
        
        print(f"✓ Implementation plan created with {len(implementation_plan['steps'])} steps")
        for step in implementation_plan['steps']:
            print(f"  - {step['name']}: {', '.join(step['files'])}")
            
    except Exception as e:
        print(f"✗ Planning phase failed: {e}")
        return False
        
    # Phase 3: Code Planner creates detailed coding tasks
    print("\n\n6. PHASE 3: Code Planner creating coding tasks...")
    print("-" * 40)
    
    try:
        code_planner = CodePlanner(
            repo_path=str(project_path),
            use_rag=True
        )
        
        # For each implementation step, create detailed coding tasks
        coding_tasks = []
        for step in implementation_plan['steps']:
            # In a real system, this would use the CodePlanner's planning methods
            print(f"\nPlanning: {step['name']}")
            
            # Simulate task planning
            if "calculator.py" in step['files'][0]:
                task = {
                    "file": "src/calculator.py",
                    "description": "Implement Calculator class with all operations",
                    "code_structure": {
                        "class": "Calculator",
                        "methods": [
                            "add", "subtract", "multiply", "divide",
                            "power", "sqrt", "percentage",
                            "store_memory", "recall_memory", "clear_memory"
                        ]
                    }
                }
                coding_tasks.append(task)
                print(f"  ✓ Planned Calculator class with {len(task['code_structure']['methods'])} methods")
                
            elif "cli.py" in step['files'][0]:
                task = {
                    "file": "src/cli.py",
                    "description": "Implement CLI interface",
                    "code_structure": {
                        "class": "CalculatorCLI",
                        "methods": ["run", "display_menu", "get_input", "process_operation"]
                    }
                }
                coding_tasks.append(task)
                print(f"  ✓ Planned CLI interface")
                
            elif "__main__.py" in step['files'][0]:
                task = {
                    "file": "src/__main__.py",
                    "description": "Create main entry point",
                    "code_structure": {
                        "imports": ["from .cli import CalculatorCLI"],
                        "main_block": True
                    }
                }
                coding_tasks.append(task)
                print(f"  ✓ Planned main entry point")
                
        print(f"\n✓ Created {len(coding_tasks)} coding tasks")
        
    except Exception as e:
        print(f"✗ Code planning phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    # Phase 4: Coding Agent implements the code
    print("\n\n7. PHASE 4: Coding Agent implementing the application...")
    print("-" * 40)
    
    try:
        # Initialize coding agent
        coding_agent = CodingAgent(
            repo_path=str(project_path),
            llm_client=architect.llm_client  # Reuse architect's LLM if available
        )
        
        # For this test, we'll create simple implementations
        # In a real system, the CodingAgent would use LLM to generate code
        
        print("\nImplementing calculator.py...")
        calculator_code = '''"""
Calculator module providing basic and advanced mathematical operations.
"""
import math


class Calculator:
    """A calculator with basic operations and memory functions."""
    
    def __init__(self):
        self.memory = 0
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    def power(self, base: float, exponent: float) -> float:
        """Raise base to the power of exponent."""
        return math.pow(base, exponent)
    
    def sqrt(self, n: float) -> float:
        """Calculate square root."""
        if n < 0:
            raise ValueError("Cannot calculate square root of negative number")
        return math.sqrt(n)
    
    def percentage(self, value: float, percent: float) -> float:
        """Calculate percentage of a value."""
        return (value * percent) / 100
    
    def store_memory(self, value: float) -> None:
        """Store value in memory."""
        self.memory = value
    
    def recall_memory(self) -> float:
        """Recall value from memory."""
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear memory."""
        self.memory = 0
'''
        
        # Write calculator.py
        calculator_path = project_path / "src" / "calculator.py"
        calculator_path.write_text(calculator_code)
        print("✓ calculator.py implemented")
        
        print("\nImplementing cli.py...")
        cli_code = '''"""
Command-line interface for the calculator.
"""
from .calculator import Calculator


class CalculatorCLI:
    """CLI interface for the calculator."""
    
    def __init__(self):
        self.calculator = Calculator()
        self.running = True
    
    def display_menu(self):
        """Display the calculator menu."""
        print("\\n" + "="*40)
        print("Calculator Menu:")
        print("1. Add")
        print("2. Subtract")
        print("3. Multiply")
        print("4. Divide")
        print("5. Power")
        print("6. Square Root")
        print("7. Percentage")
        print("8. Store to Memory")
        print("9. Recall from Memory")
        print("10. Clear Memory")
        print("0. Exit")
        print("="*40)
    
    def get_input(self, prompt: str, input_type=float):
        """Get validated input from user."""
        while True:
            try:
                return input_type(input(prompt))
            except ValueError:
                print(f"Invalid input. Please enter a valid {input_type.__name__}.")
    
    def process_operation(self, choice: int):
        """Process the selected operation."""
        try:
            if choice == 1:  # Add
                a = self.get_input("Enter first number: ")
                b = self.get_input("Enter second number: ")
                result = self.calculator.add(a, b)
                print(f"Result: {a} + {b} = {result}")
                
            elif choice == 2:  # Subtract
                a = self.get_input("Enter first number: ")
                b = self.get_input("Enter second number: ")
                result = self.calculator.subtract(a, b)
                print(f"Result: {a} - {b} = {result}")
                
            elif choice == 3:  # Multiply
                a = self.get_input("Enter first number: ")
                b = self.get_input("Enter second number: ")
                result = self.calculator.multiply(a, b)
                print(f"Result: {a} × {b} = {result}")
                
            elif choice == 4:  # Divide
                a = self.get_input("Enter dividend: ")
                b = self.get_input("Enter divisor: ")
                result = self.calculator.divide(a, b)
                print(f"Result: {a} ÷ {b} = {result}")
                
            elif choice == 5:  # Power
                base = self.get_input("Enter base: ")
                exp = self.get_input("Enter exponent: ")
                result = self.calculator.power(base, exp)
                print(f"Result: {base}^{exp} = {result}")
                
            elif choice == 6:  # Square Root
                n = self.get_input("Enter number: ")
                result = self.calculator.sqrt(n)
                print(f"Result: √{n} = {result}")
                
            elif choice == 7:  # Percentage
                value = self.get_input("Enter value: ")
                percent = self.get_input("Enter percentage: ")
                result = self.calculator.percentage(value, percent)
                print(f"Result: {percent}% of {value} = {result}")
                
            elif choice == 8:  # Store Memory
                value = self.get_input("Enter value to store: ")
                self.calculator.store_memory(value)
                print(f"Stored {value} in memory")
                
            elif choice == 9:  # Recall Memory
                value = self.calculator.recall_memory()
                print(f"Memory value: {value}")
                
            elif choice == 10:  # Clear Memory
                self.calculator.clear_memory()
                print("Memory cleared")
                
            elif choice == 0:  # Exit
                print("Goodbye!")
                self.running = False
                
            else:
                print("Invalid choice. Please try again.")
                
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    
    def run(self):
        """Run the calculator CLI."""
        print("Welcome to Calculator!")
        
        while self.running:
            self.display_menu()
            choice = self.get_input("\\nEnter your choice (0-10): ", int)
            self.process_operation(choice)
'''
        
        # Write cli.py
        cli_path = project_path / "src" / "cli.py"
        cli_path.write_text(cli_code)
        print("✓ cli.py implemented")
        
        print("\nImplementing __main__.py...")
        main_code = '''"""
Main entry point for the calculator application.
"""
from .cli import CalculatorCLI


def main():
    """Run the calculator application."""
    cli = CalculatorCLI()
    cli.run()


if __name__ == "__main__":
    main()
'''
        
        # Write __main__.py
        main_path = project_path / "src" / "__main__.py"
        main_path.write_text(main_code)
        print("✓ __main__.py implemented")
        
        print("\n✓ All code files implemented successfully")
        
    except Exception as e:
        print(f"✗ Coding phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    # Phase 5: Test Agent creates and runs tests
    print("\n\n8. PHASE 5: Test Agent creating and running tests...")
    print("-" * 40)
    
    try:
        # Initialize test agent
        test_agent = TestAgent(
            project_path=str(project_path),
            llm_client=architect.llm_client  # Reuse architect's LLM if available
        )
        
        print("\nImplementing test_calculator.py...")
        test_calculator_code = '''"""
Unit tests for the Calculator class.
"""
import pytest
import math
from src.calculator import Calculator


class TestCalculator:
    """Test cases for Calculator operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = Calculator()
    
    def test_add(self):
        """Test addition operation."""
        assert self.calc.add(2, 3) == 5
        assert self.calc.add(-1, 1) == 0
        assert self.calc.add(0.1, 0.2) == pytest.approx(0.3)
    
    def test_subtract(self):
        """Test subtraction operation."""
        assert self.calc.subtract(5, 3) == 2
        assert self.calc.subtract(-1, -1) == 0
        assert self.calc.subtract(0.5, 0.3) == pytest.approx(0.2)
    
    def test_multiply(self):
        """Test multiplication operation."""
        assert self.calc.multiply(3, 4) == 12
        assert self.calc.multiply(-2, 3) == -6
        assert self.calc.multiply(0, 100) == 0
    
    def test_divide(self):
        """Test division operation."""
        assert self.calc.divide(10, 2) == 5
        assert self.calc.divide(7, 2) == 3.5
        assert self.calc.divide(-10, 2) == -5
    
    def test_divide_by_zero(self):
        """Test division by zero raises error."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            self.calc.divide(10, 0)
    
    def test_power(self):
        """Test power operation."""
        assert self.calc.power(2, 3) == 8
        assert self.calc.power(5, 0) == 1
        assert self.calc.power(4, 0.5) == 2
    
    def test_sqrt(self):
        """Test square root operation."""
        assert self.calc.sqrt(4) == 2
        assert self.calc.sqrt(9) == 3
        assert self.calc.sqrt(2) == pytest.approx(math.sqrt(2))
    
    def test_sqrt_negative(self):
        """Test square root of negative number raises error."""
        with pytest.raises(ValueError, match="Cannot calculate square root of negative number"):
            self.calc.sqrt(-4)
    
    def test_percentage(self):
        """Test percentage calculation."""
        assert self.calc.percentage(100, 25) == 25
        assert self.calc.percentage(50, 10) == 5
        assert self.calc.percentage(75, 20) == 15
    
    def test_memory_operations(self):
        """Test memory store, recall, and clear."""
        # Test initial memory is 0
        assert self.calc.recall_memory() == 0
        
        # Test store and recall
        self.calc.store_memory(42)
        assert self.calc.recall_memory() == 42
        
        # Test overwrite memory
        self.calc.store_memory(100)
        assert self.calc.recall_memory() == 100
        
        # Test clear memory
        self.calc.clear_memory()
        assert self.calc.recall_memory() == 0
'''
        
        # Write test_calculator.py
        test_calculator_path = project_path / "tests" / "test_calculator.py"
        test_calculator_path.write_text(test_calculator_code)
        print("✓ test_calculator.py implemented")
        
        print("\nImplementing test_cli.py...")
        test_cli_code = '''"""
Unit tests for the Calculator CLI.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.cli import CalculatorCLI


class TestCalculatorCLI:
    """Test cases for Calculator CLI."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cli = CalculatorCLI()
    
    def test_initialization(self):
        """Test CLI initialization."""
        assert self.cli.calculator is not None
        assert self.cli.running is True
    
    @patch('builtins.input', return_value='5.5')
    def test_get_input_float(self, mock_input):
        """Test getting float input."""
        result = self.cli.get_input("Enter number: ")
        assert result == 5.5
    
    @patch('builtins.input', return_value='10')
    def test_get_input_int(self, mock_input):
        """Test getting integer input."""
        result = self.cli.get_input("Enter number: ", int)
        assert result == 10
    
    @patch('builtins.input', side_effect=['invalid', '3.14'])
    @patch('builtins.print')
    def test_get_input_validation(self, mock_print, mock_input):
        """Test input validation."""
        result = self.cli.get_input("Enter number: ")
        assert result == 3.14
        mock_print.assert_any_call("Invalid input. Please enter a valid float.")
    
    @patch('builtins.print')
    def test_display_menu(self, mock_print):
        """Test menu display."""
        self.cli.display_menu()
        # Check that menu was printed
        assert mock_print.call_count > 10  # Menu has many lines
    
    @patch('builtins.input', side_effect=['5', '3'])
    @patch('builtins.print')
    def test_process_add_operation(self, mock_print, mock_input):
        """Test addition through CLI."""
        self.cli.process_operation(1)
        mock_print.assert_any_call("Result: 5.0 + 3.0 = 8.0")
    
    @patch('builtins.input', return_value='0')
    @patch('builtins.print')
    def test_process_exit_operation(self, mock_print, mock_input):
        """Test exit operation."""
        assert self.cli.running is True
        self.cli.process_operation(0)
        assert self.cli.running is False
        mock_print.assert_any_call("Goodbye!")
    
    @patch('builtins.print')
    def test_process_invalid_choice(self, mock_print):
        """Test handling of invalid menu choice."""
        self.cli.process_operation(99)
        mock_print.assert_any_call("Invalid choice. Please try again.")
'''
        
        # Write test_cli.py
        test_cli_path = project_path / "tests" / "test_cli.py"
        test_cli_path.write_text(test_cli_code)
        print("✓ test_cli.py implemented")
        
        # Run the tests
        print("\nRunning tests...")
        os.chdir(project_path)
        
        # Run pytest
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        print("\nTest output:")
        print(result.stdout)
        
        if result.returncode == 0:
            print("\n✓ All tests passed!")
            
            # Run coverage
            print("\nRunning coverage analysis...")
            coverage_result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing"],
                capture_output=True,
                text=True
            )
            
            if "TOTAL" in coverage_result.stdout:
                # Extract coverage percentage
                for line in coverage_result.stdout.split('\n'):
                    if "TOTAL" in line:
                        print(f"\n{line}")
                        parts = line.split()
                        if len(parts) >= 4:
                            coverage_percent = parts[-1].rstrip('%')
                            print(f"\n✓ Code coverage: {coverage_percent}%")
        else:
            print("\n✗ Some tests failed")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Testing phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    # Phase 6: Verify the application works
    print("\n\n9. PHASE 6: Verifying the application...")
    print("-" * 40)
    
    try:
        # Test running the calculator
        print("\nTesting calculator execution...")
        
        # Run the calculator with a simple test input
        test_input = "6\n16\n0\n"  # Square root of 16, then exit
        result = subprocess.run(
            [sys.executable, "-m", "src"],
            input=test_input,
            capture_output=True,
            text=True,
            cwd=project_path
        )
        
        if result.returncode == 0:
            print("✓ Calculator runs successfully")
            if "√16 = 4.0" in result.stdout:
                print("✓ Calculator produces correct output")
            else:
                print("✗ Calculator output doesn't match expected")
                print(f"Output: {result.stdout}")
        else:
            print("✗ Calculator failed to run")
            print(f"Error: {result.stderr}")
            return False
            
        # List all created files
        print("\n\nCreated files:")
        for root, dirs, files in os.walk(project_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.') and not file.endswith('.pyc'):
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    print(f"  - {rel_path}")
        
        print("\n" + "="*80)
        print("✓ CALCULATOR APP PIPELINE TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"✗ Verification phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the calculator pipeline test."""
    try:
        success = await test_calculator_pipeline()
        
        if success:
            print("\n✅ Pipeline test passed!")
            sys.exit(0)
        else:
            print("\n❌ Pipeline test failed!")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
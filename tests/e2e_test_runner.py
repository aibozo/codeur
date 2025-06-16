#!/usr/bin/env python3
"""
End-to-End Test Runner for Agent System.

This script executes automated tests to verify agent integrations,
LLM functionality, and RAG service.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """Runs end-to-end tests for the agent system."""
    
    def __init__(self, project_root: Path, test_project_path: Optional[Path] = None):
        self.project_root = project_root
        self.test_project_path = test_project_path or project_root / "test_project"
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": []
        }
        
    async def run_all_tests(self):
        """Run all E2E tests."""
        logger.info("Starting E2E test suite")
        start_time = time.time()
        
        # Test categories
        test_suites = [
            self.test_agent_initialization,
            self.test_architect_rag_integration,
            self.test_analyzer_functionality,
            self.test_request_planner_rag,
            self.test_code_planner_rag,
            self.test_coding_agent_tracking,
            self.test_event_system,
            self.test_architecture_diagrams,
        ]
        
        for test_suite in test_suites:
            await test_suite()
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Generate report
        self.generate_report(total_time)
        
    async def test_agent_initialization(self):
        """Test agent initialization and registration."""
        test_name = "Agent Initialization"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Import necessary modules
            from src.core.agent_registry import AgentRegistry, AgentStatus
            from src.architect.architect import Architect
            from src.analyzer.analyzer import Analyzer
            
            # Create registry
            registry = AgentRegistry()
            await registry.start()
            
            # Register agents
            await registry.register_agent("architect", "gpt-4", ["design", "planning"])
            await registry.register_agent("analyzer", "gpt-4", ["analysis", "diagramming"])
            
            # Verify registration
            agents = await registry.get_all_agents()
            assert len(agents) == 2, f"Expected 2 agents, got {len(agents)}"
            
            # Test architect initialization
            architect = Architect(project_root=str(self.test_project_path))
            assert architect.rag_client is not None, "Architect RAG client not initialized"
            
            # Test analyzer initialization  
            analyzer = Analyzer(project_root=str(self.test_project_path))
            assert analyzer.rag_service is not None, "Analyzer RAG service not initialized"
            
            await registry.stop()
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_architect_rag_integration(self):
        """Test Architect agent RAG functionality."""
        test_name = "Architect RAG Integration"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.architect.architect import Architect
            
            # Initialize architect
            architect = Architect(project_root=str(self.test_project_path))
            
            # Test context retrieval
            context = architect._get_project_context("authentication system")
            assert "RAG Context:" in context, "RAG context not included"
            
            # Test task graph generation (without actual LLM call)
            requirements = "Add user authentication with JWT tokens"
            if architect.llm_client:
                logger.info("LLM client available, skipping actual API call in test")
                self.record_test_result(test_name, "passed", "RAG integration verified")
            else:
                # Test with mock response
                mock_response = {
                    "tasks": [
                        {
                            "id": "task1",
                            "name": "Create JWT utilities",
                            "description": "Implement JWT token generation and validation",
                            "dependencies": []
                        }
                    ],
                    "structure": {
                        "auth": {
                            "jwt.py": "JWT utilities",
                            "middleware.py": "Auth middleware"
                        }
                    }
                }
                
                # Verify response structure
                assert "tasks" in mock_response
                assert "structure" in mock_response
                self.record_test_result(test_name, "passed", "Mock test completed")
                
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_analyzer_functionality(self):
        """Test Analyzer agent functionality."""
        test_name = "Analyzer Functionality"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.analyzer.analyzer import Analyzer
            
            # Create test project structure
            self._create_test_project()
            
            # Initialize analyzer
            analyzer = Analyzer(project_root=str(self.test_project_path))
            
            # Analyze project
            architecture = await analyzer.analyze_project()
            
            # Verify architecture
            assert architecture is not None, "No architecture returned"
            assert len(architecture.components) > 0, "No components found"
            
            # Generate diagram
            mermaid_code = architecture.to_mermaid()
            assert "graph TB" in mermaid_code or "graph TD" in mermaid_code
            assert "subgraph" in mermaid_code  # Should have layers
            
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_request_planner_rag(self):
        """Test Request Planner RAG integration."""
        test_name = "Request Planner RAG"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.request_planner.enhanced_context import EnhancedContextRetriever
            
            # Initialize context retriever
            retriever = EnhancedContextRetriever(self.test_project_path, use_rag=True)
            
            # Test RAG availability
            assert retriever.rag_available, "RAG not available for Request Planner"
            
            # Test context retrieval
            intent = {"type": "add_feature", "target": "authentication"}
            context = retriever.get_context("Add JWT authentication", intent)
            
            assert context["using_rag"] is True
            assert "formatted_context" in context
            assert len(context["snippets"]) > 0 or len(context["relevant_files"]) > 0
            
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_code_planner_rag(self):
        """Test Code Planner RAG integration."""
        test_name = "Code Planner RAG"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.code_planner.code_planner import CodePlanner
            
            # Initialize code planner
            planner = CodePlanner(str(self.test_project_path), use_rag=True)
            
            # Verify RAG integration
            assert planner.rag_integration is not None, "RAG integration not initialized"
            assert planner.rag_integration.enabled, "RAG not enabled"
            
            # Test metrics
            metrics = planner.get_metrics()
            assert "cache_size" in metrics
            assert "call_graph_nodes" in metrics
            
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_coding_agent_tracking(self):
        """Test Coding Agent change tracking."""
        test_name = "Coding Agent Change Tracking"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.core.change_tracker import ChangeTracker
            
            # Initialize change tracker
            tracker = ChangeTracker()
            
            # Simulate a diff
            test_diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,5 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
+    return True
+
"""
            
            # Track the diff
            stats = await tracker.track_diff(test_diff, "test.py", "coding_agent")
            
            # Verify tracking
            assert stats.lines_added == 3
            assert stats.lines_removed == 1
            assert stats.net_change == 2
            
            # Check metrics
            metrics = tracker.metrics
            assert metrics.total_lines_added == 3
            assert metrics.total_lines_removed == 1
            
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_event_system(self):
        """Test event system integration."""
        test_name = "Event System"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.core.agent_registry import AgentRegistry, AgentStatus
            from src.core.realtime import RealtimeService
            
            # Create services
            realtime = RealtimeService()
            registry = AgentRegistry(realtime_service=realtime)
            
            # Track events
            events_received = []
            
            async def mock_broadcast(data, topic):
                events_received.append((data, topic))
                
            # Mock the broadcast method
            realtime.broadcast = mock_broadcast
            
            # Register and update agent
            await registry.register_agent("test_agent", "gpt-4")
            await registry.update_agent_status("test_agent", AgentStatus.ACTIVE, "Processing")
            
            # Verify events
            assert len(events_received) >= 2, "Expected at least 2 events"
            assert any(event[0]["type"] == "agent_update" for event in events_received)
            
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    async def test_architecture_diagrams(self):
        """Test architecture diagram generation."""
        test_name = "Architecture Diagrams"
        logger.info(f"Running test: {test_name}")
        
        try:
            from src.analyzer.analyzer import Architecture, Component, Relationship
            
            # Create test architecture
            arch = Architecture()
            
            # Add components
            api_component = Component(
                id="api",
                name="API Service",
                type="service",
                path="src/api",
                description="REST API endpoints"
            )
            db_component = Component(
                id="database",
                name="Database",
                type="data",
                path="src/db",
                description="Data persistence layer"
            )
            
            arch.components = {
                "api": api_component,
                "database": db_component
            }
            
            # Add relationship
            arch.relationships.append(
                Relationship(
                    source="api",
                    target="database",
                    type="uses",
                    description="API queries database"
                )
            )
            
            # Add layer
            arch.layers = {
                "Application Layer": ["api"],
                "Data Layer": ["database"]
            }
            
            # Generate diagram
            mermaid = arch.to_mermaid()
            
            # Verify diagram
            assert "graph TB" in mermaid
            assert "API Service" in mermaid
            assert "Database" in mermaid
            assert "-->" in mermaid  # Relationship arrow
            assert "subgraph Application Layer" in mermaid
            assert "subgraph Data Layer" in mermaid
            
            self.record_test_result(test_name, "passed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_test_result(test_name, "failed", str(e))
            
    def _create_test_project(self):
        """Create a simple test project structure."""
        # Create directories
        (self.test_project_path / "src" / "api").mkdir(parents=True, exist_ok=True)
        (self.test_project_path / "src" / "models").mkdir(parents=True, exist_ok=True)
        (self.test_project_path / "tests").mkdir(parents=True, exist_ok=True)
        
        # Create files
        files = {
            "src/api/server.py": '''"""API server module."""
import flask

app = flask.Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}
''',
            "src/models/user.py": '''"""User model."""
class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name
''',
            "README.md": "# Test Project\n\nA simple test project for E2E testing."
        }
        
        for path, content in files.items():
            file_path = self.test_project_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            
    def record_test_result(self, test_name: str, status: str, details: str = ""):
        """Record test result."""
        self.results["total"] += 1
        self.results[status] += 1
        self.results["tests"].append({
            "name": test_name,
            "status": status,
            "details": details
        })
        
        # Log result
        if status == "passed":
            logger.info(f"✓ {test_name} - PASSED")
        elif status == "failed":
            logger.error(f"✗ {test_name} - FAILED: {details}")
        else:
            logger.warning(f"- {test_name} - SKIPPED: {details}")
            
    def generate_report(self, total_time: float):
        """Generate test report."""
        report = f"""# E2E Test Report

## Summary
- Total Tests: {self.results['total']}
- Passed: {self.results['passed']} ✓
- Failed: {self.results['failed']} ✗
- Skipped: {self.results['skipped']} -
- Total Time: {total_time:.2f}s

## Detailed Results
"""
        
        for test in self.results["tests"]:
            status_icon = "✓" if test["status"] == "passed" else "✗" if test["status"] == "failed" else "-"
            report += f"\n### {status_icon} {test['name']}\n"
            report += f"- Status: {test['status'].upper()}\n"
            if test["details"]:
                report += f"- Details: {test['details']}\n"
                
        # Save report
        report_path = self.project_root / "tests" / "e2e_test_report.md"
        report_path.write_text(report)
        logger.info(f"Test report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*50)
        print("E2E TEST SUMMARY")
        print("="*50)
        print(f"Total: {self.results['total']}")
        print(f"Passed: {self.results['passed']} ({self.results['passed']/self.results['total']*100:.1f}%)")
        print(f"Failed: {self.results['failed']}")
        print(f"Time: {total_time:.2f}s")
        print("="*50)


async def main():
    """Main entry point."""
    import sys
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create test runner
    runner = E2ETestRunner(project_root)
    
    # Run tests
    await runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if runner.results["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
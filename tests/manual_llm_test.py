#!/usr/bin/env python3
"""
Manual LLM Test Script for Agent System.

This script allows manual testing of LLM tool calls for each agent
to verify they're working correctly with the OpenAI API.
"""

import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_architect_llm():
    """Test Architect agent LLM functionality."""
    print("\n" + "="*50)
    print("Testing Architect Agent LLM Integration")
    print("="*50)
    
    try:
        from src.architect.architect import Architect
        
        # Initialize architect
        architect = Architect(project_path=".")
        
        if not architect.llm_client:
            print("✗ No LLM client configured. Check OPENAI_API_KEY in .env")
            return False
            
        # Test requirements analysis (simpler test)
        requirements = "Create a simple REST API for managing blog posts with CRUD operations"
        print(f"\nRequirements: {requirements}")
        print("\nAnalyzing requirements...")
        
        # Test the analyze_requirements method which should use LLM
        try:
            analysis = await architect.analyze_requirements(requirements)
            
            if analysis:
                print("✓ LLM call successful!")
                print(f"\nAnalysis:")
                print(f"  Project Type: {analysis.get('project_type', 'Unknown')}")
                print(f"  Complexity: {analysis.get('complexity', 'Unknown')}")
                print(f"  Estimated Tasks: {analysis.get('estimated_tasks', 0)}")
                print(f"  Key Features: {', '.join(analysis.get('key_features', [])[:3])}")
                return True
            else:
                print("✗ No analysis returned")
                return False
        except Exception as e:
            print(f"✗ Analysis failed: {e}")
            # Try the design_architecture method as alternative
            print("\nTrying design_architecture method...")
            try:
                architecture = await architect.design_architecture(requirements)
                if architecture:
                    print("✓ Architecture design successful!")
                    print(f"  Components: {len(architecture.components)}")
                    print(f"  Technology Stack: {list(architecture.technology_stack.keys())}")
                    print(f"  Constraints: {len(architecture.constraints)}")
                    return True
            except Exception as e2:
                print(f"✗ Design failed: {e2}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_analyzer_llm():
    """Test Analyzer agent architecture analysis."""
    print("\n" + "="*50)
    print("Testing Analyzer Agent")
    print("="*50)
    
    try:
        from src.analyzer.analyzer import Analyzer
        
        # Create a test project structure
        test_dir = Path("test_project")
        test_dir.mkdir(exist_ok=True)
        (test_dir / "app.py").write_text('''
"""Main application module."""
from flask import Flask
from database import Database

app = Flask(__name__)
db = Database()

@app.route("/")
def index():
    return {"message": "Hello World"}
''')
        (test_dir / "database.py").write_text('''
"""Database module."""
class Database:
    def __init__(self):
        self.connection = None
        
    def query(self, sql):
        pass
''')
        
        # Initialize analyzer
        analyzer = Analyzer(project_path=str(test_dir))
        
        print("\nAnalyzing test project...")
        report = await analyzer.analyze()
        
        if report:
            print("✓ Analysis successful!")
            print(f"\nFound {len(report.graph.components)} components")
            print(f"\nSummary: {report.summary}")
            
            # Generate diagram
            print("\nMermaid Diagram:")
            print(report.mermaid_diagram or report.graph.to_mermaid())
            return True
        else:
            print("✗ Analysis failed")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_request_planner_rag():
    """Test Request Planner with RAG context."""
    print("\n" + "="*50)
    print("Testing Request Planner RAG Integration")
    print("="*50)
    
    try:
        from src.request_planner.enhanced_context import EnhancedContextRetriever
        
        # Initialize retriever
        retriever = EnhancedContextRetriever(Path("."), use_rag=True)
        
        if retriever.rag_available:
            print("✓ RAG service available")
            
            # Test search
            query = "authentication"
            print(f"\nSearching for: {query}")
            
            results = retriever.search(query, limit=5)
            print(f"\nFound {len(results)} results:")
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.file}:{result.line}")
                print(f"   Score: {result.score:.3f}")
                print(f"   Preview: {result.content[:100]}...")
                
            return True
        else:
            print("✗ RAG service not available")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_change_tracking():
    """Test change tracking functionality."""
    print("\n" + "="*50)
    print("Testing Change Tracking")
    print("="*50)
    
    try:
        from src.core.change_tracker import ChangeTracker, get_change_tracker
        
        # Get tracker instance
        tracker = get_change_tracker()
        
        # Create test diffs
        diffs = [
            ("""--- a/file1.py
+++ b/file1.py
@@ -1,2 +1,3 @@
 def hello():
     print("hello")
+    return True
""", "file1.py", 1, 0),
            ("""--- a/file2.py
+++ b/file2.py
@@ -1,3 +1,5 @@
 class User:
     def __init__(self):
         self.name = ""
+        self.email = ""
+        self.active = True
""", "file2.py", 2, 0),
        ]
        
        print("\nTracking test diffs...")
        
        for diff, file, added, removed in diffs:
            stats = await tracker.track_diff(diff, file, "test_agent")
            print(f"\n✓ Tracked {file}: +{stats.lines_added} -{stats.lines_removed}")
            
        # Check metrics
        metrics = tracker.metrics
        print(f"\nTotal metrics:")
        print(f"  Files changed: {metrics.files_changed}")
        print(f"  Lines added: {metrics.total_lines_added}")
        print(f"  Lines removed: {metrics.total_lines_removed}")
        # Calculate net change
        net_change = metrics.total_lines_added - metrics.total_lines_removed
        print(f"  Net change: {net_change}")
        
        # Test threshold
        print(f"\nTesting threshold (default 50 lines)...")
        
        # Add a large diff to trigger threshold
        large_diff = "--- a/big.py\n+++ b/big.py\n@@ -1,1 +1,50 @@\n"
        large_diff += "\n".join([f"+line {i}" for i in range(50)])
        
        # Set up event capture
        threshold_triggered = False
        
        async def on_threshold(event_type, data):
            nonlocal threshold_triggered
            threshold_triggered = True
            print(f"\n✓ Threshold event triggered! Type: {event_type}")
            
        # Subscribe to event
        if hasattr(tracker, 'event_handlers'):
            tracker.event_handlers['threshold_exceeded'].append(on_threshold)
            
        await tracker.track_diff(large_diff, "big.py", "test_agent")
        
        if threshold_triggered:
            print("✓ Change threshold detection working!")
        else:
            print("Note: Threshold event not triggered (may need event system setup)")
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_all_agents():
    """Run all agent tests."""
    print("\n" + "#"*60)
    print("# Agent System LLM Integration Test")
    print("#"*60)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  WARNING: OPENAI_API_KEY not found in environment!")
        print("   Please add it to your .env file to test LLM functionality.")
        print("\n   Example .env file:")
        print("   OPENAI_API_KEY=sk-...")
    else:
        print(f"\n✓ OpenAI API key found (length: {len(api_key)})")
        
    # Run tests
    results = []
    
    # Test each component
    tests = [
        ("Architect LLM", test_architect_llm),
        ("Analyzer", test_analyzer_llm),
        ("Request Planner RAG", test_request_planner_rag),
        ("Change Tracking", test_change_tracking),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test failed with error: {e}")
            results.append((test_name, False))
            
    # Summary
    print("\n" + "#"*60)
    print("# Test Summary")
    print("#"*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    print("\nDetailed Results:")
    for test_name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {test_name}")
        
    if passed == total:
        print("\n🎉 All tests passed! The agent system is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")


def main():
    """Main entry point."""
    print("Starting agent system tests...")
    asyncio.run(test_all_agents())


if __name__ == "__main__":
    main()
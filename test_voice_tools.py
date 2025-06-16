#!/usr/bin/env python3
"""
Unit tests for voice agent tool calls.

Tests each tool function independently to ensure proper integration
before running the full voice agent.
"""

import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.voice_agent.gemini_native_audio_simple import WebSocketVoiceAgent


async def test_tool_calls():
    """Test each tool call independently."""
    print("🧪 VOICE AGENT TOOL TESTING")
    print("=" * 50)
    
    # Create agent instance
    agent = WebSocketVoiceAgent(project_path=Path.cwd())
    print(f"✅ Agent created with {len(agent.tools[0]['functionDeclarations'])} tools\n")
    
    # Test cases for each tool
    test_cases = [
        {
            "name": "search_codebase",
            "args": {"query": "WebSocket"},
            "description": "Search for WebSocket-related code"
        },
        {
            "name": "search_codebase", 
            "args": {"query": "voice agent", "file_pattern": "*.py", "max_results": 3},
            "description": "Search for voice agent with filters"
        },
        {
            "name": "analyze_component",
            "args": {"component_path": "src/voice_agent", "depth": "summary"},
            "description": "Analyze voice agent component"
        },
        {
            "name": "trace_data_flow",
            "args": {"entry_point": "webhook", "flow_type": "request"},
            "description": "Trace webhook data flow"
        },
        {
            "name": "find_dependencies",
            "args": {"target": "WebSocketVoiceAgent", "direction": "imports"},
            "description": "Find WebSocketVoiceAgent dependencies"
        },
        {
            "name": "explain_system_flow",
            "args": {"feature": "task creation"},
            "description": "Explain task creation flow"
        },
        {
            "name": "get_agent_info",
            "args": {"agent_name": "coding_agent"},
            "description": "Get coding agent information"
        },
        {
            "name": "find_similar_code",
            "args": {"code_snippet": "async def search_codebase", "context": "finding search functions"},
            "description": "Find similar async search functions"
        },
        {
            "name": "read_file",
            "args": {"file_path": "src/voice_agent/__init__.py"},
            "description": "Read voice agent init file"
        },
        {
            "name": "list_directory",
            "args": {"directory": "src", "recursive": False},
            "description": "List src directory contents"
        },
        {
            "name": "get_project_stats",
            "args": {"category": "overview"},
            "description": "Get project overview statistics"
        },
        {
            "name": "get_project_stats",
            "args": {"category": "agents"},
            "description": "Get agent statistics"
        }
    ]
    
    # Test each tool
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📍 Test {i}/{len(test_cases)}: {test_case['description']}")
        print(f"   Tool: {test_case['name']}")
        print(f"   Args: {test_case['args']}")
        
        try:
            # Create tool call format
            tool_call = {
                "name": test_case["name"],
                "arguments": test_case["args"]
            }
            
            # Execute tool call
            result = await agent._handle_tool_call(tool_call)
            
            # Check for errors
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                failed += 1
            else:
                print(f"   ✅ Success!")
                # Print summary of results
                if isinstance(result, dict):
                    for key, value in list(result.items())[:3]:
                        if isinstance(value, list):
                            print(f"      {key}: {len(value)} items")
                        elif isinstance(value, str) and len(value) > 100:
                            print(f"      {key}: {value[:100]}...")
                        else:
                            print(f"      {key}: {value}")
                passed += 1
                
        except Exception as e:
            print(f"   ❌ Exception: {type(e).__name__}: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed > 0:
        print("\n⚠️  Some tests failed. Check the errors above.")
    else:
        print("\n🎉 All tests passed! Voice agent tools are ready.")
    
    return passed, failed


async def test_tool_definitions():
    """Test that tool definitions are properly formatted."""
    print("\n\n🔧 TOOL DEFINITION VALIDATION")
    print("=" * 50)
    
    agent = WebSocketVoiceAgent(project_path=Path.cwd())
    tools = agent.tools[0]['functionDeclarations']
    
    print(f"Found {len(tools)} tool definitions:\n")
    
    for tool in tools:
        print(f"• {tool['name']}")
        print(f"  Description: {tool['description'][:80]}...")
        print(f"  Parameters: {list(tool['parameters']['properties'].keys())}")
        print(f"  Required: {tool['parameters'].get('required', [])}")
        print()
    
    # Validate structure
    issues = []
    for tool in tools:
        if 'name' not in tool:
            issues.append(f"Missing 'name' in tool")
        if 'description' not in tool:
            issues.append(f"Missing 'description' in {tool.get('name', 'unknown')}")
        if 'parameters' not in tool:
            issues.append(f"Missing 'parameters' in {tool.get('name', 'unknown')}")
        elif 'properties' not in tool['parameters']:
            issues.append(f"Missing 'properties' in {tool.get('name', 'unknown')} parameters")
    
    if issues:
        print("❌ Validation issues found:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ All tool definitions are properly formatted!")


async def main():
    """Run all tests."""
    # Test tool definitions
    await test_tool_definitions()
    
    # Test tool calls
    passed, failed = await test_tool_calls()
    
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
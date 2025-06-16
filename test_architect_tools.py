#!/usr/bin/env python3
"""
Test architect tools with all three providers.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Import our modules
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.architect.architect import Architect
from src.architect.llm_tools import ArchitectTools


async def test_architect_with_provider(model: str):
    """Test architect with a specific model/provider."""
    print(f"\n{'='*60}")
    print(f"Testing Architect with model: {model}")
    print('='*60)
    
    try:
        # Set the model for architect
        os.environ["ARCHITECT_MODEL"] = model
        
        # Initialize architect
        architect = Architect(
            project_path=".",
            auto_index=False  # Skip indexing for test
        )
        
        # Check if LLM client was initialized
        if not architect.llm_client:
            print(f"❌ LLM client not initialized for {model}")
            return
        
        print(f"✅ LLM client initialized: {architect.llm_client.model_card.display_name}")
        print(f"   Provider: {architect.llm_client.model_card.provider}")
        print(f"   Model ID: {architect.llm_client.model_card.model_id}")
        
        # Test basic generation
        print("\n📝 Testing basic generation...")
        try:
            response = architect.llm_client.generate(
                prompt="What tools do you have available? List them briefly.",
                system_prompt="You are an expert software architect. Keep your response concise."
            )
            print(f"Response: {response[:200]}...")
            print(f"✅ Basic generation works!")
        except Exception as e:
            print(f"❌ Basic generation failed: {e}")
            import traceback
            traceback.print_exc()
            
        # Test with tools (if supported)
        print("\n🔧 Testing tool awareness...")
        
        # Create a prompt that asks about available tools
        tool_prompt = """I need to create a task breakdown for a new web application project.
        
What tools or capabilities do you have available to help me create and manage tasks?
Please list any specific functions or tools you can use."""
        
        try:
            response = architect.llm_client.generate(
                prompt=tool_prompt,
                system_prompt="""You are an expert software architect with access to task creation tools.

Available tools:
- create_tasks: Create tasks using markdown, list, or yaml format
- update_task: Update task details
- query_status: Get project status

Be specific about what tools you have available."""
            )
            print(f"Tool awareness response: {response[:300]}...")
            
            # Check if the response mentions tools
            if any(tool in response.lower() for tool in ['create_tasks', 'tool', 'function']):
                print(f"✅ Model seems aware of tools!")
            else:
                print(f"⚠️  Model may not be aware of tools")
                
        except Exception as e:
            print(f"❌ Tool test failed: {e}")
            
    except Exception as e:
        print(f"❌ Error testing {model}: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Test all three providers."""
    
    # Check which API keys are available
    providers = []
    
    if os.getenv("OPENAI_API_KEY"):
        providers.append(("gpt-4o", "OpenAI"))
    else:
        print("⚠️  OPENAI_API_KEY not set - skipping OpenAI tests")
    
    if os.getenv("GOOGLE_API_KEY"):
        providers.append(("gemini-2.5-flash", "Google"))
    else:
        print("⚠️  GOOGLE_API_KEY not set - skipping Google tests")
        
    if os.getenv("ANTHROPIC_API_KEY"):
        # Check if anthropic module is installed
        try:
            import anthropic
            providers.append(("claude-sonnet-4", "Anthropic"))
        except ImportError:
            print("⚠️  anthropic module not installed - skipping Anthropic tests")
            print("   Install with: pip install anthropic")
    else:
        print("⚠️  ANTHROPIC_API_KEY not set - skipping Anthropic tests")
    
    if not providers:
        print("❌ No API keys found! Please set at least one of:")
        print("   - OPENAI_API_KEY")
        print("   - GOOGLE_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        return
    
    print(f"\n🚀 Testing {len(providers)} providers...")
    
    for model, provider_name in providers:
        await test_architect_with_provider(model)
        
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
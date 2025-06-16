#!/usr/bin/env python3
"""Simple test of LLM providers without RAG initialization."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm import LLMClient

def test_provider(model, name):
    """Test a single provider."""
    print(f"\n{'='*60}")
    print(f"Testing {name} with model: {model}")
    print('='*60)
    
    try:
        # Create client
        client = LLMClient(model=model, agent_name="test")
        print(f"✅ Client created: {client.model_card.display_name}")
        print(f"   Provider: {client.model_card.provider}")
        print(f"   Model ID: {client.model_card.model_id}")
        
        # Test generation
        response = client.generate(
            prompt="What model are you? Reply in one sentence.",
            system_prompt="You are a helpful assistant. Be very concise."
        )
        print(f"✅ Response: {response}")
        
        # Test tool awareness
        tool_response = client.generate(
            prompt="List the tools you have: create_tasks, update_task, query_status",
            system_prompt="You have access to these tools: create_tasks (for task creation), update_task (for updates), query_status (for status). Be concise."
        )
        print(f"✅ Tool awareness: {tool_response[:100]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if "401" in str(e):
            print("   (Authentication error - check API key)")

# Test available providers
print("🚀 Testing LLM Providers")

if os.getenv("OPENAI_API_KEY"):
    test_provider("gpt-4o", "OpenAI")

if os.getenv("GOOGLE_API_KEY"):
    test_provider("gemini-2.5-flash", "Google Gemini")

if os.getenv("ANTHROPIC_API_KEY"):
    try:
        import anthropic
        test_provider("claude-sonnet-4", "Anthropic Claude")
    except ImportError:
        print("\n⚠️  anthropic module not installed")

print("\n✅ Tests complete!")
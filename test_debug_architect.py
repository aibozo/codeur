#!/usr/bin/env python3
"""
Debug architect model loading.
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Check environment
print("Environment variables:")
print(f"  ARCHITECT_MODEL: {os.getenv('ARCHITECT_MODEL', 'Not set')}")
print(f"  GOOGLE_API_KEY: {'Set' if os.getenv('GOOGLE_API_KEY') else 'Not set'}")
print(f"  GEMINI_API_KEY: {'Set' if os.getenv('GEMINI_API_KEY') else 'Not set'}")
print()

# Check model configuration
from src.core.agent_config import AgentConfigManager
from src.core.model_cards import ModelSelector

print("Model configuration:")
architect_model = AgentConfigManager.get_model_for_agent("architect")
print(f"  Architect default model: {architect_model}")

model_card = ModelSelector.get_model_card(architect_model)
if model_card:
    print(f"  Model card found: {model_card.display_name}")
    print(f"  Model ID: {model_card.model_id}")
    print(f"  Provider: {model_card.provider}")
else:
    print(f"  ❌ No model card found for: {architect_model}")

print()

# Try to create architect
print("Creating architect...")
try:
    from src.architect.architect import Architect
    architect = Architect(str(Path.cwd()))
    print("✅ Architect created successfully")
    
    if architect.llm_client:
        print(f"  LLM client initialized")
        print(f"  Model: {architect.llm_client.model}")
        print(f"  Model card: {architect.llm_client.model_card.display_name}")
    else:
        print("  ❌ No LLM client")
        
except Exception as e:
    print(f"❌ Failed to create architect: {e}")
    import traceback
    traceback.print_exc()

print()

# Test simple request
async def test_request():
    print("Testing architect request...")
    try:
        result = await architect.analyze_project_requirements("test project")
        print(f"✅ Request successful")
        print(f"  Result type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Keys: {list(result.keys())}")
    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()

if 'architect' in locals():
    asyncio.run(test_request())
#!/usr/bin/env python3
"""
Test architect with actual LLM call.
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Force debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

async def main():
    print("Testing Architect with LLM...")
    print("=" * 50)
    
    from src.architect.architect import Architect
    
    # Create architect
    architect = Architect(str(Path.cwd()))
    
    # Test with a real question that should use LLM
    try:
        result = await architect.analyze_project_requirements(
            "Create a web scraping tool that can extract product prices from e-commerce websites"
        )
        
        print("\n✅ Analysis successful!")
        print(f"Result type: {type(result)}")
        
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"\n{key}:")
                if isinstance(value, list):
                    for item in value:
                        print(f"  - {item}")
                else:
                    print(f"  {value}")
                    
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
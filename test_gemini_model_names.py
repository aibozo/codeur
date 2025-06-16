#!/usr/bin/env python3
"""
Test various Gemini 2.5 model name patterns to find the correct format.
"""

import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Get API key
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

client = genai.Client(api_key=api_key)

# Test content
test_content = [
    types.Content(
        role="user",
        parts=[types.Part.from_text(text="Say 'Hello' in one word")]
    )
]

config = types.GenerateContentConfig(
    response_mime_type="text/plain",
    temperature=0.1,
    max_output_tokens=10
)

# Model name variations to test
model_variants = [
    # Based on the example provided
    "gemini-2.5-pro-preview-05-06",
    
    # Flash variations without models/ prefix
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-flash",
    "gemini-2.5-flash-latest",
    
    # With models/ prefix
    "models/gemini-2.5-flash-preview-05-20",
    "models/gemini-2.5-flash-preview-04-17",
    "models/gemini-2.5-flash",
    
    # Other 2.x models that might work
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "models/gemini-2.0-flash",
    
    # Try some 1.5 models as fallback
    "gemini-1.5-flash",
    "models/gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    
    # Pro models
    "gemini-pro",
    "models/gemini-pro"
]

print("Testing Gemini model name variations...")
print("=" * 60)

working_models = []

for model_name in model_variants:
    try:
        print(f"\n📝 Testing: {model_name}")
        
        # Try non-streaming first
        response = client.models.generate_content(
            model=model_name,
            contents=test_content,
            config=config
        )
        
        # Handle different response formats
        if hasattr(response, 'text') and response.text:
            result = response.text.strip()
            print(f"✅ SUCCESS: {result}")
            working_models.append(model_name)
        elif hasattr(response, 'candidates') and response.candidates:
            # Try to extract text from candidates
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                if candidate.content.parts:
                    text = candidate.content.parts[0].text
                    print(f"✅ SUCCESS (via candidates): {text}")
                    working_models.append(model_name)
                else:
                    print(f"⚠️  Response has no text content")
            else:
                print(f"⚠️  Unexpected response format: {type(response)}")
        else:
            print(f"⚠️  Empty or None response")
        
    except Exception as e:
        error_msg = str(e)
        if "Unknown model" in error_msg:
            print(f"❌ Unknown model")
        elif "not found" in error_msg:
            print(f"❌ Model not found")
        else:
            print(f"❌ Error: {error_msg[:100]}...")

print("\n" + "=" * 60)
print(f"\n🎯 Working models ({len(working_models)}):")
for model in working_models:
    print(f"  ✅ {model}")

# If we found working models, test the best flash model
if working_models:
    flash_models = [m for m in working_models if "flash" in m.lower()]
    if flash_models:
        print(f"\n🚀 Recommended Flash model: {flash_models[0]}")
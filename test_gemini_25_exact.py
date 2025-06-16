#!/usr/bin/env python3
"""
Test Gemini 2.5 models following exact documentation pattern.
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

# Test models
test_models = [
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-pro-preview-06-05",
]

print("Testing Gemini 2.5 models with exact documentation pattern...")
print("=" * 60)

for model_id in test_models:
    print(f"\n📝 Testing: {model_id}")
    
    try:
        # Method 1: Simple generate_content (from docs)
        response = client.models.generate_content(
            model=model_id,
            contents="What's the largest planet in our solar system?"
        )
        
        # Check response format
        print(f"   Response type: {type(response)}")
        
        if hasattr(response, 'text'):
            print(f"   ✅ Has .text property: {response.text[:50]}...")
        else:
            print(f"   ❌ No .text property")
            
        if hasattr(response, 'candidates'):
            print(f"   📋 Has candidates: {len(response.candidates) if response.candidates else 0}")
            if response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    print(f"   📄 Candidate content type: {type(candidate.content)}")
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text'):
                            print(f"   ✅ Found text in candidate: {part.text[:50]}...")
        
        # Method 2: With GenerateContentConfig (from docs)
        print("\n   Testing with GenerateContentConfig...")
        response2 = client.models.generate_content(
            model=model_id,
            contents="Say 'Hello' in one word",
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=20,
                candidate_count=1,
                seed=5,
            )
        )
        
        if hasattr(response2, 'text'):
            print(f"   ✅ Config method works: {response2.text}")
        else:
            print(f"   ❌ Config method - no text")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}...")

print("\n" + "=" * 60)
print("\nTesting count_tokens (from docs)...")
try:
    response = client.models.count_tokens(
        model="gemini-2.5-flash-preview-05-20",
        contents="What's the highest mountain in Africa?",
    )
    print(f"✅ Token counting works: {response}")
except Exception as e:
    print(f"❌ Token counting error: {e}")

print("\nTesting with Content objects (from docs)...")
try:
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="What is 2+2?"),
            ],
        ),
    ]
    
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-05-20",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="text/plain",
        ),
    )
    
    if hasattr(response, 'text'):
        print(f"✅ Content objects method works: {response.text}")
    else:
        print(f"❌ Content objects method - no text")
        
except Exception as e:
    print(f"❌ Content objects error: {e}")
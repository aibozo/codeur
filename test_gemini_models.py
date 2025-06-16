#!/usr/bin/env python3
"""
Test available Gemini models.
"""

import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

# Configure API
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Available Gemini models:")
print("=" * 50)

# List available models
for model in genai.list_models():
    print(f"Model: {model.name}")
    print(f"  Display name: {model.display_name}")
    print(f"  Supported methods: {model.supported_generation_methods}")
    print()

# Test specific model
test_models = [
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-pro"
]

print("\nTesting specific models:")
print("=" * 50)

for model_name in test_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello'")
        print(f"✅ {model_name}: {response.text.strip()}")
    except Exception as e:
        print(f"❌ {model_name}: {str(e)[:100]}")
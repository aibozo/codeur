#!/usr/bin/env python3
"""
Test script for Gemini API using the basic format from documentation.
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment variables")
    sys.exit(1)

print(f"API Key found: {api_key[:8]}...")

# Configure the API
genai.configure(api_key=api_key)

# Test 1: Basic text generation
print("\n=== Test 1: Basic Text Generation ===")
try:
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
    response = model.generate_content("Write a simple Python function to calculate the factorial of a number.")
    print(f"Response: {response.text[:200]}...")
    print(f"Finish reason: {response.candidates[0].finish_reason}")
except Exception as e:
    print(f"Error in basic generation: {e}")

# Test 2: With generation config
print("\n=== Test 2: With Generation Config ===")
try:
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 1000,
    }
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash-preview-05-20',
        generation_config=generation_config
    )
    
    response = model.generate_content("What is 2 + 2?")
    print(f"Response: {response.text}")
    print(f"Finish reason: {response.candidates[0].finish_reason}")
except Exception as e:
    print(f"Error with generation config: {e}")

# Test 3: Chat format
print("\n=== Test 3: Chat Format ===")
try:
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
    chat = model.start_chat(history=[])
    
    response = chat.send_message("Hello! Can you help me write a calculator in Python?")
    print(f"Response: {response.text[:200]}...")
    print(f"Finish reason: {response.candidates[0].finish_reason}")
except Exception as e:
    print(f"Error in chat format: {e}")

# Test 4: System instruction (if supported)
print("\n=== Test 4: With System Instruction ===")
try:
    model = genai.GenerativeModel(
        'gemini-2.5-flash-preview-05-20',
        system_instruction="You are a helpful coding assistant. Always provide clear, concise code examples."
    )
    
    response = model.generate_content("Show me how to create a simple GUI window in Python")
    print(f"Response: {response.text[:200]}...")
    print(f"Finish reason: {response.candidates[0].finish_reason}")
except Exception as e:
    print(f"Error with system instruction: {e}")

# Test 5: Complex prompt (similar to what failed in our code)
print("\n=== Test 5: Complex Prompt ===")
try:
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
    
    complex_prompt = """Generate a unified diff patch to: Create a GUI calculator application using tkinter

Context:
Task Goal: Create a GUI calculator application using tkinter

Instructions:
1. Generate a valid unified diff patch (git format)
2. Only modify the files mentioned in the context
3. Ensure the changes achieve the stated goal
4. Follow the coding style of the existing code
5. Include proper error handling where appropriate
6. The patch should apply cleanly with 'git apply'

Generate the patch:"""

    response = model.generate_content(complex_prompt)
    if response.text:
        print(f"Response: {response.text[:200]}...")
    else:
        print("No text in response!")
    print(f"Finish reason: {response.candidates[0].finish_reason}")
    if hasattr(response, 'prompt_feedback'):
        print(f"Prompt feedback: {response.prompt_feedback}")
except Exception as e:
    print(f"Error with complex prompt: {e}")
    import traceback
    traceback.print_exc()
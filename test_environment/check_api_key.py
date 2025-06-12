#!/usr/bin/env python3
"""
Check which API key is being loaded.
"""

import os
from dotenv import load_dotenv

# Check current directory
print(f"Current directory: {os.getcwd()}")
print(f"Looking for .env file...")

# Try different paths
env_paths = [
    ".env",
    "../.env",
    "/home/riley/Programming/agent/.env"
]

for path in env_paths:
    if os.path.exists(path):
        print(f"Found .env at: {os.path.abspath(path)}")
        load_dotenv(path)
        break

# Check loaded API key
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    # Show first and last 4 chars for verification
    masked = f"{api_key[:7]}...{api_key[-4:]}"
    print(f"\nLoaded API key: {masked}")
    print(f"Key length: {len(api_key)}")
else:
    print("\nNo API key found!")

# Check other env vars
print(f"\nPLANNING_MODEL: {os.getenv('PLANNING_MODEL')}")
print(f"GENERAL_MODEL: {os.getenv('GENERAL_MODEL')}")
#!/usr/bin/env python3
"""
Test o3 API to see which format works.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def test_o3_chat_api():
    """Test o3 with chat completions API."""
    print("=== Testing o3 with chat.completions API ===\n")
    
    client = OpenAI()
    
    try:
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello"}
            ],
            response_format={"type": "text"},
            reasoning_effort="low"
        )
        
        print("Success! Response:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Chat API failed: {e}")
        print("\nTrying responses API...\n")
        
        # Try the responses API if available
        try:
            if hasattr(client, 'responses'):
                response = client.responses.create(
                    model="o3-mini",
                    input=[{"role": "user", "content": "Say hello"}],
                    text={
                        "format": {
                            "type": "text"
                        }
                    },
                    reasoning={
                        "effort": "low",
                        "summary": "auto"
                    },
                    tools=[],
                    store=True
                )
                
                print("Responses API Success!")
                print(response)
            else:
                print("Client doesn't have 'responses' attribute")
                
        except Exception as e2:
            print(f"Responses API also failed: {e2}")


if __name__ == "__main__":
    test_o3_chat_api()
#!/usr/bin/env python3
"""
Quick demo of the Codeur webhook system.

Run this to see the webhook server in action!
"""

import subprocess
import time
import requests
import json
from pathlib import Path

def demo():
    print("🚀 Codeur Webhook Demo")
    print("=" * 50)
    
    # Check if agent-system is installed
    try:
        subprocess.run(["agent-system", "--version"], check=True, capture_output=True)
    except:
        print("❌ Please install codeur first:")
        print("   pip install -e .")
        return
    
    print("\n1️⃣ Generating secure token...")
    result = subprocess.run(
        ["agent-system", "webhook", "generate-token"],
        capture_output=True,
        text=True
    )
    token = result.stdout.strip().split()[-1]
    print(f"✅ Token: {token[:20]}...")
    
    print("\n2️⃣ Creating demo configuration...")
    config = {
        "webhook": {
            "auth_token": token,
            "project_mapping": [
                {
                    "pattern": "demo",
                    "path": str(Path.cwd())
                }
            ]
        }
    }
    
    config_path = Path.home() / ".agent" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, 'w') as f:
        import yaml
        yaml.dump(config, f)
    
    print(f"✅ Config saved to {config_path}")
    
    print("\n3️⃣ Starting webhook server...")
    server_proc = subprocess.Popen(
        ["agent-system", "webhook", "start"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(3)
    
    print("✅ Server running on http://localhost:8080")
    
    print("\n4️⃣ Testing webhook endpoints...")
    
    # Test health check
    try:
        resp = requests.get("http://localhost:8080/health")
        print(f"   Health check: {resp.json()}")
    except:
        print("❌ Server not responding. Check logs.")
        server_proc.terminate()
        return
    
    # Test Discord webhook
    print("\n5️⃣ Simulating Discord command...")
    discord_payload = {
        "content": "!agent status",
        "channel": {"name": "demo"},
        "author": {"username": "demo-user"}
    }
    
    resp = requests.post(
        f"http://localhost:8080/webhook/discord?token={token}",
        json=discord_payload
    )
    print(f"   Response: {resp.json()}")
    
    # Test GitHub webhook  
    print("\n6️⃣ Simulating GitHub issue...")
    github_payload = {
        "action": "opened",
        "issue": {
            "title": "Add error handling",
            "body": "Please add try/except blocks to handle network errors",
            "number": 42
        },
        "repository": {"full_name": "demo/repo"}
    }
    
    resp = requests.post(
        f"http://localhost:8080/webhook/github?token={token}",
        json=github_payload,
        headers={"X-GitHub-Event": "issues"}
    )
    print(f"   Response: {resp.json()}")
    
    print("\n✨ Demo complete!")
    print("\nNext steps:")
    print("1. Set up Discord bot: https://discord.com/developers/applications")
    print("2. Configure project mappings in ~/.agent/config.yaml")
    print("3. Run: agent-system webhook start --daemon")
    print("\nPress Ctrl+C to stop the demo server...")
    
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n👋 Stopping server...")
        server_proc.terminate()


if __name__ == "__main__":
    demo()
#!/usr/bin/env python3
"""
Fix ChromaDB schema issues by recreating the database.
"""

import os
import shutil
from pathlib import Path

def fix_chromadb():
    """Remove old ChromaDB data to force recreation with new schema."""
    
    # Common locations for ChromaDB data
    possible_locations = [
        Path(".rag"),
        Path(".chroma"),
        Path("chroma_db"),
        Path.home() / ".chroma",
    ]
    
    print("🔧 Fixing ChromaDB schema issues...")
    print("=" * 50)
    
    found = False
    for location in possible_locations:
        if location.exists():
            print(f"Found ChromaDB data at: {location}")
            response = input(f"Delete {location}? (y/n): ")
            if response.lower() == 'y':
                shutil.rmtree(location)
                print(f"✅ Removed {location}")
                found = True
    
    # Also check in project directories
    for project_dir in Path.cwd().iterdir():
        if project_dir.is_dir():
            rag_dir = project_dir / ".rag"
            if rag_dir.exists():
                print(f"Found RAG data in: {rag_dir}")
                response = input(f"Delete {rag_dir}? (y/n): ")
                if response.lower() == 'y':
                    shutil.rmtree(rag_dir)
                    print(f"✅ Removed {rag_dir}")
                    found = True
    
    if not found:
        print("❌ No ChromaDB data found to clean")
    else:
        print("\n✅ ChromaDB cleanup complete!")
        print("The database will be recreated with the correct schema on next use.")

if __name__ == "__main__":
    fix_chromadb()
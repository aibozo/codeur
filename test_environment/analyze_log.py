#!/usr/bin/env python3
"""
Analyze the detailed log to understand what's happening.
"""

import json
from pathlib import Path

# Load the log
log_file = Path(__file__).parent / "logs/coding_agent_detailed_20250612_014530.summary.json"
with open(log_file) as f:
    data = json.load(f)

print("=== Coding Agent Log Analysis ===\n")

# Find key entries
for entry in data["entries"]:
    if entry["type"] == "prompt_context":
        print("1. PROMPT CONTEXT PROVIDED TO LLM:")
        print("-" * 50)
        print(entry["data"]["full_context"])
        print("-" * 50)
        print(f"Length: {entry['data']['length']} chars")
        print(f"Lines: {entry['data']['line_count']}")
        
    elif entry["type"] == "context_gathered":
        print("\n2. CONTEXT GATHERING SUMMARY:")
        print("-" * 50)
        data = entry["data"]
        print(f"Token count: {data['token_count']}")
        print(f"File snippets: {data['file_snippets']}")
        print(f"Related functions found: {len(data['related_functions'])}")
        for func in data['related_functions']:
            print(f"  - {func['file']}:{func['line']} - '{func['symbol']}' ({func['type']})")
        print(f"Error patterns: {len(data['error_patterns'])}")
        
    elif entry["type"] == "rag_results":
        print(f"\n3. RAG SEARCH: '{entry['data']['query'][:50]}...'")
        print(f"   Results: {entry['data']['result_count']}")
        for r in entry['data']['results'][:3]:
            print(f"   - {r['file_path']}:{r['start_line']} ({r['chunk_type']}) - '{r['symbol_name'].strip()}'")
            
    elif entry["type"] == "llm_tool_response":
        print(f"\n4. TOOL REQUEST FROM LLM:")
        print(f"   {entry['data']['response']}")
        
    elif entry["type"] == "patch_generated":
        print(f"\n5. PATCH GENERATION:")
        print(f"   Success: {entry['data']['success']}")
        if entry['data']['patch_preview']:
            print(f"   Preview: {entry['data']['patch_preview'][:200]}...")

print("\n\n=== KEY ISSUES IDENTIFIED ===")
print("\n1. RAG SYMBOL NAMES ARE WRONG:")
print("   - Most results have symbol_name='    ' or '    \\n    '")
print("   - This means the RAG isn't extracting method names properly")

print("\n2. NO TOOL EXECUTION:")
print("   - LLM requested find_symbol('get_user') but it wasn't executed")
print("   - The tool request was made but no tool_execute entry exists")

print("\n3. RELATED FUNCTIONS HAVE EMPTY SYMBOLS:")
print("   - Related functions list has empty symbol names")
print("   - This makes it hard for LLM to understand what's what")

print("\n4. FILE PATH FILTERS NOT WORKING:")
print("   - Query 'import statements in src/api_client.py' with filter file_path='src/api_client.py'")
print("   - But filter is relative path, while indexed paths are absolute")

print("\n5. PATCH HAS WRONG LINE NUMBERS:")
print("   - Patch shows @@ -5,6 +5,7 @@ for adding import")
print("   - But actual import is at line 5, so it should be different")
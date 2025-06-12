#!/usr/bin/env python3
"""
Test coding agent with detailed logging of all inputs/outputs.
"""

import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging


class DetailedLogger:
    """Logger that captures all coding agent interactions."""
    
    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.entries = []
        self.current_task = None
        
    def log_entry(self, entry_type: str, data: dict):
        """Log an entry with timestamp."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,
            "task_id": self.current_task,
            "data": data
        }
        self.entries.append(entry)
        
        # Also write to file immediately
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def set_task(self, task_id: str):
        """Set current task being processed."""
        self.current_task = task_id
    
    def save_summary(self):
        """Save a summary of all entries."""
        summary_file = self.log_file.with_suffix('.summary.json')
        with open(summary_file, 'w') as f:
            json.dump({
                "total_entries": len(self.entries),
                "entries": self.entries
            }, f, indent=2)


def monkey_patch_agent_for_logging(agent: CodingAgent, logger: DetailedLogger):
    """Monkey patch the coding agent to log all interactions."""
    
    # 1. Patch context gathering
    original_gather_context = agent.context_gatherer.gather_context
    def gather_context_logged(task):
        logger.log_entry("context_gather_start", {
            "goal": task.goal,
            "paths": list(task.paths)
        })
        
        context = original_gather_context(task)
        
        # Log what was gathered
        logger.log_entry("context_gathered", {
            "token_count": context.token_count,
            "file_snippets": list(context.file_snippets.keys()),
            "file_snippet_previews": {
                path: content[:200] + "..." if len(content) > 200 else content
                for path, content in context.file_snippets.items()
            },
            "blob_count": len(context.blob_contents),
            "blob_ids": list(context.blob_contents.keys()),
            "related_functions": context.related_functions,
            "imports": context.imports,
            "error_patterns": context.error_patterns
        })
        
        # Log the actual prompt context
        prompt_context = context.to_prompt_context()
        logger.log_entry("prompt_context", {
            "full_context": prompt_context,
            "length": len(prompt_context),
            "line_count": len(prompt_context.split('\n'))
        })
        
        return context
    
    agent.context_gatherer.gather_context = gather_context_logged
    
    # 2. Patch context refinement with tools
    original_refine = agent._refine_context_with_tools
    def refine_context_logged(task, context):
        logger.log_entry("context_refine_start", {
            "initial_token_count": context.token_count
        })
        
        # Patch the LLM call to see what tools are requested
        original_generate = agent.llm_client.generate_with_json
        tool_requests = []
        
        def generate_logged(prompt, **kwargs):
            logger.log_entry("llm_tool_request", {
                "prompt": prompt,
                "kwargs": {k: v for k, v in kwargs.items() if k != 'system_prompt'}
            })
            
            response = original_generate(prompt, **kwargs)
            
            logger.log_entry("llm_tool_response", {
                "response": response
            })
            
            if isinstance(response, list):
                tool_requests.extend(response)
            
            return response
        
        agent.llm_client.generate_with_json = generate_logged
        
        try:
            refined = original_refine(task, context)
            
            logger.log_entry("context_refined", {
                "final_token_count": refined.token_count,
                "tools_requested": tool_requests,
                "new_blobs": [k for k in refined.blob_contents.keys() 
                             if k not in context.blob_contents]
            })
            
            return refined
        finally:
            # Restore original
            agent.llm_client.generate_with_json = original_generate
    
    agent._refine_context_with_tools = refine_context_logged
    
    # 3. Patch tool execution
    original_execute_tool = agent._execute_tool_call
    def execute_tool_logged(tool_call, context):
        logger.log_entry("tool_execute", {
            "tool": tool_call.get("tool"),
            "args": tool_call.get("args", {})
        })
        
        try:
            result = original_execute_tool(tool_call, context)
            logger.log_entry("tool_result", {
                "tool": tool_call.get("tool"),
                "success": True,
                "blob_added": f"tool_{tool_call.get('tool')}" in context.blob_contents
            })
            return result
        except Exception as e:
            logger.log_entry("tool_error", {
                "tool": tool_call.get("tool"),
                "error": str(e)
            })
            raise
    
    agent._execute_tool_call = execute_tool_logged
    
    # 4. Patch patch generation
    original_generate_patch = agent.patch_generator.generate_patch
    def generate_patch_logged(context, **kwargs):
        logger.log_entry("patch_generate_start", {
            "context_tokens": context.token_count,
            "kwargs": kwargs
        })
        
        # Log the actual prompt sent to LLM
        prompt = agent.patch_generator._build_prompt(context)
        logger.log_entry("patch_prompt", {
            "prompt": prompt,
            "prompt_length": len(prompt)
        })
        
        result = original_generate_patch(context, **kwargs)
        
        logger.log_entry("patch_generated", {
            "success": result.success,
            "error": result.error_message,
            "patch_preview": result.patch_content[:500] if result.patch_content else None,
            "files_modified": result.files_modified,
            "tokens_used": result.tokens_used
        })
        
        return result
    
    agent.patch_generator.generate_patch = generate_patch_logged
    
    # 5. Patch file rewriter
    original_rewrite = agent.file_rewriter.rewrite_file
    def rewrite_file_logged(context, file_path, **kwargs):
        logger.log_entry("file_rewrite_start", {
            "file_path": file_path,
            "context_tokens": context.token_count
        })
        
        result = original_rewrite(context, file_path, **kwargs)
        
        logger.log_entry("file_rewrite_result", {
            "success": result.success,
            "error": result.error_message,
            "file_path": file_path
        })
        
        return result
    
    agent.file_rewriter.rewrite_file = rewrite_file_logged
    
    # 6. Patch RAG search calls
    if hasattr(agent.context_gatherer, 'rag_client') and agent.context_gatherer.rag_client:
        original_search = agent.context_gatherer.rag_client.search
        def search_logged(query, **kwargs):
            logger.log_entry("rag_search", {
                "query": query,
                "kwargs": kwargs
            })
            
            results = original_search(query, **kwargs)
            
            logger.log_entry("rag_results", {
                "query": query,
                "result_count": len(results),
                "results": [
                    {
                        "file_path": r.get("file_path"),
                        "start_line": r.get("start_line"),
                        "symbol_name": r.get("symbol_name"),
                        "chunk_type": r.get("chunk_type"),
                        "content_preview": r.get("content", "")[:100]
                    }
                    for r in results[:5]  # First 5 results
                ]
            })
            
            return results
        
        agent.context_gatherer.rag_client.search = search_logged


def run_logged_test():
    """Run a test with detailed logging."""
    
    print("\n" + "="*60)
    print("🔍 Coding Agent Test with Detailed Logging")
    print("="*60)
    
    # Setup logging
    setup_logging(logging.WARNING)  # Reduce noise
    
    # Create logger
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"coding_agent_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    logger = DetailedLogger(log_file)
    print(f"\n📝 Logging to: {log_file}")
    
    # Setup test repo
    repo_path = Path(__file__).parent / "test_repo"
    
    # Fix git
    subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "reset", "--hard"], cwd=repo_path, capture_output=True)
    # Clean up any existing branches
    result = subprocess.run(["git", "branch"], cwd=repo_path, capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'coding/' in line:
            branch = line.strip().replace('* ', '')
            subprocess.run(["git", "branch", "-D", branch], cwd=repo_path, capture_output=True)
    
    # Setup RAG
    print("\n🔧 Setting up RAG service...")
    rag_dir = repo_path / ".rag"
    if rag_dir.exists():
        import shutil
        shutil.rmtree(rag_dir)
    
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Index files
    for py_file in repo_path.glob("**/*.py"):
        if ".rag" not in str(py_file) and "__pycache__" not in str(py_file):
            rag_service.index_file(str(py_file))
    
    rag_client = RAGClient(service=rag_service)
    
    # Create agent
    print("🤖 Creating coding agent...")
    llm_client = LLMClient(model="gpt-4o")
    
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client,
        max_retries=1  # Reduce retries for cleaner logs
    )
    
    # Fix branch issue
    original_checkout = coding_agent.git_ops.checkout_branch
    def checkout_fixed(branch):
        return original_checkout("master" if branch == "main" else branch)
    coding_agent.git_ops.checkout_branch = checkout_fixed
    
    # Apply logging patches
    monkey_patch_agent_for_logging(coding_agent, logger)
    
    # Create test task
    task = messages_pb2.CodingTask()
    task.id = "test-logged-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    task.goal = "Add error handling to the get_user method in src/api_client.py. It should catch requests.exceptions.RequestException and return None with a log message when the request fails."
    task.paths.append("src/api_client.py")
    task.complexity_label = 2  # MODERATE
    task.estimated_tokens = 1000
    task.base_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    print(f"\n📋 Task: {task.goal}")
    print(f"📁 Target: {task.paths[0]}")
    
    # Process task
    print("\n🚀 Processing task with detailed logging...\n")
    
    logger.set_task(task.id)
    logger.log_entry("task_start", {
        "task_id": task.id,
        "goal": task.goal,
        "paths": list(task.paths),
        "complexity": task.complexity_label
    })
    
    try:
        result = coding_agent.process_task(task)
        
        logger.log_entry("task_complete", {
            "status": result.status.name,
            "retries": result.retries,
            "tokens_used": result.llm_tokens_used,
            "notes": result.notes,
            "commit_sha": result.commit_sha,
            "branch_name": result.branch_name
        })
        
        print(f"\n📊 Result: {result.status.name}")
        print(f"   Retries: {result.retries}")
        print(f"   Tokens: {result.llm_tokens_used}")
        
    except Exception as e:
        logger.log_entry("task_error", {
            "error": str(e),
            "type": type(e).__name__
        })
        print(f"\n❌ Error: {e}")
    
    # Save summary
    logger.save_summary()
    
    print(f"\n✅ Detailed log saved to:")
    print(f"   {log_file}")
    print(f"   {log_file.with_suffix('.summary.json')}")
    
    # Print quick analysis
    print("\n📊 Quick Analysis:")
    
    # Count entry types
    entry_types = {}
    for entry in logger.entries:
        entry_types[entry["type"]] = entry_types.get(entry["type"], 0) + 1
    
    print("\nEntry counts:")
    for entry_type, count in sorted(entry_types.items()):
        print(f"   {entry_type}: {count}")
    
    # Check for tool usage
    tool_requests = [e for e in logger.entries if e["type"] == "llm_tool_response"]
    if tool_requests:
        print(f"\n🔧 Tool requests made: {len(tool_requests)}")
        for req in tool_requests:
            print(f"   - {req['data']['response']}")
    else:
        print("\n⚠️  No tool requests made!")
    
    # Check RAG results
    rag_searches = [e for e in logger.entries if e["type"] == "rag_results"]
    if rag_searches:
        print(f"\n🔍 RAG searches: {len(rag_searches)}")
        for search in rag_searches:
            data = search["data"]
            print(f"   - Query: '{data['query']}' → {data['result_count']} results")
            for r in data["results"][:3]:
                print(f"     • {r['file_path']}:{r['start_line']} ({r['chunk_type']})")
    else:
        print("\n⚠️  No RAG searches performed!")
    
    print("\n💡 Check the log files for complete details!")


if __name__ == "__main__":
    run_logged_test()
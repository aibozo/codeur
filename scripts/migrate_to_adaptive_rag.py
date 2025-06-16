#!/usr/bin/env python3
"""
Migration script to update codebase to use adaptive RAG.

This script helps migrate existing code to use the adaptive RAG service
for improved performance and quality.
"""

import os
import sys
import argparse
from pathlib import Path
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def migrate_imports(file_path: Path, dry_run: bool = False):
    """
    Update imports in a Python file to use adaptive RAG.
    
    Args:
        file_path: Path to the Python file
        dry_run: If True, only show what would be changed
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: Direct imports that should add project context setting
    # This catches cases where RAGClient is instantiated
    rag_client_pattern = r'(rag_client\s*=\s*RAGClient\([^)]+\))'
    
    def add_project_context(match):
        instantiation = match.group(1)
        # Add project context setting after instantiation
        project_id = extract_project_id(content)
        return f"{instantiation}\n        # Set project context for adaptive learning\n        if hasattr(rag_client, 'set_project_context'):\n            rag_client.set_project_context('{project_id}')"
    
    # Apply the transformation
    new_content = re.sub(rag_client_pattern, add_project_context, content)
    
    if new_content != content:
        changes.append("Added project context setting for RAGClient")
        content = new_content
    
    # Pattern 2: Add note about automatic adaptive usage
    if "from ..rag_service import RAGService, RAGClient" in content or \
       "from src.rag_service import RAGService, RAGClient" in content:
        # Add comment about adaptive usage
        import_line = next(line for line in content.split('\n') 
                          if 'from' in line and 'rag_service import' in line)
        new_import = f"{import_line}\n# Note: RAGService and RAGClient now use adaptive versions by default when USE_ADAPTIVE_RAG=true"
        content = content.replace(import_line, new_import)
        changes.append("Added note about adaptive RAG usage")
    
    # Show or apply changes
    if content != original_content:
        print(f"\n📄 {file_path}:")
        for change in changes:
            print(f"   ✓ {change}")
        
        if not dry_run:
            with open(file_path, 'w') as f:
                f.write(content)
            print("   ✅ Updated")
        else:
            print("   🔍 (dry run - no changes made)")
    
    return len(changes) > 0


def extract_project_id(content: str) -> str:
    """Extract project ID from file content."""
    # Look for project_path or similar
    project_match = re.search(r'project_path\s*[=:]\s*["\']([^"\']+)["\']', content)
    if project_match:
        return f"project_{Path(project_match.group(1)).name}"
    
    # Look for project_id
    id_match = re.search(r'project_id\s*[=:]\s*["\']([^"\']+)["\']', content)
    if id_match:
        return id_match.group(1)
    
    return "default_project"


def add_env_configuration(dry_run: bool = False):
    """Add adaptive RAG configuration to .env file."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("\n⚠️  No .env file found. Creating from .env.example...")
        if not dry_run:
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file")
        return
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    if "USE_ADAPTIVE_RAG" in content:
        print("\n✅ .env already has adaptive RAG configuration")
        return
    
    # Add adaptive RAG configuration
    adaptive_config = """
# Adaptive RAG Configuration
USE_ADAPTIVE_RAG=true
ADAPTIVE_RATE=0.1
OUTLIER_METHOD=mad
TARGET_CHUNKS_PER_RETRIEVAL=5
"""
    
    print("\n📄 .env file:")
    print("   ✓ Adding adaptive RAG configuration")
    
    if not dry_run:
        with open(env_file, 'a') as f:
            f.write(adaptive_config)
        print("   ✅ Updated")
    else:
        print("   🔍 (dry run - no changes made)")


def find_rag_usage_files() -> list:
    """Find all Python files that use RAG service."""
    files = []
    
    # Patterns to look for
    patterns = [
        "from.*rag_service import",
        "RAGService\\(",
        "RAGClient\\(",
        "rag_client\\.",
        "rag_service\\."
    ]
    
    # Search in src directory
    src_dir = Path("src")
    if src_dir.exists():
        for py_file in src_dir.rglob("*.py"):
            # Skip adaptive files themselves
            if "adaptive" in py_file.name:
                continue
                
            with open(py_file, 'r') as f:
                content = f.read()
                
            if any(re.search(pattern, content) for pattern in patterns):
                files.append(py_file)
    
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Migrate codebase to use adaptive RAG service"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="Specific files to migrate (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Adaptive RAG Migration Tool")
    print("=" * 50)
    
    # Step 1: Update .env configuration
    print("\n📋 Step 1: Environment Configuration")
    add_env_configuration(args.dry_run)
    
    # Step 2: Find files to migrate
    print("\n🔍 Step 2: Finding files that use RAG service...")
    
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = find_rag_usage_files()
    
    print(f"Found {len(files)} files using RAG service")
    
    # Step 3: Migrate files
    if files:
        print("\n✏️  Step 3: Updating files...")
        updated_count = 0
        
        for file_path in files:
            if migrate_imports(file_path, args.dry_run):
                updated_count += 1
        
        print(f"\n📊 Summary: {updated_count}/{len(files)} files need updates")
    
    # Step 4: Show next steps
    print("\n📌 Next Steps:")
    print("1. Review the changes made by this script")
    print("2. Set USE_ADAPTIVE_RAG=true in your .env file")
    print("3. Run your tests to ensure everything works")
    print("4. Monitor adaptive performance with rag_client.get_adaptive_stats()")
    
    if args.dry_run:
        print("\n💡 This was a dry run. Run without --dry-run to apply changes.")
    else:
        print("\n✅ Migration complete!")
        print("\n🎉 Your RAG service now has adaptive similarity gating!")
        print("   - Better relevance filtering")
        print("   - Project-specific learning")
        print("   - Automatic quality improvement")


if __name__ == "__main__":
    main()
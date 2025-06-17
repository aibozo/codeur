#!/bin/bash
# Clean up ChromaDB to fix schema issues

echo "🧹 Cleaning ChromaDB data..."

# Remove .rag directories
find . -name ".rag" -type d -exec rm -rf {} + 2>/dev/null

# Remove .chroma directories
find . -name ".chroma" -type d -exec rm -rf {} + 2>/dev/null

# Remove chroma_db directories
find . -name "chroma_db" -type d -exec rm -rf {} + 2>/dev/null

echo "✅ ChromaDB cleanup complete!"
echo "The database will be recreated with the correct schema on next use."
"""
Code chunking strategies for the RAG service.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from .models import CodeChunk, ChunkType

logger = logging.getLogger(__name__)


class CodeChunker:
    """
    Chunks code files into semantic units for indexing.
    
    Supports multiple strategies:
    - Function/class level chunking
    - Fixed-size windowing
    - AST-based chunking (future)
    """
    
    def __init__(self, 
                 chunk_size: int = 1500,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 100):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size for chunks in characters
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum size for a chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Language-specific patterns
        self.language_patterns = {
            "python": {
                "function": re.compile(r'^(async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
                "class": re.compile(r'^class\s+(\w+)\s*[\(:]', re.MULTILINE),
                "method": re.compile(r'^(\s+)(async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
            },
            "javascript": {
                "function": re.compile(r'(function\s+(\w+)|const\s+(\w+)\s*=\s*(async\s+)?function|\w+\s*:\s*(async\s+)?function)', re.MULTILINE),
                "class": re.compile(r'class\s+(\w+)', re.MULTILINE),
            },
            "typescript": {
                "function": re.compile(r'(function\s+(\w+)|const\s+(\w+)\s*=\s*(async\s+)?function|\w+\s*:\s*(async\s+)?function)', re.MULTILINE),
                "class": re.compile(r'class\s+(\w+)', re.MULTILINE),
                "interface": re.compile(r'interface\s+(\w+)', re.MULTILINE),
            }
        }
    
    def chunk_file(self, 
                   content: str, 
                   file_path: str,
                   language: Optional[str] = None) -> List[CodeChunk]:
        """
        Chunk a code file into semantic units.
        
        Args:
            content: File content
            file_path: Path to the file
            language: Programming language (auto-detected if None)
            
        Returns:
            List of code chunks
        """
        if not content.strip():
            return []
        
        # Auto-detect language if not provided
        if not language:
            language = self._detect_language(file_path)
        
        # Try semantic chunking first
        chunks = self._semantic_chunk(content, file_path, language)
        
        # Fall back to sliding window if no semantic chunks
        if not chunks:
            chunks = self._window_chunk(content, file_path, language)
        
        return chunks
    
    def _semantic_chunk(self, 
                       content: str, 
                       file_path: str,
                       language: str) -> List[CodeChunk]:
        """
        Chunk based on semantic units (functions, classes, etc).
        """
        chunks = []
        lines = content.splitlines()
        
        # Get language patterns
        patterns = self.language_patterns.get(language, {})
        if not patterns:
            return []
        
        # Find all semantic boundaries
        boundaries = []
        
        # Find functions and classes
        for pattern_name, pattern in patterns.items():
            for match in pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                
                # Extract symbol name
                groups = match.groups()
                symbol_name = None
                for g in groups:
                    if g and g.strip() and g.strip() not in ['async', 'const', 'function', ':']:
                        symbol_name = g.strip()
                        break
                
                boundaries.append({
                    'line': line_no,
                    'type': pattern_name,
                    'name': symbol_name,
                    'indent': len(match.group(1)) if pattern_name == 'method' else 0
                })
        
        # Sort boundaries by line number
        boundaries.sort(key=lambda x: x['line'])
        
        # Create chunks from boundaries
        for i, boundary in enumerate(boundaries):
            start_line = boundary['line']
            
            # Determine end line
            if i + 1 < len(boundaries):
                # For methods, only go until the next method at the same indent level
                if boundary['type'] == 'method':
                    end_line = start_line
                    for j in range(i + 1, len(boundaries)):
                        if boundaries[j]['indent'] <= boundary['indent']:
                            end_line = boundaries[j]['line'] - 1
                            break
                    else:
                        end_line = len(lines)
                else:
                    end_line = boundaries[i + 1]['line'] - 1
            else:
                end_line = len(lines)
            
            # Extract chunk content
            chunk_lines = lines[start_line - 1:end_line]
            chunk_content = '\n'.join(chunk_lines)
            
            # Skip if too small
            if len(chunk_content) < self.min_chunk_size:
                continue
            
            # Create chunk
            chunk_type = ChunkType.FUNCTION if boundary['type'] == 'function' else \
                        ChunkType.CLASS if boundary['type'] == 'class' else \
                        ChunkType.METHOD if boundary['type'] == 'method' else \
                        ChunkType.GENERAL
            
            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                chunk_type=chunk_type,
                language=language,
                symbol_name=boundary['name'],
                metadata={
                    'indent_level': boundary.get('indent', 0)
                }
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _window_chunk(self, 
                     content: str, 
                     file_path: str,
                     language: str) -> List[CodeChunk]:
        """
        Chunk using sliding window approach.
        """
        chunks = []
        lines = content.splitlines()
        
        # Calculate window parameters
        window_size = self.chunk_size // 50  # Approximate lines
        overlap = self.chunk_overlap // 50
        
        i = 0
        while i < len(lines):
            # Determine chunk boundaries
            start_line = i + 1
            end_line = min(i + window_size, len(lines))
            
            # Extract chunk
            chunk_lines = lines[i:end_line]
            chunk_content = '\n'.join(chunk_lines)
            
            # Skip if too small
            if len(chunk_content) < self.min_chunk_size:
                break
            
            # Create chunk
            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                chunk_type=ChunkType.GENERAL,
                language=language,
                metadata={
                    'window_chunk': True
                }
            )
            
            chunks.append(chunk)
            
            # Move window
            i += window_size - overlap
        
        return chunks
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'matlab',
            '.lua': 'lua',
            '.pl': 'perl',
            '.sh': 'bash',
            '.sql': 'sql',
            '.md': 'markdown',
            '.rst': 'rst',
            '.tex': 'latex',
        }
        
        path = Path(file_path)
        return extension_map.get(path.suffix.lower(), 'unknown')
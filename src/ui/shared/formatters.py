"""
Code formatting and diff display utilities.
"""

from typing import Optional, List, Tuple
import difflib
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import TerminalFormatter, HtmlFormatter
from pygments.util import ClassNotFound


class CodeFormatter:
    """Format code with syntax highlighting."""
    
    def __init__(self, style: str = "monokai"):
        self.style = style
        
    def format_terminal(self, code: str, language: Optional[str] = None) -> str:
        """Format code for terminal display."""
        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                lexer = guess_lexer(code)
                
            formatter = TerminalFormatter(style=self.style)
            return highlight(code, lexer, formatter)
        except (ClassNotFound, Exception):
            # Fallback to plain text
            return code
            
    def format_html(self, code: str, language: Optional[str] = None) -> str:
        """Format code for HTML display."""
        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                lexer = guess_lexer(code)
                
            formatter = HtmlFormatter(style=self.style)
            return highlight(code, lexer, formatter)
        except (ClassNotFound, Exception):
            # Fallback to pre-formatted text
            return f"<pre>{code}</pre>"
            
    def get_css(self) -> str:
        """Get CSS for HTML formatting."""
        formatter = HtmlFormatter(style=self.style)
        return formatter.get_style_defs('.highlight')


class DiffFormatter:
    """Format git diffs with syntax highlighting."""
    
    def __init__(self):
        self.code_formatter = CodeFormatter()
        
    def format_unified_diff(self, old_content: str, new_content: str, 
                          old_name: str = "old", new_name: str = "new") -> str:
        """Create and format a unified diff."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=old_name,
            tofile=new_name
        )
        
        return ''.join(diff)
        
    def format_side_by_side(self, old_content: str, new_content: str, 
                           width: int = 80) -> List[Tuple[str, str]]:
        """Create side-by-side diff."""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        differ = difflib.Differ()
        diff = list(differ.compare(old_lines, new_lines))
        
        result = []
        for line in diff:
            if line.startswith('- '):
                result.append((line[2:], ''))
            elif line.startswith('+ '):
                result.append(('', line[2:]))
            elif line.startswith('  '):
                result.append((line[2:], line[2:]))
                
        return result
        
    def highlight_diff_terminal(self, diff: str) -> str:
        """Add terminal colors to diff."""
        lines = []
        for line in diff.splitlines():
            if line.startswith('+'):
                lines.append(f"\033[32m{line}\033[0m")  # Green
            elif line.startswith('-'):
                lines.append(f"\033[31m{line}\033[0m")  # Red
            elif line.startswith('@'):
                lines.append(f"\033[36m{line}\033[0m")  # Cyan
            else:
                lines.append(line)
                
        return '\n'.join(lines)
        
    def highlight_diff_html(self, diff: str) -> str:
        """Add HTML styling to diff."""
        lines = []
        for line in diff.splitlines():
            if line.startswith('+'):
                lines.append(f'<span class="diff-add">{line}</span>')
            elif line.startswith('-'):
                lines.append(f'<span class="diff-remove">{line}</span>')
            elif line.startswith('@'):
                lines.append(f'<span class="diff-hunk">{line}</span>')
            else:
                lines.append(line)
                
        return '<pre>' + '\n'.join(lines) + '</pre>'
        
    def get_diff_css(self) -> str:
        """Get CSS for diff styling."""
        return """
        .diff-add { color: #00FF88; background-color: #003300; }
        .diff-remove { color: #FF0066; background-color: #330000; }
        .diff-hunk { color: #00D9FF; font-weight: bold; }
        """
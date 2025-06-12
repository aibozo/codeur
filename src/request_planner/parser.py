"""
Request parser for understanding user intent.

This module analyzes natural language requests to determine what
the user wants to accomplish.
"""

import re
from typing import Dict, Any, List, Optional


class RequestParser:
    """
    Parses natural language requests to understand user intent.
    
    This is a simplified rule-based parser that will be enhanced
    with LLM capabilities in the future.
    """
    
    def __init__(self):
        """Initialize the request parser."""
        # Keywords for different intent types
        self.feature_keywords = [
            'add', 'implement', 'create', 'build', 'develop', 'introduce',
            'support', 'enable', 'integrate'
        ]
        
        self.bug_keywords = [
            'fix', 'bug', 'error', 'issue', 'problem', 'broken', 'fail',
            'crash', 'wrong', 'incorrect', 'repair', 'resolve'
        ]
        
        self.refactor_keywords = [
            'refactor', 'improve', 'optimize', 'clean', 'reorganize',
            'restructure', 'simplify', 'enhance', 'modernize'
        ]
        
        self.test_keywords = [
            'test', 'testing', 'coverage', 'unit test', 'integration test',
            'spec', 'specification'
        ]
        
        self.doc_keywords = [
            'document', 'documentation', 'readme', 'docs', 'explain',
            'describe', 'comment'
        ]
    
    def parse(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language request to understand intent.
        
        Args:
            request: The user's request
            
        Returns:
            Parsed intent information
        """
        request_lower = request.lower()
        
        # Determine intent type
        intent_type = self._determine_intent_type(request_lower)
        
        # Extract specific information based on intent
        intent = {
            "type": intent_type,
            "original_request": request
        }
        
        if intent_type == "add_feature":
            intent.update(self._parse_feature_request(request))
        elif intent_type == "fix_bug":
            intent.update(self._parse_bug_request(request))
        elif intent_type == "refactor":
            intent.update(self._parse_refactor_request(request))
        elif intent_type == "add_test":
            intent.update(self._parse_test_request(request))
        elif intent_type == "update_docs":
            intent.update(self._parse_doc_request(request))
        else:
            intent.update(self._parse_generic_request(request))
        
        return intent
    
    def _determine_intent_type(self, request_lower: str) -> str:
        """Determine the type of intent from the request."""
        # Check for specific keywords
        if any(keyword in request_lower for keyword in self.bug_keywords):
            return "fix_bug"
        elif any(keyword in request_lower for keyword in self.feature_keywords):
            return "add_feature"
        elif any(keyword in request_lower for keyword in self.refactor_keywords):
            return "refactor"
        elif any(keyword in request_lower for keyword in self.test_keywords):
            return "add_test"
        elif any(keyword in request_lower for keyword in self.doc_keywords):
            return "update_docs"
        else:
            return "generic"
    
    def _parse_feature_request(self, request: str) -> Dict[str, Any]:
        """Parse a feature addition request."""
        result = {}
        
        # Try to extract what feature to add
        # Look for patterns like "add X to Y" or "implement Z"
        patterns = [
            r'add\s+(\w+(?:\s+\w+)*)\s+to\s+(\w+)',
            r'implement\s+(\w+(?:\s+\w+)*)',
            r'create\s+(?:a\s+)?(\w+(?:\s+\w+)*)',
            r'build\s+(?:a\s+)?(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, request, re.I)
            if match:
                if match.lastindex == 2:
                    result["feature"] = match.group(1)
                    result["target"] = match.group(2)
                else:
                    result["feature"] = match.group(1)
                break
        
        # Extract function/class names
        func_match = re.search(r'\b(\w+)\s*\(\s*\)', request)
        if func_match:
            result["function_name"] = func_match.group(1)
        
        return result
    
    def _parse_bug_request(self, request: str) -> Dict[str, Any]:
        """Parse a bug fix request."""
        result = {}
        
        # Look for specific error mentions
        error_match = re.search(r'(error|exception|failure):\s*(.+?)(?:\.|$)', request, re.I)
        if error_match:
            result["error_type"] = error_match.group(2).strip()
        
        # Look for function/module mentions
        in_match = re.search(r'in\s+(?:the\s+)?(\w+(?:\.\w+)*)', request, re.I)
        if in_match:
            result["location"] = in_match.group(1)
        
        return result
    
    def _parse_refactor_request(self, request: str) -> Dict[str, Any]:
        """Parse a refactoring request."""
        result = {}
        
        # Look for what to refactor
        patterns = [
            r'refactor\s+(?:the\s+)?(\w+(?:\s+\w+)*)',
            r'improve\s+(?:the\s+)?(\w+(?:\s+\w+)*)',
            r'clean\s+up\s+(?:the\s+)?(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, request, re.I)
            if match:
                result["target"] = match.group(1)
                break
        
        # Look for specific improvements
        if 'performance' in request.lower():
            result["goal"] = "performance"
        elif 'readability' in request.lower() or 'readable' in request.lower():
            result["goal"] = "readability"
        elif 'maintainability' in request.lower():
            result["goal"] = "maintainability"
        
        return result
    
    def _parse_test_request(self, request: str) -> Dict[str, Any]:
        """Parse a test-related request."""
        result = {}
        
        # Look for what to test
        for_match = re.search(r'(?:test|tests)\s+for\s+(?:the\s+)?(\w+(?:\s+\w+)*)', request, re.I)
        if for_match:
            result["target"] = for_match.group(1)
        
        # Determine test type
        if 'unit' in request.lower():
            result["test_type"] = "unit"
        elif 'integration' in request.lower():
            result["test_type"] = "integration"
        elif 'end-to-end' in request.lower() or 'e2e' in request.lower():
            result["test_type"] = "e2e"
        
        return result
    
    def _parse_doc_request(self, request: str) -> Dict[str, Any]:
        """Parse a documentation request."""
        result = {}
        
        # Look for what to document
        patterns = [
            r'document\s+(?:the\s+)?(\w+(?:\s+\w+)*)',
            r'add\s+documentation\s+(?:for|to)\s+(?:the\s+)?(\w+(?:\s+\w+)*)',
            r'explain\s+(?:the\s+)?(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, request, re.I)
            if match:
                result["target"] = match.group(1)
                break
        
        return result
    
    def _parse_generic_request(self, request: str) -> Dict[str, Any]:
        """Parse a generic request."""
        result = {}
        
        # Try to extract any function or file names
        func_match = re.search(r'\b(\w+)\s*\(\s*\)', request)
        if func_match:
            result["function_name"] = func_match.group(1)
        
        file_match = re.search(r'(\w+\.\w+)', request)
        if file_match:
            result["file_name"] = file_match.group(1)
        
        return result
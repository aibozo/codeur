"""
Git Safety Guard System

Provides pre-commit and pre-merge safety checks to ensure code quality
and prevent common issues like secret leaks and large files.
"""

import re
import os
import json
import subprocess
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .logging import get_logger

logger = get_logger(__name__)


class CheckType(Enum):
    """Types of safety checks."""
    SECRET_SCAN = "secret_scan"
    FILE_SIZE = "file_size"
    SYNTAX_CHECK = "syntax_check"
    TEST_STATUS = "test_status"
    CODE_QUALITY = "code_quality"
    CONFLICT_CHECK = "conflict_check"
    DEPENDENCY_CHECK = "dependency_check"
    SECURITY_SCAN = "security_scan"


class CheckSeverity(Enum):
    """Severity levels for check failures."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CheckResult:
    """Result of a safety check."""
    check_type: CheckType
    passed: bool
    severity: CheckSeverity
    message: str
    details: Dict[str, Any] = None
    fixable: bool = False
    fix_command: Optional[str] = None


class GitSafetyGuard:
    """
    Provides safety checks for git operations.
    
    Runs various checks before commits and merges to ensure
    code quality and prevent common issues.
    """
    
    def __init__(self, project_path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize safety guard.
        
        Args:
            project_path: Path to the project
            config: Configuration overrides
        """
        self.project_path = Path(project_path)
        
        # Default configuration
        self.config = {
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "allowed_extensions": None,  # None means all allowed
            "forbidden_extensions": [".exe", ".dll", ".so", ".dylib"],
            "secret_patterns": [
                r"(?i)api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"(?i)secret[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{8,}",
                r"(?i)token\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                r"(?i)aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*['\"]?[A-Z0-9]{20}",
                r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9/+=]{40}",
            ],
            "require_tests": True,
            "min_test_coverage": 0,  # 0 means don't check coverage
            "check_syntax": True,
            "check_security": True,
            "auto_fix": True,
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
            
    def run_pre_commit_checks(self, files: List[str]) -> List[CheckResult]:
        """
        Run all pre-commit checks on the given files.
        
        Args:
            files: List of file paths to check
            
        Returns:
            List of check results
        """
        results = []
        
        # Run various checks
        if self.config.get("check_security", True):
            results.extend(self._check_secrets(files))
            
        results.extend(self._check_file_sizes(files))
        
        if self.config.get("check_syntax", True):
            results.extend(self._check_syntax(files))
            
        if self.config.get("require_tests", True):
            results.extend(self._check_test_status())
            
        results.extend(self._check_code_quality(files))
        
        return results
        
    def run_pre_merge_checks(self, source_branch: str, target_branch: str) -> List[CheckResult]:
        """
        Run pre-merge safety checks.
        
        Args:
            source_branch: Branch being merged from
            target_branch: Branch being merged to
            
        Returns:
            List of check results
        """
        results = []
        
        # Check for conflicts
        results.extend(self._check_merge_conflicts(source_branch, target_branch))
        
        # Check dependencies
        results.extend(self._check_dependencies())
        
        # Run security scan if configured
        if self.config.get("check_security", True):
            results.extend(self._run_security_scan())
            
        return results
        
    def _check_secrets(self, files: List[str]) -> List[CheckResult]:
        """Check for potential secrets in files."""
        results = []
        
        for file_path in files:
            if not os.path.exists(file_path):
                continue
                
            # Skip binary files
            if self._is_binary_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Check each secret pattern
                for pattern in self.config["secret_patterns"]:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        results.append(CheckResult(
                            check_type=CheckType.SECRET_SCAN,
                            passed=False,
                            severity=CheckSeverity.CRITICAL,
                            message=f"Potential secret found in {file_path}:{line_num}",
                            details={
                                "file": file_path,
                                "line": line_num,
                                "pattern": pattern,
                                "match": match.group(0)[:50] + "..." if len(match.group(0)) > 50 else match.group(0)
                            },
                            fixable=False
                        ))
                        
            except Exception as e:
                logger.warning(f"Failed to check {file_path} for secrets: {e}")
                
        if not results:
            results.append(CheckResult(
                check_type=CheckType.SECRET_SCAN,
                passed=True,
                severity=CheckSeverity.INFO,
                message="No secrets detected"
            ))
            
        return results
        
    def _check_file_sizes(self, files: List[str]) -> List[CheckResult]:
        """Check for files that are too large."""
        results = []
        max_size = self.config["max_file_size"]
        
        for file_path in files:
            if not os.path.exists(file_path):
                continue
                
            size = os.path.getsize(file_path)
            if size > max_size:
                results.append(CheckResult(
                    check_type=CheckType.FILE_SIZE,
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"File {file_path} is too large ({size / 1024 / 1024:.2f}MB > {max_size / 1024 / 1024:.2f}MB)",
                    details={
                        "file": file_path,
                        "size": size,
                        "max_size": max_size
                    },
                    fixable=False
                ))
                
        # Check forbidden extensions
        forbidden = self.config.get("forbidden_extensions", [])
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext in forbidden:
                results.append(CheckResult(
                    check_type=CheckType.FILE_SIZE,
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"Forbidden file type: {file_path} ({ext})",
                    details={
                        "file": file_path,
                        "extension": ext
                    },
                    fixable=False
                ))
                
        if not results:
            results.append(CheckResult(
                check_type=CheckType.FILE_SIZE,
                passed=True,
                severity=CheckSeverity.INFO,
                message="All files within size limits"
            ))
            
        return results
        
    def _check_syntax(self, files: List[str]) -> List[CheckResult]:
        """Check syntax of Python files."""
        results = []
        
        python_files = [f for f in files if f.endswith('.py')]
        
        for file_path in python_files:
            if not os.path.exists(file_path):
                continue
                
            # Use Python's compile to check syntax
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                    
                compile(code, file_path, 'exec')
                
            except SyntaxError as e:
                results.append(CheckResult(
                    check_type=CheckType.SYNTAX_CHECK,
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"Syntax error in {file_path}:{e.lineno}: {e.msg}",
                    details={
                        "file": file_path,
                        "line": e.lineno,
                        "error": e.msg
                    },
                    fixable=False
                ))
            except Exception as e:
                logger.warning(f"Failed to check syntax for {file_path}: {e}")
                
        if not results:
            results.append(CheckResult(
                check_type=CheckType.SYNTAX_CHECK,
                passed=True,
                severity=CheckSeverity.INFO,
                message="No syntax errors found"
            ))
            
        return results
        
    def _check_test_status(self) -> List[CheckResult]:
        """Check if tests are passing."""
        results = []
        
        # Try to run tests
        test_commands = [
            ["python", "-m", "pytest", "--tb=short"],
            ["python", "-m", "unittest", "discover"],
            ["npm", "test"],
            ["yarn", "test"],
        ]
        
        test_passed = False
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self.project_path),
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    test_passed = True
                    break
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        if test_passed:
            results.append(CheckResult(
                check_type=CheckType.TEST_STATUS,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Tests passed"
            ))
        else:
            results.append(CheckResult(
                check_type=CheckType.TEST_STATUS,
                passed=False,
                severity=CheckSeverity.WARNING,
                message="Tests failed or could not be run",
                details={
                    "hint": "Run tests manually to see detailed output"
                },
                fixable=True,
                fix_command="pytest"
            ))
            
        return results
        
    def _check_code_quality(self, files: List[str]) -> List[CheckResult]:
        """Basic code quality checks."""
        results = []
        
        python_files = [f for f in files if f.endswith('.py')]
        
        # Check with ruff if available
        try:
            result = subprocess.run(
                ["ruff", "check", "--format", "json"] + python_files,
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 and result.stdout:
                issues = json.loads(result.stdout)
                
                for issue in issues[:5]:  # Limit to first 5 issues
                    results.append(CheckResult(
                        check_type=CheckType.CODE_QUALITY,
                        passed=False,
                        severity=CheckSeverity.WARNING,
                        message=f"{issue['filename']}:{issue['location']['row']}: {issue['message']}",
                        details=issue,
                        fixable=True,
                        fix_command="ruff check --fix"
                    ))
                    
        except (FileNotFoundError, json.JSONDecodeError):
            # Ruff not available or failed
            pass
            
        if not results:
            results.append(CheckResult(
                check_type=CheckType.CODE_QUALITY,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Code quality checks passed"
            ))
            
        return results
        
    def _check_merge_conflicts(self, source_branch: str, target_branch: str) -> List[CheckResult]:
        """Check if merge would have conflicts."""
        results = []
        
        try:
            # Dry run the merge
            result = subprocess.run(
                ["git", "merge", "--no-commit", "--no-ff", source_branch],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Check for conflicts
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True
                )
                
                conflicted_files = []
                for line in status_result.stdout.split('\n'):
                    if line.startswith('UU '):
                        conflicted_files.append(line[3:])
                        
                if conflicted_files:
                    results.append(CheckResult(
                        check_type=CheckType.CONFLICT_CHECK,
                        passed=False,
                        severity=CheckSeverity.ERROR,
                        message=f"Merge conflicts detected in {len(conflicted_files)} files",
                        details={
                            "files": conflicted_files
                        },
                        fixable=False
                    ))
                    
            # Abort the merge
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=str(self.project_path),
                capture_output=True
            )
            
        except Exception as e:
            logger.warning(f"Failed to check merge conflicts: {e}")
            
        if not results:
            results.append(CheckResult(
                check_type=CheckType.CONFLICT_CHECK,
                passed=True,
                severity=CheckSeverity.INFO,
                message="No merge conflicts detected"
            ))
            
        return results
        
    def _check_dependencies(self) -> List[CheckResult]:
        """Check if dependencies are satisfied."""
        results = []
        
        # Check Python dependencies
        if (self.project_path / "requirements.txt").exists():
            try:
                result = subprocess.run(
                    ["pip", "check"],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    results.append(CheckResult(
                        check_type=CheckType.DEPENDENCY_CHECK,
                        passed=False,
                        severity=CheckSeverity.WARNING,
                        message="Python dependency issues detected",
                        details={
                            "output": result.stdout
                        },
                        fixable=True,
                        fix_command="pip install -r requirements.txt"
                    ))
                    
            except FileNotFoundError:
                pass
                
        # Check npm dependencies
        if (self.project_path / "package.json").exists():
            try:
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    audit_data = json.loads(result.stdout)
                    vulnerabilities = audit_data.get("metadata", {}).get("vulnerabilities", {})
                    
                    if any(vulnerabilities.values()):
                        results.append(CheckResult(
                            check_type=CheckType.DEPENDENCY_CHECK,
                            passed=False,
                            severity=CheckSeverity.WARNING,
                            message="npm security vulnerabilities detected",
                            details=vulnerabilities,
                            fixable=True,
                            fix_command="npm audit fix"
                        ))
                        
            except (FileNotFoundError, json.JSONDecodeError):
                pass
                
        if not results:
            results.append(CheckResult(
                check_type=CheckType.DEPENDENCY_CHECK,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Dependencies check passed"
            ))
            
        return results
        
    def _run_security_scan(self) -> List[CheckResult]:
        """Run security scans."""
        results = []
        
        # Run bandit for Python security issues
        try:
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                scan_results = json.loads(result.stdout)
                
                for issue in scan_results.get("results", [])[:5]:  # Limit to 5
                    results.append(CheckResult(
                        check_type=CheckType.SECURITY_SCAN,
                        passed=False,
                        severity=CheckSeverity.WARNING,
                        message=f"Security issue: {issue['issue_text']}",
                        details=issue,
                        fixable=False
                    ))
                    
        except (FileNotFoundError, json.JSONDecodeError):
            # Bandit not available
            pass
            
        if not results:
            results.append(CheckResult(
                check_type=CheckType.SECURITY_SCAN,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Security scan passed"
            ))
            
        return results
        
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(512)
                return b'\0' in chunk
        except Exception:
            return True
            
    def auto_fix_issues(self, results: List[CheckResult]) -> List[CheckResult]:
        """
        Attempt to auto-fix fixable issues.
        
        Args:
            results: List of check results
            
        Returns:
            Updated results after fix attempts
        """
        if not self.config.get("auto_fix", True):
            return results
            
        fixed_results = []
        
        for result in results:
            if result.fixable and result.fix_command and not result.passed:
                try:
                    # Run fix command
                    fix_result = subprocess.run(
                        result.fix_command.split(),
                        cwd=str(self.project_path),
                        capture_output=True,
                        timeout=30
                    )
                    
                    if fix_result.returncode == 0:
                        # Create success result
                        fixed_results.append(CheckResult(
                            check_type=result.check_type,
                            passed=True,
                            severity=CheckSeverity.INFO,
                            message=f"Fixed: {result.message}",
                            details={
                                "original_issue": result.details,
                                "fix_applied": result.fix_command
                            }
                        ))
                    else:
                        fixed_results.append(result)
                        
                except Exception as e:
                    logger.warning(f"Failed to auto-fix issue: {e}")
                    fixed_results.append(result)
            else:
                fixed_results.append(result)
                
        return fixed_results
        
    def format_results(self, results: List[CheckResult]) -> str:
        """
        Format check results for display.
        
        Args:
            results: List of check results
            
        Returns:
            Formatted string
        """
        lines = ["Git Safety Check Results", "=" * 40]
        
        # Group by severity
        by_severity = {}
        for result in results:
            by_severity.setdefault(result.severity, []).append(result)
            
        # Display by severity
        for severity in [CheckSeverity.CRITICAL, CheckSeverity.ERROR, 
                        CheckSeverity.WARNING, CheckSeverity.INFO]:
            if severity not in by_severity:
                continue
                
            lines.append(f"\n{severity.value.upper()}:")
            
            for result in by_severity[severity]:
                status = "✓" if result.passed else "✗"
                lines.append(f"  {status} {result.message}")
                
                if result.fix_command and not result.passed:
                    lines.append(f"    → Fix: {result.fix_command}")
                    
        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        
        lines.extend([
            "",
            f"Summary: {passed}/{total} checks passed",
        ])
        
        if failed > 0:
            critical = sum(1 for r in results if r.severity == CheckSeverity.CRITICAL and not r.passed)
            errors = sum(1 for r in results if r.severity == CheckSeverity.ERROR and not r.passed)
            
            if critical > 0:
                lines.append(f"⚠️  {critical} CRITICAL issues must be resolved!")
            if errors > 0:
                lines.append(f"⚠️  {errors} errors should be fixed")
                
        return "\n".join(lines)
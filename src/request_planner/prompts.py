"""
Prompt templates and few-shot examples for the Request Planner.

This module contains carefully crafted prompts to guide the LLM
in creating high-quality implementation plans.
"""

# Few-shot examples for different types of requests
FEW_SHOT_EXAMPLES = [
    {
        "request": "Add retry logic to the fetch_data function with exponential backoff",
        "plan": {
            "steps": [
                {
                    "order": 1,
                    "goal": "Add retry decorator with exponential backoff to fetch_data function",
                    "kind": "edit",
                    "hints": [
                        "Use tenacity library or implement custom retry logic",
                        "Add configurable max retries (default 3)",
                        "Implement exponential backoff (2^n seconds)"
                    ]
                },
                {
                    "order": 2,
                    "goal": "Add error handling for different failure types",
                    "kind": "edit",
                    "hints": [
                        "Handle network errors differently from API errors",
                        "Don't retry on 4xx client errors",
                        "Log retry attempts with context"
                    ]
                },
                {
                    "order": 3,
                    "goal": "Add unit tests for retry behavior",
                    "kind": "test",
                    "hints": [
                        "Test successful request (no retry needed)",
                        "Test transient failure recovery",
                        "Test max retries exceeded",
                        "Mock time.sleep for faster tests"
                    ]
                },
                {
                    "order": 4,
                    "goal": "Update function documentation",
                    "kind": "edit",
                    "hints": [
                        "Document retry behavior",
                        "Add examples of configuration",
                        "Note which errors trigger retries"
                    ]
                }
            ],
            "rationale": [
                "Retry logic improves reliability for transient network failures",
                "Exponential backoff prevents overwhelming the server",
                "Different error types need different handling strategies",
                "Tests ensure retry logic works correctly without side effects"
            ],
            "affected_paths": [
                "src/data/fetch.py",
                "tests/test_fetch.py",
                "requirements.txt"
            ],
            "complexity_label": "moderate",
            "estimated_tokens": 3500
        }
    },
    {
        "request": "Fix the authentication bug where users can't log in with email addresses containing plus signs",
        "plan": {
            "steps": [
                {
                    "order": 1,
                    "goal": "Fix email validation regex to accept plus signs",
                    "kind": "edit",
                    "hints": [
                        "Update regex pattern to include + character",
                        "Ensure proper escaping in the pattern",
                        "Consider using email-validator library"
                    ]
                },
                {
                    "order": 2,
                    "goal": "Add test cases for email edge cases",
                    "kind": "test",
                    "hints": [
                        "Test emails with plus signs (user+tag@domain.com)",
                        "Test other special characters",
                        "Test international domains"
                    ]
                },
                {
                    "order": 3,
                    "goal": "Check and update any email preprocessing",
                    "kind": "edit",
                    "hints": [
                        "Ensure plus signs aren't stripped during sanitization",
                        "Check database queries handle special characters",
                        "Verify URL encoding for email parameters"
                    ]
                }
            ],
            "rationale": [
                "Plus signs are valid in email addresses (RFC 5322)",
                "Bug prevents legitimate users from accessing the system",
                "Fix requires updating validation and ensuring data flow preserves special characters"
            ],
            "affected_paths": [
                "src/auth/validators.py",
                "src/auth/models.py",
                "tests/test_auth.py"
            ],
            "complexity_label": "trivial",
            "estimated_tokens": 2000
        }
    },
    {
        "request": "Refactor the user service to use dependency injection for better testability",
        "plan": {
            "steps": [
                {
                    "order": 1,
                    "goal": "Create interface definitions for user service dependencies",
                    "kind": "add",
                    "hints": [
                        "Define abstract base classes or protocols",
                        "Include database, cache, and email service interfaces",
                        "Keep interfaces focused and single-purpose"
                    ]
                },
                {
                    "order": 2,
                    "goal": "Refactor UserService to accept dependencies via constructor",
                    "kind": "refactor",
                    "hints": [
                        "Remove hardcoded instantiations",
                        "Add dependency parameters to __init__",
                        "Update all instantiation sites"
                    ]
                },
                {
                    "order": 3,
                    "goal": "Create dependency injection container",
                    "kind": "add",
                    "hints": [
                        "Simple container class to manage dependencies",
                        "Support singleton and factory patterns",
                        "Consider using existing DI library"
                    ]
                },
                {
                    "order": 4,
                    "goal": "Update tests to use mock dependencies",
                    "kind": "test",
                    "hints": [
                        "Replace real dependencies with mocks",
                        "Test UserService in isolation",
                        "Verify dependency interactions"
                    ]
                },
                {
                    "order": 5,
                    "goal": "Update application initialization",
                    "kind": "edit",
                    "hints": [
                        "Wire up dependencies at startup",
                        "Configure based on environment",
                        "Ensure proper cleanup on shutdown"
                    ]
                }
            ],
            "rationale": [
                "Dependency injection improves testability by allowing mock dependencies",
                "Reduces coupling between UserService and its dependencies",
                "Makes the system more modular and easier to maintain",
                "Enables better configuration management across environments"
            ],
            "affected_paths": [
                "src/services/user_service.py",
                "src/services/interfaces.py",
                "src/core/container.py",
                "src/main.py",
                "tests/test_user_service.py"
            ],
            "complexity_label": "complex",
            "estimated_tokens": 5000
        }
    },
    {
        "request": "Add power and square root methods to the calculator class",
        "plan": {
            "steps": [
                {
                    "order": 1,
                    "goal": "Add power method to Calculator class",
                    "kind": "edit",
                    "hints": [
                        "Implement power(a, b) method that returns a^b",
                        "Use the ** operator for exponentiation",
                        "Handle edge cases like negative exponents",
                        "Add method to calculator.py"
                    ]
                },
                {
                    "order": 2,
                    "goal": "Add square root method to Calculator class",
                    "kind": "edit",
                    "hints": [
                        "Implement square_root(a) method",
                        "Handle negative numbers appropriately (raise ValueError)",
                        "Use math.sqrt or a ** 0.5",
                        "Add method to calculator.py"
                    ]
                },
                {
                    "order": 3,
                    "goal": "Add comprehensive tests for power method",
                    "kind": "test",
                    "hints": [
                        "Test positive integer exponents: power(2, 3) == 8",
                        "Test zero exponent: power(5, 0) == 1",
                        "Test negative exponents: power(2, -1) == 0.5",
                        "Test fractional base and exponent",
                        "Add tests to tests/test_calculator.py"
                    ]
                },
                {
                    "order": 4,
                    "goal": "Add comprehensive tests for square root method",
                    "kind": "test",
                    "hints": [
                        "Test perfect squares: square_root(4) == 2, square_root(9) == 3",
                        "Test non-perfect squares: square_root(2) ≈ 1.414",
                        "Test zero: square_root(0) == 0",
                        "Test negative numbers raise ValueError",
                        "Use pytest.raises for exception testing",
                        "Add tests to tests/test_calculator.py"
                    ]
                },
                {
                    "order": 5,
                    "goal": "Update calculator documentation",
                    "kind": "edit",
                    "hints": [
                        "Add docstrings for new methods",
                        "Include parameter descriptions",
                        "Document return values and exceptions",
                        "Add usage examples"
                    ]
                }
            ],
            "rationale": [
                "Power and square root are fundamental mathematical operations",
                "Separate test steps ensure comprehensive coverage for each method",
                "Granular steps make it easier to validate each feature independently",
                "Clear test hints guide proper test implementation with minimal mocks"
            ],
            "affected_paths": [
                "calculator.py",
                "tests/test_calculator.py"
            ],
            "complexity_label": "moderate",
            "estimated_tokens": 2500
        }
    }
]

# Chain-of-thought prompting template
CHAIN_OF_THOUGHT_TEMPLATE = """Let me analyze this request step by step:

1. **Understanding the request**: {request_summary}
2. **Current state analysis**: {current_state}
3. **Required changes**: {required_changes}
4. **Implementation approach**: {approach}
5. **Potential challenges**: {challenges}
6. **Testing strategy**: {testing}

Based on this analysis, here's my implementation plan:"""

# Error handling prompt
ERROR_HANDLING_PROMPT = """If you encounter any ambiguity in the request, make reasonable assumptions based on:
1. Common software development practices
2. The existing codebase patterns
3. The principle of least surprise

State any assumptions clearly in the rationale."""

# Complexity estimation guide
COMPLEXITY_GUIDE = """Estimate complexity based on:
- **Trivial**: Single file change, < 50 lines, no architectural impact
- **Moderate**: 2-5 files, < 200 lines, localized impact
- **Complex**: Many files, architectural changes, cross-cutting concerns"""
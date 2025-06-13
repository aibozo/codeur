# Codeur Improvement Plan - Code Review Findings

## Priority 0 (Critical - Do First)

### 1. Fix Logging Idempotency Issue
**Problem**: `setup_logging()` adds handlers unconditionally; multiple imports → duplicate log lines
**Fix**: Keep a module-level flag or check hasHandlers()
**File**: src/core/logging.py

### 2. Refactor CLI Monolith
**Problem**: Business logic lives in cli.py; difficult to test; violates SRP
**Fix**: Split into cli.py (Click facade) → commands/*.py containing pure functions
**File**: src/cli.py

### 3. Add Resilient Error Handling for LLM/Network
**Problem**: Only broad Exception catching; no timeouts, exponential back-off, or partial-failure logging
**Fix**: Create ResilientLLMClient with timeout, retry with jitter, and structured error codes
**Files**: src/llm.py, src/coding_agent/agent.py

## Priority 1 (High)

### 4. Add Memory Management for AST/RAG Cache
**Problem**: No memory limits on symbol cache & call graph
**Fix**: Add LRU eviction policy; expose metrics
**File**: src/code_planner/code_planner.py

### 5. Security - Fix Symlink Traversal
**Problem**: No check for symlink traversal inside project root
**Fix**: After Path.resolve(), check is_symlink() and validate; add .agent-security.yml support
**File**: src/core/security.py

### 6. Sandbox Git Operations
**Problem**: Git operations shell out without isolation
**Fix**: Use dulwich or temp clone with --work-tree/--git-dir
**File**: src/coding_agent/git_operations.py

## Priority 2 (Medium)

### 7. Centralize Configuration
**Problem**: Defaults in code; .env only for secrets
**Fix**: Single settings.py with pydantic-settings
**Files**: Create src/core/settings.py

### 8. Fix Code Style Issues
**Problem**: PEP-8 violations, long lines
**Fix**: Add ruff/flake8 + pre-commit hooks

### 9. Implement Structured Logging
**Problem**: Text logs hamper distributed tracing
**Fix**: Use structlog or JSON logging with request_id propagation

## Priority 3 (Low)

### 10. Remove Proto Files from VCS
**Problem**: Generated files can drift
**Fix**: Generate in CI; gitignore them

## Quick Wins This Week

1. **Path-escape unit tests** - 20 LOC, catches vulnerabilities
2. **Async agent wrapper with tenacity** - isolates LLM timeouts
3. **Lock requirements & enable Dependabot** - prevents surprise upgrades
4. **Structured JSON logging + request IDs** - minimal patch, huge payoff
5. **Add --dry-run CLI flag** - outputs git patch without applying

## Testing & CI

1. Add GitHub Actions workflow: lint → type-check → unit tests → integration tests
2. Increase unit coverage for SecurityManager, GitOperations, CLI
3. Property-based testing with hypothesis
4. Mutation testing with mutmut
5. Gate merges on pytest --cov ≥ 85%

## Implementation Order

1. **Week 1**: P0 fixes (logging, CLI refactor, resilient LLM client)
2. **Week 2**: Quick wins (tests, tenacity, requirements lock, dry-run)
3. **Week 3**: P1 fixes (memory management, security hardening, git sandboxing)
4. **Week 4**: CI/CD setup and testing improvements
5. **Week 5+**: P2/P3 fixes and architecture improvements
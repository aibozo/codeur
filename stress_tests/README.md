# AI Agent Stress Testing Framework

This directory contains a progressive stress testing suite designed to systematically evaluate and improve our multi-agent coding system.

## Overview

The stress tests are organized into 5 phases of increasing complexity:

1. **Phase 1**: Single-file applications (Basic GUI apps)
2. **Phase 2**: Multi-file applications (Module organization)
3. **Phase 3**: External dependencies (Third-party integrations)
4. **Phase 4**: Multi-component systems (Client-server, complex state)
5. **Phase 5**: Full applications (Complete systems)

## Files

- `stress_tests.md` - Complete test suite documentation and roadmap
- `test_template.py` - Template for creating new stress tests
- `test_*.py` - Individual stress test implementations
- `run_tests.py` - Test runner for executing stress tests
- `results_*.json` - Test execution results (generated)

## Running Tests

### Run all tests:
```bash
python stress_tests/run_tests.py
```

### Run tests from a specific phase:
```bash
python stress_tests/run_tests.py --phase 1
```

### Run a specific test:
```bash
python stress_tests/test_todo_list.py
```

## Creating New Tests

1. Copy `test_template.py` to `test_<name>.py`
2. Update the `TEST_SPEC` dictionary with:
   - Test requirements and success criteria
   - Expected file structure
   - Complexity level and phase
3. Modify the task creation to match your test needs
4. Add verification logic for success criteria

## Test Metrics

Each test tracks:
- Execution time
- Token usage (and estimated cost)
- Model performance
- Retry counts
- Error details
- File creation success

## Current Status

✅ **Completed:**
- GUI Calculator (Phase 1) - Basic single-file app

🚧 **Ready to Test:**
- Todo List App (Phase 1) - Multi-file with persistence

📋 **Planned:**
- 18 additional tests across all phases

## Success Criteria

A test is considered successful if:
1. All required files are created
2. The application runs without errors
3. Core functionality works as specified
4. Code follows reasonable practices

## Next Steps

1. Run the Todo List test to validate multi-file handling
2. Document any failures or model limitations
3. Progress to Phase 2 tests
4. Adjust model selection based on complexity needs
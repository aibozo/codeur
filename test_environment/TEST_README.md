# Coding Agent Test Suite

This directory contains comprehensive tests for the enhanced coding agent with tool support.

## Test Structure

### Setup
- `setup_test_repo.py` - Creates a test repository with sample files
- `test_repo/` - The test repository (created by setup script)

### Test Files

1. **test_simple_task.py** - Basic context refinement test
   - Tests the LLM's ability to request appropriate tools
   - Simulates tool responses

2. **test_tool_usage.py** - Tool usage capabilities
   - Tests context refinement with tools
   - Direct tool testing
   - Error handling tests

3. **test_patch_generation.py** - Patch generation improvements
   - Tests line number inclusion in context
   - Context quality verification
   - File rewriter fallback testing

4. **test_enhanced_agent.py** - Full agent integration test
   - Tests a real coding task with o3 model
   - Verifies complete workflow

5. **test_comprehensive_agent.py** - Comprehensive test suite
   - Multiple test scenarios
   - Performance tracking
   - Success metrics
   - Results saved to JSON

### Test Runner
- `run_all_tests.py` - Runs all tests in sequence

## Running Tests

### Quick Start
```bash
# Run all tests
python run_all_tests.py

# Run individual tests
python test_simple_task.py
python test_tool_usage.py
python test_patch_generation.py
```

### Comprehensive Suite
```bash
# Run with gpt-4o (fast)
python test_comprehensive_agent.py

# Run with o3 model (slower but more accurate)
python test_comprehensive_agent.py --use-o3

# Specify custom repo
python test_comprehensive_agent.py --repo my_test_repo
```

## Test Scenarios

The comprehensive test suite includes:

1. **Error Handling Addition** - Add try/except to existing code
2. **Empty List Handling** - Refactor method to handle edge cases  
3. **Type Hints Addition** - Add type annotations
4. **Multi-file Feature** - Changes across multiple files
5. **New File Creation** - Create new file and integrate it

## Key Improvements Tested

1. **Line Numbers in Context** - Ensures accurate patch generation
2. **Full Context (No Truncation)** - Models get complete file content
3. **Tool Usage** - Agent can read files and search for context
4. **File Rewriter Fallback** - Alternative to patch generation
5. **Error Analysis** - Better feedback when patches fail

## Expected Behavior

The enhanced agent should:
- Use tools to read files before making changes
- Generate patches with correct line numbers
- Fall back to file rewriting if patches fail
- Provide clear feedback about what it's doing
- Handle multiple files in a single task

## Results

Test results are saved to `test_results.json` with:
- Pass/fail status
- Execution time
- Token usage
- Verification checks
- Process notes

## Debugging

To see more detailed output:
- Set logging to DEBUG in test files
- Check agent notes in results
- Look for "tool_read", "tool_search" in context blobs
- Verify line numbers in generated patches
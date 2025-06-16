# E2E Test Report

## Summary
- Total Tests: 8
- Passed: 0 ✓
- Failed: 8 ✗
- Skipped: 0 -
- Total Time: 3.81s

## Detailed Results

### ✗ Agent Initialization
- Status: FAILED
- Details: Architect.__init__() got an unexpected keyword argument 'project_root'

### ✗ Architect RAG Integration
- Status: FAILED
- Details: Architect.__init__() got an unexpected keyword argument 'project_root'

### ✗ Analyzer Functionality
- Status: FAILED
- Details: Analyzer.__init__() got an unexpected keyword argument 'project_root'

### ✗ Request Planner RAG
- Status: FAILED
- Details: RAG not available for Request Planner

### ✗ Code Planner RAG
- Status: FAILED
- Details: RAG not enabled

### ✗ Coding Agent Change Tracking
- Status: FAILED
- Details: 'DiffStats' object has no attribute 'net_change'

### ✗ Event System
- Status: FAILED
- Details: RealtimeService.__init__() missing 1 required positional argument: 'message_bus'

### ✗ Architecture Diagrams
- Status: FAILED
- Details: cannot import name 'Architecture' from 'src.analyzer.analyzer' (/home/riley/Programming/agent/src/analyzer/analyzer.py)

# Testing Guide

## Quick Start

### 1. Set up test environment

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Compile protobuf files
./scripts/compile_protos.sh

# Start Kafka (requires Docker)
python scripts/setup_messaging.py --start-kafka

# Create topics
python scripts/setup_messaging.py
```

### 2. Run tests

```bash
# Run all tests with setup
python tests/run_tests.py --setup

# Run only unit tests (no Kafka needed)
python tests/run_tests.py --type unit --no-kafka

# Run integration tests
python tests/run_tests.py --type integration

# Run specific test
python tests/run_tests.py -k test_message_consumption
```

### 3. Run simple E2E test

```bash
# This runs a complete end-to-end test
python tests/test_e2e_simple.py
```

## Test Structure

```
tests/
├── unit/                    # Unit tests (no external dependencies)
│   ├── test_models.py
│   ├── test_serializer.py
│   └── test_planner.py
├── integration/             # Integration tests (require Kafka)
│   └── test_request_planner_messaging.py
├── test_e2e_simple.py      # Simple E2E test script
└── run_tests.py            # Test runner with setup
```

## What the Tests Verify

### Unit Tests
- Model serialization/deserialization
- Message queue abstractions
- Planner logic without external dependencies

### Integration Tests
- Message consumption from Kafka
- Plan generation and emission
- Error handling and dead letter queues
- Graceful shutdown

### E2E Test
- Complete flow: ChangeRequest → Request Planner → Plan
- Message routing through correct topics
- Protobuf serialization in real scenario
- Service lifecycle management

## Troubleshooting

### Kafka not running
```bash
# Check if Kafka is running
docker ps | grep kafka

# Start Kafka
python scripts/setup_messaging.py --start-kafka

# Check Kafka UI
open http://localhost:8080
```

### Protobuf errors
```bash
# Recompile protos
./scripts/compile_protos.sh

# Check if files were generated
ls src/proto_gen/
```

### Test failures
```bash
# Run with verbose output
python tests/run_tests.py -v

# Run single test for debugging
python -m pytest tests/integration/test_request_planner_messaging.py::TestRequestPlannerMessaging::test_message_consumption -v
```

## Expected Output

### Successful E2E Test
```
🚀 Request Planner E2E Test
==================================================
✓ Connected to Kafka
✓ Created Request Planner service
✓ Created test request: e2e-test-a1b2c3d4
✓ Sent ChangeRequest to plan.in topic

⏳ Waiting for Request Planner to process...

✓ Received message on topic: plan.out
  Plan ID: 12345678-1234-1234-1234-123456789012
  Steps: 5
  Complexity: MODERATE
  Step 1: Analyze current file operations implementation
  Step 2: Add try-except blocks to file read operations
  Step 3: Implement logging for error cases
  ... and 2 more steps

✅ Test completed successfully!
   Received 2 messages

📋 Generated Plan Summary:
   - ID: 12345678-1234-1234-1234-123456789012
   - Parent Request: e2e-test-a1b2c3d4
   - Total Steps: 5
   - Affected Files: 3
   - Rationale Points: 4

🎉 All tests passed!
```

## Performance Expectations

- Message processing: < 100ms per message
- Plan generation: < 2s (without LLM)
- E2E latency: < 3s total
- Throughput: > 100 messages/second

## Next Steps

After tests pass:
1. Add more test scenarios
2. Test with LLM enabled
3. Add performance benchmarks
4. Test failure scenarios
5. Add load testing
#!/usr/bin/env python3
"""
Test runner for the agent system.

This script helps run different types of tests with proper setup.
"""

import subprocess
import sys
import os
from pathlib import Path
import time
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_kafka():
    """Check if Kafka is running."""
    try:
        from src.messaging import KafkaMessageQueue, QueueConfig
        config = QueueConfig(
            name="test",
            broker_url="localhost:9092"
        )
        mq = KafkaMessageQueue(config)
        healthy = mq.health_check()
        mq.close()
        return healthy
    except:
        return False


def compile_protos():
    """Compile protobuf files."""
    print("Compiling protobuf files...")
    script_path = Path(__file__).parent.parent / "scripts" / "compile_protos.sh"
    result = subprocess.run([str(script_path)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error compiling protos: {result.stderr}")
        return False
    print("✓ Protobuf files compiled")
    return True


def start_kafka():
    """Start Kafka if not running."""
    if check_kafka():
        print("✓ Kafka is already running")
        return True
    
    print("Starting Kafka...")
    setup_script = Path(__file__).parent.parent / "scripts" / "setup_messaging.py"
    result = subprocess.run(
        [sys.executable, str(setup_script), "--start-kafka"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error starting Kafka: {result.stderr}")
        return False
    
    # Wait for Kafka to be ready
    print("Waiting for Kafka to be ready...")
    for i in range(30):
        if check_kafka():
            print("✓ Kafka is ready")
            return True
        time.sleep(1)
    
    print("✗ Kafka failed to start")
    return False


def create_topics():
    """Create required topics."""
    print("Creating topics...")
    setup_script = Path(__file__).parent.parent / "scripts" / "setup_messaging.py"
    result = subprocess.run(
        [sys.executable, str(setup_script)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error creating topics: {result.stderr}")
        return False
    
    print("✓ Topics created")
    return True


def run_tests(test_type="all", verbose=False, specific_test=None):
    """Run the tests."""
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if test_type == "unit":
        cmd.extend(["tests/unit", "-m", "not integration"])
    elif test_type == "integration":
        cmd.extend(["tests/integration", "-m", "not slow"])
    elif test_type == "e2e":
        cmd.extend(["tests/integration", "-m", "integration"])
    else:
        cmd.append("tests/")
    
    if specific_test:
        cmd.extend(["-k", specific_test])
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    print(f"\nRunning tests: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="Run agent system tests")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "e2e"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Set up test infrastructure (Kafka, topics)"
    )
    parser.add_argument(
        "--no-kafka",
        action="store_true",
        help="Skip Kafka setup (for unit tests)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test output"
    )
    parser.add_argument(
        "-k",
        dest="specific_test",
        help="Run specific test by name pattern"
    )
    
    args = parser.parse_args()
    
    # Compile protos first
    if not compile_protos():
        print("Failed to compile protobuf files")
        sys.exit(1)
    
    # Set up infrastructure if needed
    if args.setup or (args.type in ["integration", "e2e", "all"] and not args.no_kafka):
        if not start_kafka():
            print("Failed to start Kafka")
            sys.exit(1)
        
        if not create_topics():
            print("Failed to create topics")
            sys.exit(1)
    
    # Run tests
    print("\n" + "="*60)
    print("Running tests...")
    print("="*60)
    
    exit_code = run_tests(args.type, args.verbose, args.specific_test)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
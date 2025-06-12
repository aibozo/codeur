#!/usr/bin/env python3
"""
Test Code Planner agent functionality.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.messaging import InMemoryMessageQueue, MessagingConfig
from src.messaging.serializer import register_agent_messages
from src.code_planner import CodePlanner
from src.code_planner.messaging_service import CodePlannerMessagingService
from src.proto_gen import messages_pb2
from google.protobuf import timestamp_pb2


def create_test_plan() -> messages_pb2.Plan:
    """Create a test Plan message."""
    plan = messages_pb2.Plan()
    plan.id = "test-plan-123"
    plan.parent_request_id = "request-123"
    
    # Add a refactor step
    step1 = plan.steps.add()
    step1.order = 1
    step1.goal = "Refactor the process_data function in src/data_processor.py"
    step1.kind = messages_pb2.STEP_KIND_REFACTOR
    step1.hints.extend([
        "Extract validation logic into separate function",
        "Add proper error handling",
        "Improve variable names"
    ])
    
    # Add a test step
    step2 = plan.steps.add()
    step2.order = 2
    step2.goal = "Add unit tests for the refactored data processor"
    step2.kind = messages_pb2.STEP_KIND_TEST
    step2.hints.extend([
        "Test happy path scenarios",
        "Test error conditions",
        "Test edge cases with empty data"
    ])
    
    # Add metadata
    plan.rationale.extend([
        "Current implementation is hard to maintain",
        "Lacks proper test coverage"
    ])
    plan.affected_paths.extend([
        "src/data_processor.py",
        "tests/test_data_processor.py"
    ])
    plan.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    plan.estimated_tokens = 2000
    
    # Set timestamp
    plan.created_at.GetCurrentTime()
    
    return plan


async def test_code_planner_flow():
    """Test Code Planner with in-memory queue."""
    print("🧪 Testing Code Planner with In-Memory Queue")
    print("=" * 50)
    
    # Register protobuf messages
    register_agent_messages()
    
    # Create in-memory configuration
    config = MessagingConfig()
    config.broker_type = "memory"
    config.broker_url = "memory://localhost"
    
    # Create in-memory queue
    queue_config = config.get_queue_config("test")
    mq = InMemoryMessageQueue(queue_config)
    print("✓ Created in-memory message queue")
    
    # Create topics
    for topic in ["code.plan.in", "coding.task.in", "code.plan.deadletter"]:
        mq.create_topic(topic)
    print("✓ Created topics")
    
    # Create sample Python files for testing
    test_repo = Path("test_repo")
    test_repo.mkdir(exist_ok=True)
    
    # Create src directory
    src_dir = test_repo / "src"
    src_dir.mkdir(exist_ok=True)
    
    # Create a sample Python file
    data_processor = src_dir / "data_processor.py"
    data_processor.write_text("""
def process_data(data):
    # This function needs refactoring
    result = []
    for item in data:
        if item is not None and item != "":
            if isinstance(item, str):
                item = item.strip()
            if item:
                result.append(item)
    return result

def helper_function():
    return "helper"
""")
    
    # Create test directory
    test_dir = test_repo / "tests"
    test_dir.mkdir(exist_ok=True)
    
    print("✓ Created test repository structure")
    
    # Create Code Planner
    planner = CodePlanner(str(test_repo))
    
    # Override the service to use our in-memory queue
    class TestMessagingService(CodePlannerMessagingService):
        def __init__(self, planner, config):
            self.code_planner = planner
            self.config = config
            from src.messaging.serializer import MessageSerializer
            self.serializer = MessageSerializer()
            register_agent_messages()
            self.running = False
            
            # Use in-memory queue
            self.message_queue = mq
            self.producer = mq.create_producer()
            self.consumer = mq.create_consumer(["code.plan.in"], group_id="test")
            
            from src.messaging.base import DeadLetterHandler
            self.dead_letter_handler = DeadLetterHandler(mq, "code.plan.deadletter")
            
            self.metrics = {
                "plans_processed": 0,
                "task_bundles_created": 0,
                "errors": 0,
                "dead_letters": 0
            }
    
    service = TestMessagingService(planner, config)
    print("✓ Created Code Planner service")
    
    # Create test plan
    plan = create_test_plan()
    
    # Send plan to queue
    producer = mq.create_producer()
    producer.produce("code.plan.in", plan, key=plan.id)
    print(f"\n✓ Sent test plan: {plan.id}")
    
    # Create consumer for results
    results = []
    consumer = mq.create_consumer(["coding.task.in"], group_id="test-consumer")
    
    # Process in background
    async def process_messages():
        await service.consumer.consume_async(
            service.handle_plan,
            timeout=2
        )
    
    # Collect results
    def collect_results(msg):
        results.append(msg)
        if isinstance(msg.value, messages_pb2.TaskBundle):
            bundle = msg.value
            print(f"\n✓ Received TaskBundle: {bundle.id}")
            print(f"  Strategy: {bundle.execution_strategy}")
            print(f"  Tasks: {len(bundle.tasks)}")
            
            for i, task in enumerate(bundle.tasks, 1):
                print(f"\n  Task {i}: {task.id[:12]}...")
                print(f"    Goal: {task.goal}")
                print(f"    Files: {', '.join(task.paths)}")
                print(f"    Complexity: {task.complexity_label.name}")
                print(f"    Dependencies: {len(task.depends_on)}")
                
                if task.skeleton_patch:
                    print(f"    Skeleton patches: {len(task.skeleton_patch)}")
    
    # Run test
    process_task = asyncio.create_task(process_messages())
    
    # Wait a bit for processing
    await asyncio.sleep(0.5)
    
    # Collect results
    consumer.consume(collect_results, timeout=1)
    
    # Wait for processing to complete
    await process_task
    
    # Check results
    print(f"\n📊 Results:")
    print(f"  Messages received: {len(results)}")
    print(f"  Metrics: {service.get_metrics()}")
    
    success = len(results) >= 1 and service.metrics["task_bundles_created"] >= 1
    
    # Cleanup
    consumer.close()
    producer.close()
    await service.shutdown()
    
    # Remove test repo
    import shutil
    shutil.rmtree(test_repo, ignore_errors=True)
    
    return success


def test_ast_analyzer():
    """Test AST analyzer functionality."""
    print("\n🔍 Testing AST Analyzer")
    print("=" * 50)
    
    from src.code_planner.ast_analyzer import ASTAnalyzer
    
    # Create test file
    test_file = Path("test_ast.py")
    test_file.write_text("""
def calculate_total(items):
    total = 0
    for item in items:
        if item.price > 0:
            total += item.price * item.quantity
    return total

class ShoppingCart:
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_total(self):
        return calculate_total(self.items)
""")
    
    # Analyze
    analyzer = ASTAnalyzer(".")
    analysis = analyzer.analyze_file("test_ast.py")
    
    print(f"✓ Analyzed {analysis.path}")
    print(f"  Language: {analysis.language}")
    print(f"  Symbols: {len(analysis.symbols)}")
    print(f"  Complexity: {analysis.complexity}")
    
    for symbol in analysis.symbols:
        print(f"\n  {symbol.kind}: {symbol.name}")
        print(f"    Lines: {symbol.line_start}-{symbol.line_end}")
        print(f"    Complexity: {symbol.complexity}")
        if symbol.calls:
            print(f"    Calls: {', '.join(symbol.calls)}")
    
    # Cleanup
    test_file.unlink()
    
    return True


def main():
    """Run all tests."""
    print("\n🚀 Code Planner Test Suite")
    print("Testing Code Planner agent functionality\n")
    
    # Test AST analyzer
    ast_success = test_ast_analyzer()
    
    # Test full flow
    flow_success = asyncio.run(test_code_planner_flow())
    
    if ast_success and flow_success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
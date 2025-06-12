#!/usr/bin/env python3
"""
Script to set up the messaging infrastructure for the agent system.

This script:
1. Creates all required topics
2. Verifies connectivity
3. Can optionally start a local Kafka instance using Docker
"""

import argparse
import subprocess
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.messaging import KafkaMessageQueue, QueueConfig, get_config, load_config_from_file
from src.messaging.config import create_default_topics
from src.core.logging import setup_logging
import logging


def check_docker():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def start_local_kafka():
    """Start a local Kafka instance using Docker Compose."""
    compose_file = """
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "9093:9093"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9093,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_JMX_PORT: 9101
      KAFKA_JMX_HOSTNAME: localhost
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'false'

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    depends_on:
      - kafka
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9093
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
"""
    
    # Write docker-compose file
    compose_path = Path("docker-compose.kafka.yml")
    compose_path.write_text(compose_file)
    
    print("Starting local Kafka instance...")
    try:
        subprocess.run(["docker-compose", "-f", str(compose_path), "up", "-d"], check=True)
        print("Kafka started successfully!")
        print("- Kafka broker: localhost:9092")
        print("- Kafka UI: http://localhost:8080")
        print("\nWaiting for Kafka to be ready...")
        time.sleep(10)  # Give Kafka time to start
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to start Kafka: {e}")
        return False


def stop_local_kafka():
    """Stop the local Kafka instance."""
    compose_path = Path("docker-compose.kafka.yml")
    if compose_path.exists():
        print("Stopping local Kafka instance...")
        subprocess.run(["docker-compose", "-f", str(compose_path), "down"], check=True)
        compose_path.unlink()
        print("Kafka stopped successfully!")


def setup_topics(config):
    """Create all required topics."""
    print("\nSetting up topics...")
    
    # Create message queue
    queue_config = config.get_queue_config("setup")
    mq = KafkaMessageQueue(queue_config)
    
    # Check health
    if not mq.health_check():
        print("ERROR: Cannot connect to Kafka broker")
        return False
    
    print("Connected to Kafka broker successfully!")
    
    # Create topics
    create_default_topics(config, mq)
    
    # List topics
    print("\nExisting topics:")
    topics = mq.list_topics()
    for topic in sorted(topics):
        if not topic.startswith("__"):  # Skip internal topics
            metadata = mq.get_topic_metadata(topic)
            print(f"  - {topic} (partitions: {metadata['partitions']})")
    
    mq.close()
    return True


def test_messaging(config):
    """Test basic messaging functionality."""
    print("\nTesting messaging functionality...")
    
    queue_config = config.get_queue_config("test")
    mq = KafkaMessageQueue(queue_config)
    
    # Create test producer and consumer
    producer = mq.create_producer()
    consumer = mq.create_consumer(["agent.events"], group_id="test-group")
    
    # Send test message
    test_message = {
        "agent_name": "test",
        "event_type": "setup_test",
        "event_id": "test-123",
        "data": {"test": True}
    }
    
    print("Sending test message...")
    producer.produce("agent.events", test_message, key="test")
    producer.flush()
    
    print("Test message sent successfully!")
    
    # Clean up
    consumer.close()
    producer.close()
    mq.close()
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Set up messaging infrastructure")
    parser.add_argument(
        "--config",
        help="Path to messaging configuration file",
        default="config/messaging.yaml"
    )
    parser.add_argument(
        "--start-kafka",
        action="store_true",
        help="Start a local Kafka instance using Docker"
    )
    parser.add_argument(
        "--stop-kafka",
        action="store_true",
        help="Stop the local Kafka instance"
    )
    parser.add_argument(
        "--skip-topics",
        action="store_true",
        help="Skip topic creation"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test messaging functionality"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(logging.INFO)
    
    # Handle stop command
    if args.stop_kafka:
        stop_local_kafka()
        return
    
    # Start Kafka if requested
    if args.start_kafka:
        if not check_docker():
            print("ERROR: Docker is not installed or not running")
            print("Please install Docker and ensure it's running")
            sys.exit(1)
        
        if not start_local_kafka():
            sys.exit(1)
    
    # Load configuration
    config_path = Path(args.config)
    if config_path.exists():
        config = load_config_from_file(str(config_path))
        print(f"Loaded configuration from {config_path}")
    else:
        config = get_config()
        print("Using default configuration")
    
    # Create topics
    if not args.skip_topics:
        if not setup_topics(config):
            sys.exit(1)
    
    # Test messaging
    if args.test:
        if not test_messaging(config):
            sys.exit(1)
    
    print("\n✅ Messaging infrastructure setup complete!")
    
    if args.start_kafka:
        print("\nTo stop Kafka later, run:")
        print("  python scripts/setup_messaging.py --stop-kafka")


if __name__ == "__main__":
    main()
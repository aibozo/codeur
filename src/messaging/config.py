"""
Configuration management for the messaging system.

This module handles loading and validating message queue configurations
from environment variables, configuration files, or code.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import yaml
import json
from pathlib import Path

from .base import QueueConfig, DeliveryMode
from .exceptions import ConfigurationException


@dataclass
class MessagingConfig:
    """Complete messaging configuration for the agent system."""
    
    # Broker configuration
    broker_type: str = "kafka"  # kafka or amqp
    broker_url: str = "localhost:9092"
    
    # Default queue settings
    default_delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    default_max_retries: int = 3
    default_retry_delay_ms: int = 1000
    default_batch_size: int = 1
    default_poll_timeout_ms: int = 1000
    
    # Topic configurations
    topics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Dead letter queue settings
    enable_dead_letter: bool = True
    dead_letter_suffix: str = ".deadletter"
    
    # Agent-specific configurations
    request_planner_group: str = "request-planner-group"
    code_planner_group: str = "code-planner-group"
    coding_agent_group: str = "coding-agent-group"
    
    # Kafka-specific settings
    kafka_compression: str = "lz4"
    kafka_batch_size: int = 16384
    kafka_linger_ms: int = 10
    
    # AMQP-specific settings
    amqp_exchange: str = "agent-exchange"
    amqp_exchange_type: str = "topic"
    amqp_prefetch_count: int = 10
    
    def __post_init__(self):
        """Initialize topic configurations with defaults."""
        if not self.topics:
            self.topics = self._get_default_topics()
    
    def _get_default_topics(self) -> Dict[str, Dict[str, Any]]:
        """Get default topic configurations."""
        return {
            # Request Planner topics
            "plan.in": {
                "partitions": 3,
                "replication_factor": 2,
                "retention_ms": 604800000,  # 7 days
            },
            "plan.out": {
                "partitions": 3,
                "replication_factor": 2,
            },
            "plan.deadletter": {
                "partitions": 1,
                "replication_factor": 2,
                "retention_ms": 2592000000,  # 30 days
            },
            
            # Code Planner topics
            "code.plan.in": {
                "partitions": 3,
                "replication_factor": 2,
            },
            "code.plan.out": {
                "partitions": 3,
                "replication_factor": 2,
            },
            
            # Coding Agent topics
            "coding.task.in": {
                "partitions": 6,  # More partitions for parallel processing
                "replication_factor": 2,
            },
            "coding.result.out": {
                "partitions": 3,
                "replication_factor": 2,
            },
            
            # Build/Test topics
            "build.report": {
                "partitions": 3,
                "replication_factor": 2,
                "retention_ms": 1209600000,  # 14 days
            },
            "test.spec.in": {
                "partitions": 3,
                "replication_factor": 2,
            },
            
            # Verifier topics
            "regression.alert": {
                "partitions": 1,
                "replication_factor": 2,
                "retention_ms": 2592000000,  # 30 days
            },
            
            # Observability
            "agent.events": {
                "partitions": 6,
                "replication_factor": 1,  # Less critical
                "retention_ms": 259200000,  # 3 days
            },
        }
    
    def get_queue_config(self, name: str, **overrides) -> QueueConfig:
        """
        Get a QueueConfig for a specific queue/topic.
        
        Args:
            name: Queue/topic name
            **overrides: Override specific settings
            
        Returns:
            QueueConfig instance
        """
        # Start with defaults
        config_dict = {
            "name": name,
            "broker_url": self.broker_url,
            "delivery_mode": self.default_delivery_mode,
            "max_retries": self.default_max_retries,
            "retry_delay_ms": self.default_retry_delay_ms,
            "batch_size": self.default_batch_size,
            "poll_timeout_ms": self.default_poll_timeout_ms,
        }
        
        # Add dead letter queue if enabled
        if self.enable_dead_letter and not name.endswith(self.dead_letter_suffix):
            config_dict["dead_letter_queue"] = name + self.dead_letter_suffix
        
        # Add broker-specific settings
        extra_config = {}
        if self.broker_type == "kafka":
            extra_config.update({
                "compression.type": self.kafka_compression,
                "batch.size": self.kafka_batch_size,
                "linger.ms": self.kafka_linger_ms,
            })
        
        config_dict["extra_config"] = extra_config
        
        # Apply any overrides
        config_dict.update(overrides)
        
        return QueueConfig(**config_dict)


def load_config_from_env() -> MessagingConfig:
    """
    Load messaging configuration from environment variables.
    
    Environment variables:
    - MQ_BROKER_TYPE: kafka or amqp
    - MQ_BROKER_URL: Broker connection string
    - MQ_DELIVERY_MODE: at_most_once, at_least_once, exactly_once
    - MQ_MAX_RETRIES: Maximum retry attempts
    - MQ_ENABLE_DEAD_LETTER: Enable dead letter queues
    - KAFKA_BOOTSTRAP_SERVERS: Kafka broker addresses
    - AMQP_URL: AMQP connection URL
    """
    config = MessagingConfig()
    
    # Broker settings
    config.broker_type = os.getenv("MQ_BROKER_TYPE", config.broker_type)
    
    # Use specific broker URLs if available
    if config.broker_type == "kafka":
        config.broker_url = os.getenv("KAFKA_BOOTSTRAP_SERVERS", config.broker_url)
    elif config.broker_type == "amqp":
        config.broker_url = os.getenv("AMQP_URL", config.broker_url)
    else:
        config.broker_url = os.getenv("MQ_BROKER_URL", config.broker_url)
    
    # Delivery settings
    delivery_mode_str = os.getenv("MQ_DELIVERY_MODE", "")
    if delivery_mode_str:
        try:
            config.default_delivery_mode = DeliveryMode(delivery_mode_str)
        except ValueError:
            pass  # Keep default
    
    # Retry settings
    if os.getenv("MQ_MAX_RETRIES"):
        config.default_max_retries = int(os.getenv("MQ_MAX_RETRIES"))
    
    # Dead letter settings
    if os.getenv("MQ_ENABLE_DEAD_LETTER"):
        config.enable_dead_letter = os.getenv("MQ_ENABLE_DEAD_LETTER").lower() == "true"
    
    # Consumer group settings
    config.request_planner_group = os.getenv("REQUEST_PLANNER_GROUP", config.request_planner_group)
    config.code_planner_group = os.getenv("CODE_PLANNER_GROUP", config.code_planner_group)
    config.coding_agent_group = os.getenv("CODING_AGENT_GROUP", config.coding_agent_group)
    
    return config


def load_config_from_file(file_path: str) -> MessagingConfig:
    """
    Load messaging configuration from a YAML or JSON file.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        MessagingConfig instance
        
    Raises:
        ConfigurationException: If file cannot be loaded
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ConfigurationException(f"Configuration file not found: {file_path}")
    
    try:
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix == '.json':
                data = json.load(f)
            else:
                raise ConfigurationException(f"Unsupported file format: {path.suffix}")
        
        # Convert delivery mode string to enum
        if 'default_delivery_mode' in data:
            data['default_delivery_mode'] = DeliveryMode(data['default_delivery_mode'])
        
        return MessagingConfig(**data)
        
    except Exception as e:
        raise ConfigurationException(f"Failed to load configuration: {e}")


def create_default_topics(config: MessagingConfig, message_queue) -> None:
    """
    Create all default topics based on configuration.
    
    Args:
        config: Messaging configuration
        message_queue: MessageQueue instance
    """
    for topic_name, topic_config in config.topics.items():
        try:
            message_queue.create_topic(
                name=topic_name,
                partitions=topic_config.get('partitions', 1),
                replication_factor=topic_config.get('replication_factor', 1),
                config={
                    'retention.ms': str(topic_config.get('retention_ms', 604800000)),
                    'compression.type': config.kafka_compression,
                }
            )
            print(f"Created topic: {topic_name}")
        except Exception as e:
            # Topic might already exist
            print(f"Topic {topic_name} already exists or error: {e}")


# Global configuration instance
_global_config: Optional[MessagingConfig] = None


def get_config() -> MessagingConfig:
    """
    Get the global messaging configuration.
    
    Loads from environment on first call.
    """
    global _global_config
    
    if _global_config is None:
        _global_config = load_config_from_env()
    
    return _global_config


def set_config(config: MessagingConfig) -> None:
    """Set the global messaging configuration."""
    global _global_config
    _global_config = config
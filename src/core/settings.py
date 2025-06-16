"""
Centralized configuration management using Pydantic Settings.

This module provides a single source of truth for all configuration
across the agent system, with support for environment variables,
.env files, and configuration files.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pydantic.types import SecretStr
import yaml
import json


class SecuritySettings(BaseSettings):
    """Security-related configuration."""
    
    # Path traversal protection
    enable_symlink_checks: bool = Field(True, description="Check for symlink traversal")
    allowed_symlinks: List[str] = Field([], description="Allowed symlink paths")
    
    # File access patterns
    forbidden_patterns: List[str] = Field(
        default_factory=lambda: [
            '.env', '.env.*', '*.key', '*.pem', '*.pfx', '*.p12',
            'id_rsa*', 'id_dsa*', 'id_ecdsa*', 'id_ed25519*',
            '.ssh/*', '.gnupg/*', '.password*', '.secret*',
            '*.secret', '*.credentials', '.aws/credentials',
            '.config/gcloud/*', '.kube/config',
        ],
        description="File patterns that should never be accessed"
    )
    
    excluded_dirs: List[str] = Field(
        default_factory=lambda: [
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'env', '.env', '.tox', '.pytest_cache', '.mypy_cache',
            '.coverage', 'htmlcov', 'dist', 'build', '*.egg-info',
        ],
        description="Directories to exclude from operations"
    )
    
    # Git sandboxing
    sandbox_git_operations: bool = Field(True, description="Use sandboxed git operations")
    git_sandbox_dir: Optional[Path] = Field(None, description="Directory for git sandboxes")
    
    class Config:
        env_prefix = "AGENT_SECURITY_"
        extra = "ignore"


class CacheSettings(BaseSettings):
    """Cache configuration."""
    
    # Cache backend
    cache_backend: str = Field("memory", description="Cache backend: memory, redis")
    redis_url: Optional[str] = Field("redis://localhost:6379", description="Redis connection URL")
    redis_db: int = Field(0, description="Redis database number")
    
    # Cache limits
    cache_ttl_seconds: int = Field(3600, description="Default cache TTL in seconds")
    max_memory_cache_items: int = Field(10000, description="Max items in memory cache")
    max_memory_cache_mb: int = Field(1024, description="Max memory cache size in MB")
    
    # LRU settings
    enable_lru_eviction: bool = Field(True, description="Enable LRU eviction")
    lru_check_interval_seconds: int = Field(300, description="LRU check interval")
    
    class Config:
        env_prefix = "AGENT_CACHE_"
        extra = "ignore"


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    # Log levels
    log_level: str = Field("INFO", description="Default log level")
    console_log_level: str = Field("INFO", description="Console log level")
    file_log_level: str = Field("DEBUG", description="File log level")
    
    # Log format
    log_format: str = Field("structured", description="Log format: text, structured, json")
    log_dir: Path = Field(Path("logs"), description="Log directory")
    log_file_name: str = Field("agent.log", description="Log file name")
    
    # Structured logging
    enable_request_id: bool = Field(True, description="Add request IDs to logs")
    enable_correlation_id: bool = Field(True, description="Track correlation IDs")
    
    # Log rotation
    max_log_size_mb: int = Field(100, description="Max log file size in MB")
    backup_count: int = Field(5, description="Number of backup files to keep")
    
    class Config:
        env_prefix = "AGENT_LOG_"
        extra = "ignore"


class LLMSettings(BaseSettings):
    """LLM configuration."""
    
    # API settings
    openai_api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[SecretStr] = Field(None, description="Anthropic API key")
    
    # Model settings
    default_model: str = Field("gpt-4", description="Default LLM model")
    temperature: float = Field(0.7, description="Model temperature")
    max_tokens: int = Field(4000, description="Max tokens per request")
    
    # Resilience settings
    request_timeout_seconds: int = Field(30, description="Request timeout")
    max_retries: int = Field(3, description="Max retry attempts")
    retry_delay_seconds: float = Field(1.0, description="Initial retry delay")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    
    class Config:
        env_prefix = "AGENT_LLM_"
        extra = "ignore"


class RAGSettings(BaseSettings):
    """RAG (Retrieval-Augmented Generation) configuration."""
    
    # Vector store
    vector_store_type: str = Field("qdrant", description="Vector store: qdrant, chroma")
    qdrant_url: str = Field("http://localhost:6333", description="Qdrant URL")
    qdrant_collection: str = Field("code_chunks", description="Qdrant collection name")
    
    # Embeddings
    embedding_model: str = Field("text-embedding-ada-002", description="Embedding model")
    embedding_batch_size: int = Field(100, description="Embedding batch size")
    
    # Chunking
    chunk_size: int = Field(1000, description="Default chunk size")
    chunk_overlap: int = Field(200, description="Chunk overlap")
    
    class Config:
        env_prefix = "AGENT_RAG_"
        extra = "ignore"


class MessagingSettings(BaseSettings):
    """Message queue configuration."""
    
    # Backend
    messaging_backend: str = Field("memory", description="Backend: memory, kafka, redis")
    
    # Kafka settings
    kafka_bootstrap_servers: str = Field("localhost:9092", description="Kafka servers")
    kafka_topic_prefix: str = Field("agent", description="Topic prefix")
    
    # Queue settings
    max_queue_size: int = Field(1000, description="Max queue size")
    consumer_timeout_ms: int = Field(1000, description="Consumer timeout")
    
    class Config:
        env_prefix = "AGENT_MESSAGING_"
        extra = "ignore"


class WebhookSettings(BaseSettings):
    """Webhook configuration."""
    
    # Server settings
    webhook_enabled: bool = Field(False, description="Enable webhook server")
    webhook_host: str = Field("0.0.0.0", description="Webhook server host")
    webhook_port: int = Field(8088, description="Webhook server port")
    
    # Authentication
    webhook_auth_enabled: bool = Field(True, description="Enable webhook authentication")
    webhook_auth_tokens: List[SecretStr] = Field([], description="Valid auth tokens")
    webhook_secret_key: Optional[SecretStr] = Field(None, description="Webhook signing secret")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests: int = Field(100, description="Max requests per window")
    rate_limit_window_seconds: int = Field(60, description="Rate limit window")
    
    # Project mapping
    project_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Map webhook sources to project directories"
    )
    
    class Config:
        env_prefix = "AGENT_WEBHOOK_"
        extra = "ignore"


class Settings(BaseSettings):
    """Main settings class combining all configuration sections."""
    
    # General settings
    project_root: Path = Field(Path.cwd(), description="Project root directory")
    debug: bool = Field(False, description="Debug mode")
    
    # Sub-configurations
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    messaging: MessagingSettings = Field(default_factory=MessagingSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "AGENT_"
        extra = "ignore"  # Ignore extra environment variables
        
    @validator("project_root", pre=True)
    def validate_project_root(cls, v):
        """Ensure project root is absolute."""
        return Path(v).resolve()
    
    @classmethod
    def from_file(cls, file_path: Path) -> "Settings":
        """Load settings from a YAML or JSON file."""
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
        elif file_path.suffix == ".json":
            with open(file_path, "r") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")
        
        return cls(**data)
    
    def save_to_file(self, file_path: Path):
        """Save settings to a YAML or JSON file."""
        data = self.dict(exclude_unset=True)
        
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False)
        elif file_path.suffix == ".json":
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def load_settings(file_path: Optional[Path] = None) -> Settings:
    """Load settings from file or environment."""
    global _settings
    
    if file_path:
        _settings = Settings.from_file(file_path)
    else:
        # Check for config file in standard locations
        config_locations = [
            Path(".agent.yaml"),
            Path(".agent.yml"),
            Path("config/agent.yaml"),
            Path("config/agent.yml"),
            Path.home() / ".config/agent/config.yaml",
        ]
        
        for config_path in config_locations:
            if config_path.exists():
                _settings = Settings.from_file(config_path)
                break
        else:
            # No config file found, use defaults and env vars
            _settings = Settings()
    
    return _settings
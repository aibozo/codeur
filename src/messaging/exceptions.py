"""
Custom exceptions for the messaging system.
"""


class MessagingException(Exception):
    """Base exception for all messaging-related errors."""
    pass


class ProducerException(MessagingException):
    """Exception raised by message producers."""
    pass


class ConsumerException(MessagingException):
    """Exception raised by message consumers."""
    pass


class SerializationException(MessagingException):
    """Exception raised during message serialization/deserialization."""
    pass


class ConnectionException(MessagingException):
    """Exception raised when connection to message broker fails."""
    pass


class ConfigurationException(MessagingException):
    """Exception raised for invalid configuration."""
    pass


class TopicException(MessagingException):
    """Exception raised for topic-related operations."""
    pass


class TimeoutException(MessagingException):
    """Exception raised when an operation times out."""
    pass


class RetryExhaustedException(MessagingException):
    """Exception raised when all retries have been exhausted."""
    
    def __init__(self, message: str, retry_count: int, original_error: Exception):
        super().__init__(message)
        self.retry_count = retry_count
        self.original_error = original_error
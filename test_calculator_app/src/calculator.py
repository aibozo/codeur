"""
Calculator module providing basic and advanced mathematical operations.
"""
import math


class Calculator:
    """A calculator with basic operations and memory functions."""
    
    def __init__(self):
        self.memory = 0
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    def power(self, base: float, exponent: float) -> float:
        """Raise base to the power of exponent."""
        return math.pow(base, exponent)
    
    def sqrt(self, n: float) -> float:
        """Calculate square root."""
        if n < 0:
            raise ValueError("Cannot calculate square root of negative number")
        return math.sqrt(n)
    
    def percentage(self, value: float, percent: float) -> float:
        """Calculate percentage of a value."""
        return (value * percent) / 100
    
    def store_memory(self, value: float) -> None:
        """Store value in memory."""
        self.memory = value
    
    def recall_memory(self) -> float:
        """Recall value from memory."""
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear memory."""
        self.memory = 0
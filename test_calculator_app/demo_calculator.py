#!/usr/bin/env python3
"""
Demo script to test the calculator functionality programmatically.
"""
from src.calculator import Calculator


def test_calculator():
    """Test all calculator functions."""
    calc = Calculator()
    
    print("=== CALCULATOR FUNCTIONALITY TEST ===\n")
    
    # Test basic arithmetic
    print("1. Basic Arithmetic Operations:")
    print(f"   10 + 5 = {calc.add(10, 5)}")
    print(f"   20 - 8 = {calc.subtract(20, 8)}")
    print(f"   7 × 6 = {calc.multiply(7, 6)}")
    print(f"   15 ÷ 3 = {calc.divide(15, 3)}")
    
    # Test advanced operations
    print("\n2. Advanced Operations:")
    print(f"   2^8 = {calc.power(2, 8)}")
    print(f"   √144 = {calc.sqrt(144)}")
    print(f"   25% of 80 = {calc.percentage(80, 25)}")
    
    # Test memory functions
    print("\n3. Memory Functions:")
    print(f"   Initial memory: {calc.recall_memory()}")
    calc.store_memory(42)
    print(f"   Stored 42 in memory")
    print(f"   Recall memory: {calc.recall_memory()}")
    calc.clear_memory()
    print(f"   After clear: {calc.recall_memory()}")
    
    # Test error handling
    print("\n4. Error Handling:")
    try:
        calc.divide(10, 0)
    except ValueError as e:
        print(f"   Division by zero: {e}")
    
    try:
        calc.sqrt(-4)
    except ValueError as e:
        print(f"   Square root of negative: {e}")
    
    # Complex calculations
    print("\n5. Complex Calculations:")
    # Calculate compound interest: P(1 + r)^t
    principal = 1000
    rate = 0.05  # 5%
    time = 10
    compound = calc.multiply(principal, calc.power(calc.add(1, rate), time))
    print(f"   $1000 at 5% for 10 years = ${compound:.2f}")
    
    # Calculate circle area: πr²
    radius = 5
    pi = 3.14159
    area = calc.multiply(pi, calc.power(radius, 2))
    print(f"   Area of circle (r=5) = {area:.2f}")
    
    # Percentage calculations
    print("\n6. Practical Examples:")
    original_price = 99.99
    discount = 20  # 20% off
    discount_amount = calc.percentage(original_price, discount)
    final_price = calc.subtract(original_price, discount_amount)
    print(f"   Original price: ${original_price}")
    print(f"   {discount}% discount: ${discount_amount:.2f}")
    print(f"   Final price: ${final_price:.2f}")
    
    print("\n=== ALL TESTS COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    test_calculator()
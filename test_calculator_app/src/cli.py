"""
Command-line interface for the calculator.
"""
from .calculator import Calculator


class CalculatorCLI:
    """CLI interface for the calculator."""
    
    def __init__(self):
        self.calculator = Calculator()
        self.running = True
    
    def display_menu(self):
        """Display the calculator menu."""
        print("\n" + "="*40)
        print("Calculator Menu:")
        print("1. Add")
        print("2. Subtract")
        print("3. Multiply")
        print("4. Divide")
        print("5. Power")
        print("6. Square Root")
        print("7. Percentage")
        print("8. Store to Memory")
        print("9. Recall from Memory")
        print("10. Clear Memory")
        print("0. Exit")
        print("="*40)
    
    def get_input(self, prompt: str, input_type=float):
        """Get validated input from user."""
        while True:
            try:
                return input_type(input(prompt))
            except ValueError:
                print(f"Invalid input. Please enter a valid {input_type.__name__}.")
    
    def process_operation(self, choice: int):
        """Process the selected operation."""
        try:
            if choice == 1:  # Add
                a = self.get_input("Enter first number: ")
                b = self.get_input("Enter second number: ")
                result = self.calculator.add(a, b)
                print(f"Result: {a} + {b} = {result}")
                
            elif choice == 2:  # Subtract
                a = self.get_input("Enter first number: ")
                b = self.get_input("Enter second number: ")
                result = self.calculator.subtract(a, b)
                print(f"Result: {a} - {b} = {result}")
                
            elif choice == 3:  # Multiply
                a = self.get_input("Enter first number: ")
                b = self.get_input("Enter second number: ")
                result = self.calculator.multiply(a, b)
                print(f"Result: {a} × {b} = {result}")
                
            elif choice == 4:  # Divide
                a = self.get_input("Enter dividend: ")
                b = self.get_input("Enter divisor: ")
                result = self.calculator.divide(a, b)
                print(f"Result: {a} ÷ {b} = {result}")
                
            elif choice == 5:  # Power
                base = self.get_input("Enter base: ")
                exp = self.get_input("Enter exponent: ")
                result = self.calculator.power(base, exp)
                print(f"Result: {base}^{exp} = {result}")
                
            elif choice == 6:  # Square Root
                n = self.get_input("Enter number: ")
                result = self.calculator.sqrt(n)
                print(f"Result: √{n} = {result}")
                
            elif choice == 7:  # Percentage
                value = self.get_input("Enter value: ")
                percent = self.get_input("Enter percentage: ")
                result = self.calculator.percentage(value, percent)
                print(f"Result: {percent}% of {value} = {result}")
                
            elif choice == 8:  # Store Memory
                value = self.get_input("Enter value to store: ")
                self.calculator.store_memory(value)
                print(f"Stored {value} in memory")
                
            elif choice == 9:  # Recall Memory
                value = self.calculator.recall_memory()
                print(f"Memory value: {value}")
                
            elif choice == 10:  # Clear Memory
                self.calculator.clear_memory()
                print("Memory cleared")
                
            elif choice == 0:  # Exit
                print("Goodbye!")
                self.running = False
                
            else:
                print("Invalid choice. Please try again.")
                
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    
    def run(self):
        """Run the calculator CLI."""
        print("Welcome to Calculator!")
        
        while self.running:
            self.display_menu()
            choice = self.get_input("\nEnter your choice (0-10): ", int)
            self.process_operation(choice)
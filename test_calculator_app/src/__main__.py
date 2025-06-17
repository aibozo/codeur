"""
Main entry point for the calculator application.
"""
from .cli import CalculatorCLI


def main():
    """Run the calculator application."""
    cli = CalculatorCLI()
    cli.run()


if __name__ == "__main__":
    main()
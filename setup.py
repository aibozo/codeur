"""
Setup script for Codeur - Multi-Agent Code Generation System
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
requirements = []
with open("requirements.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)

# Core dependencies (without development tools)
core_requirements = [
    req for req in requirements 
    if not any(dev in req for dev in ["pytest", "black", "mypy", "ruff"])
]

# Development dependencies
dev_requirements = [
    req for req in requirements 
    if any(dev in req for dev in ["pytest", "black", "mypy", "ruff"])
]

setup(
    name="codeur-agent",
    version="0.1.0",
    author="Codeur Team",
    author_email="",
    description="A sophisticated multi-agent system for automated code generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=core_requirements,
    extras_require={
        "dev": dev_requirements,
        "kafka": ["confluent-kafka>=2.3.0"],
        "amqp": ["aio-pika>=9.3.0"],
    },
    entry_points={
        "console_scripts": [
            "codeur=src.request_planner.cli:main",
            "codeur-planner=src.code_planner.cli:main",
            "codeur-agent=src.coding_agent.agent:main",
            "codeur-rag=src.rag_service.cli:main",
            "codeur-api=src.web_api.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.proto"],
    },
    zip_safe=False,
)
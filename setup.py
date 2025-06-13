"""Setup script for the Agent System."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="agent-system",
    version="0.1.0",
    author="Agent System Team",
    author_email="team@agentsystem.ai",
    description="AI-powered multi-agent code generation framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/agent-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "kafka": [
            "confluent-kafka>=2.3.0",
        ],
        "amqp": [
            "aio-pika>=9.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agent-system=src.cli:main",
            "agent-coding=src.agents.coding_agent:main",
            "agent-planner=src.agents.request_planner:main",
            "agent-rag=src.rag.service:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["proto/*.proto", "web_api/static/*", "web_api/templates/*"],
    },
)
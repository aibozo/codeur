#!/usr/bin/env python3
"""
Create a test repository for the agents to work on.
"""

import os
import shutil
from pathlib import Path
import subprocess
import click


def create_test_repo(path: Path):
    """Create a test repository with sample code."""
    
    # Create directory structure
    (path / "src").mkdir(parents=True, exist_ok=True)
    (path / "tests").mkdir(exist_ok=True)
    (path / "docs").mkdir(exist_ok=True)
    
    # Create sample Python files
    
    # API Client (for error handling test)
    (path / "src" / "api_client.py").write_text('''"""
Simple API client that needs error handling.
"""

import requests


class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_user(self, user_id):
        """Get user by ID."""
        response = requests.get(f"{self.base_url}/users/{user_id}")
        return response.json()
    
    def create_user(self, user_data):
        """Create a new user."""
        response = requests.post(f"{self.base_url}/users", json=user_data)
        return response.json()
    
    def update_user(self, user_id, user_data):
        """Update user data."""
        response = requests.put(f"{self.base_url}/users/{user_id}", json=user_data)
        return response.json()
    
    def delete_user(self, user_id):
        """Delete a user."""
        response = requests.delete(f"{self.base_url}/users/{user_id}")
        return response.status_code == 204
''')
    
    # Database modules (for refactoring test)
    (path / "src" / "db_users.py").write_text('''"""
User database operations.
"""

import sqlite3


def get_connection():
    conn = sqlite3.connect("database.db")
    return conn


def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def create_user(name, email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id
''')
    
    (path / "src" / "db_products.py").write_text('''"""
Product database operations.
"""

import sqlite3


def get_connection():
    conn = sqlite3.connect("database.db")
    return conn


def get_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def create_product(name, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id
''')
    
    # Data processor (for bug fix test)
    (path / "src" / "pipeline").mkdir(parents=True, exist_ok=True)
    (path / "src" / "pipeline" / "__init__.py").write_text("")
    (path / "src" / "pipeline" / "processor.py").write_text('''"""
Data processing pipeline with memory leak.
"""

class DataProcessor:
    def __init__(self):
        self.processed_data = []  # This causes the leak!
    
    def process_records(self, records):
        """Process a batch of records."""
        results = []
        for batch in self._batch_records(records, 100):
            transformed = self.transform_batch(batch)
            results.extend(transformed)
        return results
    
    def transform_batch(self, batch):
        """Transform a batch of records."""
        transformed = []
        for record in batch:
            # Process record
            result = {
                'id': record['id'],
                'processed': True,
                'data': record['data'].upper()
            }
            transformed.append(result)
            
            # This line causes the memory leak
            self.processed_data.append(result)
        
        return transformed
    
    def _batch_records(self, records, size):
        """Split records into batches."""
        for i in range(0, len(records), size):
            yield records[i:i + size]
''')
    
    # Create tests
    (path / "tests" / "test_api_client.py").write_text('''"""
Tests for API client.
"""

import pytest
from src.api_client import APIClient


def test_get_user():
    client = APIClient("https://api.example.com")
    # This test will fail when API is down
    user = client.get_user(123)
    assert user is not None
''')
    
    # Create requirements.txt
    (path / "requirements.txt").write_text('''requests
pytest
flask
sqlalchemy
redis
pyjwt
''')
    
    # Create README
    (path / "README.md").write_text('''# Test Repository

This is a test repository for the agent system.

## Structure

- `src/` - Source code
  - `api_client.py` - API client needing error handling
  - `db_*.py` - Database modules needing refactoring
  - `pipeline/processor.py` - Data processor with memory leak
- `tests/` - Unit tests
- `docs/` - Documentation

## Usage

This repository is used for testing the multi-agent system.
''')
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True)
    
    print(f"✓ Created test repository at {path}")


@click.command()
@click.option('--path', default='./test_repo', help='Path for test repository')
@click.option('--clean', is_flag=True, help='Remove existing repository first')
def main(path: str, clean: bool):
    """Create a test repository for agent testing."""
    repo_path = Path(path).absolute()
    
    if clean and repo_path.exists():
        shutil.rmtree(repo_path)
        print(f"Removed existing repository at {repo_path}")
    
    if repo_path.exists():
        print(f"Repository already exists at {repo_path}")
        return
    
    create_test_repo(repo_path)


if __name__ == "__main__":
    main()
#!/bin/bash
# Start all services and agents

echo "Starting Agent Testing Environment..."

# Change to script directory
cd "$(dirname "$0")"

# Start infrastructure services
echo "Starting infrastructure services..."
docker-compose up -d kafka redis

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are running
docker-compose ps

# Start the orchestrator
echo "Starting orchestrator..."
python3 orchestrator.py --start-all

echo "Testing environment started!"
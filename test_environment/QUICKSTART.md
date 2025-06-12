# Quick Start Guide - Agent Testing Environment

## Prerequisites

1. Docker and Docker Compose installed
2. Python 3.8+ with pip
3. OpenAI API key set in environment

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r ../requirements.txt
   ```

2. **Create test repository:**
   ```bash
   python create_test_repo.py --clean
   ```

3. **Start infrastructure services:**
   ```bash
   docker-compose up -d
   ```

4. **Wait for services to start:**
   ```bash
   # Check Kafka is ready
   docker-compose logs kafka | grep "started (kafka.server.KafkaServer)"
   ```

## Running the System

### Option 1: Full Orchestrator (Recommended)

```bash
python orchestrator.py --repo ./test_repo --start-all
```

This starts all agents with a unified dashboard.

### Option 2: Individual Agents

Start each agent in a separate terminal:

```bash
# Terminal 1 - Request Planner
python request_planner_runner.py --repo ./test_repo

# Terminal 2 - Code Planner  
python code_planner_runner.py --repo ./test_repo

# Terminal 3 - Coding Agent
python coding_agent_runner.py --repo ./test_repo

# Terminal 4 - Monitor
python monitor.py
```

## Testing

1. **Send test requests:**
   ```bash
   # Send all test scenarios
   python test_scenario.py --scenario all --monitor
   
   # Send specific scenario
   python test_scenario.py --scenario error_handling
   ```

2. **Monitor the system:**
   ```bash
   # Real-time monitoring dashboard
   python monitor.py
   
   # Check Kafka UI
   open http://localhost:8080
   ```

## Scenarios

- **error_handling**: Add error handling to API client
- **refactoring**: Refactor database connection code
- **feature**: Add authentication middleware
- **bug_fix**: Fix memory leak in data processor

## Troubleshooting

1. **Kafka not starting:**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

2. **Agents not connecting:**
   - Check Kafka is running: `docker-compose ps`
   - Check logs: `docker-compose logs kafka`

3. **No OpenAI key:**
   - Set environment variable: `export OPENAI_API_KEY=your-key`
   - Or create `.env` file in parent directory

## Monitoring

- **Kafka UI**: http://localhost:8080
- **Terminal Dashboard**: `python monitor.py`
- **Agent Logs**: Each agent shows its own status

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove test repository
rm -rf ./test_repo

# Clean up Docker volumes
docker-compose down -v
```
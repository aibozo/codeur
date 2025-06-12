# Agent Testing Environment

This directory contains a complete testing environment for the multi-agent system.

## Components

1. **Agent Runners** - Individual scripts to run each agent
2. **Orchestrator** - Coordinates all agents and message flow
3. **Terminal UI** - Interactive terminal interface for monitoring and control
4. **Test Repository** - Sample repository for testing code changes

## Quick Start

```bash
# Start all services
./start_all.sh

# Or start individual components
./start_kafka.sh
./start_redis.sh
./start_agents.sh

# Monitor system
./monitor.sh
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Request Planner │────>│  Code Planner   │────>│  Coding Agent   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                                │
         │                                                v
         │              ┌─────────────────┐     ┌─────────────────┐
         └─────────────>│  Test Planner   │────>│  Test Builder   │
                        └─────────────────┘     └─────────────────┘

All communication via Kafka message queue
```
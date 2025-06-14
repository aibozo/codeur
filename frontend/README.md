# Codeur Frontend

Modern web dashboard for the Codeur Agent System.

## Features

- 🔄 Real-time WebSocket updates
- 🤖 Per-agent model selection
- 📊 Live agent status monitoring
- 📜 Streaming log viewer
- 🎨 Dark theme with Tailwind CSS
- ⚡ Built with Vite + React + TypeScript

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm run dev
   ```

3. Or run both backend and frontend:
   ```bash
   cd ..
   ./run_dev.sh
   ```

## Architecture

- **React** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **TanStack Query** - Server state
- **Axios** - HTTP client

## WebSocket Events

The frontend subscribes to the following WebSocket topics:
- `agents` - Agent status updates
- `logs` - Real-time log streaming
- `jobs` - Job progress updates

## API Endpoints

- `GET /api/agents` - Get all agents
- `POST /api/agents/{agent_type}/model` - Update agent model
- `GET /api/jobs` - Get job history
- `GET /api/jobs/{job_id}` - Get job details
- `WS /ws` - WebSocket connection
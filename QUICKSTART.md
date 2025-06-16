# Quick Start Guide

## Fix Installation Issues

If you're seeing the Pydantic import error, run:

```bash
# Reinstall with updated dependencies
pip install -r requirements.txt

# Or just install pydantic-settings
pip install pydantic-settings
```

## Start the Web Dashboard

```bash
# Method 1: All-in-one command
agent web start

# Method 2: Using the helper script
./run_dev.sh

# Method 3: Start services separately
# Terminal 1:
agent webhook start

# Terminal 2:
cd frontend && npm run dev
```

## Access the Dashboard

Open http://localhost:5173 in your browser.

You should see:
- Real-time agent status cards
- Model selection dropdowns
- Live log streaming
- WebSocket connection indicator

## Terminal Dashboard

For a terminal-based UI:
```bash
agent monitor --dashboard
```

## Check Status

```bash
agent status
```
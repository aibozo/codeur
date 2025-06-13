# Pip-tools Guide for Agent System

This project uses `pip-tools` to manage Python dependencies with locked versions for reproducible builds.

## Setup

1. Install pip-tools:
   ```bash
   pip install pip-tools
   ```

2. Compile requirements:
   ```bash
   make requirements
   make dev-requirements
   ```

3. Install dependencies:
   ```bash
   make install        # Production dependencies only
   make install-dev    # All dependencies including dev tools
   ```

## Files

- `requirements.in`: Base production dependencies (unpinned)
- `requirements.txt`: Compiled production dependencies (pinned)
- `dev-requirements.in`: Development dependencies (unpinned)
- `dev-requirements.txt`: Compiled dev dependencies (pinned)

## Common Tasks

### Add a new dependency

1. Add to `requirements.in` (or `dev-requirements.in` for dev deps)
2. Run `make requirements` (or `make dev-requirements`)
3. Commit both `.in` and `.txt` files

### Upgrade dependencies

```bash
make upgrade-requirements       # Upgrade production deps
make upgrade-dev-requirements   # Upgrade all deps
```

### Sync environment

```bash
make sync       # Sync to match requirements.txt exactly
make sync-dev   # Sync to match dev-requirements.txt exactly
```

## Why pip-tools?

1. **Reproducible builds**: Lock all transitive dependencies
2. **Security**: Know exactly what versions are installed
3. **Efficiency**: Only update what you need to
4. **Clarity**: Separate human-edited `.in` files from generated `.txt` files

## Makefile Commands

Run `make help` to see all available commands:

- `make requirements`: Compile requirements.txt
- `make dev-requirements`: Compile dev-requirements.txt
- `make upgrade-requirements`: Upgrade all production dependencies
- `make upgrade-dev-requirements`: Upgrade all dependencies
- `make sync`: Install exact production dependencies
- `make sync-dev`: Install exact dev dependencies
- `make install`: Compile and install production deps
- `make install-dev`: Compile and install all deps
- `make test`: Run tests
- `make test-coverage`: Run tests with coverage
- `make lint`: Run linters
- `make format`: Format code
- `make clean`: Clean cache files
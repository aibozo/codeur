#!/bin/bash
# Convenience script to run the agent CLI

export PATH="$HOME/.local/bin:$PATH"
poetry run agent "$@"
#!/bin/bash
# Local dev server with a test gate word. Not used in production.
cd "$(dirname "$0")/.."
export GATE_WORD="${GATE_WORD:-mojave}"
export SECRET_KEY="${SECRET_KEY:-dev-only-secret}"
export PORT="${PORT:-5059}"
exec ./venv/bin/python app.py

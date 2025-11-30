#!/bin/bash
set -e

# Run indexing in the background
echo "Starting indexing..."
python src/indexing.py &

# Run FastAPI server in foreground
echo "Starting FastAPI..."
uvicorn src.app:app --host 0.0.0.0 --port 8000

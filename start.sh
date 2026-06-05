#!/bin/bash

# Start FastAPI backend in the background on localhost
echo "Starting FastAPI backend..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# Wait for backend to spin up
sleep 3

# Fallback to port 7860 (Hugging Face default) if $PORT is not defined (Render defines $PORT)
TARGET_PORT=${PORT:-7860}
echo "Starting Streamlit frontend on port $TARGET_PORT..."

# Run Streamlit in the foreground with CORS and XSRF disabled for iframe hosting
streamlit run frontend/streamlit_app.py --server.port $TARGET_PORT --server.address 0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false

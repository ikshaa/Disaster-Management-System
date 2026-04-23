#!/bin/bash
# Start the AI Disaster Response System

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "=== AI Disaster Response Coordinator ==="
echo ""

# Kill any existing servers
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :3000 | xargs kill -9 2>/dev/null
sleep 1

# Start backend
echo "[1/2] Starting backend on http://localhost:8000 ..."
cd "$PROJECT_DIR/backend"
source "$PROJECT_DIR/venv/bin/activate"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
sleep 3

# Test backend
curl -s http://localhost:8000/ > /dev/null && echo "     Backend OK" || echo "     Backend FAILED"

# Start frontend
echo "[2/2] Starting dashboard on http://localhost:3000 ..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
sleep 3

echo ""
echo "Dashboard: http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
echo ""
echo "Run the demo simulator:"
echo "  source venv/bin/activate && python simulator/generate_reports.py"
echo ""
echo "Press Ctrl+C to stop."
echo ""

wait

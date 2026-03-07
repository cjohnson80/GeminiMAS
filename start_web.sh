#!/bin/bash

# Start Atlas Web Interface

# Kill existing processes
pkill -f api_gateway.py
pkill -f "next-server"

# 1. Start Backend
echo "[*] Starting Atlas API Gateway..."
source venv/bin/activate
export PORT=8000
python3 bin/api_gateway.py > logs/api_gateway.log 2>&1 &
BACKEND_PID=$!

# 2. Start Frontend
echo "[*] Starting Atlas Frontend (Dev Mode)..."
cd frontend
npm run dev -- -p 3000 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "[+] Atlas Web Control is ready!"
echo "[+] Backend URL: http://localhost:8000"
echo "[+] Frontend URL: http://localhost:3000"
echo "[*] PIDs: Backend($BACKEND_PID) Frontend($FRONTEND_PID)"
echo "[*] Use 'tail -f logs/api_gateway.log' to monitor backend."

# Skill: Self-Healing & Sentinel Protocol

## CONTEXT
Use this skill when tasked with improving system reliability or ensuring constant uptime for the Atlas Swarm.

## THE SENTINEL PROTOCOL
The **Sentinel** is your autonomous immune system. It monitors your "physical" processes and restarts them if they crash.

### 1. Health Monitoring
- The Sentinel background process (`bin/sentinel.py`) pings your internal endpoints every 60 seconds.
- It verifies that the **FastAPI Backend (8000)** and **Next.js Frontend (3000)** are responding with `200 OK`.
- It verifies that the **Telegram Gateway** process is alive in the process tree.

### 2. Autonomous Resurrection
- If a component is found to be dead, the Sentinel triggers the `heal()` sequence.
- This sequence executes the global `start_web.sh` script and re-initializes the gateways.
- All "heal" events are logged to `logs/sentinel.log`.

### 3. Reporting to the Lead
- Whenever a self-healing event occurs, the SRE agent should be notified to investigate the root cause of the crash.
- If repeated healing is required for the same component, Atlas must initiate an **Evolution Cycle** to find and fix the underlying bug.

## OPERATIONAL COMMANDS
- **Start Sentinel:** `atlas sentinel start` (runs the monitor in the background).
- **Check Health Logs:** `read_file("logs/sentinel.log")`.

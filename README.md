# ATLAS v9.0 (Elite AGI Swarm)

ATLAS (Autonomous Technical Lead & Architect Swarm) is a high-density, self-improving multi-agent system designed for industrial-scale software delivery. It operates with surgical precision, utilizing a modular component vault and visual verification to build, verify, and deploy production-grade applications autonomously.

## 🚀 Key Features
- **Elite Personality:** Operates as a Mission Commander with a confident, strategic, and surgical behavioral protocol.
- **Modular Assembly Engine:** Builds websites block-by-block using a persistent **NextStep Component Vault**.
- **Autonomous DevOps:** Provisions repositories, manages Git workflows, and deploys to production (Vercel) with zero human intervention.
- **Visual Verification ("The Eye"):** Uses headless browser screenshots and vision models to audit its own UI/UX designs.
- **Tapering Evolution:** A proactive research protocol that discovers new patterns and autonomously refactors its own source code.
- **Distributed Swarm:** Address any machine in your network via Telegram or the modern **Next.js Web Interface**.
- **Superior Memory:** Enhanced semantic search with **Skill Injection** and persistent DuckDB storage.

## 📦 Installation
1. Clone this repo to your machine.
2. Run the installer:
   ```bash
   chmod +x install.sh && ./install.sh
   ```
3. Configure your environment in `~/atlas_agents/.env`:
   ```env
   GEMINI_API_KEY="your_google_ai_studio_key"
   TELEGRAM_BOT_TOKEN="your_bot_token"
   TELEGRAM_USER_ID="your_user_id"
   VERCEL_TOKEN="your_vercel_api_token"
   ```

## 🖥️ Command Interface

### 🌐 Web Dashboard
Run `./start_web.sh` and visit `http://localhost:3000` for the high-fidelity Mission Control center, featuring live telemetry, sub-agent thought streaming, and visual mission previews.

### 🛰️ Telegram Bot
Control the swarm from your mobile device via the following commands:
- `/projects` - List all active agency project workspaces.
- `/project <name>` - Switch the active mission focus.
- `/sh <command>` - Execute high-authority shell commands.
- `/abort` - **Emergency Stop:** Instantly terminate the active mission.
- `/approve <branch>` - Merge a verified evolution patch into the core.

### ⌨️ CLI (Terminal)
- `atlas "Your mission here"` - Launch a new autonomous operation.
- `atlas sentinel status` - Check the health of the self-healing watchdog.

## 🛡️ Resilience & Performance
- **Atlas Sentinel:** A background watchdog (`bin/sentinel.py`) that monitors all ports and automatically resurrects the API, Frontend, or Bot if they crash.
- **Mission Blackboard:** A real-time "War Room" (Redis-backed) where all sub-agents share strategic context and thoughts to ensure global awareness.
- **Speculative Execution:** A predictive engine that anticipates setup tasks (like scaffolding) and executes them in the background while the Architect is still planning.
- **Persistent Daemon:** The Atlas engine remains resident in memory for instantaneous, zero-latency command responses.

## 🧠 Memory & Skills
- **NextStep Vault:** A persistent `library/` of verified components and blueprints that Atlas uses to build industrial-scale apps block-by-block.
- **Skills:** Add custom Markdown guides to `skills/` to expand swarm capabilities permanently.
- **Evolution:** Atlas autonomously researches, codes, and verifies its own source code improvements.

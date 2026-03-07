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
3. Configure your environment in `~/gemini_agents/.env`:
   ```env
   GEMINI_API_KEY="your_google_ai_studio_key"
   TELEGRAM_BOT_TOKEN="your_bot_token"
   TELEGRAM_USER_ID="your_user_id"
   VERCEL_TOKEN="your_vercel_api_token"
   ```

## 🖥️ Command Interface
- **Modern Web UI:** Run `./start_web.sh` and visit `http://localhost:3000`.
- **Interactive Shell:** `atlas` (supports real-time streaming and commands like `/config`, `/image`, `/projects`).
- **Single Task:** `atlas "Your mission here"`
- **Evolution:** Managed automatically by the `atlas` heartbeat daemon.

## 🧠 Memory & Skills
- **Skills:** Add custom Markdown guides to `~/gemini_agents/skills/` to expand agent capabilities permanently.
- **Memory:** All interactions are semantically indexed and stored in `~/gemini_agents/memory/memory.db`.

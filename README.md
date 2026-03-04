# GeminiMAS v8.1 (Evolution Edition)

GeminiMAS is a high-density, self-improving multi-agent system designed for low-resource hardware (like Intel Celeron). It delivers production-grade AI intelligence through an autonomous, self-healing loop.

## 🚀 Key Features
- **Evolution Protocol:** Proactive self-improvement where agents examine their source code, invent optimizations, and propose them via automated git branches.
- **Telegram Approval Merging:** Review and deploy agent-authored upgrades directly from Telegram using the `/approve [branch]` command.
- **Multi-Process Persistence:** Refactored DuckDB backend allows the CLI (`gagent`), background Heartbeat, and Telegram Bot to share memory without file locks.
- **High-Density Memory:** Uses DuckDB & Polars for semantic indexing and extreme memory efficiency.
- **Self-Healing Loop:** Agents debug their own tool errors and consult a "Senior Debugger" (**Gemini 3.5 Pro Preview**) when stuck.
- **Soul & Heartbeat:** Proactive background task processing with a persistent personality defined in `SOUL.md`.
- **Venv-Isolated Runtime:** Automatically manages dependencies in a local virtual environment for system stability.

## 📦 Installation
1. Clone this repo to your machine.
2. Run the installer (now with automatic virtual environment setup):
   ```bash
   chmod +x install.sh && ./install.sh
   ```
3. Configure your environment in `~/gemini_agents/.env`:
   ```env
   GEMINI_API_KEY="your_google_ai_studio_key"
   TELEGRAM_BOT_TOKEN="your_bot_token"
   TELEGRAM_USER_ID="your_user_id"
   ```

## ⌨️ Usage
- **Interactive Shell:** `gagent`
- **Single Task:** `gagent "Your task here"`
- **Heartbeat Daemon:** Automatically managed by systemd as `gagent-heartbeat.service`.
- **Telegram Gateway:** Automatically managed by systemd as `gagent-bot.service`.

## 🧠 Memory & Skills
- **Skills:** Add custom Markdown guides to `~/gemini_agents/skills/` to expand agent capabilities.
- **Memory:** All interactions are semantically indexed and stored in `~/gemini_agents/memory/memory.db`.

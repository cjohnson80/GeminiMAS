# GeminiMAS v5.0 (Elite Autonomous Edition)

GeminiMAS is a high-density, multi-agentic system designed to run on low-resource hardware (like Intel Celeron) while delivering production-grade AI intelligence. It uses Google Gemini 3.1 Pro/Flash and an in-process DuckDB/Polars stack for extreme memory efficiency.

## 🚀 Key Features
- **High-Density Architecture:** DuckDB & Polars backend for fast, structured memory.
- **Autonomous Multi-Agent Loop:** Orchestrator (Pro), Worker (Flash), Critic (Pro), and Editor (Flash) collaborate on every task.
- **Self-Healing Tools:** Internal consulting loop where agents debug their own code errors without user input.
- **Telegram HiveMind:** Control multiple computers running GeminiMAS from a single Telegram bot with Vision support.
- **Soul & Heartbeat:** Persistent agent personality and proactive background task processing.
- **Multimodal Perception:** Automatically analyzes images/screenshots placed in the workspace.

## 📦 Installation
1. Clone this repo to your machine.
2. Run the installer:
   ```bash
   chmod +x install.sh && ./install.sh
   ```
3. Add your keys to `~/Desktop/.env`:
   ```env
   GEMINI_API_KEY="your_google_ai_studio_key"
   TELEGRAM_BOT_TOKEN="your_bot_token"
   TELEGRAM_USER_ID="your_user_id"
   ```

## ⌨️ Usage
- **Interactive Mode:** `gagent`
- **Single Task:** `gagent "Your task here"`
- **Heartbeat Daemon:** `gagent "heartbeat"`
- **Telegram Hub:** `python3 ~/gemini_agents/bin/tg_gateway.py`

## 🧠 Memory & Skills
- **Skills:** Add custom Markdown guides to `~/gemini_agents/skills/` to teach the agents new tricks.
- **Memory:** All interactions are semantically indexed in `~/gemini_agents/memory/memory.db`.
dummy update

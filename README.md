# GeminiMAS v8.2 (Distributed Swarm Edition)

GeminiMAS is a high-density, self-improving multi-agent system designed for low-resource hardware (like Intel Celeron). It delivers production-grade AI intelligence through an autonomous, self-healing loop and distributed command routing.

## 🚀 Key Features
- **Evolution Protocol:** Proactive self-improvement where agents examine their source code, invent optimizations, and propose them via automated git branches.
- **Distributed Swarm:** Address any machine in your network via Telegram (e.g., `MachineName: task`) with "Sticky Focus" routing.
- **Role-Based Orchestration:** Complex tasks are broken down and assigned to specialized agents: **Architect**, **Developer**, and **Reviewer**.
- **Multimodal Vision:** Submit images via Telegram or CLI (`/image`) for visual analysis and code refactoring.
- **Auto-Verification:** Agents use the `verify_project` tool to run `tsc` and `lint` on their own code before marking tasks as complete.
- **Superior Memory:** Enhanced semantic search with **Skill Injection** from the `/skills` directory.
- **Robust Persistence:** DuckDB with WAL mode and intelligent retry logic ensures memory is shared safely across all processes.
- **Senior Debugger:** Automatic consultation with **Gemini 3.5 Pro Preview** when worker agents encounter complex blockers.

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
   ```

## ⌨️ Usage
- **Interactive Shell:** `gagent` (supports real-time streaming and commands like `/config`, `/image`, `/disable`).
- **Single Task:** `gagent "Your task here"`
- **Distributed Commands:** On Telegram, prefix your message with a machine name (`Hostname: hello`) to shift focus to that specific node.
- **Evolution:** Managed automatically by `gagent-heartbeat.service`.

## 🧠 Memory & Skills
- **Skills:** Add custom Markdown guides to `~/gemini_agents/skills/` to expand agent capabilities permanently.
- **Memory:** All interactions are semantically indexed and stored in `~/gemini_agents/memory/memory.db`.

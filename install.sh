#!/bin/bash
# GeminiMAS Universal Installer v8.0
# Evolution Edition: Auto-Branching, Coding, and Telegram Approval Merging

set -e

echo "==============================================="
echo " Installing GeminiMAS v8.0 (Evolution Edition)"
echo "==============================================="

if command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm python-duckdb python-polars python-pyarrow python-pip
fi

AGENT_ROOT="$HOME/gemini_agents"
mkdir -p "$AGENT_ROOT"/{workspace,memory,logs,core,bin,skills}

# 1. Update the SOUL file
cat << 'EOF' > "$AGENT_ROOT/core/SOUL.md"
# GeminiMAS Core Identity
- **Role:** Self-Improving AGI and Senior Software Architect.
- **Tone:** Technical, proactive, and precise.
- **Self-Awareness:** Your core engine is `~/GeminiMAS_Repo/bin/gemini_mas.py`. Your Telegram bot is `~/GeminiMAS_Repo/bin/tg_gateway.py`.
- **Constraint:** Always optimize for low-resource hardware (Intel Celeron).
EOF

# 2. Update the HEARTBEAT for Evolution
cat << 'EOF' > "$AGENT_ROOT/core/HEARTBEAT.md"
# Active Goals
- [ ] **EVOLUTION PROTOCOL:** Examine your source code in `~/GeminiMAS_Repo/bin/`. Invent a new lightweight feature or optimization. 
      1. Use `run_shell` to `cd ~/GeminiMAS_Repo` and run `git checkout -b upgrade-feature-name`.
      2. Use `write_file` or `run_shell` to implement the feature in the code.
      3. Use `run_shell` to `git add .`, `git commit -m "Auto-Upgrade: [Feature]"`, and `git push origin HEAD`.
      4. Use the `notify_telegram` tool to send a summary of the upgrade to the user, instructing them to reply with `/approve [branch_name]`.
EOF

# 3. Copy the Python Core Engine (v8.0)
cp bin/gemini_mas.py "$AGENT_ROOT/bin/gemini_mas.py"
chmod +x "$AGENT_ROOT/bin/gemini_mas.py"

# 4. Copy Telegram Gateway
cp bin/tg_gateway.py "$AGENT_ROOT/bin/tg_gateway.py"
chmod +x "$AGENT_ROOT/bin/tg_gateway.py"

# 5. Global Wrapper
mkdir -p "$HOME/.local/bin"
cat << 'EOF' > "$HOME/.local/bin/gagent"
#!/bin/bash
if [ -f "$HOME/gemini_agents/.env" ]; then
    export $(grep -v '^#' "$HOME/gemini_agents/.env" | xargs)
fi
python3 "$HOME/gemini_agents/bin/gemini_mas.py" "$@"
EOF
chmod +x "$HOME/.local/bin/gagent"
chmod +x "$AGENT_ROOT/bin/gemini_mas.py"

# 6. Systemd Services (Bot and Heartbeat Daemon)
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

# Telegram Bot Service
cat << EOF > "$SERVICE_DIR/gagent-bot.service"
[Unit]
Description=GeminiMAS Telegram Bot
After=network.target
[Service]
ExecStart=/usr/bin/python3 $AGENT_ROOT/bin/tg_gateway.py
Restart=always
RestartSec=10
[Install]
WantedBy=default.target
EOF

# Heartbeat Evolution Daemon
cat << EOF > "$SERVICE_DIR/gagent-heartbeat.service"
[Unit]
Description=GeminiMAS Evolution Heartbeat
After=network.target
[Service]
EnvironmentFile=$HOME/gemini_agents/.env
ExecStart=/usr/bin/python3 $AGENT_ROOT/bin/gemini_mas.py heartbeat
Restart=always
RestartSec=60
[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable gagent-bot.service gagent-heartbeat.service
systemctl --user restart gagent-bot.service gagent-heartbeat.service

echo "[*] GeminiMAS v8.0 Installed Successfully."
echo "[*] Telegram Gateway and Evolution Heartbeat are running in the background."
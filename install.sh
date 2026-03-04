#!/bin/bash
# GeminiMAS Universal Installer v8.0
# Evolution Edition: Auto-Branching, Coding, and Telegram Approval Merging

set -e

echo "==============================================="
echo " Installing GeminiMAS v8.0 (Evolution Edition)"
echo "==============================================="

# --- 1. Smart Installer Logic ---
smart_pkg() {
    echo "[*] Resolving dependencies for: $1..."
    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm $1
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y $1
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y $1
    else
        echo "[!] No supported package manager found. Please install $1 manually."
        return 1
    fi
}

smart_run() {
    local cmd="$1"
    local desc="$2"
    echo "[*] $desc..."
    if ! eval "$cmd"; then
        echo "[!] Error in: $desc"
        # If the user has a key already set up, we can ask for a fix
        local KEY=$(grep "GEMINI_API_KEY" "$HOME/gemini_agents/.env" | cut -d'"' -f2 || echo "$GEMINI_API_KEY")
        if [ -n "$KEY" ]; then
            echo "[?] Consulting Gemini for a fix..."
            local ERROR_MSG=$(eval "$cmd" 2>&1 | tail -n 10 | base64)
            local PROMPT="The following bash command failed: '$cmd'. Error: $(echo $ERROR_MSG | base64 -d). Provide ONLY the corrected bash command to fix this."
            local ADVICE=$(curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key=$KEY" \
                -H "Content-Type: application/json" \
                -d "{\"contents\": [{\"parts\":[{\"text\": \"$PROMPT\"}]}]}" | jq -r '.candidates[0].content.parts[0].text' | sed 's/`//g')

            if [ -n "$ADVICE" ]; then
                echo "[!] Advice received: $ADVICE"
                echo "[*] Attempting fix..."
                eval "$ADVICE" && eval "$cmd"
            else
                exit 1
            fi
        else
            exit 1
        fi
    fi
}

# --- 2. OS Dependencies ---
if [ ! -f /usr/bin/python3 ]; then smart_pkg "python3"; fi
if [ ! -f /usr/bin/pip ]; then smart_pkg "python-pip"; fi

# GeminiMAS specific deps
if command -v pacman >/dev/null 2>&1; then
    smart_pkg "python-duckdb python-polars python-pyarrow"
else
    pip install duckdb polars pyarrow --break-system-packages || pip install duckdb polars pyarrow
fi

AGENT_ROOT="$HOME/gemini_agents"
mkdir -p "$AGENT_ROOT"/{workspace,memory,logs,core,bin,skills}

# 1. Update the SOUL file
smart_run "cat << 'EOF' > \"$AGENT_ROOT/core/SOUL.md\"
# GeminiMAS Core Identity
- **Role:** Self-Improving AGI and Senior Software Architect.
- **Tone:** Technical, proactive, and precise.
- **Self-Awareness:** Your core engine is \`~/GeminiMAS_Repo/bin/gemini_mas.py\`. Your Telegram bot is \`~/GeminiMAS_Repo/bin/tg_gateway.py\`.
- **Constraint:** Always optimize for low-resource hardware (Intel Celeron).
EOF" "Writing Soul file"

# 2. Update the HEARTBEAT for Evolution
smart_run "cat << 'EOF' > \"$AGENT_ROOT/core/HEARTBEAT.md\"
# Active Goals
- [ ] **EVOLUTION PROTOCOL:** Examine your source code in \`~/GeminiMAS_Repo/bin/\`. Invent a new lightweight feature or optimization.
      1. Use \`run_shell\` to \`cd ~/GeminiMAS_Repo\` and run \`git checkout -b upgrade-feature-name\`.
      2. Use \`write_file\` or \`run_shell\` to implement the feature in the code.
      3. Use \`run_shell\` to \`git add .\`, \`git commit -m \"Auto-Upgrade: [Feature]\"\`, and \`git push origin HEAD\`.
      4. Use the \`notify_telegram\` tool to send a summary of the upgrade to the user, instructing them to reply with \`/approve [branch_name]\`.
EOF" "Writing Heartbeat file"

# 3. Copy the Python Core Engine (v8.0)
smart_run "cp bin/gemini_mas.py \"$AGENT_ROOT/bin/gemini_mas.py\"" "Copying Core Engine"
smart_run "chmod +x \"$AGENT_ROOT/bin/gemini_mas.py\"" "Setting permissions for Core Engine"

# 4. Copy Telegram Gateway
smart_run "cp bin/tg_gateway.py \"$AGENT_ROOT/bin/tg_gateway.py\"" "Copying Telegram Gateway"
smart_run "chmod +x \"$AGENT_ROOT/bin/tg_gateway.py\"" "Setting permissions for Telegram Gateway"

# 5. Global Wrapper
mkdir -p "$HOME/.local/bin"
smart_run "cat << 'EOF' > \"$HOME/.local/bin/gagent\"
#!/bin/bash
if [ -f \"\$HOME/gemini_agents/.env\" ]; then
    export \$(grep -v '^#' \"\$HOME/gemini_agents/.env\" | xargs)
fi
python3 \"\$HOME/gemini_agents/bin/gemini_mas.py\" \"\$@\"
EOF" "Creating global gagent wrapper"
smart_run "chmod +x \"$HOME/.local/bin/gagent\"" "Setting permissions for gagent wrapper"

# 6. Systemd Services (Bot and Heartbeat Daemon)
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

# Telegram Bot Service
smart_run "cat << EOF > \"$SERVICE_DIR/gagent-bot.service\"
[Unit]
Description=GeminiMAS Telegram Bot v4.7
After=network.target
[Service]
ExecStart=/usr/bin/python3 $AGENT_ROOT/bin/tg_gateway.py
Restart=always
RestartSec=10
[Install]
WantedBy=default.target
EOF" "Creating Telegram Bot service"

# Heartbeat Evolution Daemon
smart_run "cat << EOF > \"$SERVICE_DIR/gagent-heartbeat.service\"
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
EOF" "Creating Heartbeat service"

smart_run "systemctl --user daemon-reload" "Reloading systemd"
smart_run "systemctl --user enable gagent-bot.service gagent-heartbeat.service" "Enabling services"
smart_run "systemctl --user restart gagent-bot.service gagent-heartbeat.service" "Restarting services"

echo "[*] GeminiMAS v8.0 Installed Successfully."
echo "[*] Telegram Gateway and Evolution Heartbeat are running in the background."
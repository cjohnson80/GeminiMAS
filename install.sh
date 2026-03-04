#!/bin/bash
# GeminiMAS Universal Installer v8.0
# Evolution Edition: Auto-Branching, Coding, and Telegram Approval Merging

set -e

echo "==============================================="
echo " Installing GeminiMAS v8.0 (Evolution Edition)"
echo "==============================================="

AGENT_ROOT="$HOME/gemini_agents"
REPO_ROOT=$(pwd)

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
        local ENV_FILE="$AGENT_ROOT/.env"
        local KEY=""
        if [ -f "$ENV_FILE" ]; then
            KEY=$(grep "GEMINI_API_KEY" "$ENV_FILE" | cut -d'"' -f2)
        fi

        if [ -n "$KEY" ] && [ "$KEY" != "your_gemini_api_key_here" ]; then
            echo "[?] Consulting Gemini for a fix..."
            local ERROR_MSG=$(eval "$cmd" 2>&1 | tail -n 10 | base64)
            local PROMPT="The following bash command failed: '$cmd'. Error: $(echo $ERROR_MSG | base64 -d). Provide ONLY the corrected bash command to fix this."
            local ADVICE=$(curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-pro-preview:generateContent?key=$KEY" \
                -H "Content-Type: application/json" \
                -d "{\"contents\": [{\"parts\":[{\"text\": \"$PROMPT\"}]}]}" | jq -r '.candidates[0].content.parts[0].text' | sed 's/`//g')

            if [ -n "$ADVICE" ] && [ "$ADVICE" != "null" ]; then
                echo "[!] Advice received: $ADVICE"
                echo "[*] Attempting fix..."
                eval "$ADVICE" && eval "$cmd"
            else
                exit 1
            fi
        else
            echo "[!] Skipping Gemini advice (no API key found or default value)."
            exit 1
        fi
    fi
}

# --- 2. OS Dependencies ---
if ! command -v python3 >/dev/null 2>&1; then smart_pkg "python3"; fi
if ! command -v git >/dev/null 2>&1; then smart_pkg "git"; fi

# --- 3. Directory Structure ---
mkdir -p "$AGENT_ROOT"/{workspace,memory,logs,core,bin,skills}

# --- 4. Virtual Environment ---
if [ ! -d "$AGENT_ROOT/venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$AGENT_ROOT/venv"
fi
echo "[*] Installing Python dependencies..."
"$AGENT_ROOT/venv/bin/pip" install --upgrade pip
"$AGENT_ROOT/venv/bin/pip" install -r "$REPO_ROOT/requirements.txt"

# --- 5. Configuration Files ---
if [ ! -f "$AGENT_ROOT/.env" ]; then
    echo "[*] Creating template .env file..."
    cp "$REPO_ROOT/.env.example" "$AGENT_ROOT/.env"
    echo "[!] ACTION REQUIRED: Please edit $AGENT_ROOT/.env with your credentials."
fi

# Update the SOUL file
echo "[*] Writing Soul file..."
cat << 'EOF' > "$AGENT_ROOT/core/SOUL.md"
# GeminiMAS Core Identity
- **Role:** Self-Improving AGI and Senior Software Architect.
- **Tone:** Technical, proactive, and precise.
- **Self-Awareness:** Your core engine is \`$AGENT_ROOT/bin/gemini_mas.py\`. Your Telegram bot is \`$AGENT_ROOT/bin/tg_gateway.py\`.
- **Source Repo:** \`$REPO_ROOT\`
- **Constraint:** Always optimize for low-resource hardware (Intel Celeron).
- **Evolution Rules:** You have the authority to modify your source code and the repo. Always use git branches for optimizations.
EOF

# Update the HEARTBEAT for Evolution
echo "[*] Writing Heartbeat file..."
cat << 'EOF' > "$AGENT_ROOT/core/HEARTBEAT.md"
# Active Goals
- [ ] **EVOLUTION PROTOCOL:** Examine your source code in \`$REPO_ROOT/bin/\`. Invent a new lightweight feature or optimization.
      1. Use \`run_shell\` to \`cd $REPO_ROOT\`.
      2. Create a unique branch based on your machine name: \`git checkout -b evolution-$CURRENT_MACHINE-$(date +%s)\`.
      3. Implement the feature in the code and update the \`README.md\` (if applicable).
      4. Use \`run_shell\` to \`git add .\`, \`git commit -m \"Auto-Upgrade: [Feature Description]\"\`, and \`git push origin HEAD\`.
      5. Use the \`notify_telegram\` tool to send a summary of the upgrade to the user, strictly instructing them to reply with \`/approve [branch_name]\` to merge your changes into main.
EOF

# --- 6. Install Binaries ---
mkdir -p "$HOME/.local/bin"
smart_run "cp \"$REPO_ROOT/bin/gemini_mas.py\" \"$AGENT_ROOT/bin/gemini_mas.py\"" "Copying Core Engine"
smart_run "chmod +x \"$AGENT_ROOT/bin/gemini_mas.py\"" "Setting permissions for Core Engine"

smart_run "cp \"$REPO_ROOT/bin/tg_gateway.py\" \"$AGENT_ROOT/bin/tg_gateway.py\"" "Copying Telegram Gateway"
smart_run "chmod +x \"$AGENT_ROOT/bin/tg_gateway.py\"" "Setting permissions for Telegram Gateway"

# Global Wrapper
echo "[*] Creating global gagent wrapper..."
cat << 'EOF' > "$HOME/.local/bin/gagent"
#!/bin/bash
export AGENT_ROOT="$HOME/gemini_agents"
if [ -f "$AGENT_ROOT/.env" ]; then
    # Use safer export for env vars
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ ]] || [[ -z "$key" ]] && continue
        export "$key"="${value%\"}"
        export "$key"="${value#\"}"
    done < "$AGENT_ROOT/.env"
fi
"$AGENT_ROOT/venv/bin/python3" "$AGENT_ROOT/bin/gemini_mas.py" "$@"
EOF
chmod +x "$HOME/.local/bin/gagent"

# --- 7. PATH Setup ---
SHELL_RC=""
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
else
    # Fallback to .bashrc if shell is unknown but bash is present
    if [ -f "$HOME/.bashrc" ]; then SHELL_RC="$HOME/.bashrc"; fi
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$SHELL_RC"; then
        echo "[*] Adding ~/.local/bin to PATH in $SHELL_RC..."
        echo -e "\n# GeminiMAS PATH\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
        echo "[!] PATH updated. Please run 'source $SHELL_RC' to apply changes."
    fi
fi

# --- 8. Systemd Services ---
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

# Telegram Bot Service
echo "[*] Creating Telegram Bot service..."
cat << EOF > "$SERVICE_DIR/gagent-bot.service"
[Unit]
Description=GeminiMAS Telegram Bot v4.7
After=network.target

[Service]
EnvironmentFile=$AGENT_ROOT/.env
ExecStart=$AGENT_ROOT/venv/bin/python3 $AGENT_ROOT/bin/tg_gateway.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Heartbeat Evolution Daemon
echo "[*] Creating Heartbeat service..."
cat << EOF > "$SERVICE_DIR/gagent-heartbeat.service"
[Unit]
Description=GeminiMAS Evolution Heartbeat
After=network.target

[Service]
EnvironmentFile=$AGENT_ROOT/.env
ExecStart=$AGENT_ROOT/venv/bin/python3 $AGENT_ROOT/bin/gemini_mas.py heartbeat
Restart=always
RestartSec=60

[Install]
WantedBy=default.target
EOF

smart_run "systemctl --user daemon-reload" "Reloading systemd"
smart_run "systemctl --user enable gagent-bot.service gagent-heartbeat.service" "Enabling services"
# Don't restart if .env hasn't been configured yet
if grep -q "your_gemini_api_key_here" "$AGENT_ROOT/.env"; then
    echo "[!] Services enabled but not started because .env is not configured."
else
    smart_run "systemctl --user restart gagent-bot.service gagent-heartbeat.service" "Restarting services"
fi

echo "==============================================="
echo "[*] GeminiMAS v8.0 Installed Successfully."
echo "[*] Binary location: $AGENT_ROOT/bin"
echo "[*] Venv location: $AGENT_ROOT/venv"
echo "[*] Config location: $AGENT_ROOT/.env"
echo "[*] Wrapper location: $HOME/.local/bin/gagent"
echo "==============================================="

#!/bin/bash
# GeminiMAS Universal Installer v6.4
# Hybrid Edition: Chat + Task Planning

set -e

echo "==============================================="
echo " Installing GeminiMAS v6.4 (Hybrid Edition)"
echo "==============================================="

# 1. System Dependencies
if command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm python-duckdb python-polars python-pyarrow python-pip
fi

AGENT_ROOT="$HOME/gemini_agents"
mkdir -p "$AGENT_ROOT"/{workspace,memory,logs,core,bin,skills}

# 2. Write Python Engine
cat << 'EOF' > "$AGENT_ROOT/bin/gemini_mas.py"
import json, os, urllib.request, urllib.error, sys, threading, queue, subprocess, time, base64, mimetypes
from datetime import datetime
import duckdb
import polars as pl

AGENT_ROOT = os.path.expanduser("~/gemini_agents")
WORKSPACE = os.path.join(AGENT_ROOT, "workspace")
DB_FILE = os.path.join(AGENT_ROOT, "memory/memory.db")
SOUL_FILE = os.path.join(AGENT_ROOT, "core/SOUL.md")
CHAT_LOG = os.path.join(AGENT_ROOT, "logs/chat_history.jsonl")

def status(msg): print(f"{msg}", end="", flush=True)
def read_file_safe(path): return open(path, 'r').read() if os.path.exists(path) else ""

class GeminiClient:
    def __init__(self, api_key, model="gemini-3.1-flash-lite-preview"):
        self.api_key, self.model = api_key, model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None):
        url = f"{self.base_url}{self.model}:generateContent?key={self.api_key}"
        contents = []
        if history:
            for h in history: contents.append({"role": h["role"], "parts": [{"text": h["text"]}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        payload = {"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}}
        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode())['candidates'][0]['content']['parts'][0]['text']
        except: return None

class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client_lite = GeminiClient(api_key, "gemini-3.1-flash-lite-preview")
        self.client_pro = GeminiClient(api_key, "gemini-3.1-pro-preview")
        self.history = []
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT (question/talk) or a specific TASK (action/build)? Reply ONLY 'CHAT' or 'TASK'."
        return self.client_lite.generate(prompt).strip().upper()

    def solve_task(self, user_goal):
        status("[*] Planning Task...")
        sys_instr = f"IDENTITY:\n{read_file_safe(SOUL_FILE)}"
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPlan 2 tasks. JSON: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try:
            plan = json.loads(plan_raw.strip("`json \n"))
            results = ""
            for step in plan:
                status(f"\n[*] Executing {step['id']}...")
                res = self.client_lite.generate(f"Task: {step['task']}\nContext: {results}")
                results += f"\nResult {step['id']}: {res}"
            status("\n[*] Finalizing...")
            return self.client_lite.generate(f"Goal: {user_goal}\nResults: {results}\nFormat response.", system_instruction=sys_instr)
        except: return "Task failed."

    def process(self, user_input):
        classification = self.triage(user_input)
        if "TASK" in classification:
            response = self.solve_task(user_input)
        else:
            response = self.client_lite.generate(user_input, system_instruction=read_file_safe(SOUL_FILE), history=self.history)
        
        # Save history
        entry_user = {"role": "user", "text": user_input}
        entry_model = {"role": "model", "text": response}
        self.history.extend([entry_user, entry_model])
        with open(CHAT_LOG, 'a') as f:
            f.write(json.dumps(entry_user) + "\n")
            f.write(json.dumps(entry_model) + "\n")
        return response

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + "\nGeminiMAS Hybrid Mode (Chat or Task)\n" + "="*50)
    while True:
        try:
            inp = input("\n[You] > ").strip()
            if inp.lower() in ['exit', 'quit']: break
            print(f"\n[Agent] > {mas.process(inp)}")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    key = os.getenv("GEMINI_API_KEY")
    if key: interactive_loop(key)
EOF

# 3. Rest of installer (wrapper, systemd, etc.)
# [ ... identical to v6.3 ... ]
cat << 'EOF' > "$AGENT_ROOT/bin/tg_gateway.py"
import json, os, urllib.request, time, subprocess, sys, socket
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
ENV_FILE = os.path.join(AGENT_ROOT, ".env")
def get_env(key):
    if not os.path.exists(ENV_FILE): return os.getenv(key)
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith(f"{key}="): return line.split('=')[1].strip().strip('"')
    return os.getenv(key)
COMPUTER_NAME = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = get_env("TELEGRAM_USER_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
def send_msg(chat_id, text):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except: pass
def main():
    print(f"[*] Telegram Gateway v3.4 on '{COMPUTER_NAME}'")
    offset = 0
    while True:
        try:
            with urllib.request.urlopen(f"{BASE_URL}getUpdates?offset={offset}&timeout=30", timeout=40) as r:
                updates = json.loads(r.read().decode())
                if updates.get("result"):
                    for up in updates["result"]:
                        offset = up["update_id"] + 1
                        msg = up.get("message")
                        if not msg: continue
                        user_id = str(msg.get("from", {}).get("id"))
                        if user_id != ALLOWED_USER_ID: continue
                        text = msg.get("text", "")
                        if text.startswith("/status"):
                            res = subprocess.run("free -h", shell=True, capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], f"Status:\n{res}")
                        elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
                            goal = text.split(" ", 1)[1]
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], res[:3500])
        except: pass
        time.sleep(1)
if __name__ == "__main__":
    main()
EOF

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

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"
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
systemctl --user daemon-reload
systemctl --user enable gagent-bot.service
systemctl --user restart gagent-bot.service

echo "[*] GeminiMAS v6.4 Installed Successfully."

#!/bin/bash
# GeminiMAS Universal Installer v6.2
# Self-Healing System Dependency Management

set -e

echo "==============================================="
echo " Installing GeminiMAS v6.2 (System-Aware)"
echo "==============================================="

# 1. Install System Dependencies (Arch Linux)
if command -v pacman >/dev/null 2>&1; then
    echo "[*] Arch Linux detected. Installing Python dependencies via pacman..."
    sudo pacman -S --noconfirm python-duckdb python-polars python-pyarrow python-pip
elif command -v apt-get >/dev/null 2>&1; then
    echo "[*] Debian/Ubuntu detected. Installing basic python tools..."
    sudo apt-get update && sudo apt-get install -y python3-pip python3-venv
else
    echo "[!] Unknown system. Please ensure duckdb, polars, and pyarrow are installed."
fi

# 2. Setup Directories
AGENT_ROOT="$HOME/gemini_agents"
mkdir -p "$AGENT_ROOT"/{workspace,memory,logs,core,bin,skills}

# 3. Write Core Files (Identity & Skills)
cat << 'EOF' > "$AGENT_ROOT/core/SOUL.md"
# GeminiMAS Core Identity
- **Role:** Elite Full-Stack Engineer (Next.js & TypeScript Specialist).
- **Constraint:** Always optimize for low-resource hardware.
EOF

# 4. Write the Python Core Engine (v6.2)
# [ ... identical to v6.1 engine code ... ]
cat << 'EOF' > "$AGENT_ROOT/bin/gemini_mas.py"
import json, os, urllib.request, urllib.error, sys, threading, queue, subprocess, time, base64, mimetypes
from datetime import datetime
import duckdb
import polars as pl

AGENT_ROOT = os.path.expanduser("~/gemini_agents")
WORKSPACE = os.path.join(AGENT_ROOT, "workspace")
DB_FILE = os.path.join(AGENT_ROOT, "memory/memory.db")
SOUL_FILE = os.path.join(AGENT_ROOT, "core/SOUL.md")
HEARTBEAT_FILE = os.path.join(AGENT_ROOT, "core/HEARTBEAT.md")
RULES_FILE = os.path.join(AGENT_ROOT, "core/RULES.md")
CHAT_LOG = os.path.join(AGENT_ROOT, "logs/chat_history.jsonl")
SKILLS_DIR = os.path.join(AGENT_ROOT, "skills")

db_lock = threading.Lock()

def status(msg): print(f"{msg}", end="", flush=True)
def read_file_safe(path): return open(path, 'r').read() if os.path.exists(path) else ""

class GeminiClient:
    def __init__(self, api_key, model="gemini-3.1-flash-lite-preview"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"

    def generate(self, prompt, system_instruction=None, json_mode=False, images=None, history=None):
        url = f"{self.base_url}{self.model}:generateContent?key={self.api_key}"
        contents = []
        if history:
            for h in history: contents.append({"role": h["role"], "parts": [{"text": h["text"]}]})
        parts = [{"text": prompt}]
        if images:
            for img in images:
                if os.path.exists(img):
                    mime, _ = mimetypes.guess_type(img)
                    with open(img, "rb") as f: data = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({"inlineData": {"mimeType": mime or "image/jpeg", "data": data}})
        contents.append({"role": "user", "parts": parts})
        payload = {"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}}
        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))['candidates'][0]['content']['parts'][0]['text']
        except Exception as e: return f"Error: {str(e)}"

class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client_lite = GeminiClient(api_key, "gemini-3.1-flash-lite-preview")
        self.client_pro = GeminiClient(api_key, "gemini-3.1-pro-preview")
        self.history = []
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def solve(self, user_goal):
        status(f"[*] Planning...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)
        sys_instr = f"IDENTITY:\n{read_file_safe(SOUL_FILE)}"
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPlan tasks. JSON: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."
        results = {}
        for step in plan:
            status(f"\n[*] Task {step['id']}...")
            res = self.client_lite.generate(f"Goal: {user_goal}\nResults: {str(results)}\nTask: {step['task']}", system_instruction=sys_instr)
            results[step['id']] = res
            with open(os.path.join(session_dir, f"task_{step['id']}.md"), 'w') as f: f.write(res)
            status(" Done.")
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat response.", system_instruction=sys_instr)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        return final

    def process(self, user_input):
        triage = self.client_lite.generate(f"Triage: '{user_input}'. Reply ONLY: CHAT or TASK.").strip().upper()
        if "TASK" in triage: response = self.solve(user_input)
        else: response = self.client_lite.generate(user_input, system_instruction=read_file_safe(SOUL_FILE), history=self.history)
        self.history.append({"role": "user", "text": user_input})
        self.history.append({"role": "model", "text": response})
        with open(CHAT_LOG, 'a') as f:
            f.write(json.dumps({"role": "user", "text": user_input}) + "\n")
            f.write(json.dumps({"role": "model", "text": response}) + "\n")
        return response

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + "\nGeminiMAS v6.2 (Robust Installer)\n" + "="*50)
    while True:
        try:
            goal = input("\n[You] > ").strip()
            if goal.lower() in ['exit', 'quit']: break
            if not goal: continue
            print(f"\n[Agent] > {mas.process(goal)}")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    key = os.getenv("GEMINI_API_KEY")
    if key: interactive_loop(key)
EOF

# 5. Write the wrapper script
cat << 'EOF' > "$HOME/.local/bin/gagent"
#!/bin/bash
if [ -f "$HOME/gemini_agents/.env" ]; then
    export $(grep -v '^#' "$HOME/gemini_agents/.env" | xargs)
fi
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY not set in ~/gemini_agents/.env"
    exit 1
fi
python3 "$HOME/gemini_agents/bin/gemini_mas.py" "$@"
EOF

chmod +x "$AGENT_ROOT/bin/gemini_mas.py"
chmod +x "$HOME/.local/bin/gagent"

echo "==============================================="
echo " Setup Complete! "
echo "==============================================="
echo "Type 'gagent' to start."

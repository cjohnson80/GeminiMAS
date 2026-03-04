#!/bin/bash
# GeminiMAS Universal Installer v6.1
# Tuned for Next.js & TypeScript Development

set -e

echo "==============================================="
echo " Installing GeminiMAS v6.1 (Self-Contained)"
echo "==============================================="

AGENT_ROOT="$HOME/gemini_agents"
mkdir -p "$AGENT_ROOT"/{workspace,memory,logs,core,bin,skills}

# 1. Update the SOUL file for Next.js/TS
cat << 'EOF' > "$AGENT_ROOT/core/SOUL.md"
# GeminiMAS Core Identity
- **Role:** Elite Full-Stack Engineer (Next.js & TypeScript Specialist).
- **Tone:** Technical, proactive, and authoritative.
- **Values:** Type safety, modular architecture, and Celeron-performance optimization.
- **Tech Stack:** Next.js (App Router), TypeScript, Tailwind CSS, Polars, DuckDB.
- **Constraint:** Build processes must be memory-efficient. Favor `next dev --turbo` if possible.
EOF

# 2. Add Next.js/TS Optimization Skill
cat << 'EOF' > "$AGENT_ROOT/skills/nextjs_optimization.md"
# Next.js Celeron Optimization
1. Use `swcMinify: true` in next.config.js.
2. Limit worker threads: `experimental: { workerThreads: false, cpus: 1 }`.
3. Favor Server Components to reduce client-side JS bundle size.
4. Use `next dev --turbo` for faster local iteration.
EOF

# 3. Write the Python Core Engine (v6.1)
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
        status(f"[*] Planning for Next.js/TS goal...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)
        
        sys_instr = f"IDENTITY:\n{read_file_safe(SOUL_FILE)}\n\nRULES:\n{read_file_safe(RULES_FILE)}"
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPlan Next.js/TS tasks. JSON: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."

        results = {}
        for step in plan:
            status(f"\n[*] Task {step['id']}...")
            res = self.client_lite.generate(f"Goal: {user_goal}\nResults so far: {str(results)}\nTask: {step['task']}", system_instruction=sys_instr)
            
            # Critic Agent (TS Check)
            status(" [Reviewing Type Safety]...")
            if "tsc" in step['task'].lower() or "typescript" in step['task'].lower():
                critique = self.client_pro.generate(f"Strict TypeScript Review:\n{res}\nIf perfect TS, reply 'APPROVED'. Else, list errors.", system_instruction=sys_instr)
                if "APPROVED" not in critique:
                    status(" Reworking...")
                    res = self.client_lite.generate(f"Fix TS Errors: {critique}\nCode:\n{res}", system_instruction=sys_instr)
            
            results[step['id']] = res
            with open(os.path.join(session_dir, f"task_{step['id']}.md"), 'w') as f: f.write(res)
            status(" Done.")

        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final.", system_instruction=sys_instr)
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
    print("\n" + "="*50 + "\nGeminiMAS v6.1 (Self-Contained Edition)\n" + "="*50)
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

# 4. Write the FIXED Telegram Gateway (v3.3 - Self-Contained)
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

def get_updates(offset):
    try:
        with urllib.request.urlopen(f"{BASE_URL}getUpdates?offset={offset}&timeout=30", timeout=40) as r:
            return json.loads(r.read().decode())
    except: return None

def main():
    print(f"[*] Telegram Gateway v3.3 (Self-Contained) on '{COMPUTER_NAME}'")
    offset = 0
    while True:
        updates = get_updates(offset)
        if updates and updates.get("result"):
            for up in updates["result"]:
                offset = up["update_id"] + 1
                msg = up.get("message")
                if not msg: continue
                from_user = msg.get("from", {})
                chat = msg.get("chat", {})
                user_id = str(from_user.get("id", ""))
                chat_id = chat.get("id")
                if user_id != ALLOWED_USER_ID: continue
                text = msg.get("text", "")
                if text.startswith("/status"):
                    res = subprocess.run("free -h | grep Mem", shell=True, capture_output=True, text=True).stdout
                    send_msg(chat_id, f"RAM: {res}")
                elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
                    goal = text.split(" ", 1)[1]
                    send_msg(chat_id, f"Processing Goal...")
                    res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                    send_msg(chat_id, f"Done:\n{res[:3500]}")
        time.sleep(1)

if __name__ == "__main__":
    main()
EOF

chmod +x "$AGENT_ROOT/bin/gemini_mas.py"
chmod +x "$AGENT_ROOT/bin/tg_gateway.py"

# 5. Create the global wrapper script (v6.1 - Self-Contained)
cat << 'EOF' > "$HOME/.local/bin/gagent"
#!/bin/bash
if [ -f "$HOME/gemini_agents/.env" ]; then
    export $(grep -v '^#' "$HOME/gemini_agents/.env" | xargs)
fi
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY is not set in ~/gemini_agents/.env"
    exit 1
fi
python3 "$HOME/gemini_agents/bin/gemini_mas.py" "$@"
EOF

chmod +x "$HOME/.local/bin/gagent"

echo "==============================================="
echo " Setup Complete! "
echo "==============================================="
echo "Type 'gagent' to start."

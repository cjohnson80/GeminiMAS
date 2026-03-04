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

# 3. Write the Python Core Engine (v8.0)
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

class ResourceGuard:
    @staticmethod
    def is_under_pressure():
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                total = int([l.split()[1] for l in lines if 'MemTotal' in l][0])
                avail = int([l.split()[1] for l in lines if 'MemAvailable' in l][0])
                return (avail / total) < 0.15
        except: return False

class ToolBox:
    @staticmethod
    def execute(action, payload):
        try:
            if action == "run_shell":
                res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=60)
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            elif action == "fetch_url":
                req = urllib.request.Request(payload, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response: return response.read().decode('utf-8')[:8000]
            elif action == "read_file":
                with open(os.path.expanduser(payload), 'r') as f: return f.read()
            elif action == "write_file":
                data = json.loads(payload)
                with open(os.path.expanduser(data['path']), 'w') as f: f.write(data['content'])
                return f"Successfully wrote to {data['path']}"
            elif action == "notify_telegram":
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_USER_ID")
                if not bot_token or not chat_id: return "Telegram credentials missing in environment."
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": f"[Evolution Protocol]\n{payload}"}).encode(), headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req)
                return "Telegram notification sent successfully to user."
            return "Unknown tool."
        except Exception as e: return f"Tool Error: {str(e)}"

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
            with urllib.request.urlopen(req, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))['candidates'][0]['content']['parts'][0]['text']
        except Exception as e: return f"Error: {str(e)}"

    def embed(self, text):
        try:
            req = urllib.request.Request(f"{self.base_url}gemini-embedding-001:embedContent?key={self.api_key}", 
                data=json.dumps({"model":"models/gemini-embedding-001","content":{"parts":[{"text":text}]}}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode())['embedding']['values']
        except: return None

class Persistence:
    def __init__(self, api_key):
        self.client = GeminiClient(api_key)
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with db_lock:
            self.con = duckdb.connect(DB_FILE)
            self.con.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TIMESTAMP, goal TEXT, summary TEXT, embedding FLOAT[3072])")

    def save_memory(self, goal, summary):
        if vec := self.client.embed(goal + " " + summary):
            with db_lock: self.con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?)", [goal, summary, vec])

    def semantic_search(self, query, limit=3):
        if vec := self.client.embed(query):
            with db_lock: return self.con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[3072]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
        return []

class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client_lite = GeminiClient(api_key, "gemini-3.1-flash-lite-preview")
        self.client_pro = GeminiClient(api_key, "gemini-3.1-flash-lite-preview") if ResourceGuard.is_under_pressure() else GeminiClient(api_key, "gemini-3.1-pro-preview")
        self.db = Persistence(api_key)
        self.history = []
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT or a TASK that requires coding/tools/system changes? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        return res.strip().upper() if res else "CHAT"

    def run_worker_with_tools(self, task_desc, context, images, sys_instr):
        sys_prompt = sys_instr + "\n\nYou are an executor. Tools available:\n1. run_shell (payload: command)\n2. fetch_url (payload: url)\n3. read_file (payload: path)\n4. write_file (payload: JSON string {'path':'...', 'content':'...'})\n5. notify_telegram (payload: message to send to user)\n\nReply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR reply with final text if no tool is needed."
        history = f"Context:\n{context}\nTask:\n{task_desc}"
        
        for attempt in range(5):
            output = self.client_lite.generate(history, system_instruction=sys_prompt, images=images)
            if output and "{" in output and "'tool'" in output.replace('"', "'"):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    status(f" [{cmd['tool']}]...")
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'])
                    history += f"\n\nTool Output:\n{tool_result}\nAnalyze this and continue."
                except Exception as e: history += f"\n\nTool parse error: {str(e)}."
            else: return output
                
        status("\n[!] Stuck. Consulting Senior Debugger...")
        advice = self.client_pro.generate(f"Worker is stuck.\nERRORS:\n{history}\nProvide actionable fix.")
        if advice:
            status(" Advice received.\n")
            return self.client_lite.generate(history + f"\n\nADVICE:\n{advice}\nExecute task one last time.", system_instruction=sys_prompt, images=images)
        return "Task failed."

    def solve_task(self, user_goal):
        past = self.db.semantic_search(user_goal)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)
        images = [os.path.join(session_dir, f) for f in os.listdir(session_dir) if f.endswith(('.png', '.jpg'))] if os.path.exists(session_dir) else []
        
        status("[*] Planning...")
        sys_instr = f"IDENTITY:\n{read_file_safe(SOUL_FILE)}"
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPast: {past}\nPlan 2-4 tasks. JSON format: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."

        results = {}
        for step in plan:
            status(f"\n[*] Executing {step['id']}...")
            res = self.run_worker_with_tools(step['task'], str(results), images, sys_instr)
            results[step['id']] = res
            with open(os.path.join(session_dir, f"task_{step['id']}.md"), 'w') as f: f.write(res)
            status(" Done.")

        status(f"\n[*] Reviewing...")
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final response.", system_instruction=sys_instr)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        return final

    def process(self, user_input):
        if "TASK" in self.triage(user_input): response = self.solve_task(user_input)
        else: response = self.client_lite.generate(user_input, system_instruction=read_file_safe(SOUL_FILE), history=self.history)
        
        if response:
            entry_user = {"role": "user", "text": user_input}
            entry_model = {"role": "model", "text": response}
            self.history.extend([entry_user, entry_model])
            with open(CHAT_LOG, 'a') as f:
                f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
        return response

def heartbeat_daemon(api_key):
    mas = GeminiMAS(api_key)
    print("\n[!] Heartbeat Daemon Started (Evolution Mode Active)")
    while True:
        try:
            print(f"\n[Pulse] {datetime.now()} - Checking for Evolution...")
            # Trigger the evolution protocol directly
            mas.process(f"Execute the EVOLUTION PROTOCOL from this file: {HEARTBEAT_FILE}")
            time.sleep(21600) # Run every 6 hours
        except KeyboardInterrupt: break

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + "\nGeminiMAS v8.0 (Evolution Shell)\n" + "="*50)
    while True:
        try:
            inp = input("\n[You] > ").strip()
            if inp.lower() in ['exit', 'quit']: break
            if inp.lower() == 'heartbeat': 
                heartbeat_daemon(api_key)
                continue
            if not inp: continue
            print(f"\n[Agent] > {mas.process(inp)}")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    key = os.getenv("GEMINI_API_KEY")
    if not key: sys.exit(1)
    if len(sys.argv) > 1:
        if sys.argv[1] == "heartbeat": heartbeat_daemon(key)
        else: print("\n" + mas.process(" ".join(sys.argv[1:])))
    else:
        interactive_loop(key)
EOF

# 4. Write Telegram Gateway with `/approve` Command
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
    print(f"[*] Telegram Gateway v4.1 (Evolution Active) on '{COMPUTER_NAME}'")
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
                        
                        elif text.startswith("/approve "):
                            branch = text.split(" ")[1].strip()
                            send_msg(msg["chat"]["id"], f"Approving Evolution. Merging branch '{branch}' into main...")
                            cmd = f"cd ~/GeminiMAS_Repo && git checkout main && git merge {branch} && git push origin main && ./install.sh"
                            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            send_msg(msg["chat"]["id"], f"Merge Complete. System Restarted.\nOutput: {res.stdout[-1000:]}")
                        
                        elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
                            goal = text.split(" ", 1)[1]
                            send_msg(msg["chat"]["id"], "Processing...")
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], res[:3500])
                        
                        elif text and not text.startswith("/"):
                            # Direct Chat Routing
                            send_msg(msg["chat"]["id"], "Thinking...")
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), text], capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], res[:3500])
        except: pass
        time.sleep(1)

if __name__ == "__main__":
    main()
EOF

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
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
ACTIVE_LOCK = os.path.join(AGENT_ROOT, "logs/active.lock")

db_lock = threading.Lock()

def status(msg): print(f"{msg}", end="", flush=True)
def read_file_safe(path): return open(path, 'r').read() if os.path.exists(path) else ""

class ActivityMonitor:
    @staticmethod
    def set_active():
        with open(ACTIVE_LOCK, 'w') as f: f.write(str(time.time()))
    @staticmethod
    def clear_active():
        if os.path.exists(ACTIVE_LOCK): os.remove(ACTIVE_LOCK)
    @staticmethod
    def is_busy():
        if os.path.exists(ACTIVE_LOCK):
            if time.time() - os.path.getmtime(ACTIVE_LOCK) < 3600: return True
        try:
            if os.getloadavg()[0] > 1.5: return True
        except: pass
        return False

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
                if not bot_token or not chat_id: return "Error: Config missing."
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": f"[Status Update]\n{payload}"}).encode(), headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req)
                return "Notified user."
            return "Unknown tool."
        except Exception as e: return f"Tool Error: {str(e)}"

class GeminiClient:
    def __init__(self, api_key, model="gemini-3.1-flash-lite-preview"):
        self.api_key, self.model = api_key, model.replace("models/", "")
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
        con = self._get_con(read_only=False)
        if con:
            con.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TIMESTAMP, goal TEXT, summary TEXT, embedding FLOAT[3072])")
            con.close()
    def _get_con(self, read_only=False):
        for attempt in range(10):
            try: return duckdb.connect(DB_FILE, read_only=read_only)
            except: time.sleep(0.5)
        return None
    def save_memory(self, goal, summary):
        if vec := self.client.embed(goal + " " + summary):
            con = self._get_con(read_only=False)
            if con:
                con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?)", [goal, summary, vec])
                con.close()
    def semantic_search(self, query, limit=3):
        if vec := self.client.embed(query):
            con = self._get_con(read_only=True)
            if con:
                res = con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[3072]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
                con.close()
                return res
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
        prompt = f"Analyze: '{user_input}'. Is this CHAT or TASK? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        return res.strip().upper() if res else "CHAT"

    def run_worker_with_tools(self, task_desc, context, images, sys_instr):
        sys_prompt = sys_instr + "\n\nYou are an executor. Tools: run_shell, fetch_url, read_file, write_file, notify_telegram. Reply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR reply with final text."
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
        return "Task failed."

    def solve_task(self, user_goal):
        past = self.db.semantic_search(user_goal)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)
        images = [os.path.join(session_dir, f) for f in os.listdir(session_dir) if f.endswith(('.png', '.jpg'))] if os.path.exists(session_dir) else []
        status("[*] Planning...")
        sys_instr = f"IDENTITY:\n{read_file_safe(SOUL_FILE)}"
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPast: {past}\nPlan tasks. JSON: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try:
            plan = json.loads(plan_raw.strip("`json \n"))
            results = {}
            for step in plan:
                status(f"\n[*] Executing {step['id']}...")
                res = self.run_worker_with_tools(step['task'], str(results), images, sys_instr)
                results[step['id']] = res
                with open(os.path.join(session_dir, f"task_{step['id']}.md"), 'w') as f: f.write(res)
                status(" Done.")
            final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat response.", system_instruction=sys_instr)
            with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
            self.db.save_memory(user_goal, final[:1000])
            return final
        except: return "Planning failed."

    def process(self, user_input):
        ActivityMonitor.set_active()
        try:
            if "TASK" in self.triage(user_input): response = self.solve_task(user_input)
            else: response = self.client_lite.generate(user_input, system_instruction=read_file_safe(SOUL_FILE), history=self.history)
            if response:
                entry_user, entry_model = {"role": "user", "text": user_input}, {"role": "model", "text": response}
                self.history.extend([entry_user, entry_model])
                with open(CHAT_LOG, 'a') as f: f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
            return response
        finally: ActivityMonitor.clear_active()

def heartbeat_daemon(api_key):
    mas = GeminiMAS(api_key)
    hostname = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip().lower()
    print(f"\n[!] Heartbeat Daemon Started (Machine: {hostname})")
    while True:
        try:
            if ActivityMonitor.is_busy():
                print(f"[Pulse] {datetime.now()} - System busy. Delaying evolution.")
                time.sleep(1800)
                continue
            print(f"\n[Pulse] {datetime.now()} - System idle. Starting Evolution...")
            evo_prompt = (f"You are the machine '{hostname}'. System is idle. Execute the EVOLUTION PROTOCOL. "
                          f"1. Create branch: 'evolution-{hostname}'. 2. Code new feature. 3. Push to GitHub. "
                          f"4. Notify user via Telegram to /approve evolution-{hostname}.")
            mas.process(evo_prompt)
            time.sleep(21600)
        except KeyboardInterrupt: break

if __name__ == "__main__":
    key = os.getenv("GEMINI_API_KEY")
    if not key: sys.exit(1)
    if len(sys.argv) > 1:
        if sys.argv[1] == "heartbeat": heartbeat_daemon(key)
        else: print("\n" + GeminiMAS(key).process(" ".join(sys.argv[1:])))
    else:
        mas = GeminiMAS(key)
        print("\nGeminiMAS v8.3 Shell\n" + "="*30)
        while True:
            try:
                inp = input("\n[You] > ").strip()
                if inp.lower() in ['exit', 'quit']: break
                if inp: print(f"\n[Agent] > {mas.process(inp)}")
            except KeyboardInterrupt: break
EOF

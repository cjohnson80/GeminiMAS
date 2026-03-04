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

def notify_desktop(title, message):
    try: subprocess.run(["notify-send", title, message], check=False)
    except: pass

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
            self.con.execute("CREATE TABLE IF NOT EXISTS experience (timestamp TIMESTAMP, error TEXT, hint TEXT)")
            self.con.execute("CREATE TABLE IF NOT EXISTS codebase (path TEXT, chunk TEXT, embedding FLOAT[3072])")

    def save_memory(self, goal, summary):
        if vec := self.client.embed(goal + " " + summary):
            with db_lock: self.con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?)", [goal, summary, vec])

    def save_experience(self, error, hint):
        with db_lock: self.con.execute("INSERT INTO experience VALUES (now(), ?, ?)", [error, hint])

    def save_code_chunk(self, path, chunk):
        if vec := self.client.embed(chunk):
            with db_lock: self.con.execute("INSERT INTO codebase VALUES (?, ?, ?)", [path, chunk, vec])

    def semantic_search(self, query, limit=3):
        if vec := self.client.embed(query):
            with db_lock: return self.con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[3072]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
        return []

    def search_code(self, query, limit=5):
        if vec := self.client.embed(query):
            with db_lock: return self.con.execute("SELECT path, chunk FROM codebase ORDER BY list_cosine_similarity(embedding, ?::FLOAT[3072]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
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

    def load_relevant_skills(self):
        skills_text = ""
        if os.path.exists(SKILLS_DIR):
            for file in os.listdir(SKILLS_DIR):
                if file.endswith(".md"): skills_text += f"\n--- SKILL: {file} ---\n" + read_file_safe(os.path.join(SKILLS_DIR, file))[:1000]
        return skills_text

    def index_project(self, path):
        if not os.path.exists(path): return "Path not found."
        count = 0
        for root, dirs, files in os.walk(path):
            if '.git' in root or 'node_modules' in root: continue
            for file in files:
                if not file.endswith(('.py', '.js', '.html', '.css', '.ts', '.md', '.json')): continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f: content = f.read()
                    chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
                    for chunk in chunks:
                        self.db.save_code_chunk(filepath, chunk)
                        count += 1
                except: pass
        return f"Indexed {count} code chunks into Semantic DuckDB."

    def sync_hivemind(self):
        cmd = f"cd {AGENT_ROOT} && git init && git add . && git commit -m 'Auto-sync' && git pull --rebase origin main && git push origin main"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return f"HiveMind Sync Output:\n{res.stdout}\n{res.stderr}"

    def execute_tool(self, action, payload):
        try:
            if action == "run_shell":
                res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=30)
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            elif action == "fetch_url":
                req = urllib.request.Request(payload, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response: return response.read().decode('utf-8')[:5000]
            elif action == "git":
                res = subprocess.run(f"git {payload}", shell=True, capture_output=True, text=True, timeout=30)
                return f"Git:\n{res.stdout}\n{res.stderr}"
            elif action == "index_codebase": return self.index_project(payload)
            elif action == "search_codebase": return str(self.db.search_code(payload))
            elif action == "sync_hivemind": return self.sync_hivemind()
            elif action == "learn_skill":
                req = urllib.request.Request(payload, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    content = response.read().decode('utf-8')
                    name = payload.split("/")[-1].replace(".md", "").split("?")[0] + "_skill.md"
                    with open(os.path.join(SKILLS_DIR, name), "w") as f: f.write(content[:10000])
                    return f"Skill saved as {name}"
            return "Unknown tool."
        except Exception as e: return f"Tool Error: {str(e)}"

    def triage(self, user_input):
        prompt = f"Triage input: '{user_input}'.\nReply ONLY with one word: CHAT or TASK."
        return self.client_lite.generate(prompt).strip().upper()

    def run_worker_with_tools(self, task_desc, context, images):
        sys_prompt = "You are an executor. Tools: run_shell, fetch_url, git, index_codebase, search_codebase, sync_hivemind, learn_skill. Reply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR reply with final text."
        history = f"Context:\n{context}\nTask:\n{task_desc}"
        
        for attempt in range(4):
            output = self.client_lite.generate(history, system_instruction=sys_prompt, images=images)
            if output and "{" in output and "'tool'" in output.replace('"', "'"):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    status(f" [{cmd['tool']}]...")
                    tool_result = self.execute_tool(cmd['tool'], cmd['payload'])
                    history += f"\n\nTool Output:\n{tool_result}\nAnalyze this and continue."
                except Exception as e: history += f"\n\nTool parse error: {str(e)}."
            else: return output
                
        status("\n[!] Stuck. Consulting Senior Debugger...")
        advice = self.client_pro.generate(f"Worker is stuck.\nERRORS:\n{history}\nProvide actionable fix.")
        if advice:
            status(" Advice received.\n")
            return self.client_lite.generate(history + f"\n\nADVICE:\n{advice}\nExecute task one last time.", system_instruction=sys_prompt, images=images)
        return "Task failed."

    def distill_knowledge(self):
        status("\n[*] Distilling Knowledge & Pruning Memory...")
        with db_lock: df = self.db.con.execute("SELECT goal, summary FROM memory").pl()
        if len(df) < 5: return
        rules = self.client_pro.generate(f"Analyze memories: {df.to_dicts()}\nExtract 3 permanent 'Golden Rules' about user preferences. Markdown format.")
        if rules:
            with open(RULES_FILE, 'a') as f: f.write("\n" + rules)
            with db_lock: self.db.con.execute("DELETE FROM memory")
            status(" Done.\n")

    def task_workflow(self, user_input):
        past = self.db.semantic_search(user_input)
        skills = self.load_relevant_skills()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)
        images = [os.path.join(session_dir, f) for f in os.listdir(session_dir) if f.endswith(('.png', '.jpg'))] if os.path.exists(session_dir) else []
        
        status("[*] Planning...")
        sys_instr = f"IDENTITY:\n{read_file_safe(SOUL_FILE)}\nRULES:\n{read_file_safe(RULES_FILE)}\nSKILLS:\n{skills}"
        plan_raw = self.client_pro.generate(f"Goal: {user_input}\nPast: {past}\nPlan tasks. JSON format: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."

        results = {}
        for step in plan:
            status(f"\n[*] Executing {step['id']}...")
            res = self.run_worker_with_tools(step['task'], str(results), images)
            
            # The Critic Step
            status("\n[*] Critic Reviewing...")
            critique = self.client_pro.generate(f"Review code/output for bugs & efficiency (Intel Celeron focus). Output:\n{res}\nIf perfect, reply EXACTLY 'APPROVED'. Otherwise, list fixes.", system_instruction=sys_instr)
            if "APPROVED" not in critique:
                status(" Critic rejected. Reworking...")
                res = self.run_worker_with_tools(f"Critic feedback: {critique}\nFix the output.", str(results) + res, images)
            else: status(" Critic approved.")
            
            results[step['id']] = res
            with open(os.path.join(session_dir, f"task_{step['id']}.md"), 'w') as f: f.write(res)
            status(" Done.")

        status(f"\n[*] Finalizing...")
        final = self.client_lite.generate(f"Goal: {user_input}\nResults: {json.dumps(results)}\nFormat final response.", system_instruction=sys_instr)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_input, final[:1000])
        notify_desktop("GeminiMAS Complete", "Task finished.")
        return final

    def process(self, user_input):
        if "TASK" in self.triage(user_input): response = self.task_workflow(user_input)
        else: response = self.client_lite.generate(user_input, system_instruction=read_file_safe(SOUL_FILE), history=self.history)

        self.history.append({"role": "user", "text": user_input})
        self.history.append({"role": "model", "text": response})
        with open(CHAT_LOG, 'a') as f:
            f.write(json.dumps({"role": "user", "text": user_input}) + "\n")
            f.write(json.dumps({"role": "model", "text": response}) + "\n")
        return response

def heartbeat_daemon(api_key):
    mas = GeminiMAS(api_key)
    print("\n[!] Heartbeat Daemon Started")
    while True:
        try:
            print(f"\n[Pulse] {datetime.now()}")
            mas.distill_knowledge()
            time.sleep(1800)
        except KeyboardInterrupt: break

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + "\nGeminiMAS v5.0 (Elite Edition)\n" + "="*50)
    while True:
        try:
            goal = input("\n[You] > ").strip()
            if goal.lower() in ['exit', 'quit']: break
            if goal.lower() == 'heartbeat': heartbeat_daemon(api_key); continue
            if not goal: continue
            print(f"\n[Agent] > {mas.process(goal)}")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    key = os.getenv("GEMINI_API_KEY")
    if key: interactive_loop(key)
    else: print("Error: GEMINI_API_KEY not set.")

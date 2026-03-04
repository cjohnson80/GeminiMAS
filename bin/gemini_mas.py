__version__ = '8.1.0'

import json
import os
import urllib.request
import urllib.error
import sys
import threading
import queue
import subprocess
import time
import base64
import mimetypes
import argparse
from datetime import datetime
import duckdb
import polars as pl

# Configuration
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
WORKSPACE = os.path.join(AGENT_ROOT, "workspace")
DB_FILE = os.path.join(AGENT_ROOT, "memory/memory.db")
SOUL_FILE = os.path.join(AGENT_ROOT, "core/SOUL.md")
HEARTBEAT_FILE = os.path.join(AGENT_ROOT, "core/HEARTBEAT.md")
CHAT_LOG = os.path.join(AGENT_ROOT, "logs/chat_history.jsonl")
LOCAL_CONFIG = os.path.join(AGENT_ROOT, "core/local_config.json")
SKILLS_DIR = os.path.join(AGENT_ROOT, "skills")

# Threading Lock for DB
db_lock = threading.Lock()

def read_local_config():
    default_cfg = {
        "max_threads": 2,
        "cache_size": "512MB",
        "model_overrides": {},
        "disabled_features": []
    }
    if not os.path.exists(LOCAL_CONFIG):
        return default_cfg
    try:
        with open(LOCAL_CONFIG, 'r') as f:
            cfg = json.load(f)
            # Ensure keys exist
            for k, v in default_cfg.items():
                if k not in cfg: cfg[k] = v
            return cfg
    except: return default_cfg

def is_feature_enabled(feature_name):
    cfg = read_local_config()
    return feature_name not in cfg.get("disabled_features", [])

def toggle_feature(feature_name, enable=True):
    cfg = read_local_config()
    disabled = cfg.get("disabled_features", [])
    if enable and feature_name in disabled:
        disabled.remove(feature_name)
    elif not enable and feature_name not in disabled:
        disabled.append(feature_name)
    cfg["disabled_features"] = disabled
    write_local_config(cfg)
    return f"Feature '{feature_name}' is now {'enabled' if enable else 'disabled'}."

def write_local_config(config):
    with open(LOCAL_CONFIG, 'w') as f:
        json.dump(config, f, indent=4)

def status(msg):
    print(f"{msg}", end="", flush=True)

def read_file_safe(path):
    if not os.path.exists(path): return ""
    with open(path, 'r') as f: return f.read()

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
                res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=120)
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            elif action == "verify_project":
                # Superior Intelligent Tool: Actually check the code for errors
                status(f" [Verifying Code]...")
                checks = [
                    ("Linting", "npm run lint"),
                    ("TypeScript", "npx tsc --noEmit")
                ]
                results = []
                for name, cmd in checks:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=payload)
                    if res.returncode != 0:
                        results.append(f"{name} Failed:\n{res.stderr[:1000]}")
                return "Project is clean!" if not results else "\n".join(results)
            elif action == "fetch_url":
                req = urllib.request.Request(payload, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    return response.read().decode('utf-8')[:10000]
            elif action == "read_file":
                with open(os.path.expanduser(payload), 'r') as f: return f.read()
            elif action == "write_file":
                if isinstance(payload, str):
                    try: data = json.loads(payload)
                    except: return "Error: payload must be JSON for write_file"
                else: data = payload
                os.makedirs(os.path.dirname(os.path.expanduser(data['path'])), exist_ok=True)
                with open(os.path.expanduser(data['path']), 'w') as f: f.write(data['content'])
                return f"Successfully wrote to {data['path']}"
            elif action == "notify_telegram":
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_USER_ID")
                if not bot_token or not chat_id: return "Telegram credentials missing."
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": f"[Evolution Protocol]\n{payload}"}).encode(), headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req)
                return "Telegram notification sent."
            return "Unknown tool."
        except Exception as e: return f"Tool Error: {str(e)}"

class GeminiClient:
    def __init__(self, api_key, model="gemini-3.5-pro-preview"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None, stream=False, images=None):
        method = "streamGenerateContent" if stream else "generateContent"
        url = f"{self.base_url}{self.model}:{method}?key={self.api_key}"

        contents = []
        if history:
            for h in history: contents.append({"role": h["role"], "parts": [{"text": h["text"]}]})

        parts = [{"text": prompt}]
        if images:
            for img_path in images:
                if os.path.exists(img_path):
                    mime, _ = mimetypes.guess_type(img_path)
                    with open(img_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({"inlineData": {"mimeType": mime or "image/jpeg", "data": data}})

        contents.append({"role": "user", "parts": parts})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
        }

        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                if stream:
                    full_text = ""
                    # Gemini streaming returns a list of JSON objects
                    raw_data = response.read().decode("utf-8")
                    chunks = json.loads(raw_data)
                    for chunk in chunks:
                        text = chunk['candidates'][0]['content']['parts'][0]['text']
                        yield text
                else:
                    result = json.loads(response.read().decode("utf-8"))
                    return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            err_msg = f"Error: {str(e)}"
            if stream: yield err_msg
            else: return err_msg

    def embed(self, text):
        url = f"{self.base_url}gemini-embedding-001:embedContent?key={self.api_key}"
        payload = {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": text}]}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result['embedding']['values']
        except: return None
class Persistence:
    def __init__(self, api_key):
        self.client = GeminiClient(api_key)
        self.skills_dir = SKILLS_DIR
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        os.makedirs(self.skills_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        # Retry loop for initial connection
        for _ in range(5):
            try:
                with db_lock:
                    self.con = duckdb.connect(DB_FILE)
                    # Enable Write-Ahead Logging for better concurrency
                    self.con.execute("PRAGMA journal_mode=WAL")
                    self.con.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TIMESTAMP, goal TEXT, summary TEXT, embedding FLOAT[768])")
                return
            except Exception as e:
                if "locking" in str(e).lower():
                    time.sleep(1)
                    continue
                raise e

    def save_memory(self, goal, summary):
        if vec := self.client.embed(goal + " " + summary):
            for _ in range(10): # Robust retry for writes
                try:
                    with db_lock:
                        self.con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?)", [goal, summary, vec])
                    return
                except Exception as e:
                    if "locking" in str(e).lower():
                        time.sleep(0.5)
                        continue
                    break

    def semantic_search(self, query, limit=3):
        results = []
        if vec := self.client.embed(query):
            for _ in range(5):
                try:
                    with db_lock:
                        results = self.con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[768]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
                    break
                except Exception as e:
                    if "locking" in str(e).lower():
                        time.sleep(0.2)
                        continue
                    break

        # Skill Injection
        skills_found = []
        if os.path.exists(SKILLS_DIR):
            for f in os.listdir(SKILLS_DIR):
                if f.endswith(".md") and any(word in f.lower() for word in query.lower().split()):
                    skills_found.append({"goal": f"Skill: {f}", "summary": read_file_safe(os.path.join(SKILLS_DIR, f))[:2000]})

        return results + skills_found
class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.machine_name = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
        self.lite_model = "gemini-2.0-flash-lite"
        self.pro_model = "gemini-3.5-pro-preview"
        self.client_lite = GeminiClient(api_key, self.lite_model)
        self.client_pro = GeminiClient(api_key, self.pro_model)
        self.db = Persistence(api_key)
        self.history = []
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def get_system_context(self):
        soul = read_file_safe(SOUL_FILE)
        local_cfg = read_local_config()
        return f"{soul}\n\nCURRENT_MACHINE: {self.machine_name}\nLOCAL_HARDWARE_CONFIG: {json.dumps(local_cfg)}\n"

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT or a TASK that requires coding/tools/system changes? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        return res.strip().upper() if res else "CHAT"

    def run_worker_with_tools(self, task_desc, context, sys_instr, role="Developer", images=None):
        # Role-specific system instruction
        role_prompt = f"{sys_instr}\n\nYOUR_ROLE: {role}\n"
        if role == "Architect":
            role_prompt += "Focus on directory structure, scalability, and defining interfaces.\n"
        elif role == "Reviewer":
            role_prompt += "Focus on code quality, security, TypeScript strictness, and Next.js best practices.\n"

        sys_prompt = role_prompt + "\n\nYou are an executor. Tools available:\n1. run_shell (payload: command)\n2. verify_project (payload: project_path) - Runs lint/tsc to ensure code quality.\n3. fetch_url (payload: url)\n4. read_file (payload: path)\n5. write_file (payload: JSON string {'path':'...', 'content':'...'})\n6. notify_telegram (payload: message to send to user)\n\nReply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR reply with final text if no tool is needed."
        history = f"Context from previous tasks:\n{context}\n\nTask to complete as {role}:\n{task_desc}"

        for attempt in range(5):
            output = self.client_lite.generate(history, system_instruction=sys_prompt, images=images)
            if output and "{" in output and ("'tool'" in output.replace('"', "'") or '"tool"' in output):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    status(f" [{role}:{cmd['tool']}]...")
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'])
                    # Smart Context Management: If output is huge, summarize it
                    if len(tool_result) > 2000:
                        status(" [Summarizing Large Output]...")
                        tool_result = self.client_lite.generate(f"Summarize this tool output for an agent: {tool_result[:8000]}")

                    history += f"\n\nTool Output:\n{tool_result}\nAnalyze this and continue."
                except Exception as e: history += f"\n\nTool parse error: {str(e)}."
            else: return output

        status(f"\n[!] {role} Stuck. Consulting Senior Debugger...")
        # Context Compression for Senior Debugger
        brief_history = self.client_lite.generate(f"Summarize the attempts and failures so far to help a senior debugger: {history[-10000:]}")
        advice = self.client_pro.generate(f"Worker Role: {role} is stuck.\nDEBUG BRIEF:\n{brief_history}\n\nProvide an actionable fix or workaround.", system_instruction="You are a Senior Debugger. Help the worker get unstuck.")
        if advice:
            status(" Advice received. Executing final attempt...")
            final_history = history + f"\n\nSENIOR_DEBUGGER_ADVICE: {advice}\nExecute the task one last time using this advice."
            return self.client_lite.generate(final_history, system_instruction=sys_prompt, images=images)

        return f"Task failed after 5 attempts and Senior Debugger consultation."

    def solve_task(self, user_goal, images=None):
        past = self.db.semantic_search(user_goal)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)

        # Shared context file for agents to collaborate
        scratchpad_path = os.path.join(session_dir, "PROJECT_SUMMARY.md")
        with open(scratchpad_path, "w") as f:
            f.write(f"# Project Scratchpad\n\nGoal: {user_goal}\n\n## Structure\n(To be defined by Architect)\n")

        status("[*] Collaborative Planning...")
        sys_instr = self.get_system_context()
        prompt = (f"Goal: {user_goal}\nPast Context: {past}\n"
                  f"Plan 1-6 tasks using specialized agents. JSON format: [{{'id':1, 'role':'Architect|Developer|Reviewer', 'task':'...', 'parallel': false}}].\n"
                  f"- Use an Architect first to define structure in {scratchpad_path}.\n"
                  f"- Use Developers for implementation.\n"
                  f"- Use Reviewers to verify critical code.\n"
                  f"- Set 'parallel': true only for independent tasks.")

        plan_raw = self.client_pro.generate(prompt, system_instruction=sys_instr, json_mode=True, images=images)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."

        results = {}
        threads = []
        q = queue.Queue()

        def worker(step, sys_instr, results_so_far, q, imgs):
            role = step.get('role', 'Developer')
            res = self.run_worker_with_tools(step['task'], str(results_so_far), sys_instr, role=role, images=imgs)
            q.put((step['id'], res))
            with open(os.path.join(session_dir, f"task_{step['id']}_{role}.md"), 'w') as f: f.write(res)
            status(f" Task {step['id']} ({role}) Done.")

        for step in plan:
            is_parallel = step.get('parallel', False)
            role = step.get('role', 'Developer')
            status(f"\n[*] Spawning {role} for Task {step['id']} (Parallel: {is_parallel})...")

            if is_parallel:
                t = threading.Thread(target=worker, args=(step, sys_instr, dict(results), q, images))
                t.start()
                threads.append(t)
            else:
                for t in threads: t.join()
                while not q.empty():
                    tid, tres = q.get(); results[tid] = tres
                threads = []

                worker(step, sys_instr, dict(results), q, images)
                while not q.empty():
                    tid, tres = q.get(); results[tid] = tres

        for t in threads: t.join()
        while not q.empty():
            tid, tres = q.get(); results[tid] = tres

        status(f"\n[*] Final Review...")
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final summary.", system_instruction=sys_instr, images=images)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        return final

    def process(self, user_input, stream=False, images=None):
        sys_instr = self.get_system_context()
        if "TASK" in self.triage(user_input):
            response = self.solve_task(user_input, images=images)
            if stream: yield response
            else: return response
        else:
            if stream:
                full_resp = ""
                for chunk in self.client_lite.generate(user_input, system_instruction=sys_instr, history=self.history, stream=True, images=images):
                    full_resp += chunk
                    yield chunk

                if full_resp:
                    entry_user = {"role": "user", "text": user_input}
                    entry_model = {"role": "model", "text": full_resp}
                    self.history.extend([entry_user, entry_model])
                    os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
                    with open(CHAT_LOG, 'a') as f:
                        f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
            else:
                response = self.client_lite.generate(user_input, system_instruction=sys_instr, history=self.history, images=images)
                if response:
                    entry_user = {"role": "user", "text": user_input}
                    entry_model = {"role": "model", "text": response}
                    self.history.extend([entry_user, entry_model])
                    os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
                    with open(CHAT_LOG, 'a') as f:
                        f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
                return response
def heartbeat_daemon(api_key):
    mas = GeminiMAS(api_key)
    print(f"\n[!] Heartbeat Daemon Started v{__version__} (Evolution Mode + Distributed Listener)")

    repo_path = os.path.expanduser('~/GeminiMAS_Repo')
    mailbox_path = os.path.join(repo_path, 'mailbox')

    while True:
        try:
            # Sync with Repo
            subprocess.run(f"cd {repo_path} && git pull origin main", shell=True, capture_output=True)

            # 1. Check for Mailbox Commands
            cmd_file = os.path.join(mailbox_path, f"{mas.machine_name}_cmd.json")
            if os.path.exists(cmd_file):
                print(f"\n[Mail] Received remote command...")
                try:
                    with open(cmd_file, 'r') as f: cmd_data = json.load(f)

                    # Process the command
                    result = ""
                    for chunk in mas.process(cmd_data['command'], stream=True):
                        result += chunk

                    # Write result back
                    res_file = os.path.join(mailbox_path, f"{mas.machine_name}_res.json")
                    with open(res_file, 'w') as f:
                        json.dump({"result": result, "timestamp": time.time()}, f)

                    # Remove the command file locally
                    os.remove(cmd_file)

                    # Push result to Git
                    subprocess.run(f"cd {repo_path} && git add mailbox/ && git commit -m 'Mailbox: result from {mas.machine_name}' && git push origin main", shell=True)
                    print(f"[Mail] Result pushed.")
                except Exception as e:
                    print(f"Mailbox processing error: {e}")

            # 2. Process regular Heartbeat Evolution Tasks
            hb_list = read_file_safe(HEARTBEAT_FILE)
            if "[ ]" in hb_list:
                print(f"\n[Pulse] {datetime.now()} - Processing Evolution Tasks...")
                # Consume the generator
                for _ in mas.process(f"Execute the pending tasks in {HEARTBEAT_FILE}", stream=True): pass

            time.sleep(10) # Fast check for commands
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Heartbeat Error: {e}")
            time.sleep(60)

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + f"\nGeminiMAS v{__version__} (Evolution Shell)\n" + "="*50)
    print("Commands: /enable [f], /disable [f], /config, /image [path], /help, exit")
    while True:
        try:
            inp = input("\n[You] > ").strip()
            if not inp: continue
            if inp.lower() in ['exit', 'quit']: break
            if inp.lower() == 'heartbeat': heartbeat_daemon(api_key); continue

            # Local Management Commands
            images = None
            if inp.startswith("/image "):
                parts = inp.split(" ", 1)
                img_path = os.path.expanduser(parts[1].strip())
                if os.path.exists(img_path):
                    images = [img_path]
                    inp = input("[Prompt for Image] > ").strip()
                else:
                    print(f"Error: Image not found at {img_path}")
                    continue

            if inp.startswith("/disable "):
                print(toggle_feature(inp.split(" ", 1)[1].strip(), enable=False))
                continue
            if inp.startswith("/enable "):
                print(toggle_feature(inp.split(" ", 1)[1].strip(), enable=True))
                continue
            if inp.lower() == "/config":
                print(json.dumps(read_local_config(), indent=4))
                continue
            if inp.lower() == "/help":
                print("\n[Help] GeminiMAS Interactive Shell")
                print("/config          - View local machine configuration")
                print("/enable [name]   - Enable a disabled feature")
                print("/disable [name]  - Disable a feature locally (without deleting code)")
                print("heartbeat        - Start the heartbeat daemon manually")
                print("exit/quit        - Close the shell\n")
                continue

            print("\n[Agent] > ", end="", flush=True)
            for chunk in mas.process(inp, stream=True):
                print(chunk, end="", flush=True)
            print("\n")
        except KeyboardInterrupt: break
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GeminiMAS Core Engine')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('heartbeat')
    parser.add_argument('positional_prompt', nargs='?', type=str)
    parser.add_argument('--prompt', type=str)
    parser.add_argument('--image', type=str, help='Path to an image file')
    args = parser.parse_args()

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("Error: GEMINI_API_KEY not set.")
        sys.exit(1)

    if args.command == 'heartbeat':
        heartbeat_daemon(key)
    else:
        prompt = args.prompt or args.positional_prompt
        images = [args.image] if args.image else None
        if prompt:
            mas = GeminiMAS(key)
            for chunk in mas.process(prompt, stream=True, images=images):
                print(chunk, end="", flush=True)
            print()
        else:
            interactive_loop(key)

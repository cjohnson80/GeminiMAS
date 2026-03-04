import json, os, urllib.request, urllib.error, sys, threading, queue, subprocess, time, base64, mimetypes
from datetime import datetime
import duckdb
import polars as pl

AGENT_ROOT = os.path.expanduser("~/gemini_agents")
REPO_DIR = os.path.expanduser("~/GeminiMAS_Repo")
WORKSPACE = os.path.join(AGENT_ROOT, "workspace")
DB_FILE = os.path.join(AGENT_ROOT, "memory/memory.db")
SOUL_FILE = os.path.join(AGENT_ROOT, "core/SOUL.md")
HEARTBEAT_FILE = os.path.join(AGENT_ROOT, "core/HEARTBEAT.md")
CHAT_LOG = os.path.join(AGENT_ROOT, "logs/chat_history.jsonl")
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

class ToolBox:
    @staticmethod
    def execute(action, payload):
        try:
            if action == "run_shell":
                # Ensure we are always in the Repo Dir for git commands
                res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=60, cwd=REPO_DIR)
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            elif action == "notify_telegram":
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_USER_ID")
                if not bot_token or not chat_id: return "Error: Config missing."
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload_msg = {"chat_id": chat_id, "text": f"🧬 [Evolution Protocol]\n{payload}"}
                req = urllib.request.Request(url, data=json.dumps(payload_msg).encode(), headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req)
                return "Notified user via Telegram."
            elif action == "read_file":
                with open(os.path.expanduser(payload), 'r') as f: return f.read()
            elif action == "write_file":
                data = json.loads(payload)
                with open(os.path.expanduser(data['path']), 'w') as f: f.write(data['content'])
                return f"Successfully wrote to {data['path']}"
            return "Unknown tool."
        except Exception as e: return f"Tool Error: {str(e)}"

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
            with urllib.request.urlopen(req, timeout=90) as response:
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
                for l in f.readlines()[-10:]:
                    try: self.history.append(json.loads(l))
                    except: pass

    def solve_task(self, user_goal):
        hostname = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip().lower()
        status(f"[*] Planning...")
        sys_instr = f"{read_file_safe(SOUL_FILE)}\n\nHOSTNAME: {hostname}"
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPlan tasks. JSON: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try:
            plan = json.loads(plan_raw.strip("`json \n"))
            results = ""
            for step in plan:
                status(f"\n[*] Executing {step['id']}...")
                res = self.run_worker_with_tools(step['task'], results, sys_instr)
                results += f"\nResult {step['id']}: {res}"
            return self.client_lite.generate(f"Goal: {user_goal}\nResults: {results}\nFormat final response.", system_instruction=sys_instr)
        except: return "Task failed."

    def run_worker_with_tools(self, task_desc, context, sys_instr):
        sys_prompt = sys_instr + "\n\nYou are an executor. Tools: run_shell, read_file, write_file, notify_telegram. Reply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR final text."
        history = f"Context: {context}\nTask: {task_desc}"
        for attempt in range(5):
            output = self.client_lite.generate(history, system_instruction=sys_prompt)
            if output and "{" in output and "'tool'" in output.replace('"', "'"):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    status(f" [{cmd['tool']}]...")
                    tool_res = ToolBox.execute(cmd['tool'], cmd['payload'])
                    history += f"\nTool Output:\n{tool_res}"
                except: history += "\nTool parse error."
            else: return output
        return "Failed."

    def process(self, user_input):
        ActivityMonitor.set_active()
        try:
            triage = self.client_lite.generate(f"Triage: '{user_input}'. CHAT or TASK?").strip().upper()
            if "TASK" in triage: response = self.solve_task(user_input)
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
    print(f"[*] Heartbeat Active on {hostname}")
    while True:
        if not ActivityMonitor.is_busy():
            print("[Pulse] System Idle. Evolving...")
            evo_branch = f"evolution-{hostname}"
            prompt = (f"System is idle. Execute EVOLUTION PROTOCOL:\n"
                      f"1. Git: checkout -b {evo_branch}\n"
                      f"2. Invent and code one small optimization in ~/GeminiMAS_Repo/bin/\n"
                      f"3. Git: add, commit, and push origin {evo_branch}\n"
                      f"4. notify_telegram: Tell user to '/approve {evo_branch}' to merge.")
            mas.process(prompt)
        time.sleep(21600)

if __name__ == "__main__":
    key = os.getenv("GEMINI_API_KEY")
    if key:
        if len(sys.argv) > 1 and sys.argv[1] == "heartbeat": heartbeat_daemon(key)
        else: print(f"\n[Agent] > {GeminiMAS(key).process(' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Hi')}")

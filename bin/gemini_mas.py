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

# Threading Lock for DB
db_lock = threading.Lock()

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
                res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=60)
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
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

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None):
        url = f"{self.base_url}{self.model}:generateContent?key={self.api_key}"
        contents = []
        if history:
            for h in history: contents.append({"role": h["role"], "parts": [{"text": h["text"]}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

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
                result = json.loads(response.read().decode("utf-8"))
                return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            return f"Error: {str(e)}"

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
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with db_lock:
            self.con = duckdb.connect(DB_FILE)
            self.con.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TIMESTAMP, goal TEXT, summary TEXT, embedding FLOAT[768])")

    def save_memory(self, goal, summary):
        if vec := self.client.embed(goal + " " + summary):
            with db_lock: self.con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?)", [goal, summary, vec])

    def semantic_search(self, query, limit=3):
        if vec := self.client.embed(query):
            with db_lock:
                return self.con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[768]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
        return []

class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.lite_model = "gemini-2.0-flash-lite"
        self.pro_model = "gemini-3.5-pro-preview"
        self.client_lite = GeminiClient(api_key, self.lite_model)
        self.client_pro = GeminiClient(api_key, self.pro_model)
        self.db = Persistence(api_key)
        self.history = []
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT or a TASK that requires coding/tools/system changes? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        return res.strip().upper() if res else "CHAT"

    def run_worker_with_tools(self, task_desc, context, sys_instr):
        sys_prompt = sys_instr + "\n\nYou are an executor. Tools available:\n1. run_shell (payload: command)\n2. fetch_url (payload: url)\n3. read_file (payload: path)\n4. write_file (payload: JSON string {'path':'...', 'content':'...'})\n5. notify_telegram (payload: message to send to user)\n\nReply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR reply with final text if no tool is needed."
        history = f"Context:\n{context}\nTask:\n{task_desc}"

        for attempt in range(5):
            output = self.client_lite.generate(history, system_instruction=sys_prompt)
            if output and "{" in output and ("'tool'" in output.replace('"', "'") or '"tool"' in output):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    status(f" [{cmd['tool']}]...")
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'])
                    history += f"\n\nTool Output:\n{tool_result}\nAnalyze this and continue."
                except Exception as e: history += f"\n\nTool parse error: {str(e)}."
            else: return output

        return self.client_pro.generate(history + "\n\nSummarize the final outcome of this task.", system_instruction=sys_instr)

    def solve_task(self, user_goal):
        past = self.db.semantic_search(user_goal)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)

        status("[*] Planning...")
        sys_instr = read_file_safe(SOUL_FILE)
        plan_raw = self.client_pro.generate(f"Goal: {user_goal}\nPast Context: {past}\nPlan 2-4 tasks. JSON format: [{{'id':1, 'task':'...'}}]", system_instruction=sys_instr, json_mode=True)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."

        results = {}
        for step in plan:
            status(f"\n[*] Executing Task {step['id']}...")
            res = self.run_worker_with_tools(step['task'], str(results), sys_instr)
            results[step['id']] = res
            with open(os.path.join(session_dir, f"task_{step['id']}.md"), 'w') as f: f.write(res)
            status(" Done.")

        status(f"\n[*] Final Review...")
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final response for the user.", system_instruction=sys_instr)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        return final

    def process(self, user_input):
        if "TASK" in self.triage(user_input):
            response = self.solve_task(user_input)
        else:
            response = self.client_lite.generate(user_input, system_instruction=read_file_safe(SOUL_FILE), history=self.history)

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
    print(f"\n[!] Heartbeat Daemon Started v{__version__} (Evolution Mode)")
    while True:
        try:
            hb_list = read_file_safe(HEARTBEAT_FILE)
            if "[ ]" in hb_list:
                print(f"\n[Pulse] {datetime.now()} - Processing Evolution Tasks...")
                mas.process(f"Execute the pending tasks in {HEARTBEAT_FILE}")
            time.sleep(3600) # Check every hour
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Heartbeat Error: {e}")
            time.sleep(60)

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + f"\nGeminiMAS v{__version__} (Evolution Shell)\n" + "="*50)
    while True:
        try:
            inp = input("\n[You] > ").strip()
            if inp.lower() in ['exit', 'quit']: break
            if inp.lower() == 'heartbeat': heartbeat_daemon(api_key); continue
            if not inp: continue
            print(f"\n[Agent] > {mas.process(inp)}")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GeminiMAS Core Engine')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('heartbeat')
    parser.add_argument('positional_prompt', nargs='?', type=str)
    parser.add_argument('--prompt', type=str)
    args = parser.parse_args()

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("Error: GEMINI_API_KEY not set.")
        sys.exit(1)

    if args.command == 'heartbeat':
        heartbeat_daemon(key)
    else:
        prompt = args.prompt or args.positional_prompt
        if prompt:
            mas = GeminiMAS(key)
            print(mas.process(prompt))
        else:
            interactive_loop(key)

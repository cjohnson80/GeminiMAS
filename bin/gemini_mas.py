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

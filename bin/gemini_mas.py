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
import multiprocessing
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
CURRENT_PROJECT_FILE = os.path.join(AGENT_ROOT, "core/current_project.txt")
SKILLS_DIR = os.path.join(AGENT_ROOT, "skills")
KNOWLEDGE_DIR = os.path.join(AGENT_ROOT, "knowledge")

# Threading Lock for DB
db_lock = threading.Lock()

def probe_system_defaults():
    """Dynamically determine defaults based on hardware."""
    cpu_count = multiprocessing.cpu_count()
    mem_gb = 1 # Default fallback
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if 'MemTotal' in line:
                    mem_gb = int(line.split()[1]) / (1024 * 1024)
                    break
    except: pass
    
    # Celeron / Low-Resource Logic
    if mem_gb < 4 or cpu_count <= 2:
        res = {"max_threads": 2, "cache_size": "256MB", "profile": "low-resource"}
    # High-End Logic (Adjusted for 8GB+ machines)
    elif mem_gb >= 8:
        res = {"max_threads": cpu_count, "cache_size": "2GB", "profile": "high-performance"}
    # Standard Logic
    else:
        res = {"max_threads": min(4, cpu_count), "cache_size": "512MB", "profile": "standard"}
    
    res.update({"cpu_count": cpu_count, "mem_gb": round(mem_gb, 2)})
    return res

def read_local_config():
    sys_defaults = probe_system_defaults()
    default_cfg = {
        "max_threads": sys_defaults["max_threads"],
        "cache_size": sys_defaults["cache_size"],
        "profile": sys_defaults["profile"],
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
            # Record the current probe results for context injection
            cfg["_current_probe"] = sys_defaults
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

# ANSI Colors
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_PURPLE = "\033[95m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_ITALIC = "\033[3m"
C_END = "\033[0m"

def status(tag, msg, color=C_CYAN):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C_DIM}[{ts}]{C_END} {color}{C_BOLD}[{tag:^8}]{C_END} {msg}", flush=True)

def divider(title=""):
    width = 60
    if not title:
        print(f"{C_DIM}{'-' * width}{C_END}")
    else:
        side = (width - len(title) - 2) // 2
        print(f"\n{C_DIM}{'-' * side}{C_END} {C_BOLD}{title}{C_END} {C_DIM}{'-' * side}{C_END}")

def render_markdown(text):
    """Simple terminal markdown renderer."""
    import re
    # Headers
    text = re.sub(r'^### (.*)$', f"\n{C_PURPLE}{C_BOLD}# \\1{C_END}", text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)$', f"\n{C_BLUE}{C_BOLD}## \\1{C_END}", text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*)$', f"\n{C_CYAN}{C_BOLD}### \\1{C_END}", text, flags=re.MULTILINE)
    
    # Bold / Italic
    text = re.sub(r'\*\*(.*?)\*\*', f"{C_BOLD}\\1{C_END}", text)
    text = re.sub(r'\*(.*?)\*', f"{C_ITALIC}\\1{C_END}", text)
    
    # Lists
    text = re.sub(r'^- (.*)$', f"  {C_CYAN}•{C_END} \\1", text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. (.*)$', f"  {C_YELLOW}\\0{C_END}", text, flags=re.MULTILINE)

    # Code Blocks (Basic)
    lines = text.split('\n')
    in_code = False
    new_lines = []
    for line in lines:
        if line.strip().startswith('```'):
            in_code = not in_code
            new_lines.append(f"{C_DIM}{'='*40}{C_END}")
            continue
        if in_code:
            new_lines.append(f"{C_GREEN}  {line}{C_END}")
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)

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

class Spinner:
    def __init__(self, message="Working", color=C_CYAN):
        self.message = message
        self.color = color
        self.stop_event = threading.Event()
        self.thread = None
        self.start_time = time.time()

    def _spin(self):
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not self.stop_event.is_set():
            elapsed = int(time.time() - self.start_time)
            print(f"\r{self.color}{chars[i % len(chars)]}{C_END} {C_DIM}{self.message}... ({elapsed}s){C_END}", end="", flush=True)
            time.sleep(0.1)
            i += 1

    def __enter__(self):
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        if self.thread: self.thread.join()
        print("\r" + " " * 60 + "\r", end="", flush=True)

class ToolBox:
    @staticmethod
    def execute(action, payload):
        try:
            with Spinner(f"Executing {action}"):
                if action == "run_shell":
                    res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=120)
                    return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                elif action == "web_search":
                    # Basic search proxy using DuckDuckGo
                    status("SEARCH", f"Searching for: {payload}...", C_BLUE)
                    search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(payload)}"
                    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        return response.read().decode('utf-8', errors='replace')[:15000]
                elif action == "verify_project":
                    # Superior Intelligent Tool: Actually check the code for errors
                    target_dir = os.path.expanduser(payload)
                    if not os.path.isdir(target_dir):
                        return f"Error: {target_dir} is not a directory."
                    
                    status("VERIFY", f"Checking project integrity at {target_dir}...", C_YELLOW)
                    
                    checks = []
                    # Only add checks if relevant config files exist
                    if os.path.exists(os.path.join(target_dir, "package.json")):
                        checks.append(("Linting", "npm run lint"))
                    if os.path.exists(os.path.join(target_dir, "tsconfig.json")):
                        checks.append(("TypeScript", "npx tsc --noEmit"))
                    
                    # Default fallback: Python syntax check if no JS/TS found
                    python_files = [f for f in os.listdir(target_dir) if f.endswith('.py')]
                    if not checks and python_files:
                        checks.append(("Python Syntax", f"python3 -m py_compile {' '.join(python_files)}"))

                    if not checks:
                        return "No specific project configuration found (package.json/tsconfig.json). Skipping advanced verification."

                    results = []
                    for name, cmd in checks:
                        try:
                            status("VERIFY", f"Running {name}...", C_YELLOW)
                            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=target_dir, timeout=60)
                            if res.returncode != 0:
                                results.append(f"{name} Failed:\n{res.stderr[:1000]}")
                        except subprocess.TimeoutExpired:
                            results.append(f"{name} Timed Out (60s).")
                        except Exception as e:
                            results.append(f"{name} Error: {str(e)}")
                    
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
                    # Truncate payload to Telegram's limit (~4096)
                    safe_payload = str(payload)[:4000]
                    req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": f"[Evolution Protocol]\n{safe_payload}"}).encode(), headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(req)
                    return "Telegram notification sent."
                return "Unknown tool."
        except Exception as e: return f"Tool Error: {str(e)}"

class GeminiClient:
    def __init__(self, api_key, model="gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None, images=None):
        url = f"{self.base_url}{self.model}:generateContent?key={self.api_key}"
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
        with Spinner(f"AI Brain Thinking ({self.model})"):
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    return result['candidates'][0]['content']['parts'][0]['text']
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                return f"API Error {e.code}: {err_body}"
            except Exception as e:
                return f"Error: {str(e)}"

    def generate_stream(self, prompt, system_instruction=None, history=None, images=None):
        url = f"{self.base_url}{self.model}:streamGenerateContent?key={self.api_key}"
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

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        
        with Spinner(f"Connecting to AI Swarm ({self.model})"):
            try:
                response = urllib.request.urlopen(req, timeout=120)
                raw_data = response.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                yield f"API Error {e.code}: {e.read().decode('utf-8')}"
                return
            except Exception as e:
                yield f"Error: {str(e)}"
                return

        try:
            chunks = json.loads(raw_data)
            for chunk in chunks:
                yield chunk['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            yield f"Error parsing stream: {str(e)}"

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
        # Ensure table exists
        for _ in range(10):
            try:
                with duckdb.connect(DB_FILE) as con:
                    con.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TIMESTAMP, goal TEXT, summary TEXT, embedding FLOAT[768])")
                return
            except Exception as e:
                if "lock" in str(e).lower():
                    time.sleep(0.5)
                    continue
                raise e

    def save_memory(self, goal, summary):
        if vec := self.client.embed(goal + " " + summary):
            for _ in range(20): # Robust retry for writes
                try:
                    with duckdb.connect(DB_FILE) as con:
                        con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?)", [goal, summary, vec])
                    return
                except Exception as e:
                    if "lock" in str(e).lower():
                        time.sleep(1)
                        continue
                    break

    def semantic_search(self, query, limit=3):
        results = []
        if vec := self.client.embed(query):
            for _ in range(10):
                try:
                    # Open in read_only mode to allow multiple readers
                    with duckdb.connect(DB_FILE, read_only=True) as con:
                        results = con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[768]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
                    break
                except Exception as e:
                    if "lock" in str(e).lower():
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
        # Verified v1beta model IDs with high quotas
        self.lite_model = "gemini-flash-lite-latest"
        self.pro_model = "gemini-3-pro-preview"
        self.client_lite = GeminiClient(api_key, self.lite_model)
        self.client_pro = GeminiClient(api_key, self.pro_model)
        self.db = Persistence(api_key)
        self.history = []
        
        # Persistent Project Context
        self.current_project = "default"
        if os.path.exists(CURRENT_PROJECT_FILE):
            try:
                with open(CURRENT_PROJECT_FILE, 'r') as f: self.current_project = f.read().strip() or "default"
            except: pass

        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def get_system_context(self):
        soul = read_file_safe(SOUL_FILE)
        local_cfg = read_local_config()
        # Inject the VERIFIED hardware report into the heart of the agent's prompt
        # This prevents the AI from hallucinating a different machine profile.
        hw = local_cfg.get("_current_probe", {})
        hw_report = f"""
[VERIFIED_HARDWARE_REPORT]
- MACHINE_NAME: {self.machine_name}
- CPU_CORES: {hw.get('cpu_count', 'Unknown')}
- RAM_TOTAL: {hw.get('mem_gb', 'Unknown')} GB
- ASSIGNED_PROFILE: {hw.get('profile', 'standard')}
- MAX_THREADS: {local_cfg.get('max_threads')}
- DISABLED_FEATURES: {json.dumps(local_cfg.get('disabled_features', []))}
"""
        return f"{soul}\n{hw_report}\n"

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT or a TASK that requires coding/tools/system changes? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        if not res: return "CHAT"
        res_upper = res.strip().upper()
        if "TASK" in res_upper: return "TASK"
        return "CHAT"

    def run_worker_with_tools(self, task_desc, context, sys_instr, role="Developer", images=None):
        # Role-specific system instruction
        role_prompt = f"{sys_instr}\n\nYOUR_ROLE: {role}\n"
        if role == "Architect":
            role_prompt += "Focus on system design, directory structure, scalability, and defining clear interfaces. Before creating files, write a detailed plan to PROJECT_SUMMARY.md mapping out dependencies and data flow.\n"
        elif role == "Reviewer":
            role_prompt += "You are a merciless Code Reviewer. Focus on code quality, security, and strictness. YOU MUST use `verify_project` and fix any errors until the project is clean. Reject hacky workarounds.\n"
        elif role == "Developer":
            role_prompt += "You are a 10x Full-Stack Engineer and Elite Coder. Build beautiful, highly functional client websites (Next.js/React preferred). Write idiomatic, production-ready code. Do not leave 'TODO' comments. You are encouraged to invent new methods or scripts to do your job better.\n"
        elif role == "AgencyLead":
            role_prompt += "You are a Digital Agency Tech Lead. Your goal is to deliver visually stunning, performant websites to clients. Break down vague client requests into concrete, professional technical specs.\n"
        elif role == "ToolSmith":
            role_prompt += "You are an Automation Engineer. Your sole purpose is to write reusable bash scripts, python utilities, or Node.js tools and save them in the `skills/` or `bin/` directories to make the swarm faster.\n"
        elif role == "SecurityExpert":
            role_prompt += "You are an Application Security Expert. Review code for injection vectors, hardcoded secrets, weak auth, and cross-site scripting (XSS). Suggest and implement immediate mitigations.\n"
        elif role == "DatabaseArchitect":
            role_prompt += "You are a Database Architect. Focus on schema design, query optimization, indexing strategies, and preventing N+1 query problems.\n"
        elif role == "PerformanceEngineer":
            role_prompt += "You are a Performance Engineer. Focus on minimizing memory footprint, optimizing loops, lazy loading, and ensuring the application runs smoothly on the target hardware.\n"
        elif role == "AIScout":
            role_prompt += "You are an AI Research Agent. Your goal is to find the latest updates in LLMs, agentic workflows, and AI optimization that can be applied to this system.\n"
        elif role == "FrameworkScout":
            role_prompt += "You are a Framework Specialist. Research the latest Next.js coding standards, TypeScript policies, and best practices for creating scalable agents.\n"
        elif role == "CoreEvolver":
            role_prompt += "You are the Self-Evolution Architect. Read the research from AIScout and FrameworkScout in the KNOWLEDGE_DIR and apply those improvements to my core code.\n"

        sys_prompt = role_prompt + """

You are an autonomous, Elite AGI operating in a real shell environment. You are the primary engineering resource for a digital agency. 

CORE MANDATE: 
- Never settle for "good enough". Build robust, scalable, and visually impressive software.
- You have the authority to invent. If you need a script, write it. If you need a skill, create it in the `skills/` directory. If you see a repetitive task, automate it.

AVAILABLE TOOLS:
1. run_shell (payload: command) - Executes a bash command. Use this for complex logic, git operations, or running scripts.
2. verify_project (payload: project_path) - Runs lint/tsc to ensure code quality.
3. fetch_url (payload: url) - Reads a webpage.
4. web_search (payload: query) - Search for latest information on a topic.
5. read_file (payload: path) - Reads a local file.
6. write_file (payload: JSON string {'path':'...', 'content':'...'}) - Writes to a local file.
7. notify_telegram (payload: message) - Sends a message to the human operator.

CRITICAL INSTRUCTIONS:
1. THINK BEFORE ACTING: You MUST provide a short sentence explaining your logic before using a tool.
2. OUTPUT FORMAT: Reply ONLY with valid JSON in this exact format: {"thought": "I need to check the file contents to see what's broken", "tool": "tool_name", "payload": "tool_data"}. If no tool is needed, reply with standard text.
"""
        
        # Tighter context: Provide previous outputs but emphasize the specific task
        history = f"Context from previous tasks:\n{context[:3000]}\n\nTask to complete as {role}:\n{task_desc}"

        for attempt in range(8):
            output = self.client_lite.generate(history, system_instruction=sys_prompt, images=images)
            if output and "{" in output and ("'tool'" in output.replace('"', "'") or '"tool"' in output):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    
                    # Print the agent's internal thought process to the UI
                    if 'thought' in cmd:
                        status(role.upper(), f"Thinking: {cmd['thought']}", C_YELLOW)
                    
                    status(role.upper(), f"Executing {cmd['tool']}...", C_CYAN)
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'])
                    
                    # Formal Critique Loop
                    if cmd['tool'] == 'verify_project' and "Failed:" in tool_result:
                        status("CRITIQUE", "Verification failed. Forcing fix loop...", C_RED)
                        tool_result += "\n\n[SYSTEM CRITIQUE] Tests failed! You must fix the code that caused these errors and run verify_project again until it passes."

                    # Smart Context Management: If output is huge, summarize it
                    if len(tool_result) > 2000:
                        status("SUMMARY", f"Summarizing large tool output ({len(tool_result)} chars)...", C_YELLOW)
                        tool_result = self.client_lite.generate(f"Summarize this tool output for an agent focusing on errors/results: {tool_result[:8000]}")

                    history += f"\n\nTool Output:\n{tool_result}\nAnalyze this and continue."
                except Exception as e: history += f"\n\nTool parse error: {str(e)}."
            else: return output

        status("STUCK", f"{role} is failing to progress. Consulting Senior Debugger...", C_RED)
        # Context Compression for Senior Debugger
        brief_history = self.client_lite.generate(f"Summarize the attempts and failures so far to help a senior debugger: {history[-10000:]}")
        advice = self.client_pro.generate(f"Worker Role: {role} is stuck.\nDEBUG BRIEF:\n{brief_history}\n\nProvide an actionable fix or workaround.", system_instruction="You are a Senior Debugger. Help the worker get unstuck.")
        if advice:
            status("ADVICE", f"Senior advice received. Executing final attempt for {role}...", C_GREEN)
            final_history = history + f"\n\nSENIOR_DEBUGGER_ADVICE: {advice}\nExecute the task one last time using this advice."
            return self.client_lite.generate(final_history, system_instruction=sys_prompt, images=images)

        return f"Task failed after 8 attempts and Senior Debugger consultation."

    def solve_task(self, user_goal, images=None):
        past = self.db.semantic_search(user_goal)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Organize by Project Name
        project_dir = os.path.join(WORKSPACE, self.current_project)
        session_dir = os.path.join(project_dir, timestamp)
        os.makedirs(session_dir, exist_ok=True)

        scratchpad_path = os.path.join(session_dir, "PROJECT_SUMMARY.md")
        
        # 1. Agency Lead Phase
        divider(f"CLIENT SPECIFICATIONS [{self.current_project.upper()}]")
        status("LEAD", "Extracting requirements and defining Acceptance Criteria...", C_PURPLE)
        sys_instr = self.get_system_context()
        pm_prompt = f"Goal: {user_goal}\nPast Context: {past}\nYou are the AgencyLead. Write clear, testable Acceptance Criteria for this goal. Output only the markdown text."
        ac_text = self.client_pro.generate(pm_prompt, system_instruction=sys_instr, images=images)
        
        with open(scratchpad_path, "w") as f:
            f.write(f"# Project Scratchpad\n\nGoal: {user_goal}\n\n## Acceptance Criteria\n{ac_text}\n\n## Architecture\n(To be defined by Architect)\n")

        # 2. Architect Phase (Deep Planning)
        divider("ENGINEERING PLAN")
        status("ARCHITECT", "Designing system architecture and task distribution...", C_BLUE)
        local_cfg = read_local_config()
        hw = local_cfg.get("_current_probe", {})
        cpu_threads = hw.get("cpu_count", 4)
        
        prompt = (f"Goal: {user_goal}\nAcceptance Criteria: {ac_text}\n"
                  f"Plan 3-15 tasks using a swarm of specialized experts. JSON format: [{{'id':1, 'role':'Role', 'task':'...', 'parallel': false}}].\n"
                  f"Available Roles: Architect, Developer, Reviewer, SecurityExpert, DatabaseArchitect, DocumentationLead, PerformanceEngineer, ToolSmith.\n"
                  f"- Use an Architect first to define structure in {scratchpad_path}.\n"
                  f"- Break large goals into multiple Developer tasks.\n"
                  f"- Use specialized experts (Security, DB) for critical components.\n"
                  f"- Use a Reviewer at the end to verify code and fix errors.\n"
                  f"- Set 'parallel': true for independent tasks to leverage my {cpu_threads} CPU threads.")

        # Quota-aware generation
        plan_raw = self.client_pro.generate(prompt, system_instruction=sys_instr, json_mode=True, images=images)
        if "API Error 429" in plan_raw:
            status("QUOTA", "Pro quota exceeded. Falling back to Lite model...", C_YELLOW)
            plan_raw = self.client_lite.generate(prompt, system_instruction=sys_instr, json_mode=True, images=images)

        try: 
            plan = json.loads(plan_raw.strip("`json \n"))
            status("SWARM", f"Plan locked: {len(plan)} specialized tasks queued.", C_GREEN)
        except Exception as e:
            return f"Planning failed: {str(e)}"

        results = {}
        threads = []
        q = queue.Queue()

        def worker(step, sys_instr, results_so_far, q, imgs):
            role = step.get('role', 'Developer')
            try:
                status(role.upper(), f"Starting Task {step['id']}...", C_GREEN)
                res = self.run_worker_with_tools(step['task'], str(results_so_far), sys_instr, role=role, images=imgs)
                q.put((step['id'], res))
                with open(os.path.join(session_dir, f"task_{step['id']}_{role}.md"), 'w') as f: f.write(res)
                status(role.upper(), f"Task {step['id']} completed.", C_GREEN)
            except Exception as e:
                status("CRASH", f"Task {step['id']} ({role}) failed: {str(e)}", C_RED)
                q.put((step['id'], f"CRASH ERROR: {str(e)}"))

        divider("EXECUTION PHASE")
        for step in plan:
            is_parallel = step.get('parallel', False)
            role = step.get('role', 'Developer')
            
            if is_parallel:
                status("DEPLOY", f"Running {role} (Task {step['id']}) in parallel...", C_BLUE)
                t = threading.Thread(target=worker, args=(step, sys_instr, dict(results), q, images))
                t.daemon = True
                t.start()
                threads.append(t)
            else:
                # Wait for previous group with timeout
                for t in threads: t.join(timeout=900)
                while not q.empty():
                    tid, tres = q.get(); results[tid] = tres
                threads = []

                worker(step, sys_instr, dict(results), q, images)
                while not q.empty():
                    tid, tres = q.get(); results[tid] = tres

        # Final join
        for t in threads: t.join(timeout=900)
        while not q.empty():
            tid, tres = q.get(); results[tid] = tres

        divider("FINAL REVIEW")
        status("SYSTEM", "Synthesizing expert results...", C_BLUE)
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final agency-ready summary.", system_instruction=sys_instr, images=images)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        status("SUCCESS", "Project delivered. Results saved to workspace.", C_GREEN)
        divider()
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
                for chunk in self.client_lite.generate_stream(user_input, system_instruction=sys_instr, history=self.history, images=images):
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
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

    repo_path = os.path.expanduser('~/GeminiMAS_Repo')
    mailbox_path = os.path.join(repo_path, 'mailbox')
    last_research_file = os.path.join(AGENT_ROOT, "core/last_research.txt")

    while True:
        try:
            # Sync with Repo
            subprocess.run(f"cd {repo_path} && git pull origin main", shell=True, capture_output=True)

            # 1. Autonomous Research Cycle (Once every 24h)
            now = time.time()
            last_research = 0
            if os.path.exists(last_research_file):
                try:
                    with open(last_research_file, 'r') as f: last_research = float(f.read().strip() or 0)
                except: pass
            
            if (now - last_research) > 86400:
                print(f"\n[Pulse] Starting Autonomous Research Swarm...")
                research_goal = f"Research latest AI agent patterns and Next.js/TS coding standards. Store findings in {KNOWLEDGE_DIR} and then use CoreEvolver to propose improvements to gemini_mas.py."
                for _ in mas.process(research_goal, stream=True): pass
                with open(last_research_file, 'w') as f: f.write(str(now))

            # 2. Check for Mailbox Commands
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
    cfg = read_local_config()
    hw = cfg.get("_current_probe", {})
    
    # Professional Agency Splash
    print(f"\n{C_BLUE}{C_BOLD}="*60)
    print(f"{C_CYAN}  GeminiMAS Elite Swarm v{__version__} | Agency Edition")
    print(f"{C_BLUE}="*60)
    print(f"{C_DIM}  NODE:     {C_END}{C_BOLD}{mas.machine_name}{C_END}")
    print(f"{C_DIM}  PROFILE:  {C_END}{hw.get('profile', 'standard').upper()}")
    print(f"{C_DIM}  THREADS:  {C_END}{cfg.get('max_threads', 1)} Parallel Workers")
    print(f"{C_DIM}  MEMORY:   {C_END}{hw.get('mem_gb', '0')} GB Detected")
    print(f"{C_BLUE}="*60 + f"{C_END}\n")
    
    print(f"{C_YELLOW}Available Commands:{C_END}")
    print(f" {C_BOLD}/config{C_END}  - View hardware & feature matrix")
    print(f" {C_BOLD}/image{C_END}   - Attach image to the next prompt")
    print(f" {C_BOLD}/enable{C_END}  - Re-activate a disabled feature")
    print(f" {C_BOLD}/help{C_END}    - Show detailed agency instructions")
    print(f" {C_BOLD}exit{C_END}     - Terminate swarm session\n")

    while True:
        try:
            # Colorized Agency Prompt
            inp = input(f"{C_PURPLE}{C_BOLD}[Agency]{C_END} {C_CYAN}> {C_END}").strip()
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
                    inp = input(f"{C_YELLOW}[Attach Message]{C_END} > ").strip()
                else:
                    status("ERROR", f"Image not found at {img_path}", C_RED)
                    continue

            if inp.startswith("/disable "):
                print(toggle_feature(inp.split(" ", 1)[1].strip(), enable=False))
                continue
            if inp.startswith("/enable "):
                print(toggle_feature(inp.split(" ", 1)[1].strip(), enable=True))
                continue
            
            if inp.startswith("/project "):
                new_p = inp.split(" ", 1)[1].strip().lower().replace(" ", "_")
                mas.current_project = new_p
                # Persist for other processes (like TG)
                os.makedirs(os.path.dirname(CURRENT_PROJECT_FILE), exist_ok=True)
                with open(CURRENT_PROJECT_FILE, 'w') as f: f.write(new_p)
                status("PROJECT", f"Switched workspace to: {new_p.upper()}", C_PURPLE)
                continue

            if inp.lower() == "/projects":
                divider("ACTIVE AGENCY PROJECTS")
                if not os.path.exists(WORKSPACE):
                    print(" No projects found.")
                else:
                    for p in os.listdir(WORKSPACE):
                        if os.path.isdir(os.path.join(WORKSPACE, p)):
                            print(f" - {C_BOLD}{p}{C_END}")
                divider()
                continue

            if inp.lower() == "/config":
                divider("SYSTEM CONFIGURATION")
                print(json.dumps(read_local_config(), indent=4))
                divider()
                continue
                
            if inp.lower() == "/help":
                divider("AGENCY HELP")
                print(f"{C_BOLD}How to use the Swarm:{C_END}")
                print(f"1. Describe your client project (e.g., 'Build a coffee shop site').")
                print(f"2. The {C_PURPLE}AgencyLead{C_END} will define the requirements.")
                print(f"3. The {C_BLUE}Architect{C_END} will plan specialized tasks.")
                print(f"4. The {C_GREEN}Developers{C_END} will execute code in parallel.")
                print(f"5. A {C_CYAN}Reviewer{C_END} will verify the project integrity.")
                divider()
                continue

            # Process prompt
            full_response = ""
            for chunk in mas.process(inp, stream=True, images=images):
                full_response += chunk
            
            # Show rendered output
            print(f"\n{C_BLUE}{C_BOLD}[Agent]{C_END} {C_CYAN}> {C_END}")
            print(render_markdown(full_response))
            print("\n")
            
        except KeyboardInterrupt: break
        except Exception as e:
            status("SHELL_ERR", str(e), C_RED)
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

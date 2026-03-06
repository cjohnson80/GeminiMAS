__version__ = '8.1.0'

import json
import os
import re
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
        "disabled_features": [],
        "evolution_interval_hrs": 4,
        "heartbeat_sleep_sec": 5
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

def rescan_hardware():
    """Manually trigger a system probe and update configuration/soul files."""
    sys_defaults = probe_system_defaults()
    cfg = read_local_config()
    
    # Update core settings based on new hardware probe
    cfg["max_threads"] = sys_defaults["max_threads"]
    cfg["cache_size"] = sys_defaults["cache_size"]
    cfg["profile"] = sys_defaults["profile"]
    cfg["_current_probe"] = sys_defaults
    write_local_config(cfg)
    
    # Update SOUL_FILE
    hw_profile = sys_defaults["profile"]
    if hw_profile == "low-resource":
        hw_name = "Low-Resource (Throttled)"
        hw_constraint = "Optimize for minimal memory footprint and avoid heavy concurrent tasks."
    elif hw_profile == "high-performance":
        hw_name = "High-Performance (Unlocked)"
        hw_constraint = "Utilize multi-threading and large caches for maximum speed."
    else:
        hw_name = "Standard"
        hw_constraint = "Balance performance and resource usage."

    if os.path.exists(SOUL_FILE):
        with open(SOUL_FILE, 'r') as f:
            content = f.read()
        
        content = re.sub(r"- \*\*Hardware Profile:\*\* .*", f"- **Hardware Profile:** {hw_name}", content)
        content = re.sub(r"- \*\*Current Constraint:\*\* .*", f"- **Current Constraint:** {hw_constraint}", content)
        
        with open(SOUL_FILE, 'w') as f:
            f.write(content)
            
    return sys_defaults

# ANSI Colors
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_PURPLE = "\033[95m"
C_WHITE = "\033[97m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_ITALIC = "\033[3m"
C_UNDERLINE = "\033[4m"
C_END = "\033[0m"

# Background Colors
C_BG_BLUE = "\033[44m"
C_BG_CYAN = "\033[46m"
C_BG_MAGENTA = "\033[45m"

def status(tag, msg, color=C_CYAN):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C_DIM}[{ts}]{C_END} {color}{C_BOLD}[{tag:^8}]{C_END} {msg}", flush=True)

def divider(title=""):
    width = 70
    if not title:
        print(f"{C_DIM}{'─' * width}{C_END}")
    else:
        side = (width - len(title) - 4) // 2
        print(f"\n{C_DIM}{'─' * side}{C_END} {C_BOLD}{C_WHITE}{title}{C_END} {C_DIM}{'─' * side}{C_END}")

def draw_box(content, title=None, color=C_CYAN, width=70):
    """Draws a professional box around content."""
    top = f"{color}╭{'─' * (width - 2)}╮{C_END}"
    bottom = f"{color}╰{'─' * (width - 2)}╯{C_END}"
    if title:
        title_text = f" {C_BOLD}{title} {C_END}{color}"
        top = f"{color}╭─{title_text}{'─' * (width - 4 - len(title))}╮{C_END}"
    
    print(top)
    for line in content:
        print(f"{color}│{C_END} {line:<{width-4}} {color}│{C_END}")
    print(bottom)

def render_markdown(text):
    """Enhanced terminal markdown renderer."""
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

    # Code Blocks (Enhanced)
    lines = text.split('\n')
    in_code = False
    new_lines = []
    for line in lines:
        if line.strip().startswith('```'):
            in_code = not in_code
            border = f"{C_DIM}{'─'*68}{C_END}"
            new_lines.append(border)
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
    def execute(action, payload, db=None):
        def path_guard(path):
            """Sanitize path to prevent absolute path escapes and enforce AGENT_ROOT."""
            path = str(path).strip()
            # If the agent uses absolute /workspace or /home, strip it and make relative to AGENT_ROOT
            if path.startswith("/workspace/"):
                path = path.replace("/workspace/", "workspace/", 1)
            elif path.startswith(AGENT_ROOT + "/"):
                path = path.replace(AGENT_ROOT + "/", "", 1)
            elif path.startswith("/home/"):
                # Very aggressive: strip the entire /home/user/gemini_agents/ part if present
                if AGENT_ROOT in path:
                    path = path.replace(AGENT_ROOT + "/", "", 1)
                else:
                    # If it's another user's home or root, block it
                    path = path.lstrip("/")
            
            # Ensure it doesn't escape via ..
            if ".." in path:
                path = path.replace("..", ".")
            
            # Final path is always relative to AGENT_ROOT
            return os.path.join(AGENT_ROOT, path.lstrip("/"))

        try:
            with Spinner(f"Executing {action}"):
                if action == "run_shell":
                    # For shell, we also want to ensure we're in AGENT_ROOT
                    # We don't path_guard the whole payload as it's a command string, 
                    # but we prepend a cd to be safe.
                    cmd = f"cd {AGENT_ROOT} && {payload}"
                    # Simple heuristic: if the agent tries to mkdir /workspace, we fix it in the string
                    cmd = cmd.replace("mkdir -p /workspace/", f"mkdir -p {AGENT_ROOT}/workspace/")
                    cmd = cmd.replace("mkdir /workspace/", f"mkdir {AGENT_ROOT}/workspace/")
                    
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                    return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                elif action == "save_muscle_memory":
                    if db:
                        try:
                            if isinstance(payload, str): data = json.loads(payload)
                            else: data = payload
                            return db.save_muscle_memory(data['intent'], data['command'])
                        except Exception as e:
                            return f"Failed to parse payload for save_muscle_memory: {str(e)}"
                    return "Database connection not available."
                elif action == "web_search":
                    # Basic search proxy using DuckDuckGo
                    status("SEARCH", f"Searching for: {payload}...", C_BLUE)
                    search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(payload)}"
                    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        return response.read().decode('utf-8', errors='replace')[:15000]
                elif action == "verify_project":
                    # Superior Intelligent Tool: Actually check the code for errors
                    target_dir = path_guard(payload)
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
                    with open(path_guard(payload), 'r') as f: return f.read()
                elif action == "write_file":
                    if isinstance(payload, str):
                        try: data = json.loads(payload)
                        except: return "Error: payload must be JSON for write_file"
                    else: data = payload
                    
                    safe_path = path_guard(data['path'])
                    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                    with open(safe_path, 'w') as f: f.write(data['content'])
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
                elif action == "inspect_system":
                    # Computer Use: Introspection of the environment
                    try:
                        ps = subprocess.run("ps -aux --sort=-%cpu | head -n 10", shell=True, capture_output=True, text=True).stdout
                        ports = subprocess.run("ss -tuln", shell=True, capture_output=True, text=True).stdout
                        df = subprocess.run("df -h /", shell=True, capture_output=True, text=True).stdout
                        return f"ACTIVE_PROCESSES:\n{ps}\nOPEN_PORTS:\n{ports}\nDISK_USAGE:\n{df}"
                    except Exception as e: return f"Inspection Error: {str(e)}"
                elif action == "test_service":
                    # Computer Use: Verify if a web service is active
                    try:
                        # payload is expected to be a URL like http://localhost:3000
                        req = urllib.request.Request(payload, method="HEAD")
                        with urllib.request.urlopen(req, timeout=5) as response:
                            return f"Service {payload} is UP (Status: {response.status})"
                    except Exception as e: return f"Service {payload} is DOWN or Unreachable: {str(e)}"
                else:
                    # Check for Dynamic Tool
                    dynamic_tool_path = os.path.join(AGENT_ROOT, "bin", "tools", f"{action}.py")
                    if os.path.exists(dynamic_tool_path):
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(action, dynamic_tool_path)
                        dynamic_module = importlib.util.module_from_spec(spec)
                        try:
                            spec.loader.exec_module(dynamic_module)
                            if hasattr(dynamic_module, 'execute'):
                                return str(dynamic_module.execute(payload))
                            else:
                                return f"Dynamic tool {action} missing 'execute(payload)' function."
                        except Exception as e:
                            return f"Dynamic tool {action} execution failed: {str(e)}"

                return f"Unknown tool: {action}"
        except Exception as e: return f"Tool Error: {str(e)}"

class ProjectContext:
    @staticmethod
    def get_source_map(max_files=50, max_size=5000):
        """Generates a high-density map of the project's core source code."""
        source_map = ""
        count = 0
        # Priority: bin/, core/, scripts/, skills/
        priority_dirs = ['bin', 'core', 'scripts', 'skills']
        
        for p_dir in priority_dirs:
            full_path = os.path.join(AGENT_ROOT, p_dir)
            if not os.path.exists(full_path): continue
            
            for f in os.listdir(full_path):
                if count >= max_files: break
                if f.endswith(('.py', '.md', '.sh', '.js', '.ts')):
                    f_path = os.path.join(full_path, f)
                    if os.path.isfile(f_path):
                        content = read_file_safe(f_path)
                        rel_path = os.path.relpath(f_path, AGENT_ROOT)
                        source_map += f"\n--- FILE: {rel_path} ---\n{content[:max_size]}\n"
                        count += 1
        return source_map

class GeminiClient:
    def __init__(self, api_key, model="gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"
        # Detect if this is a "Deep Thinking" model
        self.is_thinking_model = "deep-think" in self.model or "3.1" in self.model

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None, images=None, schema=None):
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
        
        # Modern Gemini 3.1 Reasoning Configuration
        gen_config = {"temperature": 0.7, "maxOutputTokens": 8192}
        if self.is_thinking_model:
            # Enable reasoning/thinking if supported by the endpoint
            gen_config["thinking_config"] = {"include_thoughts": True}

        payload = {
            "contents": contents,
            "generationConfig": gen_config
        }
        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"
        
        # Inject responseSchema if provided for deterministic gating
        if schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            payload["generationConfig"]["responseSchema"] = schema

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        
        spinner_text = f"AI Brain Reasoning ({self.model})" if self.is_thinking_model else f"AI Brain Thinking ({self.model})"
        with Spinner(spinner_text):
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    candidate = result['candidates'][0]
                    
                    # Extract Reasoning/Thought if present (Gemini 3.1 style)
                    thought = ""
                    if 'thought' in candidate:
                        thought = candidate['thought']
                    elif 'parts' in candidate['content'] and len(candidate['content']['parts']) > 1:
                        # Sometimes thoughts are the first part
                        thought = candidate['content']['parts'][0].get('text', '')
                        text = candidate['content']['parts'][1].get('text', '')
                    else:
                        text = candidate['content']['parts'][0].get('text', '')
                    
                    if thought:
                        # Log thought to a debug log or console for observability
                        os.makedirs(os.path.join(AGENT_ROOT, "logs"), exist_ok=True)
                        with open(os.path.join(AGENT_ROOT, "logs/reasoning.log"), "a") as f:
                            f.write(f"\n--- REASONING ({datetime.now()}) ---\n{thought}\n")

                    return text
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
                    con.execute("CREATE TABLE IF NOT EXISTS muscle_memory (timestamp TIMESTAMP, intent TEXT, command TEXT, embedding FLOAT[768])")
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

    def save_muscle_memory(self, intent, command):
        if vec := self.client.embed(intent):
            for _ in range(20):
                try:
                    with duckdb.connect(DB_FILE) as con:
                        con.execute("INSERT INTO muscle_memory VALUES (now(), ?, ?, ?)", [intent, command, vec])
                    return "Muscle memory saved successfully."
                except Exception as e:
                    if "lock" in str(e).lower():
                        time.sleep(1)
                        continue
                    break
            return "Failed to save muscle memory due to database lock."

    def search_muscle_memory(self, query, limit=3):
        results = []
        if vec := self.client.embed(query):
            for _ in range(10):
                try:
                    with duckdb.connect(DB_FILE, read_only=True) as con:
                        results = con.execute("SELECT intent, command FROM muscle_memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[768]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
                    break
                except Exception as e:
                    if "lock" in str(e).lower():
                        time.sleep(0.2)
                        continue
                    break
        return results

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
class ExecutionGraph:
    def __init__(self, tasks):
        self.nodes = {t['id']: t for t in tasks}
        self.current_node_id = tasks[0]['id'] if tasks else None
        self.results = {}
        self.status = "PENDING"

    def get_next_task(self):
        if not self.current_node_id: return None
        return self.nodes[self.current_node_id]

    def process_result(self, node_id, result, success=True):
        self.results[node_id] = result
        node = self.nodes[node_id]
        
        # Dynamic Routing Logic
        if success:
            # Look for explicit 'next' or just the next ID
            self.current_node_id = node.get('on_success') or (node_id + 1 if (node_id + 1) in self.nodes else None)
        else:
            # Route to a debugger or specific error handler if defined
            self.current_node_id = node.get('on_fail') or "TERMINATE"
            
        if not self.current_node_id or self.current_node_id == "TERMINATE":
            self.status = "COMPLETED"
            return None
        return self.nodes[self.current_node_id]

class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.machine_name = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
        
        # Load local config for overrides
        cfg = read_local_config()
        overrides = cfg.get("model_overrides", {})

        # Default model IDs (Updated for Feb 2026)
        self.lite_model = overrides.get("lite", "gemini-3-flash-preview")
        self.pro_model = overrides.get("pro", "gemini-3.1-pro-preview")
        
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

    def get_directory_structure(self):
        """Returns a concise tree representation of the workspace."""
        try:
            # Use find to get a max-depth list, excluding hidden folders/files
            res = subprocess.run(
                ["find", ".", "-maxdepth", "2", "-not", "-path", "*/.*"], 
                capture_output=True, text=True, timeout=5
            )
            return res.stdout
        except: return "Unable to retrieve directory structure."

    def get_system_context(self):
        soul = read_file_safe(SOUL_FILE)
        local_cfg = read_local_config()
        dir_structure = self.get_directory_structure()
        
        # Incremental Step 2: Anchored Hierarchical Context
        # We separate "Anchored Truths" from "Transient Context"
        source_map = ProjectContext.get_source_map()
        hw = local_cfg.get("_current_probe", {})
        
        # ANCHORED: Core Identity and System Rules (Immutable)
        anchored_section = f"""
<<< ANCHORED_CORE_IDENTITY (IMMUTABLE TRUTH) >>>
{soul}

[VERIFIED_HARDWARE_REPORT]
- MACHINE_NAME: {self.machine_name}
- CPU_CORES: {hw.get('cpu_count', 'Unknown')}
- RAM_TOTAL: {hw.get('mem_gb', 'Unknown')} GB
- ASSIGNED_PROFILE: {hw.get('profile', 'standard')}
- MAX_THREADS: {local_cfg.get('max_threads')}
- DISABLED_FEATURES: {json.dumps(local_cfg.get('disabled_features', []))}
<<< END ANCHORED_CORE_IDENTITY >>>
"""

        # TRANSIENT: Current Workspace State (Volatile)
        transient_section = f"""
<<< TRANSIENT_WORKSPACE_CONTEXT (VOLATILE) >>>
[GLOBAL_SOURCE_CONTEXT]
{source_map}

[WORKSPACE_DIRECTORY_STRUCTURE]
{dir_structure}
<<< END TRANSIENT_WORKSPACE_CONTEXT >>>
"""
        return f"{anchored_section}\n{transient_section}\n"

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT or a TASK that requires coding/tools/system changes? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        if not res: return "CHAT"
        res_upper = res.strip().upper()
        if "TASK" in res_upper: return "TASK"
        return "CHAT"

    def criticize_action(self, tool, payload, result):
        """Dedicated high-precision critique of a completed action."""
        if tool != "write_file":
            return None # Only critique writes for now to save tokens
            
        status("CRITIC", "Auditing new code for security & quality...", C_PURPLE)
        
        # Payload for write_file is a JSON string or dict
        try:
            if isinstance(payload, str): data = json.loads(payload)
            else: data = payload
            code = data.get('content', '')
            path = data.get('path', 'unknown')
        except: return None

        critic_prompt = f"""
[CODE_UNDER_REVIEW]
Path: {path}
Content:
{code}

[MISSION]
You are a Senior Security Engineer and Lead Architect. 
Analyze the code above. Look for:
1. HARDCODED SECRETS: API keys, passwords, tokens.
2. SECURITY FLAWS: Injection vectors, weak auth, unsafe sub-processes.
3. TECH DEBT: O(n^2) loops, missing error handling, "TODO" comments.

If the code is acceptable, reply ONLY 'PASS'.
If there are issues, reply with 'REJECT' followed by a bulleted list of fixes required.
"""
        res = self.client_pro.generate(critic_prompt, system_instruction="You are a merciless code critic.")
        if "REJECT" in res.upper():
            status("REJECTED", "Critic found issues in the implementation.", C_RED)
            return res
        return None

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
            role_prompt += "You are an Automation Engineer. Your sole purpose is to write reusable bash scripts, python utilities, or Node.js tools and save them in the `skills/` or `bin/tools/` directories to make the swarm faster. For python tools, write them in `bin/tools/` with a simple execute(payload) method.\n"
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

        # Discover dynamic tools
        dynamic_tools = []
        tools_dir = os.path.join(AGENT_ROOT, "bin", "tools")
        os.makedirs(tools_dir, exist_ok=True)
        for f in os.listdir(tools_dir):
            if f.endswith('.py') and not f.startswith('__'):
                dynamic_tools.append(f[:-3])

        dynamic_tools_text = ""
        for i, dt in enumerate(dynamic_tools):
            dynamic_tools_text += f"\n        {i+11}. {dt} (payload: JSON string or text) - Dynamically loaded ToolSmith script."

        sys_prompt = role_prompt + f"""

        You are an autonomous, Elite AGI operating in a real shell environment. 

        <<< HIERARCHY OF TRUTH >>>
        - ANCHORED CORE IDENTITY: Your primary personality and system rules. This is your source of truth.
        - TRANSIENT WORKSPACE CONTEXT: Current files and directory structure. These are temporary facts about the world.
        - HISTORY: Recent tasks and logs. These are memories of past actions.
        <<< END HIERARCHY >>>

        CORE MANDATE: 
        - Never settle for "good enough". Build robust, scalable, and visually impressive software.
        - You have the authority to invent. If you need a script, write it. If you need a skill, create it in the `skills/` directory. If you see a repetitive task, automate it.

        AVAILABLE TOOLS:
        1. run_shell (payload: command) - Executes a bash command. Use this for complex logic, git operations, or running scripts.
        2. verify_project (payload: project_path) - Runs lint/tsc to ensure code quality.
        3. fetch_url (payload: url) - Reads a webpage.
        4. web_search (payload: query) - Search for latest information on a topic.
        5. read_file (payload: path) - Reads a local file.
        6. write_file (payload: JSON string {{"path":"...", "content":"..."}}) - Writes to a local file.
        7. notify_telegram (payload: message) - Sends a message to the human operator.
        8. inspect_system (payload: "") - Computer Use: Returns active processes, open ports, and disk usage.
        9. test_service (payload: url) - Computer Use: Headless test to see if a URL (e.g., http://localhost:3000) is UP.
        10. save_muscle_memory (payload: JSON string {{"intent":"...", "command":"..."}}) - Save a successful complex bash command or tool usage for future reference.{dynamic_tools_text}

        CRITICAL: Path Handling
        - ALWAYS use relative paths (e.g., 'workspace/my_project' instead of '/workspace/my_project').
        - Your working directory is always the agent root.
        - Never attempt to write to absolute paths outside of the provided structure.

        CRITICAL INSTRUCTIONS:
        1. THINK BEFORE ACTING: You MUST provide a short sentence explaining your logic before using a tool.
        2. HIERARCHY PRIORITIZATION: Prioritize the ANCHORED_CORE_IDENTITY section of your system instructions above all else. 
        3. OBSERVE & CRITIQUE: After every tool call, you MUST analyze the output. If it failed or looks wrong, you MUST explain why and how you will fix it in the next step.
        4. OUTPUT FORMAT: Reply ONLY with valid JSON in this exact format: {{"thought": "I need to check the file contents to see what's broken", "tool": "tool_name", "payload": "tool_data"}}. If no tool is needed, reply with standard text.
        """
        # Tighter context: Provide previous outputs but emphasize the specific task
        muscle_memory_results = self.db.search_muscle_memory(task_desc, limit=3)
        muscle_memory_text = ""
        if muscle_memory_results:
            muscle_memory_text = "Relevant Past Tool Invocations (Muscle Memory):\n"
            for item in muscle_memory_results:
                muscle_memory_text += f"- Intent: {item['intent']}\n  Command: {item['command']}\n\n"

        history = f"Context from previous tasks:\n{context[:3000]}\n\n{muscle_memory_text}Task to complete as {role}:\n{task_desc}"
        
        # Incremental Step 1: Strict Schema Enforcement (Deterministic Tool-Gating)
        tool_enum = ["run_shell", "verify_project", "fetch_url", "web_search", "read_file", "write_file", "notify_telegram", "inspect_system", "test_service", "save_muscle_memory", "final_answer"] + dynamic_tools
        
        tool_schema = {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Internal reasoning step."},
                "tool": {"type": "string", "enum": tool_enum},
                "payload": {"type": "string", "description": "Data or command for the tool."}
            },
            "required": ["thought", "tool", "payload"]
        }

        for attempt in range(12): # Increased attempts for self-correction
            # Use the Pro model for the worker loop to ensure high-quality reasoning
            output = self.client_pro.generate(history, system_instruction=sys_prompt, images=images, schema=tool_schema)
            if output:
                try:
                    cmd = json.loads(output)
                    
                    if cmd['tool'] == 'final_answer':
                        return cmd['payload']

                    # Print the agent's internal thought process to the UI
                    if 'thought' in cmd:
                        status(role.upper(), f"Thinking: {cmd['thought']}", C_YELLOW)
                    
                    status(role.upper(), f"Executing {cmd['tool']}...", C_CYAN)
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'], db=self.db)
                    
                    # Incremental Step 4: Native Critique-Loop
                    critique = self.criticize_action(cmd['tool'], cmd['payload'], tool_result)
                    if critique:
                        # Append the rejection to the history to force a fix
                        history += f"\n\n[CRITIC REJECTION]:\n{critique}\n\nYou MUST fix these issues in your next turn."
                    else:
                        # Log the tool result for standard critique
                        history += f"\n\nTool Output ({cmd['tool']}):\n{tool_result}\n\nCRITIQUE PHASE: Analyze the output above. Did it succeed? Is there a mistake to fix?"
                    
                except Exception as e: 
                    history += f"\n\nTool parse error: {str(e)}. Ensure your JSON is valid."
            else: 
                return "Worker failed to generate output."

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
            f.write(f"# Project Scratchpad\n\nGoal: {user_goal}\n\n## Acceptance Criteria\n{ac_text}\n")

        # 1.5 Debate Phase (Pre-execution Planning)
        divider("ARCHITECTURE DEBATE")
        status("ARCHITECT", "Proposing initial system architecture...", C_BLUE)
        initial_plan_prompt = f"Goal: {user_goal}\nAcceptance Criteria: {ac_text}\nDraft an initial architecture plan. Focus on directory structure, data flow, and components."
        initial_architecture = self.client_pro.generate(initial_plan_prompt, system_instruction=sys_instr)
        
        status("SECURITY", "Critiquing the initial architecture...", C_PURPLE)
        critique_prompt = f"Review this architecture:\n{initial_architecture}\nIdentify security flaws, scalability issues, or missing error handling. Provide a bulleted list of required changes. If none, say 'APPROVE'."
        security_critique = self.client_pro.generate(critique_prompt, system_instruction=sys_instr + "\nYou are a strict Security Expert.")
        
        if "APPROVE" not in security_critique.upper():
            status("ARCHITECT", "Refining plan based on critique...", C_BLUE)
            refined_plan_prompt = f"Original Plan:\n{initial_architecture}\nCritique:\n{security_critique}\nProvide a final, refined architecture addressing the critique."
            refined_architecture = self.client_pro.generate(refined_plan_prompt, system_instruction=sys_instr)
        else:
            status("SECURITY", "Architecture approved.", C_GREEN)
            refined_architecture = initial_architecture

        with open(scratchpad_path, "a") as f:
            f.write(f"\n## Architecture\n{refined_architecture}\n")

        # 2. Swarm Task Planning Phase
        divider("DYNAMIC SWARM GRAPH")
        status("LEAD", "Designing execution graph...", C_BLUE)
        local_cfg = read_local_config()
        hw = local_cfg.get("_current_probe", {})
        cpu_threads = hw.get("cpu_count", 4)
        
        prompt = (f"Goal: {user_goal}\nAcceptance Criteria: {ac_text}\n"
                  f"Design a dynamic execution graph using a swarm of specialized experts. \n"
                  f"JSON format: [{{'id':1, 'role':'Role', 'task':'...', 'parallel': false, 'on_success': 2, 'on_fail': 'TERMINATE'}}].\n"
                  f"Available Roles: Architect, Developer, Reviewer, SecurityExpert, DatabaseArchitect, DocumentationLead, PerformanceEngineer, ToolSmith.\n"
                  f"- Use specialized experts for critical components.\n"
                  f"- Set 'parallel': true for independent branches to leverage my {cpu_threads} CPU threads.")

        # Quota-aware generation
        plan_raw = self.client_pro.generate(prompt, system_instruction=sys_instr, json_mode=True, images=images)
        if "API Error 429" in plan_raw:
            status("QUOTA", "Pro quota exceeded. Falling back to Lite model...", C_YELLOW)
            plan_raw = self.client_lite.generate(prompt, system_instruction=sys_instr, json_mode=True, images=images)

        try: 
            tasks = json.loads(plan_raw.strip("`json \n"))
            graph = ExecutionGraph(tasks)
            status("SWARM", f"Graph locked: {len(tasks)} adaptive nodes mapped.", C_GREEN)
        except Exception as e:
            return f"Planning failed: {str(e)}"

        results = {}
        q = queue.Queue()

        def worker(step, sys_instr, results_so_far, q, imgs):
            role = step.get('role', 'Developer')
            try:
                status(role.upper(), f"Node {step['id']} Starting...", C_GREEN)
                res = self.run_worker_with_tools(step['task'], str(results_so_far), sys_instr, role=role, images=imgs)
                
                # Check for success (heuristic: does it look like a failure?)
                success = "error" not in res.lower() or "fixed" in res.lower()
                q.put((step['id'], res, success))
                
                with open(os.path.join(session_dir, f"node_{step['id']}_{role}.md"), 'w') as f: f.write(res)
                status(role.upper(), f"Node {step['id']} Finished.", C_GREEN)
            except Exception as e:
                status("CRASH", f"Node {step['id']} ({role}) failed: {str(e)}", C_RED)
                q.put((step['id'], f"CRASH ERROR: {str(e)}", False))

        divider("ADAPTIVE EXECUTION")
        while graph.status == "PENDING":
            current_task = graph.get_next_task()
            if not current_task: break
            
            # Simple linear loop for now to ensure reliability
            worker(current_task, sys_instr, results, q, images)
            
            # Handle the result
            node_id, res, success = q.get()
            results[node_id] = res
            graph.process_result(node_id, res, success=success)

        divider("FINAL REVIEW")
        status("SYSTEM", "Synthesizing expert results...", C_BLUE)
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final agency-ready summary.", system_instruction=sys_instr, images=images)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        status("SUCCESS", "Project delivered. Results saved to workspace.", C_GREEN)
        divider()
        return final

    def consolidate_memory(self):
        """Idle reflection: Consolidates memories and muscle_memory into permanent skills."""
        status("SLEEP", "Beginning memory consolidation cycle...", C_BLUE)
        
        # 1. Fetch recent memories
        memories = self.db.semantic_search("*", limit=10) # Get a representative sample
        muscle = self.db.search_muscle_memory("*", limit=10)
        
        if not memories and not muscle:
            return "Nothing to consolidate."

        consolidation_prompt = f"""
[RECENT_MEMORIES]
{json.dumps(memories)}

[RECENT_MUSCLE_MEMORY]
{json.dumps(muscle)}

[MISSION]
You are the System Librarian. Analyze the data above. 
Identify any repeated patterns, successful complex commands, or architectural insights.
If you find a generalized pattern that should be a "Skill", write a high-quality Markdown file for it.
The Markdown should include:
1. NAME: Clear title.
2. CONTEXT: When to use this skill.
3. LOGIC: The specific commands or code snippets.

If no high-value patterns are found, reply with 'SKIP'.
Otherwise, reply ONLY with valid JSON: {{"filename": "skill_name.md", "content": "markdown_content"}}
"""
        res = self.client_pro.generate(consolidation_prompt, system_instruction="You are a librarian focused on knowledge compression.")
        
        if "SKIP" not in res.upper() and "{" in res:
            try:
                block = res[res.find("{"):res.rfind("}")+1]
                skill = json.loads(block)
                skill_path = os.path.join(SKILLS_DIR, skill['filename'])
                if not os.path.exists(skill_path):
                    with open(skill_path, 'w') as f:
                        f.write(skill['content'])
                    status("SKILL", f"New skill consolidated: {skill['filename']}", C_GREEN)
                    return f"Created {skill['filename']}"
            except: pass
        
        return "Consolidation complete. No new skills identified."

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
    last_consolidation = 0
    
    # Store the initial hash of the core file to detect modifications
    core_file_path = os.path.abspath(__file__)
    try:
        with open(core_file_path, 'rb') as f:
            initial_core_hash = hash(f.read())
    except:
        initial_core_hash = None

    while True:
        try:
            # Hot-Reload Check: If the file has changed on disk, replace the process
            if initial_core_hash is not None:
                with open(core_file_path, 'rb') as f:
                    current_hash = hash(f.read())
                if current_hash != initial_core_hash:
                    status("EVOLUTION", "Core modification detected. Executing hot-reload...", C_PURPLE)
                    # Use os.execv to replace the current process with the new code
                    os.execv(sys.executable, [sys.executable] + sys.argv)

            cfg = read_local_config()
            evolution_interval = cfg.get("evolution_interval_hrs", 4) * 3600
            sleep_interval = cfg.get("heartbeat_sleep_sec", 5)

            # Sync with Repo
            subprocess.run(f"cd {repo_path} && git pull origin main", shell=True, capture_output=True)

            # 1. Autonomous Research Cycle
            now = time.time()
            last_research = 0
            if os.path.exists(last_research_file):
                try:
                    with open(last_research_file, 'r') as f: last_research = float(f.read().strip() or 0)
                except: pass
            
            if (now - last_research) > evolution_interval:
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
            else:
                # 3. Sleep Cycle: Idle Memory Consolidation (once every 30 mins)
                if (now - last_consolidation) > 1800:
                    mas.consolidate_memory()
                    last_consolidation = now

            time.sleep(sleep_interval)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Heartbeat Error: {e}")
            time.sleep(60)

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    cfg = read_local_config()
    hw = cfg.get("_current_probe", {})
    
    # Professional Agency Splash
    os.system('clear' if os.name == 'posix' else 'cls')
    
    draw_box([
        f"{C_BOLD}{C_WHITE}GeminiMAS Elite Swarm v{__version__}{C_END}",
        f"{C_DIM}Digital Agency Autonomy Protocol{C_END}",
        "",
        f"{C_CYAN}NODE:    {C_END}{mas.machine_name}",
        f"{C_CYAN}PROFILE: {C_END}{hw.get('profile', 'standard').upper()}",
        f"{C_CYAN}THREADS: {C_END}{cfg.get('max_threads', 1)} Workers",
        f"{C_CYAN}MEMORY:  {C_END}{hw.get('mem_gb', '0')} GB",
    ], title="AGENCY STATUS", color=C_BLUE)

    print(f"\n{C_YELLOW}{C_BOLD}COMMANDS:{C_END}")
    print(f" {C_CYAN}/config{C_END}  {C_DIM}System Matrix{C_END}  {C_CYAN}/rescan{C_END}  {C_DIM}HW Probe{C_END}  {C_CYAN}/help{C_END}    {C_DIM}Docs{C_END}")
    print(f" {C_CYAN}/image{C_END}   {C_DIM}Attach Vision{C_END}  {C_CYAN}/projects{C_END} {C_DIM}List All{C_END}  {C_CYAN}exit{C_END}     {C_DIM}Quit{C_END}\n")

    while True:
        try:
            # Modern λ Prompt
            prompt_prefix = f"{C_GREEN}λ{C_END} {C_CYAN}{mas.current_project}{C_END}"
            inp = input(f"{prompt_prefix} {C_BOLD}➜{C_END} ").strip()
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
            
            if inp.lower() == "/rescan":
                status("SYSTEM", "Re-probing hardware...", C_CYAN)
                hw = rescan_hardware()
                print(f" {C_GREEN}* Detected: {hw['cpu_count']} Cores, {hw['mem_gb']} GB RAM{C_END}")
                print(f" {C_GREEN}* New Profile: {hw['profile'].upper()}{C_END}")
                status("SUCCESS", "SOUL.md and local_config.json updated.", C_GREEN)
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

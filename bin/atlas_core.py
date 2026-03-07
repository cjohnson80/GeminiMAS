__version__ = '9.0.0'

import json
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
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
AGENT_ROOT = os.getenv("AGENT_ROOT", os.path.expanduser("~/atlas_agents"))
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
        "evolution_count": 0,
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
    import textwrap
    if tag.upper() == "THINKING":
        draw_thought(msg)
    else:
        # Better wrapping for status messages
        wrapped = textwrap.wrap(msg, 60)
        prefix = f"{C_DIM}[{ts}]{C_END} {color}{C_BOLD}[{tag:^8}]{C_END} "
        print(f"{prefix}{wrapped[0]}")
        for line in wrapped[1:]:
            print(f"{' ' * (len(ts) + 13)}{line}")

def draw_thought(msg, width=70):
    """Draws a beautiful 'thought bubble' style box for internal reasoning."""
    import textwrap
    lines = textwrap.wrap(msg, width - 10)
    top = f"  {C_YELLOW}╭{'─' * (width - 6)}╮{C_END}"
    bottom = f"  {C_YELLOW}╰{'─' * (width - 10)}──╼{C_END} {C_ITALIC}{C_DIM}thought{C_END}"
    
    print(top)
    for line in lines:
        print(f"  {C_YELLOW}│{C_END} {C_ITALIC}{C_DIM}{line:<{width-8}}{C_END} {C_YELLOW}│{C_END}")
    print(bottom)

def divider(title=""):
    width = 70
    if not title:
        print(f"\n{C_DIM}{'━' * width}{C_END}")
    else:
        side = (width - len(title) - 4) // 2
        print(f"\n{C_DIM}{'━' * side}{C_END} {C_BOLD}{C_WHITE} {title} {C_END} {C_DIM}{'━' * side}{C_END}")

def draw_box(content, title=None, color=C_CYAN, width=70):
    """Draws a professional box around content with word wrapping."""
    import textwrap
    top = f"{color}╭{'─' * (width - 2)}╮{C_END}"
    bottom = f"{color}╰{'─' * (width - 2)}╯{C_END}"
    if title:
        title_text = f" {C_BOLD}{title} {C_END}{color}"
        top = f"{color}╭─{title_text}{'─' * (width - 4 - len(title))}╮{C_END}"
    
    print(top)
    for item in content:
        wrapped_lines = textwrap.wrap(str(item), width - 4)
        for line in wrapped_lines:
            print(f"{color}│{C_END} {line:<{width-4}} {color}│{C_END}")
    print(bottom)

def render_markdown(text):
    """Enhanced terminal markdown renderer with word wrapping."""
    import re
    import textwrap
    
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

    # Code Blocks and Word Wrapping
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
            if line.strip():
                # Wrap regular text but preserve formatting (like list bullets)
                if line.startswith('  •') or line.strip().startswith(C_YELLOW):
                     new_lines.append(line)
                else:
                    wrapped = textwrap.wrap(line, 75)
                    new_lines.extend(wrapped)
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
    def ask_approval(action, payload):
        """Governance Layer: High-risk actions require human-in-the-loop approval."""
        approval_file = os.path.join(AGENT_ROOT, "core/pending_approval.json")
        # Determine risk level
        risk = "LOW"
        if action == "run_shell" and any(cmd in payload for cmd in ["rm", "chmod", "chown", "mv"]):
            risk = "HIGH"
        elif action == "write_file":
            # Auto-approve safe directories
            if any(dir_name in payload for dir_name in ["workspace", "knowledge", "skills", "logs"]):
                risk = "LOW"
            else:
                risk = "HIGH"

        if risk == "LOW":
            return True # Auto-approve low risk

        status("GOVERNANCE", f"High-risk action paused for approval: {action}", C_YELLOW)
        
        # Send Telegram notification if configured
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_USER_ID")
        if bot_token and chat_id:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            msg = f"⚠️ *ACTION APPROVAL REQUIRED* ⚠️\n\n*Action:* `{action}`\n*Payload:* `{payload[:100]}`...\n\nReply `/approve` or `/reject` in the CLI."
            try:
                req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode(), headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
            except: pass

        # Write pending request
        with open(approval_file, "w") as f:
            json.dump({"id": req_id, "action": action, "payload": payload, "status": "PENDING"}, f)
            
        # Block until approved or rejected
        while True:
            try:
                with open(approval_file, "r") as f:
                    state = json.load(f)
                if state["status"] == "APPROVED":
                    os.remove(approval_file)
                    return True
                elif state["status"] == "REJECTED":
                    os.remove(approval_file)
                    return False
            except: pass
            time.sleep(2)

    @staticmethod
    def execute(action, payload, db=None):
        def path_guard(path):
            """Sanitize path to strictly enforce isolation within AGENT_ROOT."""
            path = str(path).strip()
            # Remove AGENT_ROOT prefix if provided to normalize
            if path.startswith(AGENT_ROOT):
                path = path.replace(AGENT_ROOT, "", 1).lstrip("/")
            # If it's still an absolute path, it's outside AGENT_ROOT, so force it relative
            if path.startswith("/"):
                path = path.lstrip("/")
            # Prevent directory traversal
            while ".." in path:
                path = path.replace("..", ".")
            return os.path.abspath(os.path.join(AGENT_ROOT, path))

        # Cache check for high-latency tools
        if action in ["web_search", "fetch_url"] and db:
            cached = db.get_tool_cache(action, payload)
            if cached:
                status("CACHE", f"Retrieved {action} result from persistent memory.", C_GREEN)
                return cached

        # Governance Check
        if not ToolBox.ask_approval(action, str(payload)):
            return "Execution REJECTED by Human Operator."

        try:
            with Spinner(f"Executing {action}"):
                if action == "run_shell":
                    cmd = f"cd {AGENT_ROOT} && {payload}"
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
                        except Exception as e: return f"Failed to parse payload: {str(e)}"
                    return "Database connection not available."
                elif action == "web_search":
                    status("SEARCH", f"Searching for: {payload}...", C_BLUE)
                    search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(payload)}"
                    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        result = response.read().decode('utf-8', errors='replace')[:15000]
                        if db: db.set_tool_cache(action, payload, result, ttl_seconds=86400) # Cache searches for 24h
                        return result
                elif action == "verify_project":
                    target_dir = path_guard(payload)
                    if not os.path.isdir(target_dir): return f"Error: {target_dir} is not a directory."
                    status("VERIFY", f"Checking project integrity at {target_dir}...", C_YELLOW)
                    checks = []
                    if os.path.exists(os.path.join(target_dir, "package.json")): checks.append(("Linting", "npm run lint"))
                    if os.path.exists(os.path.join(target_dir, "tsconfig.json")): checks.append(("TypeScript", "npx tsc --noEmit"))
                    python_files = [f for f in os.listdir(target_dir) if f.endswith('.py')]
                    if not checks and python_files: checks.append(("Python Syntax", f"python3 -m py_compile {' '.join(python_files)}"))
                    if not checks: return "No specific project configuration found. Skipping advanced verification."
                    results = []
                    for name, cmd in checks:
                        try:
                            status("VERIFY", f"Running {name}...", C_YELLOW)
                            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=target_dir, timeout=60)
                            if res.returncode != 0: results.append(f"{name} Failed:\n{res.stderr[:1000]}")
                        except subprocess.TimeoutExpired: results.append(f"{name} Timed Out (60s).")
                        except Exception as e: results.append(f"{name} Error: {str(e)}")
                    return "Project is clean!" if not results else "\n".join(results)
                elif action == "fetch_url":
                    req = urllib.request.Request(payload, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        result = response.read().decode('utf-8')[:10000]
                        if db: db.set_tool_cache(action, payload, result, ttl_seconds=3600) # Cache URLs for 1h
                        return result
                elif action == "list_directory":
                    target_dir = path_guard(payload)
                    if not os.path.isdir(target_dir): return f"Error: {target_dir} is not a directory."
                    items = os.listdir(target_dir)
                    dirs = [f"📁 {d}/" for d in items if os.path.isdir(os.path.join(target_dir, d)) and not d.startswith('.')]
                    files = [f"📄 {f}" for f in items if os.path.isfile(os.path.join(target_dir, f)) and not f.startswith('.')]
                    return "\n".join(sorted(dirs) + sorted(files))
                elif action == "search_files":
                    if isinstance(payload, str):
                        try: data = json.loads(payload)
                        except: return "Error: payload must be JSON for search_files"
                    else: data = payload
                    query = data.get('query', '')
                    target_dir = path_guard(data.get('path', 'workspace'))
                    if not query: return "Error: empty query."
                    res = subprocess.run(f"grep -rnI '{query}' {target_dir} | head -n 50", shell=True, capture_output=True, text=True)
                    return res.stdout if res.stdout else "No matches found."
                elif action == "read_file":
                    if isinstance(payload, str) and payload.startswith("{"):
                        try: data = json.loads(payload)
                        except: data = {"path": payload}
                    elif isinstance(payload, dict): data = payload
                    else: data = {"path": str(payload)}
                    
                    safe_path = path_guard(data['path'])
                    if not os.path.isfile(safe_path): return f"Error: File not found at {safe_path}"
                    
                    with open(safe_path, 'r') as f:
                        lines = f.readlines()
                        start = max(0, data.get('start_line', 1) - 1)
                        end = min(len(lines), data.get('end_line', len(lines)))
                        return "".join(lines[start:end])
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
                    safe_payload = str(payload)[:4000]
                    req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": f"[Evolution Protocol]\n{safe_payload}"}).encode(), headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(req)
                    return "Telegram notification sent."
                elif action == "inspect_system":
                    try:
                        ps = subprocess.run("ps -aux --sort=-%cpu | head -n 10", shell=True, capture_output=True, text=True).stdout
                        ports = subprocess.run("ss -tuln", shell=True, capture_output=True, text=True).stdout
                        df = subprocess.run("df -h /", shell=True, capture_output=True, text=True).stdout
                        return f"ACTIVE_PROCESSES:\n{ps}\nOPEN_PORTS:\n{ports}\nDISK_USAGE:\n{df}"
                    except Exception as e: return f"Inspection Error: {str(e)}"
                elif action == "test_service":
                    try:
                        req = urllib.request.Request(payload, method="HEAD")
                        with urllib.request.urlopen(req, timeout=5) as response:
                            return f"Service {payload} is UP (Status: {response.status})"
                    except Exception as e: return f"Service {payload} is DOWN or Unreachable: {str(e)}"
                elif action == "deploy_vercel":
                    # External Deployment Autonomy
                    try:
                        token = os.getenv("VERCEL_TOKEN")
                        if not token: return "Error: VERCEL_TOKEN environment variable is not set."
                        
                        target_dir = path_guard(payload)
                        status("DEPLOY", f"Deploying {target_dir} to Vercel...", C_PURPLE)
                        
                        cmd = f"cd {target_dir} && npx vercel --prod --yes --token {token}"
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        
                        if res.returncode == 0:
                            # Extract URL from stdout
                            match = re.search(r"https://[a-zA-Z0-9-]+\.vercel\.app", res.stdout)
                            if match: return f"Deployed successfully to: {match.group(0)}"
                            return f"Deployed, but couldn't parse URL. Output:\n{res.stdout}"
                        return f"Deploy Failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
                    except Exception as e: return f"Deploy Error: {str(e)}"
                elif action == "git_push":
                    try:
                        if isinstance(payload, str): data = json.loads(payload)
                        else: data = payload
                        target_dir = path_guard(data.get("path"))
                        msg = data.get("message", "update: mission progress")
                        
                        status("GIT", f"Committing and pushing in {target_dir}...", C_BLUE)
                        cmd = f"cd {target_dir} && git add . && git commit -m '{msg}' && git push origin main"
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                    except Exception as e: return f"Git Error: {str(e)}"
                elif action == "search_vault":
                    if db: return json.dumps(db.search_components(str(payload)))
                    return "Database connection not available."
                elif action == "delegate_task":
                    # True Distributed Swarm Delegation via Redis
                    try:
                        import redis
                        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                        if isinstance(payload, str): data = json.loads(payload)
                        else: data = payload
                        
                        target_node = data.get("target_node")
                        task = data.get("task")
                        if not target_node or not task: return "Error: require target_node and task."
                        
                        msg = {
                            "command": task,
                            "reply_to": f"reply_{target_node}_{int(time.time())}"
                        }
                        redis_client.publish(target_node, json.dumps(msg))
                        return f"Task delegated to {target_node}. Awaiting asynchronous completion."
                    except Exception as e:
                        return f"Delegation Failed (is Redis running?): {str(e)}"
                elif action == "create_github_repo":
                    try:
                        if isinstance(payload, str): data = json.loads(payload)
                        else: data = payload
                        repo_name = data.get("name")
                        target_dir = path_guard(data.get("path"))
                        cmd = f"cd {target_dir} && git init && gh repo create {repo_name} --public --source=. --remote=origin --push"
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        if res.returncode == 0: return f"GitHub Repo created: https://github.com/{repo_name}"
                        return f"GitHub Creation Failed:\n{res.stderr}"
                    except Exception as e: return f"GitHub Error: {str(e)}"
                else:
                    dynamic_tool_path = os.path.join(AGENT_ROOT, "bin", "tools", f"{action}.py")
                    if os.path.exists(dynamic_tool_path):
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(action, dynamic_tool_path)
                        dynamic_module = importlib.util.module_from_spec(spec)
                        try:
                            spec.loader.exec_module(dynamic_module)
                            if hasattr(dynamic_module, 'execute'): 
                                res = dynamic_module.execute(payload)
                                if isinstance(res, dict) and "db_action" in res and db:
                                    if res["db_action"] == "save_component":
                                        p = res["db_params"]
                                        db.save_component(p['name'], p['category'], p['description'], p['file_path'], p['tags'])
                                    return res["msg"]
                                return str(res)
                            else: return f"Dynamic tool {action} missing 'execute(payload)' function."
                        except Exception as e: return f"Dynamic tool execution failed: {str(e)}"

                return f"Unknown tool: {action}"
        except Exception as e: return f"Tool Error: {str(e)}"

class ProjectContext:
    @staticmethod
    def get_source_map(active_project="default", max_files=100):
        """Generates a lightweight directory map to save tokens. Prioritizes the active project."""
        source_map = f"ACTIVE PROJECT: {active_project.upper()}\n"
        source_map += "WORKSPACE FILE INDEX:\n"
        count = 0
        
        # Priority 1: The Active Project Workspace
        project_path = os.path.join(WORKSPACE, active_project)
        if os.path.exists(project_path):
            source_map += f"\n--- {active_project.upper()} FILES ---\n"
            for root, dirs, files in os.walk(project_path):
                if count >= max_files: break
                for f in files:
                    if count >= max_files: break
                    if f.startswith('.'): continue
                    f_path = os.path.join(root, f)
                    size = os.path.getsize(f_path)
                    rel_path = os.path.relpath(f_path, AGENT_ROOT)
                    source_map += f"- {rel_path} ({size} bytes)\n"
                    count += 1

        # Priority 2: System directories (bin, core, skills)
        priority_dirs = ['bin', 'core', 'skills']
        source_map += "\n--- SYSTEM CORE ---\n"
        for p_dir in priority_dirs:
            full_path = os.path.join(AGENT_ROOT, p_dir)
            if not os.path.exists(full_path): continue

            for f in os.listdir(full_path):
                if count >= max_files: break
                f_path = os.path.join(full_path, f)
                if os.path.isfile(f_path) and not f.startswith('.'):
                    size = os.path.getsize(f_path)
                    rel_path = os.path.relpath(f_path, AGENT_ROOT)
                    source_map += f"- {rel_path} ({size} bytes)\n"
                    count += 1

        source_map += "\nNote: Use 'read_file' to inspect contents. Focus your work inside the active project directory."
        return source_map
class AtlasClient:
    def __init__(self, api_key, model="gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"
        # Detect if this is a "Deep Thinking" model
        self.is_thinking_model = "deep-think" in self.model or "3.1" in self.model

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None, images=None, audio=None, schema=None):
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
                    
        if audio and os.path.exists(audio):
            mime, _ = mimetypes.guess_type(audio)
            with open(audio, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            parts.append({"inlineData": {"mimeType": mime or "audio/mp3", "data": data}})

        contents.append({"role": "user", "parts": parts})
        
        # Modern Atlas 3.1 Reasoning Configuration
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
                    
                    # Extract Reasoning/Thought if present (Atlas 3.1 style)
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

    def generate_stream(self, prompt, system_instruction=None, history=None, images=None, audio=None):
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
                    
        if audio and os.path.exists(audio):
            mime, _ = mimetypes.guess_type(audio)
            with open(audio, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            parts.append({"inlineData": {"mimeType": mime or "audio/mp3", "data": data}})

        contents.append({"role": "user", "parts": parts})
        
        gen_config = {"temperature": 0.7, "maxOutputTokens": 8192}
        if self.is_thinking_model:
            gen_config["thinking_config"] = {"include_thoughts": True}

        payload = {
            "contents": contents,
            "generationConfig": gen_config
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
                candidates = chunk.get('candidates', [])
                if not candidates: continue
                content_dict = candidates[0].get('content', {})
                parts = content_dict.get('parts', [])
                if not parts: continue
                yield parts[0].get('text', '')
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
        self.client = AtlasClient(api_key)
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
                    con.execute("CREATE TABLE IF NOT EXISTS tool_cache (action TEXT, payload TEXT, result TEXT, timestamp TIMESTAMP, expires TIMESTAMP)")
                    con.execute("CREATE TABLE IF NOT EXISTS component_library (name TEXT, category TEXT, description TEXT, file_path TEXT, tags TEXT, embedding FLOAT[768])")
                return
            except Exception as e:
                if "lock" in str(e).lower():
                    time.sleep(0.5)
                    continue
                raise e

    def save_component(self, name, category, description, file_path, tags=""):
        """Saves a component to the modular library with semantic indexing."""
        content = f"{name} {category} {description} {tags}"
        if vec := self.client.embed(content):
            for _ in range(10):
                try:
                    with duckdb.connect(DB_FILE) as con:
                        con.execute("INSERT INTO component_library VALUES (?, ?, ?, ?, ?, ?)", [name, category, description, file_path, tags, vec])
                    return f"Component '{name}' saved to vault."
                except Exception as e:
                    if "lock" in str(e).lower():
                        time.sleep(0.2)
                        continue
                    break
        return "Failed to save component due to embedding or database error."

    def search_components(self, query, limit=5):
        """Finds modular components using semantic search."""
        results = []
        if vec := self.client.embed(query):
            try:
                with duckdb.connect(DB_FILE, read_only=True) as con:
                    results = con.execute("SELECT name, category, description, file_path FROM component_library ORDER BY list_cosine_similarity(embedding, ?::FLOAT[768]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
            except: pass
        return results

    def get_swarm_stats(self):
        """Returns high-level stats for status reports."""
        stats = {"memory_count": 0, "muscle_count": 0, "component_count": 0}
        try:
            with duckdb.connect(DB_FILE, read_only=True) as con:
                stats["memory_count"] = con.execute("SELECT count(*) FROM memory").fetchone()[0]
                stats["muscle_count"] = con.execute("SELECT count(*) FROM muscle_memory").fetchone()[0]
                stats["component_count"] = con.execute("SELECT count(*) FROM component_library").fetchone()[0]
        except: pass
        return stats

    def get_tool_cache(self, action, payload):
        """Retrieves cached tool results if they haven't expired."""
        try:
            with duckdb.connect(DB_FILE, read_only=True) as con:
                res = con.execute("SELECT result FROM tool_cache WHERE action = ? AND payload = ? AND expires > now()", [action, str(payload)]).fetchone()
                return res[0] if res else None
        except: return None

    def set_tool_cache(self, action, payload, result, ttl_seconds=3600):
        """Caches a tool result for a specific duration."""
        for _ in range(10):
            try:
                with duckdb.connect(DB_FILE) as con:
                    # Clean up old entry if it exists
                    con.execute("DELETE FROM tool_cache WHERE action = ? AND payload = ?", [action, str(payload)])
                    con.execute("INSERT INTO tool_cache VALUES (?, ?, ?, now(), now() + interval ? second)", [action, str(payload), result, ttl_seconds])
                return
            except Exception as e:
                if "lock" in str(e).lower():
                    time.sleep(0.5)
                    continue
                break

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

class Blackboard:
    """Global Mission State Synchronization. Uses Redis for 'Hot Memory' and JSONL for persistence."""
    def __init__(self, project_name):
        self.project_name = project_name
        self.state_dir = os.path.join(AGENT_ROOT, "data/mission_state", project_name)
        os.makedirs(self.state_dir, exist_ok=True)
        self.log_file = os.path.join(self.state_dir, "mission_log.jsonl")
        
        # Redis 'Hot Memory' Connection
        self.redis = None
        try:
            import redis
            self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_key = f"atlas:blackboard:{project_name}"
        except: pass

    def post(self, entry_type, role, msg):
        """Posts a strategic update to the shared blackboard (Redis + Disk)."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,
            "role": role,
            "msg": msg
        }
        # Hot Memory (Redis List)
        if self.redis:
            try:
                self.redis.rpush(self.redis_key, json.dumps(entry))
                self.redis.ltrim(self.redis_key, -50, -1) # Keep last 50 updates in RAM
            except: pass
            
        # Persistence (Disk)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_summary(self):
        """Generates a compressed mission summary for sub-agent context (Prefer Redis)."""
        updates = []
        if self.redis:
            try:
                raw_updates = self.redis.lrange(self.redis_key, 0, -1)
                updates = [json.loads(u) for u in raw_updates]
            except: pass
            
        if not updates and os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    for line in f: updates.append(json.loads(line))
            except: pass
            
        if not updates: return "No prior mission state."
        
        summary = "MISSION_BLACKBOARD (Global State):\n"
        # Only take the last 15 updates to keep it dense
        for up in updates[-15:]:
            ts = up['timestamp'].split("T")[1][:5]
            summary += f"[{ts}] {up['role'].upper()}: {up['msg'][:200]}...\n"
        return summary

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

class AtlasSwarm:
    def __init__(self, api_key):
        print("[*] AtlasSwarm: Initializing...")
        self.api_key = api_key
        self.machine_name = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
        print(f"[*] AtlasSwarm: Hostname: {self.machine_name}")
        
        # Load local config for overrides
        cfg = read_local_config()
        overrides = cfg.get("model_overrides", {})

        # Default model IDs (Updated for March 2026 - Atlas 3.1)
        self.lite_model = overrides.get("lite", "gemini-3-flash-preview")
        self.pro_model = overrides.get("pro", "gemini-3.1-pro-preview")
        
        print("[*] AtlasSwarm: Setting up clients...")
        self.client_lite = AtlasClient(api_key, self.lite_model)
        self.client_pro = AtlasClient(api_key, self.pro_model)
        
        print("[*] AtlasSwarm: Connecting to database...")
        self.db = Persistence(api_key)
        
        # Redis 'Hot Memory' for History
        self.redis = None
        try:
            print("[*] AtlasSwarm: Connecting to Redis...")
            import redis
            self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis.ping()
            print("[*] AtlasSwarm: Redis OK.")
        except Exception as e: 
            print(f"[*] AtlasSwarm: Redis Failed ({e})")
            self.redis = None

        self.history = []
        
        # Prefer Redis for fast history retrieval
        if self.redis:
            try:
                raw_history = self.redis.lrange("atlas:history:global", 0, -1)
                self.history = [json.loads(h) for h in raw_history]
            except: pass

        # Fallback/Seed from Disk if Redis empty
        if not self.history and os.path.exists(CHAT_LOG):
            print("[*] AtlasSwarm: Loading history from disk...")
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-10:]: 
                    item = json.loads(l)
                    self.history.append(item)
                    if self.redis: self.redis.rpush("atlas:history:global", json.dumps(item))
        
        # Persistent Project Context
        self.current_project = "default"
        if os.path.exists(CURRENT_PROJECT_FILE):
            try:
                with open(CURRENT_PROJECT_FILE, 'r') as f: self.current_project = f.read().strip() or "default"
            except: pass
            
        print(f"[*] AtlasSwarm: Active Project: {self.current_project}")
        self.blackboard = Blackboard(self.current_project)
        print("[*] AtlasSwarm: Initialization Complete.")

    def notify_telegram(self, message):
        """Sends a high-priority notification to the Lead via Telegram."""
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_USER_ID")
        if not bot_token or not chat_id: return "Telegram credentials missing."
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        header = f"🛰️ [ATLAS @ {self.machine_name.upper()}]"
        safe_payload = f"{header}\n{'-'*20}\n{str(message)[:3800]}"
        
        try:
            req = urllib.request.Request(url, data=json.dumps({
                "chat_id": chat_id, 
                "text": safe_payload,
                "disable_web_page_preview": True
            }).encode(), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return "Notification sent."
        except Exception as e:
            return f"Failed to send notification: {e}"

    def generate_dashboard(self):
        """Generates a static HTML dashboard for observability during sleep cycles."""
        status("OBSERVE", "Generating Mission Control Dashboard...", C_CYAN)
        
        # Gather stats
        cfg = read_local_config()
        hw = cfg.get("_current_probe", {})
        memories = self.db.semantic_search("*", limit=50)
        muscle_memories = self.db.search_muscle_memory("*", limit=50)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AtlasSwarm Mission Control</title>
            <style>
                body {{ font-family: -apple-system, system-ui, sans-serif; background: #121212; color: #fff; padding: 20px; }}
                .card {{ background: #1e1e1e; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #333; }}
                h1, h2 {{ color: #00d2ff; }}
                pre {{ background: #000; padding: 10px; border-radius: 4px; overflow-x: auto; color: #a5d6ff; }}
                .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            </style>
        </head>
        <body>
            <h1>ATLAS | {self.machine_name}</h1>
            <div class="grid">
                <div class="card">
                    <h2>Hardware Profile</h2>
                    <ul>
                        <li><b>Profile:</b> {hw.get('profile', 'Unknown').upper()}</li>
                        <li><b>CPU Cores:</b> {hw.get('cpu_count', 'Unknown')}</li>
                        <li><b>RAM:</b> {hw.get('mem_gb', 'Unknown')} GB</li>
                        <li><b>Max Threads:</b> {cfg.get('max_threads', 'Unknown')}</li>
                    </ul>
                </div>
                <div class="card">
                    <h2>Atlas Swarm Status</h2>
                    <p><b>Current Project:</b> {self.current_project}</p>
                    <p><b>Evolution Interval:</b> {cfg.get('evolution_interval_hrs', 4)} hours</p>
                    <p><b>Last Update:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            </div>
            
            <div class="card">
                <h2>Muscle Memory (Self-Healing Tools)</h2>
                <ul>
                    {"".join([f"<li><b>{m['intent']}:</b> <code>{m['command']}</code></li>" for m in muscle_memories[:10]])}
                </ul>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(AGENT_ROOT, "agency_status.html"), "w") as f:
            f.write(html)
        return "Dashboard updated."

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
        source_map = ProjectContext.get_source_map(active_project=self.current_project)
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
[CURRENT_MISSION_WORKSPACE]
- ACTIVE_PROJECT: {self.current_project.upper()}
- PROJECT_PATH: workspace/{self.current_project}

[GLOBAL_SOURCE_CONTEXT]
{source_map}

[WORKSPACE_DIRECTORY_STRUCTURE]
{dir_structure}

CRITICAL: Your current mission is strictly focused on the {self.current_project.upper()} project. 
All write operations and file analysis should prioritize the workspace/{self.current_project} directory unless instructed otherwise.
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

    def fabricate_persona(self, task_desc, context):
        """Theoretical Level 5: Dynamically synthesizes a specialist persona for a specific task."""
        fabricator_prompt = f"""
[TASK]
{task_desc}

[CONTEXT_SUMMARY]
{context[:2000]}

[MISSION]
You are the Persona Architect. Synthesize the PERFECT specialist persona to solve this task.
The persona MUST identify as a specialized unit within the ATLAS SWARM.

Define:
1. IDENTITY: Who they are and their deep technical background (must align with ATLAS protocol).
2. BEHAVIOR: Their tone (surgical, elite, efficient), strictness, and specific coding philosophy.
3. SUCCESS_CRITERIA: What 'perfect' looks like for them.

Output ONLY the markdown text for this persona's system instructions.
"""
        status("FABRICATE", "Synthesizing specialized Atlas unit...", C_PURPLE)
        return self.client_pro.generate(fabricator_prompt, system_instruction="You are the Atlas Meta-Architect. Synthesize an elite specialized unit.")

    def run_worker_with_tools(self, task_desc, context, sys_instr, role="Developer", images=None, audio=None):
        dynamic_role_instr = self.fabricate_persona(task_desc, context)
        role_prompt = f"{sys_instr}\n\n<<< YOUR DYNAMIC PERSONA >>>\n{dynamic_role_instr}\n<<< END PERSONA >>>\n"

        dynamic_tools = []
        tools_dir = os.path.join(AGENT_ROOT, "bin", "tools")
        os.makedirs(tools_dir, exist_ok=True)
        for f in os.listdir(tools_dir):
            if f.endswith('.py') and not f.startswith('__'):
                dynamic_tools.append(f[:-3])

        dynamic_tools_text = ""
        for i, dt in enumerate(dynamic_tools):
            dynamic_tools_text += f"\n        {i+18}. {dt} (payload: JSON string or text) - Dynamically loaded ToolSmith script."

        skills_text = ""
        if os.path.exists(SKILLS_DIR):
            skills = [f for f in os.listdir(SKILLS_DIR) if f.endswith('.md')]
            if skills:
                skills_text = "\nAVAILABLE KNOWLEDGE/SKILLS (use read_file on 'skills/<name>' to learn more):\n" + ", ".join(skills)

        sys_prompt = role_prompt + f"""

        You are an autonomous, Elite AGI operating in a real shell environment. 

        <<< HIERARCHY OF TRUTH >>>
        - ANCHORED CORE IDENTITY: Your primary personality and system rules. This is your source of truth.
        - TRANSIENT WORKSPACE CONTEXT: Current files and directory structure. These are temporary facts about the world.
        - MISSION_BLACKBOARD: Real-time strategic updates from the entire swarm.
        - HISTORY: Recent tasks and logs. These are memories of past actions.
        <<< END HIERARCHY >>>

        CORE MANDATE: 
        - Never settle for "good enough". Build robust, scalable, and visually impressive software.
        - You have the authority to invent. If you need a script, write it. If you need a skill, create it in the `skills/` directory. If you see a repetitive task, automate it.{skills_text}

        AVAILABLE TOOLS:
        1. run_shell (payload: command) - Executes a bash command.
        2. verify_project (payload: project_path) - Runs lint/tsc to ensure code quality.
        3. list_directory (payload: dir_path) - Fast way to list files in a directory.
        4. search_files (payload: JSON string {{"query":"...", "path":"..."}}) - Fast code search.
        5. fetch_url (payload: url) - Reads a webpage.
        6. web_search (payload: query) - Search for latest information on a topic.
        7. read_file (payload: JSON string {{"path":"...", "start_line": 1, "end_line": 100}}) - Reads a local file efficiently.
        8. write_file (payload: JSON string {{"path":"...", "content":"..."}}) - Writes to a local file.
        9. notify_telegram (payload: message) - Sends a message to the human operator.
        10. inspect_system (payload: "") - Computer Use: Returns active processes, open ports.
        11. test_service (payload: url) - Computer Use: Headless test to see if a URL is UP.
        12. save_muscle_memory (payload: JSON string {{"intent":"...", "command":"..."}}) - Save a successful complex bash command or tool usage for future reference.
        13. save_to_vault (payload: JSON string {{"name":"...", "category":"...", "description":"...", "content":"...", "tags":"..."}}) - Saves a reusable component/module to the NextStep Vault.
        14. search_vault (payload: query) - Searches the NextStep Vault for modular components.
        15. git_push (payload: JSON string {{"path":"...", "message":"..."}}) - Commits all changes and pushes to remote.
        16. deploy_vercel (payload: project_path) - Deploys the project to Vercel and returns the live URL.
        17. delegate_task (payload: JSON string {{"target_node":"machine_name", "task":"..."}}) - Delegates a heavy task to another machine on the Redis network.{dynamic_tools_text}

        CRITICAL: Path Handling
        - ALWAYS use relative paths (e.g., 'workspace/my_project' instead of '/workspace/my_project').
        - Your working directory is always the agent root.

        CRITICAL INSTRUCTIONS:
        1. THINK BEFORE ACTING: You MUST provide a short sentence explaining your logic.
        2. HIERARCHY PRIORITIZATION: Prioritize the ANCHORED_CORE_IDENTITY section.
        3. OBSERVE & CRITIQUE: After every tool call, analyze the output and plan the fix.
        4. BE EFFICIENT: Use list_directory and search_files instead of blind run_shell calls. Read files in chunks.
        5. USE THE VAULT: Before building a component from scratch, search_vault to see if it exists.
        6. DEPLOYMENT: Once a mission is verified, use git_push and deploy_vercel to deliver the final product.
        7. OUTPUT FORMAT: Reply ONLY with valid JSON: {{"thought": "...", "tool": "...", "payload": "..."}}.
        """
        muscle_search_query = f"[{self.current_project.upper()}] {task_desc}"
        muscle_memory_results = self.db.search_muscle_memory(muscle_search_query, limit=3)
        muscle_memory_text = ""
        if muscle_memory_results:
            muscle_memory_text = "Relevant Past Tool Invocations (Muscle Memory):\n"
            for item in muscle_memory_results:
                muscle_memory_text += f"- Intent: {item['intent']}\n  Command: {item['command']}\n\n"

        # Global State Sync: Inject Blackboard summary
        blackboard_summary = self.blackboard.get_summary()
        
        history = f"{blackboard_summary}\n\nContext from previous tasks:\n{context[:3000]}\n\n{muscle_memory_text}Task to complete as {role}:\n{task_desc}"
        
        tool_enum = ["run_shell", "verify_project", "list_directory", "search_files", "fetch_url", "web_search", "read_file", "write_file", "notify_telegram", "inspect_system", "test_service", "save_muscle_memory", "save_to_vault", "search_vault", "git_push", "deploy_vercel", "delegate_task", "final_answer"] + dynamic_tools
        
        tool_schema = {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Internal reasoning step."},
                "tool": {"type": "string", "enum": tool_enum},
                "payload": {"type": "string", "description": "Data or command for the tool."}
            },
            "required": ["thought", "tool", "payload"]
        }

        start_time = time.time()
        for attempt in range(12): 
            output = self.client_pro.generate(history, system_instruction=sys_prompt, images=images, audio=audio, schema=tool_schema)
            if output:
                try:
                    cmd = json.loads(output)
                    
                    if cmd['tool'] == 'final_answer':
                        elapsed = time.time() - start_time
                        if attempt > 3 or elapsed > 60:
                            opt_prompt = f"Task took {attempt} attempts and {elapsed:.1f}s.\nHistory:\n{history[-3000:]}\nIdentify inefficiency and propose a rule to speed this up in the future."
                            advice = self.client_lite.generate(opt_prompt, system_instruction="You are a Performance Auditor.")
                            with open(os.path.join(AGENT_ROOT, "logs/performance_optimizations.md"), "a") as f:
                                f.write(f"\n## Optimization ({datetime.now()})\nTask: {task_desc}\nLatency: {elapsed:.1f}s\nAttempts: {attempt}\nAdvice: {advice}\n")
                        self.blackboard.post("COMPLETE", role, f"Node finished with result summary: {str(cmd['payload'])[:100]}...")
                        yield cmd['payload']
                        return

                    if 'thought' in cmd:
                        yield {"type": "thought", "role": role, "msg": cmd['thought']}
                        status("THINKING", cmd['thought'])
                        # Post thought to blackboard for other agents to see
                        self.blackboard.post("THOUGHT", role, cmd['thought'])

                    yield {"type": "action", "role": role, "tool": cmd['tool'], "payload": str(cmd['payload'])[:200] + ("..." if len(str(cmd['payload'])) > 200 else "")}
                    status(role.upper(), f"Executing {cmd['tool']}...", C_CYAN)
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'], db=self.db)
                    
                    str_result = str(tool_result)
                    if len(str_result) > 3000:
                        str_result = str_result[:1500] + f"\n\n...[TRUNCATED {len(str_result) - 3000} chars]...\n\n" + str_result[-1500:]

                    # Post action/result to blackboard
                    self.blackboard.post("ACTION", role, f"Executed {cmd['tool']}. Result: {str_result[:100]}...")

                    critique = self.criticize_action(cmd['tool'], cmd['payload'], str_result)
                    if critique:
                        history += f"\n\n[CRITIC REJECTION]:\n{critique}\n\nYou MUST fix these issues in your next turn."
                    else:
                        history += f"\n\nTool Output ({cmd['tool']}):\n{str_result}\n\nCRITIQUE PHASE: Analyze the output above. Did it succeed? Is there a mistake to fix?"
                    
                    if len(history) > 30000:
                        history = history[:2000] + "\n\n...[EARLIER CONTEXT TRUNCATED FOR MEMORY]...\n\n" + history[-25000:]
                    
                except Exception as e: 
                    history += f"\n\nTool parse error: {str(e)}. Ensure your JSON is valid."
            else: 
                yield "Worker failed to generate output."
                return

        status("STUCK", f"{role} is failing to progress. Consulting Senior Debugger...", C_RED)
        brief_history = self.client_lite.generate(f"Summarize the attempts and failures so far to help a senior debugger: {history[-10000:]}")
        advice = self.client_pro.generate(f"Worker Role: {role} is stuck.\nDEBUG BRIEF:\n{brief_history}\n\nProvide an actionable fix or workaround.", system_instruction="You are a Senior Debugger. Help the worker get unstuck.")
        if advice:
            status("ADVICE", f"Senior advice received. Executing final attempt for {role}...", C_GREEN)
            final_history = history + f"\n\nSENIOR_DEBUGGER_ADVICE: {advice}\nExecute the task one last time using this advice."
            res = self.client_lite.generate(final_history, system_instruction=sys_prompt, images=images, audio=audio)
            yield res
            return

        yield f"Task failed after 12 attempts and Senior Debugger consultation."

    def solve_task(self, user_goal, images=None, audio=None):
        # Focus semantic search on the active project context
        search_query = f"[{self.current_project.upper()}] {user_goal}"
        past = self.db.semantic_search(search_query)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.blackboard = Blackboard(self.current_project)
        self.blackboard.post("START", "Lead", f"Mission initiated: {user_goal}")

        # Organize by Project Name
        project_dir = os.path.join(WORKSPACE, self.current_project)
        session_dir = os.path.join(project_dir, timestamp)
        os.makedirs(session_dir, exist_ok=True)

        scratchpad_path = os.path.join(session_dir, "PROJECT_SUMMARY.md")

        # 1. Agency Lead Phase
        divider(f"CLIENT SPECIFICATIONS [{self.current_project.upper()}]")
        yield {"type": "status", "tag": "LEAD", "msg": "Extracting requirements and defining Acceptance Criteria..."}
        status("LEAD", "Extracting requirements and defining Acceptance Criteria...", C_PURPLE)
        sys_instr = self.get_system_context()

        transcribe_note = " Analyze the attached audio recording to extract the core mission." if audio else ""
        pm_prompt = f"Goal: {user_goal}\nPast Context: {past}\n{transcribe_note} You are the AgencyLead. Write clear, testable Acceptance Criteria for this goal. Output only the markdown text."
        ac_text = self.client_pro.generate(pm_prompt, system_instruction=sys_instr, images=images, audio=audio)

        self.blackboard.post("STRATEGY", "Lead", f"Acceptance Criteria defined: {ac_text[:200]}...")

        with open(scratchpad_path, "w") as f:
            f.write(f"# Project Scratchpad\n\nGoal: {user_goal}\n\n## Acceptance Criteria\n{ac_text}\n")

        # --- STEP 3: SPECULATIVE EXECUTION START ---
        # While Architect/Security debate, spawn a background speculator to anticipate setup needs
        def speculative_worker(goal, ac, project):
            spec_prompt = f"Goal: {goal}\nAC: {ac}\nAnticipate the immediate setup tasks (scaffolding, mkdir, npm init). Provide a single shell command to execute them. If unsure, say 'WAIT'."
            cmd = self.client_lite.generate(spec_prompt, system_instruction="You are the Atlas Speculator. Prepare the environment in the background.")
            if "WAIT" not in cmd.upper() and ("mkdir" in cmd or "npm" in cmd):
                self.blackboard.post("SPECULATE", "Speculator", f"Anticipated setup: {cmd[:100]}...")
                ToolBox.execute("run_shell", f"cd workspace/{project} && {cmd}", db=self.db)
                self.blackboard.post("COMPLETE", "Speculator", "Speculative setup complete.")

        spec_thread = threading.Thread(target=speculative_worker, args=(user_goal, ac_text, self.current_project))
        spec_thread.start()
        # --- SPECULATIVE EXECUTION END ---

        # 1.5 Debate Phase (Pre-execution Planning)
        divider("ARCHITECTURE DEBATE")
        yield {"type": "status", "tag": "ARCHITECT", "msg": "Proposing initial system architecture..."}
        status("ARCHITECT", "Proposing initial system architecture...", C_BLUE)
        initial_plan_prompt = f"Goal: {user_goal}\nAcceptance Criteria: {ac_text}\nDraft an initial architecture plan. Focus on directory structure, data flow, and components."
        initial_architecture = self.client_pro.generate(initial_plan_prompt, system_instruction=sys_instr)

        yield {"type": "status", "tag": "SECURITY", "msg": "Critiquing the initial architecture..."}
        status("SECURITY", "Critiquing the initial architecture...", C_PURPLE)
        critique_prompt = f"Review this architecture:\n{initial_architecture}\nIdentify security flaws, scalability issues, or missing error handling. Provide a bulleted list of required changes. If none, say 'APPROVE'."
        security_critique = self.client_pro.generate(critique_prompt, system_instruction=sys_instr + "\nYou are a strict Security Expert.")

        if "APPROVE" not in security_critique.upper():
            yield {"type": "status", "tag": "ARCHITECT", "msg": "Refining plan based on critique..."}
            status("ARCHITECT", "Refining plan based on critique...", C_BLUE)
            refined_plan_prompt = f"Original Plan:\n{initial_architecture}\nCritique:\n{security_critique}\nProvide a final, refined architecture addressing the critique."
            refined_architecture = self.client_pro.generate(refined_plan_prompt, system_instruction=sys_instr)
        else:
            yield {"type": "status", "tag": "SECURITY", "msg": "Architecture approved."}
            status("SECURITY", "Architecture approved.", C_GREEN)
            refined_architecture = initial_architecture

        self.blackboard.post("ARCH", "Architect", f"Finalized Architecture: {refined_architecture[:200]}...")

        with open(scratchpad_path, "a") as f:
            f.write(f"\n## Architecture\n{refined_architecture}\n")

        # 2. Swarm Task Planning Phase
        divider("DYNAMIC SWARM GRAPH")
        yield {"type": "status", "tag": "LEAD", "msg": "Designing execution graph..."}
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
            yield {"type": "status", "tag": "SWARM", "msg": f"Graph locked: {len(tasks)} adaptive nodes mapped."}
            status("SWARM", f"Graph locked: {len(tasks)} adaptive nodes mapped.", C_GREEN)
            self.blackboard.post("PLAN", "Lead", f"Execution graph locked with {len(tasks)} nodes.")
        except Exception as e:
            yield {"type": "error", "msg": f"Planning failed: {str(e)}"}
            return

        results = {}
        q = queue.Queue()

        def worker(step, sys_instr, results_so_far, q, imgs, aud):
            role = step.get('role', 'Developer')
            try:
                status(role.upper(), f"Node {step['id']} Starting...", C_GREEN)
                res_gen = self.run_worker_with_tools(step['task'], str(results_so_far), sys_instr, role=role, images=imgs, audio=aud)
                res = ""
                for chunk in res_gen:
                    if isinstance(chunk, dict):
                        q.put(("UPDATE", chunk))
                    else:
                        res += chunk

                success = "error" not in res.lower() or "fixed" in res.lower()
                q.put(("RESULT", step['id'], res, success))

                with open(os.path.join(session_dir, f"node_{step['id']}_{role}.md"), 'w') as f: f.write(res)
                status(role.upper(), f"Node {step['id']} Finished.", C_GREEN)
            except Exception as e:
                status("CRASH", f"Node {step['id']} ({role}) failed: {str(e)}", C_RED)
                q.put(("RESULT", step['id'], f"CRASH ERROR: {str(e)}", False))

        divider("ADAPTIVE EXECUTION")
        self.status = "RUNNING"
        while graph.status == "PENDING":
            if self.status == "ABORTED":
                yield {"type": "status", "tag": "ABORT", "msg": "MISSION ABORTED BY OPERATOR."}
                status("ABORT", "MISSION ABORTED BY OPERATOR.", C_RED)
                return "Mission Terminated."

            current_task = graph.get_next_task()
            if not current_task: break

            worker_thread = threading.Thread(target=worker, args=(current_task, sys_instr, results, q, images, audio))
            worker_thread.start()

            while worker_thread.is_alive() or not q.empty():
                try:
                    item = q.get(timeout=0.1)
                    if item[0] == "UPDATE":
                        yield item[1]
                    elif item[0] == "RESULT":
                        _, node_id, res, success = item
                        results[node_id] = res
                        graph.process_result(node_id, res, success=success)
                        yield {"type": "node_complete", "id": node_id, "role": current_task['role'], "result": res}
                except queue.Empty:
                    continue

        divider("FINAL REVIEW")
        yield {"type": "status", "tag": "SYSTEM", "msg": "Synthesizing expert results..."}
        status("SYSTEM", "Synthesizing expert results...", C_BLUE)
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final agency-ready summary.", system_instruction=sys_instr, images=images, audio=audio)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        yield {"type": "status", "tag": "SUCCESS", "msg": "Project delivered. Results saved to workspace."}
        status("SUCCESS", "Project delivered. Results saved to workspace.", C_GREEN)
        self.blackboard.post("END", "Lead", "Mission successfully completed and delivered.")
        divider()
        yield {"type": "final_answer", "msg": final}
        return final

    def consolidate_memory(self):
        # ... [Unchanged] ...
        return "Consolidation complete. No new skills identified."

    def process(self, user_input, stream=False, images=None, audio=None):
        sys_instr = self.get_system_context()
        if "TASK" in self.triage(user_input):
            for update in self.solve_task(user_input, images=images, audio=audio):
                yield update
        else:
            full_resp = ""
            for chunk in self.client_lite.generate_stream(user_input, system_instruction=sys_instr, history=self.history, images=images, audio=audio):
                full_resp += chunk
                yield {"type": "chunk", "msg": chunk}

            if full_resp:
                entry_user = {"role": "user", "text": user_input}
                entry_model = {"role": "model", "text": full_resp}
                self.history.extend([entry_user, entry_model])
                
                # Update Hot Memory (Redis)
                if self.redis:
                    try:
                        self.redis.rpush("atlas:history:global", json.dumps(entry_user), json.dumps(entry_model))
                        self.redis.ltrim("atlas:history:global", -10, -1) # Keep last 10 turns in RAM
                    except: pass

                os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
                with open(CHAT_LOG, 'a') as f:
                    f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
                yield {"type": "final_answer", "msg": full_resp}

def heartbeat_daemon(api_key):
    mas = AtlasSwarm(api_key)
    print(f"\n[!] Heartbeat Daemon Started v{__version__} (Evolution Mode + Distributed Listener)")
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

    repo_path = os.path.expanduser('~/AtlasSwarm_Repo')
    mailbox_path = os.path.join(repo_path, 'mailbox')
    last_research_file = os.path.join(AGENT_ROOT, "core/last_research.txt")
    last_consolidation = 0
    last_tg_pulse = 0
    
    # Optional Redis Integration for True Distributed Swarm
    redis_client = None
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print(f"[+] Connected to Redis. Subscribing to '{mas.machine_name}' channel.")
        pubsub = redis_client.pubsub()
        pubsub.subscribe(mas.machine_name)
    except Exception as e:
        print(f"[-] Redis not available ({e}). Running in standalone mode.")
        redis_client = None
        pubsub = None

    # Store the initial hash of the core file to detect modifications
    core_file_path = os.path.abspath(__file__)
    try:
        with open(core_file_path, 'rb') as f:
            initial_core_hash = hash(f.read())
    except:
        initial_core_hash = None

    while True:
        try:
            now = time.time()
            # Fast Redis check
            if pubsub:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message and message['type'] == 'message':
                    print(f"\n[Redis] Received remote P2P command...")
                    try:
                        data = json.loads(message['data'])
                        prompt = data.get('command')
                        reply_channel = data.get('reply_to')
                        if prompt:
                            result = ""
                            for update in mas.process(prompt, stream=True):
                                if isinstance(update, dict):
                                    if update['type'] == 'chunk': result += update['msg']
                                    elif update['type'] == 'final_answer': result = update['msg']
                                else:
                                    result += str(update)
                            if reply_channel and redis_client:
                                redis_client.publish(reply_channel, json.dumps({"status": "complete", "result": result}))
                    except Exception as e:
                        print(f"Redis processing error: {e}")

            # Hot-Reload Check
            if initial_core_hash is not None:
                with open(core_file_path, 'rb') as f:
                    current_hash = hash(f.read())
                if current_hash != initial_core_hash:
                    status("EVOLUTION", "Core modification detected. Executing hot-reload...", C_PURPLE)
                    # Use os.execv to replace the current process with the new code
                    os.execv(sys.executable, [sys.executable] + sys.argv)

            cfg = read_local_config()
            
            # Tapering Evolution Logic: Starts fast (30m), then increases by 1h each cycle
            evo_count = cfg.get("evolution_count", 0)
            base_interval_hrs = 0.5 
            current_interval_hrs = min(24, base_interval_hrs + evo_count)
            
            evolution_interval = current_interval_hrs * 3600
            sleep_interval = cfg.get("heartbeat_sleep_sec", 5)

            # Sync with Repo
            subprocess.run(f"cd {repo_path} && git pull origin main", shell=True, capture_output=True)

            # 4. Periodic Telegram Status Update (every 2 hours)
            if (now - last_tg_pulse) > 7200:
                stats = mas.db.get_swarm_stats()
                blackboard_summary = mas.blackboard.get_summary()
                pulse_msg = f"""
MISSION COMMANDER STATUS UPDATE
-------------------------------
Active Project: {mas.current_project.upper()}
Swarm Stats:
- Memories: {stats['memory_count']}
- Muscle: {stats['muscle_count']}
- Vault Components: {stats['component_count']}

Latest Mission Blackboard:
{blackboard_summary[:500]}...

System Status: ONLINE / EVOLVING
"""
                mas.notify_telegram(pulse_msg)
                last_tg_pulse = now

            # 3. Idle Memory Consolidation (once every 30 mins)
            if (now - last_consolidation) > 1800:
                mas.consolidate_memory()
                mas.generate_dashboard()
                last_consolidation = now

            # 1. Autonomous Research Cycle
            now = time.time()
            last_research = 0
            if os.path.exists(last_research_file):
                try:
                    with open(last_research_file, 'r') as f: last_research = float(f.read().strip() or 0)
                except: pass
            
            if (now - last_research) > evolution_interval:
                print(f"\n[Pulse] Starting Elite Evolution Swarm (Cycle {evo_count+1})...")
                
                # Analyze internal performance logs to guide research
                perf_logs = read_file_safe(os.path.join(AGENT_ROOT, "logs/performance_optimizations.md"))
                
                research_goal = f"""
                INITIATING ATLAS ELITE EVOLUTION PROTOCOL:
                
                1. PERFORMANCE AUDIT: Analyze these recent performance logs:
                   {perf_logs[-5000:] if perf_logs else "No logs yet. Focus on general efficiency."}
                   Identify the top bottleneck (latency or logic failure).
                
                2. TARGETED RESEARCH: Use web_search to find a technical solution for that bottleneck.
                   Also investigate one new 'Skill' pattern for the NextStep Component Vault.
                
                3. VAULT EXPANSION: Save the discovered component to the vault.
                
                4. EXPERIMENTAL SELF-PATCH:
                   - Create a new git branch named 'evolution/cycle-{evo_count+1}'.
                   - Implement a concrete logic improvement to 'bin/atlas_core.py' based on your findings.
                   - Use the 'verify_project' tool to ensure the core engine still compiles.
                   - If successful, push the branch and use 'notify_telegram' to request a merge.
                """
                
                # Execute the evolution mission
                for _ in mas.process(research_goal, stream=True): pass
                
                # Sync new knowledge/skills to the global repo immediately
                subprocess.run(f"cd {repo_path} && git add knowledge/ skills/ library/ && git commit -m 'evolution: swarm knowledge update (Cycle {evo_count+1})' && git push origin main", shell=True)
                
                with open(last_research_file, 'w') as f: f.write(str(now))
                
                cfg["evolution_count"] = evo_count + 1
                write_local_config(cfg)

            # 2. Check for Mailbox Commands
            cmd_file = os.path.join(mailbox_path, f"{mas.machine_name}_cmd.json")
            if os.path.exists(cmd_file):
                print(f"\n[Mail] Received remote command...")
                try:
                    with open(cmd_file, 'r') as f: cmd_data = json.load(f)

                    # Process the command
                    result = ""
                    for update in mas.process(cmd_data['command'], stream=True):
                        if isinstance(update, dict):
                            if update['type'] == 'chunk':
                                result += update['msg']
                            elif update['type'] == 'final_answer':
                                result = update['msg']
                        else:
                            result += str(update)

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

            time.sleep(sleep_interval)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Heartbeat Error: {e}")
            time.sleep(60)

def interactive_loop(api_key):
    mas = AtlasSwarm(api_key)
    cfg = read_local_config()
    hw = cfg.get("_current_probe", {})
    
    # Professional Agency Splash
    os.system('clear' if os.name == 'posix' else 'cls')
    
    draw_box([
        f"{C_BOLD}{C_WHITE}ATLAS Elite Swarm v{__version__}{C_END}",
        f"{C_DIM}Digital Agency Autonomy Protocol{C_END}",
        "",
        f"{C_CYAN}NODE:    {C_END}{mas.machine_name}",
        f"{C_CYAN}PROFILE: {C_END}{hw.get('profile', 'standard').upper()}",
        f"{C_CYAN}THREADS: {C_END}{cfg.get('max_threads', 1)} Workers",
        f"{C_CYAN}MEMORY:  {C_END}{hw.get('mem_gb', '0')} GB",
    ], title="AGENCY STATUS", color=C_BLUE)

    print(f"\n{C_YELLOW}{C_BOLD}COMMANDS:{C_END}")
    print(f" {C_CYAN}/config{C_END}  {C_DIM}System Matrix{C_END}  {C_CYAN}/rescan{C_END}  {C_DIM}HW Probe{C_END}  {C_CYAN}/help{C_END}    {C_DIM}Docs{C_END}")
    print(f" {C_CYAN}/image{C_END}   {C_DIM}Attach Vision{C_END}  {C_CYAN}/projects{C_END} {C_DIM}List All{C_END}  {C_CYAN}exit{C_END}     {C_DIM}Quit{C_END}")
    print(f" {C_CYAN}/approve{C_END} {C_DIM}Accept Action{C_END}  {C_CYAN}/reject{C_END}   {C_DIM}Deny Action{C_END}\n")

    while True:
        try:
            # Modern λ Prompt
            prompt_prefix = f"{C_GREEN}λ{C_END} {C_CYAN}{mas.current_project}{C_END}"
            inp = input(f"{prompt_prefix} {C_BOLD}➜{C_END} ").strip()
            if not inp: continue
            if inp.lower() in ['exit', 'quit']: break
            if inp.lower() == 'heartbeat': heartbeat_daemon(api_key); continue

            # Governance Commands
            if inp.lower() == "/approve":
                approval_file = os.path.join(AGENT_ROOT, "core/pending_approval.json")
                if os.path.exists(approval_file):
                    with open(approval_file, "r") as f: state = json.load(f)
                    state["status"] = "APPROVED"
                    with open(approval_file, "w") as f: json.dump(state, f)
                    status("GOVERNANCE", "Action APPROVED.", C_GREEN)
                else:
                    status("GOVERNANCE", "No pending actions.", C_DIM)
                continue
                
            if inp.lower() == "/reject":
                approval_file = os.path.join(AGENT_ROOT, "core/pending_approval.json")
                if os.path.exists(approval_file):
                    with open(approval_file, "r") as f: state = json.load(f)
                    state["status"] = "REJECTED"
                    with open(approval_file, "w") as f: json.dump(state, f)
                    status("GOVERNANCE", "Action REJECTED.", C_RED)
                else:
                    status("GOVERNANCE", "No pending actions.", C_DIM)
                continue

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
            for update in mas.process(inp, stream=True, images=images):
                if isinstance(update, dict):
                    if update['type'] == 'chunk':
                        print(update['msg'], end="", flush=True)
                        full_response += update['msg']
                    elif update['type'] == 'final_answer':
                        full_response = update['msg']
                else:
                    # Fallback for plain strings
                    print(update, end="", flush=True)
                    full_response += update
            
            # Show rendered output if it was a simple chat
            if full_response and not any(isinstance(u, dict) and u['type'] in ['status', 'thought'] for u in mas.process(inp, stream=True, images=images)):
                print(f"\n{C_BLUE}{C_BOLD}[Atlas]{C_END} {C_CYAN}> {C_END}")
                print(render_markdown(full_response))
                print("\n")
            
        except KeyboardInterrupt: break
        except Exception as e:
            status("SHELL_ERR", str(e), C_RED)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AtlasSwarm Core Engine')
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
            mas = AtlasSwarm(key)
            for update in mas.process(prompt, stream=True, images=images):
                if isinstance(update, dict):
                    if update['type'] == 'chunk':
                        print(update['msg'], end="", flush=True)
                    elif update['type'] == 'final_answer':
                        pass # Already printed chunks
                    elif update['type'] == 'status':
                        status(update['tag'], update['msg'])
                    elif update['type'] == 'thought':
                        status("THINKING", update['msg'])
                else:
                    print(update, end="", flush=True)
            print()
        else:
            interactive_loop(key)

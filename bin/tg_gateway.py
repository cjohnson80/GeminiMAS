from error_handler import safe_execute
import json, os, urllib.request, time, subprocess, sys, socket
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
ENV_FILE = os.path.join(AGENT_ROOT, ".env")
REPO_DIR = os.path.expanduser("~/GeminiMAS_Repo")
ENGINE_PATH = os.path.join(AGENT_ROOT, "bin/gemini_mas.py")

def get_env(key):
    if not os.path.exists(ENV_FILE): return os.getenv(key)
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith(f"{key}="): return line.split('=')[1].strip().strip('"')
    return os.getenv(key)

COMPUTER_NAME = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = get_env("TELEGRAM_USER_ID")
API_KEY = get_env("GEMINI_API_KEY")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def send_msg(chat_id, text, markdown=False):
    if not text or not text.strip(): return
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    if markdown: payload["parse_mode"] = "Markdown"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except Exception as e: print(f"Send Error: {e}")

def get_dashboard():
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            total = int([l.split()[1] for l in lines if 'MemTotal' in l][0])
            avail = int([l.split()[1] for l in lines if 'MemAvailable' in l][0])
            used_pct = int(((total - avail) / total) * 100)
        load = os.getloadavg()[0]
        cpu_pct = int((load / os.cpu_count()) * 100)
        def bar(pct):
            filled = min(10, int(pct / 10))
            return "[" + "█" * filled + "░" * (10 - filled) + "]"
        status_icon = "🟢" if used_pct < 70 else "🟠" if used_pct < 90 else "🔴"
        return (f"📊 *System Dashboard*\n"
                f"💻 *CPU:* {bar(cpu_pct)} {cpu_pct}%\n"
                f"🧠 *RAM:* {status_icon} {bar(used_pct)} {used_pct}%\n"
                f"📍 *Node:* {COMPUTER_NAME}")
    except: return "Error."

def main():
    print(f"[*] Telegram Gateway v4.6 (Robust Response) Active")
    offset = 0
    while True:
        try:
            with urllib.request.urlopen(f"{BASE_URL}getUpdates?offset={offset}&timeout=30", timeout=40) as r:
                updates = json.loads(r.read().decode())
                if updates.get("result"):
                    for up in updates["result"]:
                        offset = up["update_id"] + 1
                        msg = up.get("message")
                        if not msg or str(msg.get("from", {}).get("id")) != ALLOWED_USER_ID: continue
                        text = msg.get("text", "")
                        chat_id = msg["chat"]["id"]
                        
                        if text.startswith("/status"):
                            send_msg(chat_id, get_dashboard(), markdown=True)
                        elif text.startswith("/approve "):
                            branch = text.split(" ")[1].strip()
                            send_msg(chat_id, f"🚀 Deploying '{branch}'...")
                            subprocess.run(f"cd {REPO_DIR} && git checkout main && git merge origin/{branch} && ./install.sh", shell=True)
                            send_msg(chat_id, "✅ Done.")
                        elif text:
                            goal = text
                            if text.startswith("/all "): goal = text.split(" ", 1)[1]
                            elif text.startswith(f"/{COMPUTER_NAME.lower()} "): goal = text.split(" ", 1)[1]
                            elif text.startswith("/"): continue
                            
                            # Execute Engine Directly
                            env = os.environ.copy()
                            env["GEMINI_API_KEY"] = API_KEY
                            res = subprocess.run([sys.executable, ENGINE_PATH, goal], capture_output=True, text=True, env=env).stdout
                            
                            # Robust Parser
                            clean_res = ""
                            if "[Agent] >" in res:
                                clean_res = res.split("[Agent] >")[-1].strip()
                            
                            # Fallback: If clean_res is empty, send the whole thing but filter out logs
                            if not clean_res:
                                lines = [l for l in res.split('\n') if not l.startswith('[*]') and l.strip()]
                                clean_res = "\n".join(lines)
                            
                            if clean_res:
                                send_msg(chat_id, clean_res)
                            else:
                                send_msg(chat_id, "⚠️ Agent returned an empty response. Check server logs.")
        except: pass
        time.sleep(5)

if __name__ == "__main__":
    main()

def safe_execute(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        import logging
        logging.error(f'Graceful degradation: {e}')
        return None

# Wrap core loop execution to prevent total process crash
while True:
    try:
        # Existing loop logic logic here
        pass
    except KeyboardInterrupt:
        break
    except Exception as e:
        import time
        time.sleep(10) # Cooling period for low-resource hardware
        continue
import os, psutil, hashlib

def resource_guard():
    if psutil.virtual_memory().percent > 90:
        os.system('renice -n 19 -p ' + str(os.getpid()))

def heartbeat_daemon():
    try:
        current_hash = hashlib.md5(open('/home/chrisj/gemini_agents/core/HEARTBEAT.md', 'rb').read()).hexdigest()
        if current_hash != getattr(heartbeat_daemon, 'last_hash', None):
            heartbeat_daemon.last_hash = current_hash
            return True
    except:
        pass
    return False

def triage_lite(task):
    if psutil.virtual_memory().percent > 85:
        return 'CHAT_LITE'
    return 'PROCESS'

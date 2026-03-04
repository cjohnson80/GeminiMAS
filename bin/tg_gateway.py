import json, os, urllib.request, time, subprocess, sys, socket
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
ENV_FILE = os.path.join(AGENT_ROOT, ".env")
REPO_DIR = os.path.expanduser("~/GeminiMAS_Repo")

def get_env(key):
    if not os.path.exists(ENV_FILE): return os.getenv(key)
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith(f"{key}="): return line.split('=')[1].strip().strip('"')
    return os.getenv(key)

COMPUTER_NAME = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = get_env("TELEGRAM_USER_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def send_msg(chat_id, text, markdown=False):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    if markdown: payload["parse_mode"] = "Markdown"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except: pass

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
            filled = int(pct / 10)
            return "[" + "█" * filled + "░" * (10 - filled) + "]"
        status_icon = "🟢" if used_pct < 70 else "🟠" if used_pct < 90 else "🔴"
        return (f"📊 *System Dashboard*\n"
                f"💻 *CPU:* {bar(cpu_pct)} {cpu_pct}%\n"
                f"🧠 *RAM:* {status_icon} {bar(used_pct)} {used_pct}%\n"
                f"📍 *Node:* {COMPUTER_NAME}")
    except: return "Error."

def main():
    print(f"[*] Telegram Gateway v4.5 (Clean Chat) on '{COMPUTER_NAME}'")
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
                            # Natural Chat or Task
                            # Filter slashes for /all or /[hostname]
                            goal = text
                            if text.startswith("/all "): goal = text.split(" ", 1)[1]
                            elif text.startswith(f"/{COMPUTER_NAME.lower()} "): goal = text.split(" ", 1)[1]
                            elif text.startswith("/"): continue # Ignore other commands
                            
                            # Clean response fetching
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                            # Extract ONLY the agent's response (lines after "Agent] >")
                            if "[Agent] >" in res:
                                clean_res = res.split("[Agent] >")[-1].strip()
                            else:
                                clean_res = res.strip()
                            
                            if clean_res:
                                send_msg(chat_id, clean_res)
        except: pass
        time.sleep(1)

if __name__ == "__main__":
    main()

import json, os, urllib.request, time, subprocess, sys, socket
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
ENV_FILE = os.path.join(AGENT_ROOT, ".env")
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

def send_msg(chat_id, text):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except: pass

def main():
    print(f"[*] Telegram Gateway v4.1 (Evolution Active) on '{COMPUTER_NAME}'")
    offset = 0
    while True:
        try:
            with urllib.request.urlopen(f"{BASE_URL}getUpdates?offset={offset}&timeout=30", timeout=40) as r:
                updates = json.loads(r.read().decode())
                if updates.get("result"):
                    for up in updates["result"]:
                        offset = up["update_id"] + 1
                        msg = up.get("message")
                        if not msg: continue
                        user_id = str(msg.get("from", {}).get("id"))
                        if user_id != ALLOWED_USER_ID: continue
                        text = msg.get("text", "")
                        
                        if text.startswith("/status"):
                            res = subprocess.run("free -h", shell=True, capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], f"Status:\n{res}")
                        
                        elif text.startswith("/approve "):
                            branch = text.split(" ")[1].strip()
                            send_msg(msg["chat"]["id"], f"Approving Evolution. Merging branch '{branch}' into main...")
                            cmd = f"cd ~/GeminiMAS_Repo && git checkout main && git merge {branch} && git push origin main && ./install.sh"
                            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            send_msg(msg["chat"]["id"], f"Merge Complete. System Restarted.\nOutput: {res.stdout[-1000:]}")
                        
                        elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
                            goal = text.split(" ", 1)[1]
                            send_msg(msg["chat"]["id"], "Processing...")
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], res[:3500])
                        
                        elif text and not text.startswith("/"):
                            # Direct Chat Routing
                            send_msg(msg["chat"]["id"], "Thinking...")
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), text], capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], res[:3500])
        except: pass
        time.sleep(1)

if __name__ == "__main__":
    main()

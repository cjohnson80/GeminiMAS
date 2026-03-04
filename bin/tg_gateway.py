import json, os, urllib.request, time, subprocess, sys, socket

AGENT_ROOT = os.path.expanduser("~/gemini_agents")
ENV_FILE = os.path.expanduser("~/Desktop/.env")

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

def get_updates(offset):
    try:
        with urllib.request.urlopen(f"{BASE_URL}getUpdates?offset={offset}&timeout=30", timeout=40) as r:
            return json.loads(r.read().decode())
    except: return None

def main():
    print(f"[*] Telegram Gateway v3.2 (Robust) on '{COMPUTER_NAME}'")
    offset = 0
    while True:
        updates = get_updates(offset)
        if updates and updates.get("result"):
            for up in updates["result"]:
                offset = up["update_id"] + 1
                msg = up.get("message")
                if not msg: continue
                
                # Robust ID check
                from_user = msg.get("from", {})
                chat = msg.get("chat", {})
                user_id = str(from_user.get("id", ""))
                chat_id = chat.get("id")

                if user_id != ALLOWED_USER_ID:
                    print(f"Unauthorized: {user_id}")
                    continue

                text = msg.get("text", "")
                if text.startswith("/status"):
                    res = subprocess.run("free -h | grep Mem", shell=True, capture_output=True, text=True).stdout
                    send_msg(chat_id, f"RAM: {res}")
                elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
                    goal = text.split(" ", 1)[1]
                    send_msg(chat_id, f"Processing Goal...")
                    res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                    send_msg(chat_id, f"Done:\n{res[:3500]}")
        time.sleep(1)

if __name__ == "__main__":
    main()

import json, os, urllib.request, time, subprocess, sys
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
sys.path.append(os.path.join(AGENT_ROOT, "bin"))
from gemini_mas import GeminiMAS

def get_env(key):
    path = os.path.join(AGENT_ROOT, ".env")
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                if line.startswith(f"{key}="): return line.split('=')[1].strip().strip('"')
    return os.getenv(key)

COMPUTER_NAME = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = get_env("TELEGRAM_USER_ID")
API_KEY = get_env("GEMINI_API_KEY")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def send_msg(chat_id, text):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except: pass

def main():
    if not API_KEY: return
    mas = GeminiMAS(API_KEY)
    print(f"[*] Telegram v3.5 (Natural Chat) Active on '{COMPUTER_NAME}'")
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
                        if text.startswith("/status"):
                            res = subprocess.run("free -h", shell=True, capture_output=True, text=True).stdout
                            send_msg(msg["chat"]["id"], f"Status:\n{res}")
                        else:
                            # Natural Chat / Triage Task
                            response = mas.process(text)
                            send_msg(msg["chat"]["id"], response[:4000])
        except: pass
        time.sleep(1)

if __name__ == "__main__":
    main()

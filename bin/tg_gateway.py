import json
import os
import urllib.request
import urllib.error
import time
import subprocess
import sys
from datetime import datetime

# Configuration
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
WORKSPACE = os.path.join(AGENT_ROOT, "workspace")
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

if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not found.")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
FILE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}/"

def send_msg(chat_id, text):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except Exception as e: print(f"Send Error: {e}")

def get_updates(offset):
    url = f"{BASE_URL}getUpdates?offset={offset}&timeout=30"
    try:
        with urllib.request.urlopen(url, timeout=40) as r:
            return json.loads(r.read().decode())
    except: return None

def download_file(file_id, chat_id):
    """Downloads a photo from Telegram to the workspace."""
    try:
        # Get file path from API
        url = f"{BASE_URL}getFile?file_id={file_id}"
        with urllib.request.urlopen(url) as r:
            file_path = json.loads(r.read().decode())['result']['file_path']
        
        # Download the actual file
        download_url = f"{FILE_URL}{file_path}"
        # Save to latest workspace
        workspaces = sorted([os.path.join(WORKSPACE, d) for d in os.listdir(WORKSPACE) if os.path.isdir(os.path.join(WORKSPACE, d))], reverse=True)
        target_dir = workspaces[0] if workspaces else WORKSPACE
        
        filename = f"vision_{int(time.time())}.jpg"
        target_path = os.path.join(target_dir, filename)
        
        with urllib.request.urlopen(download_url) as r, open(target_path, 'wb') as f:
            f.write(r.read())
        
        send_msg(chat_id, f"Image received and saved to: {target_path}. You can now run tasks that refer to this image.")
    except Exception as e:
        send_msg(chat_id, f"Failed to download image: {str(e)}")

def process_msg(msg):
    chat_id = msg["chat_id"]
    # Handle Photos
    if "photo" in msg:
        # Telegram sends multiple sizes, get the largest one (last in list)
        file_id = msg["photo"][-1]["file_id"]
        download_file(file_id, chat_id)
        return

    # Handle Text Commands
    text = msg.get("text", "")
    if text.startswith("/status"):
        res = subprocess.run("free -h | grep Mem", shell=True, capture_output=True, text=True).stdout
        send_msg(chat_id, f"Memory: {res}")
    elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
        goal = text.split(" ", 1)[1]
        send_msg(chat_id, f"Starting task: {goal}")
        try:
            res = subprocess.run(["gagent", goal], capture_output=True, text=True, timeout=300).stdout
            send_msg(chat_id, f"Result:\n{res[:3500]}")
        except Exception as e:
            send_msg(chat_id, f"Task Error: {str(e)}")

def main():
    print(f"[*] Telegram Gateway v2.0 (Vision Enabled) on '{COMPUTER_NAME}'")
    offset = 0
    while True:
        updates = get_updates(offset)
        if updates and updates.get("result"):
            for up in updates["result"]:
                offset = up["update_id"] + 1
                msg = up.get("message")
                if not msg or str(msg.get("from", {}).get("id")) != ALLOWED_USER_ID: continue
                process_msg(msg)
        time.sleep(1)

if __name__ == "__main__":
    main()

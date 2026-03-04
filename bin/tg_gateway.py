import json
import os
import urllib.request
import urllib.error
import time
import subprocess
import sys
import socket
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

# Track the server process
server_proc = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def send_msg(chat_id, text):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except Exception as e: print(f"Send Error: {e}")

def get_updates(offset):
    url = f"{BASE_URL}getUpdates?offset={offset}&timeout=30"
    try:
        with urllib.request.urlopen(url, timeout=40) as r: return json.loads(r.read().decode())
    except: return None

def download_file(file_id, chat_id):
    try:
        url = f"{BASE_URL}getFile?file_id={file_id}"
        with urllib.request.urlopen(url) as r: file_path = json.loads(r.read().decode())['result']['file_path']
        download_url = f"{FILE_URL}{file_path}"
        workspaces = sorted([os.path.join(WORKSPACE, d) for d in os.listdir(WORKSPACE) if os.path.isdir(os.path.join(WORKSPACE, d))], reverse=True)
        target_dir = workspaces[0] if workspaces else WORKSPACE
        filename = f"vision_{int(time.time())}.jpg"
        target_path = os.path.join(target_dir, filename)
        with urllib.request.urlopen(download_url) as r, open(target_path, 'wb') as f: f.write(r.read())
        send_msg(chat_id, f"Image saved to workspace. You can now reference it in tasks.")
    except Exception as e: send_msg(chat_id, f"Download failed: {str(e)}")

def process_msg(msg):
    global server_proc
    chat_id = msg["chat_id"]
    if "photo" in msg:
        download_file(msg["photo"][-1]["file_id"], chat_id)
        return

    text = msg.get("text", "")
    if text.startswith("/status"):
        res = subprocess.run("free -h | grep Mem", shell=True, capture_output=True, text=True).stdout
        send_msg(chat_id, f"Memory: {res}")
    
    elif text.startswith("/server "):
        cmd = text.split(" ")[1].lower()
        if cmd == "start":
            if server_proc:
                send_msg(chat_id, "Server already running.")
            else:
                ip = get_local_ip()
                server_proc = subprocess.Popen(["python3", "-m", "http.server", "8000"], cwd=WORKSPACE)
                send_msg(chat_id, f"Web Server started! Preview here:\nhttp://{ip}:8000")
        elif cmd == "stop":
            if server_proc:
                server_proc.terminate()
                server_proc = None
                send_msg(chat_id, "Web Server stopped.")
            else:
                send_msg(chat_id, "No server running.")

    elif text.startswith("/all ") or text.startswith(f"/{COMPUTER_NAME.lower()} "):
        goal = text.split(" ", 1)[1]
        send_msg(chat_id, f"Starting: {goal}")
        try:
            res = subprocess.run(["gagent", goal], capture_output=True, text=True, timeout=300).stdout
            send_msg(chat_id, f"Result:\n{res[:3500]}")
        except Exception as e: send_msg(chat_id, f"Error: {str(e)}")

def main():
    print(f"[*] Telegram Gateway v3.0 (Server Control) on '{COMPUTER_NAME}'")
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

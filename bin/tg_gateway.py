import json, os, urllib.request, time, subprocess, sys, socket
AGENT_ROOT = os.path.expanduser("~/gemini_agents")
REPO_DIR = os.path.expanduser("~/GeminiMAS_Repo")
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

def send_msg(chat_id, text, markdown=False):
    url = f"{BASE_URL}sendMessage"
    payload = {"chat_id": chat_id, "text": f"[{COMPUTER_NAME}] {text}"}
    if markdown: payload["parse_mode"] = "Markdown"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req)
    except: pass

def main():
    print(f"[*] Telegram Gateway v4.7 Active on '{COMPUTER_NAME}'")
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
                        
                        if text.startswith("/approve "):
                            branch = text.split(" ")[1].strip()
                            send_msg(chat_id, f"🚀 APPROVAL RECEIVED: {branch}\nStarting Deployment...")
                            
                            # Execute Merge Logic
                            cmds = [
                                f"cd {REPO_DIR} && git checkout main",
                                f"cd {REPO_DIR} && git pull origin main",
                                f"cd {REPO_DIR} && git fetch origin {branch}",
                                f"cd {REPO_DIR} && git merge origin/{branch} --no-edit",
                                f"cd {REPO_DIR} && git push origin main",
                                f"cd {REPO_DIR} && ./install.sh"
                            ]
                            
                            success = True
                            for i, cmd in enumerate(cmds):
                                send_msg(chat_id, f"Step {i+1}/6: Executing...")
                                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                                if res.returncode != 0:
                                    send_msg(chat_id, f"❌ ERROR in Step {i+1}:\n{res.stderr}")
                                    success = False
                                    break
                            
                            if success:
                                send_msg(chat_id, "🎉 DEPLOYMENT COMPLETE! System restarted.")

                        elif text.startswith("/status"):
                            res = subprocess.run("free -h | grep Mem", shell=True, capture_output=True, text=True).stdout
                            send_msg(chat_id, f"RAM Status:\n{res}")
                        
                        elif text:
                            # Natural Triage
                            goal = text
                            if text.startswith("/all "): goal = text.split(" ", 1)[1]
                            elif text.startswith(f"/{COMPUTER_NAME.lower()} "): goal = text.split(" ", 1)[1]
                            elif text.startswith("/"): continue
                            
                            send_msg(chat_id, "🧠 Thinking...")
                            res = subprocess.run([os.path.expanduser("~/.local/bin/gagent"), goal], capture_output=True, text=True).stdout
                            if "[Agent] >" in res: clean = res.split("[Agent] >")[-1].strip()
                            else: clean = "\n".join([l for l in res.split('\n') if not l.startswith('[*]') and l.strip()])
                            send_msg(chat_id, clean[:4000])
        except: pass
        time.sleep(1)

if __name__ == "__main__":
    main()

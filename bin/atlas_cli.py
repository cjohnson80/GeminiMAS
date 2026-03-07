import sys
import json
import requests
import os

# Configuration
API_URL = "http://localhost:8000/prompt"

def main():
    if len(sys.argv) < 2:
        print("Usage: atlas <prompt> | sentinel [start|stop|status]")
        sys.exit(1)

    cmd = sys.argv[1]
    
    # Handle Sentinel Management
    if cmd == "sentinel":
        action = sys.argv[2] if len(sys.argv) > 2 else "status"
        agent_root = os.path.expanduser("~/atlas_agents")
        if action == "start":
            print("[*] Launching Atlas Sentinel...")
            os.system(f"nohup {agent_root}/venv/bin/python3 {agent_root}/bin/sentinel.py > {agent_root}/logs/sentinel.out 2>&1 &")
            print("[+] Sentinel active in background.")
        elif action == "stop":
            print("[*] Terminating Atlas Sentinel...")
            os.system("pkill -f sentinel.py")
            print("[+] Sentinel offline.")
        elif action == "status":
            os.system("pgrep -af sentinel.py || echo 'Sentinel is NOT running.'")
        return

    prompt = cmd
    
    # Try to get project from context if possible
    project = "default"
    current_proj_file = os.path.expanduser("~/atlas_agents/core/current_project.txt")
    if os.path.exists(current_proj_file):
        with open(current_proj_file, "r") as f:
            project = f.read().strip()

    payload = {
        "message": prompt,
        "project": project
    }

    try:
        response = requests.post(API_URL, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                update = json.loads(line.decode("utf-8"))
                # Handle different update types for terminal display
                if update['type'] == 'chunk':
                    print(update['msg'], end="", flush=True)
                elif update['type'] == 'status':
                    print(f"\n[*] {update['tag']}: {update['msg']}")
                elif update['type'] == 'thought':
                    print(f"\n💭 {update['msg']}")
                elif update['type'] == 'action':
                    print(f"\n⚙️ Executing {update['tool']}...")
                elif update['type'] == 'final_answer':
                    pass # Handled by chunks
        print() # Newline at end
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Atlas Daemon. Is the server running? (./start_web.sh)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

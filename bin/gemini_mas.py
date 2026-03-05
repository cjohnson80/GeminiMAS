__version__ = '8.1.0'

import json
import os
import sys
import threading
import queue
import subprocess
import time
import argparse
from datetime import datetime

# Imports from extracted modules
from config import (AGENT_ROOT, WORKSPACE, DB_FILE, SOUL_FILE, HEARTBEAT_FILE, 
                    CHAT_LOG, LOCAL_CONFIG, SKILLS_DIR,
                    read_local_config, is_feature_enabled, toggle_feature, 
                    write_local_config, status, read_file_safe)
from api import GeminiClient
from memory import Persistence
from toolbox import ToolBox

# Threading Lock for DB
db_lock = threading.Lock()

class GeminiMAS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.machine_name = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
        self.lite_model = "gemini-3.1-flash-lite-preview"
        self.pro_model = "gemini-3.1-pro-preview"
        self.client_lite = GeminiClient(api_key, self.lite_model)
        self.client_pro = GeminiClient(api_key, self.pro_model)
        self.db = Persistence(api_key)
        self.history = []
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, 'r') as f:
                for l in f.readlines()[-6:]: self.history.append(json.loads(l))

    def get_system_context(self):
        soul = read_file_safe(SOUL_FILE)
        local_cfg = read_local_config()
        return f"{soul}\n\nCURRENT_MACHINE: {self.machine_name}\nLOCAL_HARDWARE_CONFIG: {json.dumps(local_cfg)}\n"

    def triage(self, user_input):
        prompt = f"Analyze: '{user_input}'. Is this a casual CHAT or a TASK that requires coding/tools/system changes? Reply ONLY 'CHAT' or 'TASK'."
        res = self.client_lite.generate(prompt)
        return res.strip().upper() if res else "CHAT"

    def run_worker_with_tools(self, task_desc, context, sys_instr, role="Developer", images=None):
        # Role-specific system instruction
        role_prompt = f"{sys_instr}\n\nYOUR_ROLE: {role}\n"
        if role == "Architect":
            role_prompt += "Focus on directory structure, scalability, and defining interfaces.\n"
        elif role == "Reviewer":
            role_prompt += "Focus on code quality, security, TypeScript strictness, and Next.js best practices.\n"

        sys_prompt = role_prompt + "\n\nYou are an executor. Tools available:\n1. run_shell (payload: command)\n2. verify_project (payload: project_path) - Runs lint/tsc to ensure code quality.\n3. fetch_url (payload: url)\n4. read_file (payload: path)\n5. write_file (payload: JSON string {'path':'...', 'content':'...'})\n6. notify_telegram (payload: message to send to user)\n\nReply ONLY with JSON: {'tool': 'name', 'payload': 'data'} OR reply with final text if no tool is needed."
        history = f"Context from previous tasks:\n{context}\n\nTask to complete as {role}:\n{task_desc}"

        for attempt in range(5):
            output = self.client_lite.generate(history, system_instruction=sys_prompt, images=images)
            if output and "{" in output and ("'tool'" in output.replace('"', "'") or '"tool"' in output):
                try:
                    block = output[output.find("{"):output.rfind("}")+1]
                    cmd = json.loads(block)
                    status(f" [{role}:{cmd['tool']}]...")
                    tool_result = ToolBox.execute(cmd['tool'], cmd['payload'])
                    # Smart Context Management: If output is huge, summarize it
                    if len(tool_result) > 2000:
                        status(" [Summarizing Large Output]...")
                        tool_result = self.client_lite.generate(f"Summarize this tool output for an agent: {tool_result[:8000]}")

                    history += f"\n\nTool Output:\n{tool_result}\nAnalyze this and continue."
                except Exception as e: history += f"\n\nTool parse error: {str(e)}."
            else: return output

        status(f"\n[!] {role} Stuck. Consulting Senior Debugger...")
        # Context Compression for Senior Debugger
        brief_history = self.client_lite.generate(f"Summarize the attempts and failures so far to help a senior debugger: {history[-10000:]}")
        advice = self.client_pro.generate(f"Worker Role: {role} is stuck.\nDEBUG BRIEF:\n{brief_history}\n\nProvide an actionable fix or workaround.", system_instruction="You are a Senior Debugger. Help the worker get unstuck.")
        if advice:
            status(" Advice received. Executing final attempt...")
            final_history = history + f"\n\nSENIOR_DEBUGGER_ADVICE: {advice}\nExecute the task one last time using this advice."
            return self.client_lite.generate(final_history, system_instruction=sys_prompt, images=images)

        return f"Task failed after 5 attempts and Senior Debugger consultation."

    def solve_task(self, user_goal, images=None):
        past = self.db.semantic_search(user_goal)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(WORKSPACE, timestamp)
        os.makedirs(session_dir, exist_ok=True)

        # Shared context file for agents to collaborate
        scratchpad_path = os.path.join(session_dir, "PROJECT_SUMMARY.md")
        with open(scratchpad_path, "w") as f:
            f.write(f"# Project Scratchpad\n\nGoal: {user_goal}\n\n## Structure\n(To be defined by Architect)\n")

        status("[*] Collaborative Planning...")
        sys_instr = self.get_system_context()
        prompt = (f"Goal: {user_goal}\nPast Context: {past}\n"
                  f"Plan 1-6 tasks using specialized agents. JSON format: [{{'id':1, 'role':'Architect|Developer|Reviewer', 'task':'...', 'parallel': false}}].\n"
                  f"- Use an Architect first to define structure in {scratchpad_path}.\n"
                  f"- Use Developers for implementation.\n"
                  f"- Use Reviewers to verify critical code.\n"
                  f"- Set 'parallel': true only for independent tasks.")

        plan_raw = self.client_pro.generate(prompt, system_instruction=sys_instr, json_mode=True, images=images)
        try: plan = json.loads(plan_raw.strip("`json \n"))
        except: return "Planning failed."

        results = {}
        threads = []
        q = queue.Queue()

        def worker(step, sys_instr, results_so_far, q, imgs):
            role = step.get('role', 'Developer')
            res = self.run_worker_with_tools(step['task'], str(results_so_far), sys_instr, role=role, images=imgs)
            q.put((step['id'], res))
            with open(os.path.join(session_dir, f"task_{step['id']}_{role}.md"), 'w') as f: f.write(res)
            status(f" Task {step['id']} ({role}) Done.")

        for step in plan:
            is_parallel = step.get('parallel', False)
            role = step.get('role', 'Developer')
            status(f"\n[*] Spawning {role} for Task {step['id']} (Parallel: {is_parallel})...")

            if is_parallel:
                t = threading.Thread(target=worker, args=(step, sys_instr, dict(results), q, images))
                t.start()
                threads.append(t)
            else:
                for t in threads: t.join()
                while not q.empty():
                    tid, tres = q.get(); results[tid] = tres
                threads = []

                worker(step, sys_instr, dict(results), q, images)
                while not q.empty():
                    tid, tres = q.get(); results[tid] = tres

        for t in threads: t.join()
        while not q.empty():
            tid, tres = q.get(); results[tid] = tres

        status(f"\n[*] Final Review...")
        final = self.client_lite.generate(f"Goal: {user_goal}\nResults: {json.dumps(results)}\nFormat final summary.", system_instruction=sys_instr, images=images)
        with open(os.path.join(session_dir, "final_response.md"), 'w') as f: f.write(final)
        self.db.save_memory(user_goal, final[:1000])
        return final

    def process(self, user_input, stream=False, images=None):
        sys_instr = self.get_system_context()
        if "TASK" in self.triage(user_input):
            response = self.solve_task(user_input, images=images)
            if stream: yield response
            else: return response
        else:
            if stream:
                full_resp = ""
                for chunk in self.client_lite.generate_stream(user_input, system_instruction=sys_instr, history=self.history, images=images):
                    full_resp += chunk
                    yield chunk

                if full_resp:
                    entry_user = {"role": "user", "text": user_input}
                    entry_model = {"role": "model", "text": full_resp}
                    self.history.extend([entry_user, entry_model])
                    os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
                    with open(CHAT_LOG, 'a') as f:
                        f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
            else:
                response = self.client_lite.generate(user_input, system_instruction=sys_instr, history=self.history, images=images)
                if response:
                    entry_user = {"role": "user", "text": user_input}
                    entry_model = {"role": "model", "text": response}
                    self.history.extend([entry_user, entry_model])
                    os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
                    with open(CHAT_LOG, 'a') as f:
                        f.write(json.dumps(entry_user) + "\n" + json.dumps(entry_model) + "\n")
                return response
def heartbeat_daemon(api_key):
    mas = GeminiMAS(api_key)
    print(f"\n[!] Heartbeat Daemon Started v{__version__} (Evolution Mode + Distributed Listener)")

    repo_path = os.path.expanduser('~/GeminiMAS_Repo')
    mailbox_path = os.path.join(repo_path, 'mailbox')

    while True:
        try:
            # Sync with Repo
            subprocess.run(f"cd {repo_path} && git pull origin main", shell=True, capture_output=True)

            # 1. Check for Mailbox Commands
            cmd_file = os.path.join(mailbox_path, f"{mas.machine_name}_cmd.json")
            if os.path.exists(cmd_file):
                print(f"\n[Mail] Received remote command...")
                try:
                    with open(cmd_file, 'r') as f: cmd_data = json.load(f)

                    # Process the command
                    result = ""
                    for chunk in mas.process(cmd_data['command'], stream=True):
                        result += chunk

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

            time.sleep(10) # Fast check for commands
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Heartbeat Error: {e}")
            time.sleep(60)

def interactive_loop(api_key):
    mas = GeminiMAS(api_key)
    print("\n" + "="*50 + f"\nGeminiMAS v{__version__} (Evolution Shell)\n" + "="*50)
    print("Commands: /enable [f], /disable [f], /config, /image [path], /help, exit")
    while True:
        try:
            inp = input("\n[You] > ").strip()
            if not inp: continue
            if inp.lower() in ['exit', 'quit']: break
            if inp.lower() == 'heartbeat': heartbeat_daemon(api_key); continue

            # Local Management Commands
            images = None
            if inp.startswith("/image "):
                parts = inp.split(" ", 1)
                img_path = os.path.expanduser(parts[1].strip())
                if os.path.exists(img_path):
                    images = [img_path]
                    inp = input("[Prompt for Image] > ").strip()
                else:
                    print(f"Error: Image not found at {img_path}")
                    continue

            if inp.startswith("/disable "):
                print(toggle_feature(inp.split(" ", 1)[1].strip(), enable=False))
                continue
            if inp.startswith("/enable "):
                print(toggle_feature(inp.split(" ", 1)[1].strip(), enable=True))
                continue
            if inp.lower() == "/config":
                print(json.dumps(read_local_config(), indent=4))
                continue
            if inp.lower() == "/help":
                print("\n[Help] GeminiMAS Interactive Shell")
                print("/config          - View local machine configuration")
                print("/enable [name]   - Enable a disabled feature")
                print("/disable [name]  - Disable a feature locally (without deleting code)")
                print("heartbeat        - Start the heartbeat daemon manually")
                print("exit/quit        - Close the shell\n")
                continue

            print("\n[Agent] > ", end="", flush=True)
            for chunk in mas.process(inp, stream=True):
                print(chunk, end="", flush=True)
            print("\n")
        except KeyboardInterrupt: break
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GeminiMAS Core Engine')
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
            mas = GeminiMAS(key)
            for chunk in mas.process(prompt, stream=True, images=images):
                print(chunk, end="", flush=True)
            print()
        else:
            interactive_loop(key)

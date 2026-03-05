import os
import asyncio
import subprocess
import logging
import sys
import json
import time
import psutil
import gc
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from logger_setup import setup_async_logger

# Configure logging
logger = logging.getLogger('TG_GATEWAY')

# Global task tracking
running_tasks = {} # chat_id -> subprocess.Process

async def celeron_watchdog(threshold_mb=150, check_interval_sec=30):
    process = psutil.Process(os.getpid())
    while True:
        try:
            rss_mb = process.memory_info().rss / (1024 * 1024)
            if rss_mb > threshold_mb:
                logger.warning(f'[WATCHDOG] High Memory: {rss_mb:.2f}MB. Forcing GC.')
                gc.collect()
            await asyncio.sleep(check_interval_sec)
        except asyncio.CancelledError:
            break

# Distributed Config
REPO_PATH = os.path.expanduser('~/GeminiMAS_Repo')
MAILBOX_PATH = os.path.join(REPO_PATH, 'mailbox')
FOCUS_FILE = os.path.join(os.path.expanduser('~/gemini_agents/core'), 'current_focus.json')
MY_HOSTNAME = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()

semaphore = asyncio.Semaphore(4)
ALLOWED_USER_ID = os.getenv('TELEGRAM_USER_ID')

def get_focus():
    if not os.path.exists(FOCUS_FILE):
        return MY_HOSTNAME
    try:
        with open(FOCUS_FILE, 'r') as f: return json.load(f).get('focused_machine', MY_HOSTNAME)
    except: return MY_HOSTNAME

def set_focus(name):
    os.makedirs(os.path.dirname(FOCUS_FILE), exist_ok=True)
    with open(FOCUS_FILE, 'w') as f: json.dump({'focused_machine': name}, f)

def is_authorized(update: Update):
    if not ALLOWED_USER_ID:
        logger.critical("SECURITY CRITICAL: TELEGRAM_USER_ID not set in .env! Refusing all commands for safety.")
        return False
    
    user_id = str(update.effective_user.id)
    if user_id != str(ALLOWED_USER_ID):
        logger.warning(f"UNAUTHORIZED ACCESS ATTEMPT: User {user_id} (@{update.effective_user.username}) tried to message the bot.")
        return False
    return True

def is_safe_command(command):
    blacklist = ["rm -rf /", ":(){ :|:& };:"]
    for forbidden in blacklist:
        if forbidden in command:
            return False
    return True

# --- NEW ADMIN COMMANDS ---

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    chat_id = update.effective_chat.id
    if chat_id in running_tasks:
        proc = running_tasks[chat_id]
        proc.terminate()
        await update.message.reply_text("🛑 Task cancelled. Process terminated.")
        if chat_id in running_tasks: del running_tasks[chat_id]
    else:
        await update.message.reply_text("No active tasks found to cancel.")

async def status_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    tasks = len(running_tasks)
    
    # Detailed memory
    swap = psutil.swap_memory().percent
    disk = psutil.disk_usage('/').percent
    
    report = (f"📊 System Status [{MY_HOSTNAME}]\n"
              f"CPU: {cpu}%\n"
              f"RAM: {mem}%\n"
              f"SWAP: {swap}%\n"
              f"DISK: {disk}%\n"
              f"Active Tasks: {tasks}")
    await update.message.reply_text(report)

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    # Check for logs in both repo and agent_root
    log_paths = [
        os.path.join(os.path.expanduser("~/gemini_agents"), "logs/chat_history.jsonl"),
        "/home/chrisj/GeminiMAS_Repo/logs/gemini_mas.log"
    ]
    
    resp = "📋 Recent Logs:\n"
    for path in log_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    lines = f.readlines()[-10:]
                    resp += f"\n--- {os.path.basename(path)} ---\n" + "".join(lines)
            except: pass
    
    await update.message.reply_text(resp[:4096])

async def restart_heartbeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("🔄 Restarting Heartbeat Service...")
    subprocess.run("systemctl --user restart gagent-heartbeat.service", shell=True)
    await update.message.reply_text("✅ Heartbeat restarted.")

# --- END ADMIN COMMANDS ---

async def route_to_machine(target_name, command, update):
    status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Routing to {target_name} via Git...")
    cmd_file = os.path.join(MAILBOX_PATH, f"{target_name}_cmd.json")
    payload = {"command": command, "chat_id": update.message.chat_id, "timestamp": time.time()}
    with open(cmd_file, 'w') as f: json.dump(payload, f)
    subprocess.run(f"cd {REPO_PATH} && git add mailbox/ && git commit -m 'Mailbox: command for {target_name}' && git push origin main", shell=True)
    await status_msg.edit_text(f"[{MY_HOSTNAME}] Command queued for {target_name}. Awaiting heartbeat response (up to 60s)...")
    res_file = os.path.join(MAILBOX_PATH, f"{target_name}_res.json")
    for _ in range(12):
        await asyncio.sleep(5)
        subprocess.run(f"cd {REPO_PATH} && git pull origin main", shell=True, capture_output=True)
        if os.path.exists(res_file):
            try:
                with open(res_file, 'r') as f: res_data = json.load(f)
                await status_msg.edit_text(f"[{target_name}]\n{res_data['result']}")
                os.remove(res_file)
                if os.path.exists(cmd_file): os.remove(cmd_file)
                subprocess.run(f"cd {REPO_PATH} && git add mailbox/ && git commit -m 'Mailbox: cleanup {target_name}' && git push origin main", shell=True)
                return
            except: pass
    await status_msg.edit_text(f"[{MY_HOSTNAME}] Timeout: {target_name} did not respond.")

CURRENT_PROJECT_FILE = os.path.join(os.path.expanduser('~/gemini_agents/core'), 'current_project.txt')
WORKSPACE_DIR = os.path.expanduser('~/gemini_agents/workspace')

async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        curr = "default"
        if os.path.exists(CURRENT_PROJECT_FILE):
            with open(CURRENT_PROJECT_FILE, 'r') as f: curr = f.read().strip()
        await update.message.reply_text(f"📁 Current Project: {curr.upper()}")
        return
    new_p = context.args[0].lower().replace(" ", "_")
    os.makedirs(os.path.dirname(CURRENT_PROJECT_FILE), exist_ok=True)
    with open(CURRENT_PROJECT_FILE, 'w') as f: f.write(new_p)
    await update.message.reply_text(f"✅ Switched workspace to: {new_p.upper()}")

async def list_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not os.path.exists(WORKSPACE_DIR):
        await update.message.reply_text("No projects found.")
        return
    projects = [p for p in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, p))]
    if not projects: await update.message.reply_text("No projects found.")
    else:
        resp = "📂 Active Agency Projects:\n" + "\n".join([f"• {p}" for p in projects])
        await update.message.reply_text(resp)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    branch_name = context.args[0] if context.args else "main"
    cmd = f"cd {REPO_PATH} && git checkout main && git pull origin main && git merge {branch_name} && git push origin main && ./install.sh"
    proc = await asyncio.create_subprocess_shell(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await proc.communicate()
    await update.message.reply_text(f"Successfully merged evolution: {branch_name}. System updated.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not update.message or not update.message.text: return
    text = update.message.text
    chat_id = update.effective_chat.id

    if not is_safe_command(text):
        await update.message.reply_text("❌ SECURITY ALERT: High-risk command blocked.")
        return

    target_machine = get_focus()
    if ":" in text and len(text.split(":")[0].split()) == 1:
        prefix = text.split(":")[0].strip().lower()
        target_machine = prefix
        text = text.split(":", 1)[1].strip()
        set_focus(target_machine)

    if target_machine == MY_HOSTNAME.lower() or target_machine == MY_HOSTNAME:
        curr_p = "default"
        if os.path.exists(CURRENT_PROJECT_FILE):
            with open(CURRENT_PROJECT_FILE, 'r') as f: curr_p = f.read().strip()
            
        status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] 🧠 Working on '{curr_p.upper()}'...")
        
        async with semaphore:
            typing_task = asyncio.create_task(context.bot.send_chat_action(chat_id=chat_id, action="typing"))
            try:
                cmd_executable = "gagent" if subprocess.run(["which", "gagent"], capture_output=True).returncode == 0 else sys.executable
                if cmd_executable == "gagent":
                    proc = await asyncio.create_subprocess_exec(cmd_executable, "--prompt", text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    mas_path = os.path.expanduser('~/gemini_agents/bin/gemini_mas.py')
                    proc = await asyncio.create_subprocess_exec(sys.executable, mas_path, '--prompt', text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                running_tasks[chat_id] = proc
                
                full_stdout = []
                last_notify_time = time.time()
                
                # Stream stdout for progress notifications
                while True:
                    line = await proc.stdout.readline()
                    if not line: break
                    line_str = line.decode('utf-8', errors='replace').strip()
                    full_stdout.append(line_str)
                    
                    # If line looks like a status update, notify user (throttled)
                    if any(x in line_str for x in ["[", "Thinking", "Executing", "Completed"]):
                        if time.time() - last_notify_time > 3: # Max every 3 seconds
                            # Extract clean message from ANSI/Tags
                            clean_line = "".join(c for c in line_str if ord(c) >= 32 or c == '\n')
                            try: await status_msg.edit_text(f"[{MY_HOSTNAME}] 🧠 {clean_line[:100]}...")
                            except: pass
                            last_notify_time = time.time()

                stderr_data = await proc.stderr.read()
                await proc.wait()
                
                out_str = "\n".join(full_stdout).strip()
                err_str = stderr_data.decode('utf-8', errors='replace').strip()
                
                response = out_str or f"Error: {err_str}"
                if not response: response = "Core engine returned empty response."
                
                await status_msg.edit_text(response[:4096])
            except asyncio.CancelledError:
                if status_msg: await status_msg.edit_text("Task was manually cancelled.")
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                if status_msg: await status_msg.edit_text(f"Error: {str(e)}")
            finally:
                typing_task.cancel()
                if chat_id in running_tasks: del running_tasks[chat_id]
    else:
        await route_to_machine(target_machine, text, update)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    photo_file = await update.message.photo[-1].get_file()
    img_path = os.path.expanduser(f'~/gemini_agents/workspace/tg_image_{int(time.time())}.jpg')
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    await photo_file.download_to_drive(img_path)
    caption = update.message.caption or "Analyze this image."
    status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Image received. Thinking...")
    mas_path = os.path.expanduser('~/gemini_agents/bin/gemini_mas.py')
    async with semaphore:
        try:
            proc = await asyncio.create_subprocess_exec(sys.executable, mas_path, '--prompt', caption, '--image', img_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            running_tasks[update.effective_chat.id] = proc
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
            if update.effective_chat.id in running_tasks: del running_tasks[update.effective_chat.id]
            out_str = stdout.decode('utf-8', errors='replace').strip()
            err_str = stderr.decode('utf-8', errors='replace').strip()
            response = out_str or f"Error: {err_str}"
            await status_msg.edit_text(response[:4096])
        except Exception as e:
            if status_msg: await status_msg.edit_text(f"Error: {str(e)}")

async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token: sys.exit(1)
    listener = setup_async_logger()
    app = ApplicationBuilder().token(token).build()
    bot_info = await app.bot.get_me()
    logger.info(f"Gateway started. Bot: @{bot_info.username}")
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("project", project_command))
    app.add_handler(CommandHandler("projects", list_projects))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("status", status_report))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("restart", restart_heartbeat))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    watchdog = asyncio.create_task(celeron_watchdog())
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True: await asyncio.sleep(1)
    finally:
        watchdog.cancel()
        if app.updater: await app.updater.stop()
        await app.stop()
        await app.shutdown()
        listener.stop()

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

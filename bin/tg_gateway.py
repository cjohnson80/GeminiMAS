import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import asyncio
import subprocess
import logging
import sys
import json
import time
import psutil
import gc
import signal
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from logger_setup import setup_async_logger

# Configure logging
logger = logging.getLogger('TG_GATEWAY')

async def celeron_watchdog(threshold_mb=150, check_interval_sec=30):
    process = psutil.Process(os.getpid())
    while True:
        try:
            rss_mb = process.memory_info().rss / (1024 * 1024)
            if rss_mb > threshold_mb:
                logger.warning(f"[WATCHDOG] High Memory: {rss_mb:.2f}MB. Forcing GC.")
                gc.collect()
            await asyncio.sleep(check_interval_sec)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[WATCHDOG] Exception: {e}")
            await asyncio.sleep(5)

# Distributed Config
REPO_PATH = os.path.expanduser('~/AtlasSwarm_Repo')
MAILBOX_PATH = os.path.join(REPO_PATH, 'mailbox')
FOCUS_FILE = os.path.join(os.path.expanduser('~/atlas_agents/core'), 'current_focus.json')
MY_HOSTNAME = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()

semaphore = asyncio.Semaphore(2)
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
    """Basic sandbox to prevent catastrophic commands."""
    blacklist = ["rm -rf /", ":(){ :|:& };:"]
    for forbidden in blacklist:
        if forbidden in command:
            return False
    return True

async def route_to_machine(target_name, command, update):
    """Mails a command to another machine via Git."""
    status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Routing to {target_name} via Git...")

    cmd_file = os.path.join(MAILBOX_PATH, f"{target_name}_cmd.json")
    payload = {
        "command": command,
        "chat_id": update.message.chat_id,
        "timestamp": time.time()
    }

    with open(cmd_file, 'w') as f: json.dump(payload, f)

    # Push to Git so the other machine sees it
    subprocess.run(f"cd {REPO_PATH} && git add mailbox/ && git commit -m 'Mailbox: command for {target_name}' && git push origin main", shell=True)

    await status_msg.edit_text(f"[{MY_HOSTNAME}] Command queued for {target_name}. Awaiting heartbeat response (up to 60s)...")

    # Wait for result file
    res_file = os.path.join(MAILBOX_PATH, f"{target_name}_res.json")
    for _ in range(12): # Wait 60 seconds
        await asyncio.sleep(5)
        subprocess.run(f"cd {REPO_PATH} && git pull origin main", shell=True, capture_output=True)
        if os.path.exists(res_file):
            try:
                with open(res_file, 'r') as f: res_data = json.load(f)
                await status_msg.edit_text(f"[{target_name}]\n{res_data['result']}")
                os.remove(res_file)
                # Cleanup cmd file too
                if os.path.exists(cmd_file): os.remove(cmd_file)
                subprocess.run(f"cd {REPO_PATH} && git add mailbox/ && git commit -m 'Mailbox: cleanup {target_name}' && git push origin main", shell=True)
                return
            except: pass

    await status_msg.edit_text(f"[{MY_HOSTNAME}] Timeout: {target_name} did not respond. Check its heartbeat.")

CURRENT_PROJECT_FILE = os.path.join(os.path.expanduser('~/atlas_agents/core'), 'current_project.txt')
WORKSPACE_DIR = os.path.expanduser('~/atlas_agents/workspace')

async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        # Show current project if no name provided
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
    if not projects:
        await update.message.reply_text("No projects found.")
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


async def abort_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/abort")
        await update.message.reply_text("🚨 EMERGENCY STOP: Abort signal transmitted to Atlas Swarm.")
    except Exception as e:
        await update.message.reply_text(f"Error sending abort signal: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not update.message or not update.message.text: return
    text = update.message.text

    # Security check for shell-injection or risky commands
    if not is_safe_command(text):
        await update.message.reply_text("❌ SECURITY ALERT: High-risk command blocked by gateway.")
        logger.error(f"BLOCKED RISKY COMMAND: {text}")
        return

    # Check for focus shift
    target_machine = get_focus()
    if ":" in text and len(text.split(":")[0].split()) == 1:
        prefix = text.split(":")[0].strip().lower()
        target_machine = prefix
        text = text.split(":", 1)[1].strip()
        set_focus(target_machine)
        logger.info(f"Focus shifted to: {target_machine}")

    if target_machine == MY_HOSTNAME.lower() or target_machine == MY_HOSTNAME:
        # Get project name for context
        curr_p = "default"
        if os.path.exists(CURRENT_PROJECT_FILE):
            with open(CURRENT_PROJECT_FILE, 'r') as f: curr_p = f.read().strip()
            
        # Process locally with activity feedback
        status_msg = await update.message.reply_text(f"[ATLAS @ {MY_HOSTNAME}] 🧠 Working on '{curr_p.upper()}'...")
        
        async with semaphore:
            # Start background "typing" status
            typing_task = asyncio.create_task(context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action="typing"))
            
            try:
                import httpx
                full_output = []
                last_update_time = time.time()
                
                async with httpx.AsyncClient(timeout=300.0) as client:
                    async with client.stream("POST", "http://localhost:8000/prompt", json={
                        "message": text,
                        "project": curr_p
                    }) as response:
                        async for line in response.aiter_lines():
                            if not line: continue
                            update_data = json.loads(line)
                            
                            if update_data['type'] == 'chunk':
                                full_output.append(update_data['msg'])
                            
                            # Update Telegram every 3 seconds if there's new important info
                            if time.time() - last_update_time > 3.0:
                                display_text = f"[ATLAS @ {MY_HOSTNAME}] 🧠 Working...\n"
                                
                                # Use high-level progress info for the status msg
                                if update_data['type'] == 'thought':
                                    display_text += f"\n💭 *Thought:* {update_data['msg'][:200]}..."
                                elif update_data['type'] == 'action':
                                    display_text += f"\n⚙️ *Action:* Executing {update_data['tool']}..."
                                elif update_data['type'] == 'status':
                                    display_text += f"\n[*] *{update_data['tag']}:* {update_data['msg'][:200]}..."
                                
                                try:
                                    await status_msg.edit_text(display_text[:4096], parse_mode='Markdown')
                                    last_update_time = time.time()
                                except: pass

                final_response = "".join(full_output)
                if not final_response: final_response = "Core engine returned empty response."
                
                if len(final_response) > 4000:
                    final_response = final_response[-4000:]
                
                await status_msg.edit_text(final_response)
            except Exception as e:
                logger.error(f"Error handling message via Daemon: {e}")
                if status_msg:
                    await status_msg.edit_text(f"Daemon Error: {str(e)}")
            finally:
                typing_task.cancel()
    else:
        # Route to another machine
        await route_to_machine(target_machine, text, update)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return

    photo_file = await update.message.photo[-1].get_file()
    img_path = os.path.expanduser(f'~/atlas_agents/workspace/tg_image_{int(time.time())}.jpg')
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    await photo_file.download_to_drive(img_path)

    caption = update.message.caption or "Analyze this image."
    status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Image received. Processing via Daemon...")

    async with semaphore:
        try:
            import httpx
            full_output = []
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "http://localhost:8000/prompt", json={
                    "message": caption,
                    "project": get_focus(),
                    "image_path": img_path # Note: Added image_path to the gateway but need to ensure it's handled
                }) as response:
                    async for line in response.aiter_lines():
                        if not line: continue
                        update_data = json.loads(line)
                        if update_data['type'] == 'chunk':
                            full_output.append(update_data['msg'])

            response_text = "".join(full_output) or "Core engine returned empty response."
            await status_msg.edit_text(response_text[:4096])
        except Exception as e:
            logger.error(f"Error handling photo via Daemon: {e}")
            if status_msg:
                await status_msg.edit_text(f"Daemon Error: {str(e)}")


async def sh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    
    command = " ".join(context.args)
    if not command:
        await update.message.reply_text("Usage: /sh <command>")
        return
        
    target_machine = get_focus()
    
    if target_machine == MY_HOSTNAME.lower() or target_machine == MY_HOSTNAME:
        status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Executing...")
        
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            MAX_EXEC_TIME = 60.0
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=MAX_EXEC_TIME)
            except asyncio.TimeoutError:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                await asyncio.sleep(1)
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await status_msg.edit_text(f"[{MY_HOSTNAME}] Execution timed out after {MAX_EXEC_TIME}s.")
                return

            out_str = stdout.decode('utf-8', errors='replace').strip()
            err_str = stderr.decode('utf-8', errors='replace').strip()
            
            output = ""
            if out_str:
                output += f"STDOUT:\n{out_str}\n"
            if err_str:
                output += f"STDERR:\n{err_str}\n"
                
            if not output:
                output = "Command executed silently (no output)."
                
            if len(output) > 4000:
                output = output[:4000] + "\n...[TRUNCATED]"
                
            # Escape for MarkdownV2
            escaped_hostname = MY_HOSTNAME.replace('-', r'\-').replace('_', r'\_')
            output = output.replace('`', "'") # Prevent breaking code blocks
            
            await status_msg.edit_text(rf"\[{escaped_hostname}\]" + f"\n```text\n{output}\n```", parse_mode='MarkdownV2')
            
        except Exception as e:
            logger.error(f"Error executing /sh: {e}")
            await status_msg.edit_text(f"[{MY_HOSTNAME}] Error: {str(e)}")
            
    else:
        await route_to_machine(target_machine, f"/sh {command}", update)

async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("CRITICAL: TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    listener = setup_async_logger()

    app = ApplicationBuilder().token(token).build()
    
    # Get bot info to display identity
    async def log_identity():
        bot = await app.bot.get_me()
        logger.info(f"Gateway started. Bot: @{bot.username} | Host: {MY_HOSTNAME} | Focus: {get_focus()}")
    
    await log_identity()

    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("abort", abort_command))
    app.add_handler(CommandHandler("project", project_command))
    app.add_handler(CommandHandler("projects", list_projects))
    app.add_handler(CommandHandler("sh", sh_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Run polling and watchdog
    watchdog = asyncio.create_task(celeron_watchdog())

    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    finally:
        watchdog.cancel()
        if app.updater: await app.updater.stop()
        await app.stop()
        await app.shutdown()
        listener.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

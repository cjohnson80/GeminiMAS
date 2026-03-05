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
from logger_setup import setup_async_logger

# Configure logging
logger = logging.getLogger('TG_GATEWAY')

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

    # Security check for shell-injection or risky commands
    if not is_safe_command(text):
        await update.message.reply_text("❌ SECURITY ALERT: High-risk command blocked by gateway.")
        logger.error(f"BLOCKED RISKY COMMAND: {text}")
        return

    # Check for focus shift
    target_machine = get_focus()
    if ":" in text and len(text.split(":")[0].split()) == 1:
        prefix = text.split(":")[0].strip().lower()
        # We'll assume any single-word prefix before a colon might be a machine name
        # If it's a known machine or you address it, we shift focus
        target_machine = prefix
        text = text.split(":", 1)[1].strip()
        set_focus(target_machine)
        logger.info(f"Focus shifted to: {target_machine}")

    if target_machine == MY_HOSTNAME.lower() or target_machine == MY_HOSTNAME:
        # Process locally
        status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Thinking...")
        mas_path = os.path.expanduser('~/gemini_agents/bin/gemini_mas.py')
        async with semaphore:
            try:
                proc = await asyncio.create_subprocess_exec(sys.executable, mas_path, '--prompt', text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
                
                # Robust decoding and truncation
                out_str = stdout.decode('utf-8', errors='replace').strip()
                err_str = stderr.decode('utf-8', errors='replace').strip()
                
                response = out_str or f"Error: {err_str}"
                if not response: response = "Core engine returned empty response."
                
                await status_msg.edit_text(response[:4096])
            except Exception as e:
                import traceback
                logger.error(f"Error handling message: {e}\n{traceback.format_exc()}")
                if status_msg:
                    await status_msg.edit_text(f"Error: {str(e)}")
    else:
        # Route to another machine
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
            # Call core engine with image
            proc = await asyncio.create_subprocess_exec(
                sys.executable, mas_path, '--prompt', caption, '--image', img_path,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
            
            # Robust decoding and truncation
            out_str = stdout.decode('utf-8', errors='replace').strip()
            err_str = stderr.decode('utf-8', errors='replace').strip()
            
            response = out_str or f"Error: {err_str}"
            if not response: response = "Core engine returned empty response."
            
            await status_msg.edit_text(response[:4096])
        except Exception as e:
            import traceback
            logger.error(f"Error handling photo: {e}\n{traceback.format_exc()}")
            if status_msg:
                await status_msg.edit_text(f"Error: {str(e)}")

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    listener = setup_async_logger()

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info(f"Gateway started on {MY_HOSTNAME}. Focus: {get_focus()}")

    # Run polling and watchdog
    loop = asyncio.get_event_loop()
    watchdog = loop.create_task(celeron_watchdog())

    try:
        app.run_polling()
    finally:
        watchdog.cancel()
        listener.stop()

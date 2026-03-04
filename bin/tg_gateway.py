import os
import asyncio
import subprocess
import logging
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.expanduser('~/gemini_agents/logs/tg_gateway.log')
)
logger = logging.getLogger(__name__)

# Implementation of Semaphore to match core engine resource constraints
# Celeron-optimized: 2 concurrent processes max
semaphore = asyncio.Semaphore(2)

# Load restricted user ID
ALLOWED_USER_ID = os.getenv('TELEGRAM_USER_ID')

def is_authorized(update: Update):
    if not ALLOWED_USER_ID:
        return True # Default to allowed if not set (not recommended for production)
    return str(update.effective_user.id) == str(ALLOWED_USER_ID)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve [branch_name]")
        return

    branch_name = context.args[0]
    repo_path = os.path.expanduser('~/GeminiMAS_Repo')

    async with semaphore:
        try:
            # Evolution Protocol: Merge the approved branch into main
            # We pull main first to avoid conflicts
            cmd = f"cd {repo_path} && git checkout main && git pull origin main && git merge {branch_name} && git push origin main && ./install.sh"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                await update.message.reply_text(f"Successfully merged evolution: {branch_name}. System updated.")
            else:
                await update.message.reply_text(f"Merge failed: {stderr.decode()}")
        except Exception as e:
            await update.message.reply_text(f"Error during merge: {str(e)}")
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_input = update.message.text
    mas_path = os.path.expanduser('~/gemini_agents/bin/gemini_mas.py')

    # Send initial status message
    status_msg = await update.message.reply_text("Thinking...")

    async with semaphore:
        try:
            # Run the core engine
            proc = await asyncio.create_subprocess_exec(
                sys.executable, mas_path, '--prompt', user_input,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Since we don't have true streaming from subprocess yet,
            # we'll poll the output or just wait.
            # For now, let's keep it simple but improve the response handling.

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
            response = stdout.decode().strip() or f"Error: {stderr.decode()}"

            if response:
                await status_msg.edit_text(response[:4096])
            else:
                await status_msg.edit_text("No response received.")

        except asyncio.TimeoutError:
            await status_msg.edit_text("Gateway Timeout: Hardware resource limit reached.")
        except Exception as e:
            await status_msg.edit_text(f"Gateway Error: {str(e)}")
if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment.")
        exit(1)

    app = ApplicationBuilder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Telegram Gateway started.")
    app.run_polling()

import os
import asyncio
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Implementation of Semaphore to match core engine resource constraints
# Celeron-optimized: 2 concurrent processes max
semaphore = asyncio.Semaphore(2)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    async with semaphore:
        try:
            proc = await asyncio.create_subprocess_exec(
                'python3', os.path.expanduser('~/GeminiMAS_Repo/bin/gemini_mas.py'), user_input,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            response = stdout.decode().strip() or f"Error: {stderr.decode()}"
            await update.message.reply_text(response[:4096])
        except asyncio.TimeoutError:
            await update.message.reply_text("Gateway Timeout: Hardware resource limit reached.")
        except Exception as e:
            await update.message.reply_text(f"Gateway Error: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv('TG_BOT_TOKEN')).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
import sys
import os

with open('bin/tg_gateway.py', 'r') as f:
    content = f.read()

if 'import signal' not in content:
    content = content.replace('import os', 'import os\nimport signal')

shell_cmd_code = """
async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        await update.message.reply_text("Usage: /sh <command>")
        return
    
    command = " ".join(context.args)
    if not is_safe_command(command):
        await update.message.reply_text("❌ SECURITY ALERT: High-risk command blocked by gateway.")
        logger.error(f"BLOCKED RISKY COMMAND: {command}")
        return

    target_machine = get_focus()
    if target_machine != MY_HOSTNAME.lower() and target_machine != MY_HOSTNAME:
        await route_to_machine(target_machine, f"/sh {command}", update)
        return

    status_msg = await update.message.reply_text(f"[{MY_HOSTNAME}] Executing...")
    
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            await status_msg.edit_text(f"[{MY_HOSTNAME}] Execution timed out.")
            return

        out_str = stdout.decode('utf-8', errors='replace').strip()
        err_str = stderr.decode('utf-8', errors='replace').strip()
        
        output = ""
        if out_str:
            output += f"STDOUT:\n{out_str}\n"
        if err_str:
            output += f"STDERR:\n{err_str}"
            
        if not output:
            output = "Command executed silently."
            
        if len(output) > 4000:
            output = output[:4000] + "\n...[TRUNCATED]"
            
        await status_msg.edit_text(f"[{MY_HOSTNAME}]\n{output}")
    except Exception as e:
        logger.error(f"Error executing shell command: {e}")
        await status_msg.edit_text(f"[{MY_HOSTNAME}] Error: {str(e)}")
"""

if 'async def shell_command' not in content:
    content = content.replace('async def handle_message', shell_cmd_code + '\nasync def handle_message')

if 'CommandHandler("sh", shell_command)' not in content:
    content = content.replace('app.add_handler(CommandHandler("approve", approve_command))', 'app.add_handler(CommandHandler("approve", approve_command))\n    app.add_handler(CommandHandler("sh", shell_command))')

with open('bin/tg_gateway.py', 'w') as f:
    f.write(content)
print("Patched bin/tg_gateway.py")

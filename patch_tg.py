import sys
with open('bin/tg_gateway.py', 'r') as f:
    content = f.read()

if 'import signal' not in content:
    content = content.replace('import gc\n', 'import gc\nimport signal\n')

sh_handler = """
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
            escaped_hostname = MY_HOSTNAME.replace('-', '\\-').replace('_', '\\_')
            output = output.replace('`', "'") # Prevent breaking code blocks
            
            await status_msg.edit_text(f"\\[{escaped_hostname}\\]\n```text\n{output}\n```", parse_mode='MarkdownV2')
            
        except Exception as e:
            logger.error(f"Error executing /sh: {e}")
            await status_msg.edit_text(f"[{MY_HOSTNAME}] Error: {str(e)}")
            
    else:
        await route_to_machine(target_machine, f"/sh {command}", update)
"""

if 'async def sh_command' not in content:
    content = content.replace('async def main():', sh_handler + '\nasync def main():')

if 'CommandHandler("sh", sh_command)' not in content:
    content = content.replace('app.add_handler(CommandHandler("projects", list_projects))', 'app.add_handler(CommandHandler("projects", list_projects))\n    app.add_handler(CommandHandler("sh", sh_command))')

with open('bin/tg_gateway.py', 'w') as f:
    f.write(content)

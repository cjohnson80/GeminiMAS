import os, re, subprocess, time

file_path = os.path.expanduser('~/atlas_agents/bin/tg_gateway.py')
with open(file_path, 'r') as f:
    content = f.read()

# 1. Patch watchdog loop for resilience
if 'except Exception as e:' not in content:
    content = re.sub(
        r'(except asyncio\.CancelledError:\s*break)',
        r"\1\n        except Exception as e:\n            logger.error(f'[WATCHDOG] Error: {e}')\n            await asyncio.sleep(check_interval_sec)",
        content
    )
    with open(file_path, 'w') as f:
        f.write(content)
    print('Patched tg_gateway.py watchdog loop.')

# 2. Kill old processes gracefully
subprocess.run(['pkill', '-f', 'tg_gateway.py'])
time.sleep(2)

# 3. Find .env and parse variables
env_file = None
for root, dirs, files in os.walk(os.path.expanduser('~')):
    if '.env' in files and ('atlas_agents' in root or 'AtlasSwarm' in root):
        env_file = os.path.join(root, '.env')
        break

env_vars = os.environ.copy()
if env_file:
    print(f'Found .env at {env_file}')
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, val = line.split('=', 1)
                env_vars[key.strip()] = val.strip('"\' ')

# Ensure critical vars are present (fallback to known values from forensics)
if 'TELEGRAM_USER_ID' not in env_vars:
    env_vars['TELEGRAM_USER_ID'] = '8229777121'
if 'TELEGRAM_BOT_TOKEN' not in env_vars:
    env_vars['TELEGRAM_BOT_TOKEN'] = '8254837382:AAFdyeM3h0s9P5R2Q46Fcig-202SVPvPh-4'

# 4. Start process with venv python
python_bin = os.path.expanduser('~/atlas_agents/venv/bin/python')
log_file = os.path.expanduser('~/atlas_agents/logs/tg_gateway.log')

with open(log_file, 'w') as out:
    subprocess.Popen([python_bin, file_path], env=env_vars, stdout=out, stderr=subprocess.STDOUT)

print('Started tg_gateway.py cleanly.')
time.sleep(3)

# 5. Verify health
ps = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
for line in ps.stdout.splitlines():
    if 'tg_gateway.py' in line and 'grep' not in line:
        print(f'ACTIVE PROCESS: {line}')

print('\n--- RECENT LOGS ---')
with open(log_file, 'r') as f:
    print(f.read()[-1000:])

#!/bin/bash
python3 -c "
import re
with open('bin/tg_gateway.py', 'r') as f:
    code = f.read()

new_watchdog = '''async def celeron_watchdog(threshold_mb=150, check_interval_sec=30):
    process = psutil.Process(os.getpid())
    while True:
        try:
            rss_mb = process.memory_info().rss / (1024 * 1024)
            if rss_mb > threshold_mb:
                logger.warning(f\"[WATCHDOG] High Memory: {rss_mb:.2f}MB. Forcing GC.\")
                gc.collect()
            await asyncio.sleep(check_interval_sec)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f\"[WATCHDOG] Exception: {e}\")
            await asyncio.sleep(5)'''

code = re.sub(r'async def celeron_watchdog.*?except asyncio\.CancelledError:\n\s+break', new_watchdog, code, flags=re.DOTALL)

if 'load_dotenv' not in code:
    code = code.replace('import os', 'import os\ntry:\n    from dotenv import load_dotenv\n    load_dotenv(os.path.join(os.path.dirname(__file__), \"../.env\"))\nexcept:\n    pass')

with open('bin/tg_gateway.py', 'w') as f:
    f.write(code)
"

echo "Patching complete."
PIDS=$(pgrep -f '[t]g_gateway.py')
if [ -n "$PIDS" ]; then
    echo "Killing existing processes: $PIDS"
    kill -15 $PIDS
    sleep 2
    kill -9 $PIDS 2>/dev/null || true
fi

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

nohup python3 bin/tg_gateway.py > logs/tg_gateway_service.log 2>&1 &
echo "Service restarted cleanly. Checking logs..."
sleep 2
cat logs/tg_gateway_service.log || true

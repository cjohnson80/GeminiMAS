import logging
import sys

logging.basicConfig(filename='/home/chrisj/GeminiMAS_Repo/logs/gemini_mas.log', level=logging.ERROR)

def safe_execute(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f'Critical failure in {func.__name__}: {str(e)}', exc_info=True)
        # Graceful degradation: return None or neutral state instead of crashing
        return None

def monitor_resources():
    import psutil
    mem = psutil.virtual_memory().percent
    if mem > 95:
        sys.exit(0) # Emergency exit for Celeron hardware safety

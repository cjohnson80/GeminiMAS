import time
import threading
from gemini_mas import GeminiMAS

class GeminiMASWrapper:
    def __init__(self, api_key, max_threads=2):
        self.api_key = api_key
        self.max_threads = max_threads
        self.mas = None
        self._initialize_with_backoff()

    def _initialize_with_backoff(self, retries=5):
        delay = 1
        for i in range(retries):
            try:
                self.mas = GeminiMAS(self.api_key)
                return
            except Exception as e:
                if i == retries - 1: raise e
                time.sleep(delay)
                delay *= 2

    def execute_task(self, func, *args):
        # Celeron-optimized thread management
        if threading.active_count() <= self.max_threads:
            t = threading.Thread(target=func, args=args, daemon=True)
            t.start()
            return True
        return False

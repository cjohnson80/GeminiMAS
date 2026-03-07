import time
import json
import threading
from datetime import datetime, timedelta

# Core Identity Reference
AGENT_ROOT = "$AGENT_ROOT"
CONFIG_PATH = f"{AGENT_ROOT}/core/local_config.json"

class APIQuotaManager:
    """Manages API rate limiting states and enforces backoff."""

    def __init__(self, default_retry_seconds=86400):
        self.lock = threading.Lock()
        self.retry_until = 0
        # Defaulting to a safe 24h if no specific context is provided
        self.default_retry_seconds = default_retry_seconds
        self.load_state()

    def load_state(self):
        """Loads state from a mock config or memory (In a real system, this would check a persistent store)."""
        # For this simulation, we assume the context provided the exact failure time.
        # We will hardcode the known ~24h delay for the initial state setup.
        try:
            # In a real scenario, we would read the exact delay from the last 429 response.
            # Using the known ~24h delay (86030s) as the baseline for the *next* required wait.
            self.retry_until = time.time() + self.default_retry_seconds
            print(f"[API_MANAGER] State loaded. Next attempt allowed after: {datetime.fromtimestamp(self.retry_until).isoformat()}")
        except Exception as e:
            print(f"[API_MANAGER] Could not load state, using default: {e}")
            self.retry_until = time.time() + self.default_retry_seconds

    def record_429(self, retry_after_seconds=None):
        """Records a 429 error and sets the next allowed time."""
        with self.lock:
            wait_time = retry_after_seconds if retry_after_seconds is not None else self.default_retry_seconds
            self.retry_until = time.time() + wait_time
            print(f"[API_MANAGER] 429 Received. Enforcing wait until: {datetime.fromtimestamp(self.retry_until).isoformat()}")

    def is_rate_limited(self):
        """Checks if the current time is before the enforced retry time."""
        return time.time() < self.retry_until

    def get_wait_time(self):
        """Returns seconds remaining until access is granted."""
        if self.is_rate_limited():
            return self.retry_until - time.time()
        return 0

    def wait_if_necessary(self):
        """Blocks execution until the rate limit expires."""
        wait_seconds = self.get_wait_time()
        if wait_seconds > 0:
            print(f"[API_MANAGER] Waiting for {wait_seconds:.2f} seconds before proceeding.")
            time.sleep(wait_seconds)

# --- Wrapper Function for External Use ---

QUOTA_MANAGER = APIQuotaManager(default_retry_seconds=85983) # Using the precise 85983s from context

def execute_with_retry(api_call_function, *args, **kwargs):
    """Executes an API call function, handling rate limiting automatically."""
    # First, wait if the manager dictates it
    QUOTA_MANAGER.wait_if_necessary()

    try:
        # Attempt the call
        response = api_call_function(*args, **kwargs)
        # Check response status manually if the function doesn't raise on 429
        if hasattr(response, 'status_code') and response.status_code == 429:
            # If the underlying call returns 429, record it.
            QUOTA_MANAGER.record_429(retry_after_seconds=response.headers.get('Retry-After', 86400))
            # Re-raise or handle based on desired wrapper behavior
            raise Exception("API Call resulted in 429 after waiting.")
        return response
    except Exception as e:
        # If the error is a known rate limit error that didn't trigger the explicit check above
        if "429" in str(e):
             QUOTA_MANAGER.record_429() # Use default or extract from error message
             # Re-raise to ensure caller knows the operation failed this attempt
             raise e
        raise e

# Utility for demonstration/testing
def mock_external_api_call(task_name):
    print(f"[API CALL] Executing task: {task_name}")
    # Simulate success or failure based on current time
    if QUOTA_MANAGER.is_rate_limited():
        # In a real scenario, the underlying library would raise, but here we simulate a return object
        class MockResponse:
            status_code = 429
            headers = {'Retry-After': '3600'} # Simulate a shorter retry header for quick testing
        return MockResponse()
    else:
        class MockResponse:
            status_code = 200
            content = f"Result for {task_name}"
        return MockResponse()

if __name__ == '__main__':
    print("--- Testing API Quota Manager ---")
    # 1. Initial check (should pass)
    print("Attempt 1 (Immediate)")
    execute_with_retry(mock_external_api_call, "Initial Research")

    # 2. Simulate receiving a 429 error with a 10-second delay
    print("
Attempt 2 (Simulating 429 with 10s delay)")
    QUOTA_MANAGER.record_429(retry_after_seconds=10)
    execute_with_retry(mock_external_api_call, "Task Blocked") # This should wait 10 seconds

    # 3. Check immediately after (should still be blocked by the manager)
    print("
Attempt 3 (Immediate check after simulated block)")
    execute_with_retry(mock_external_api_call, "Second Blocked Task") # This should wait the remaining time

    # 4. Final check (should pass after waiting)
    print("
Attempt 4 (Check after forced wait)")
    execute_with_retry(mock_external_api_call, "Resumed Task")

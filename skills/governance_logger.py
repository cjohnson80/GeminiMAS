import json
import datetime
import os

LOG_FILE = 'logs/governance.log'

# Ensure the log directory exists
if not os.path.exists(os.path.dirname(LOG_FILE)) and os.path.dirname(LOG_FILE):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_governance_decision(actor_id: str, action_hash: str, decision: str, details: str = ""):
    """
    Logs a governance decision event to the centralized governance log file.

    :param actor_id: The ID of the entity making the decision (e.g., Operator, System).
    :param action_hash: A unique identifier for the proposed action.
    :param decision: The outcome (e.g., APPROVED, DENIED, TIMED_OUT).
    :param details: Optional additional context.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    log_entry = {
        'timestamp': timestamp,
        'actor_id': actor_id,
        'action_hash': action_hash,
        'decision': decision,
        'details': details
    }

    try:
        # Use 'a' for append mode
        with open(LOG_FILE, 'a') as f:
            # Write as a single line JSON object for easy parsing
            f.write(json.dumps(log_entry) + '
')
        print(f"[GovernanceLogger] Logged decision for {action_hash}: {decision}")
    except Exception as e:
        # In a real system, this would need more robust error handling/fallback
        print(f"[GovernanceLogger ERROR] Failed to write to {LOG_FILE}: {e}")

if __name__ == '__main__':
    # Example Usage (for verification)
    print("Testing GovernanceLogger utility...")
    log_governance_decision("Operator_Chris", "SHA256-ABC123XYZ", "APPROVED", "Approved deployment of new configuration v1.2")
    log_governance_decision("System_Core", "SHA256-DEF456GHI", "DENIED", "Risk score too high (9.5/10)")
    print("Test complete. Check logs/governance.log" )

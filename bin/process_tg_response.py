import json
import logging
from datetime import datetime

# Assume these paths are available or mocked for this utility
from skills.governance_logger import GovernanceLogger

# Configuration simulation
APPROVAL_MANAGER_ENDPOINT = "http://localhost:8080/api/approval/resolve"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ApprovalResponseProcessor:
    """Handles incoming decisions from the Telegram Gateway."""

    def __init__(self, logger_instance: GovernanceLogger):
        self.logger = logger_instance

    def _parse_response(self, raw_message: str) -> dict | None:
        """Parses raw Telegram message string into structured decision data."""
        parts = raw_message.strip().split(':', 1)
        if len(parts) != 2:
            logger.warning(f"Malformed response received: {raw_message}")
            return None
        
        decision = parts[0].strip().upper()
        request_id_part = parts[1].strip()
        
        if decision not in ["APPROVE", "DENY"]:
            logger.warning(f"Unknown decision verb: {decision}")
            return None
            
        # Simplification: Assume RequestID is the entire remaining string,
        # In a real system, this would be more complex parsing.
        request_id = request_id_part
        
        return {
            "request_id": request_id,
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        }

    def process(self, raw_message: str, actor_id: str) -> bool:
        """Main entry point to process and log a decision."""
        parsed_data = self._parse_response(raw_message)
        
        if not parsed_data:
            return False
            
        # Log the decision using the dedicated logger utility
        self.logger.log_decision(
            actor_id=actor_id, 
            action_hash=parsed_data['request_id'], # Using RequestID as a simple hash proxy here
            decision_result=parsed_data['decision'],
            timestamp=parsed_data['timestamp']
        )
        
        # In a real system, this would involve an HTTP call to the core manager
        # Example: print(f"Simulating API call to {APPROVAL_MANAGER_ENDPOINT} with {parsed_data}")
        
        logger.info(f"Successfully processed decision for Request ID: {parsed_data['request_id']} by Actor: {actor_id}")
        return True

if __name__ == '__main__':
    # Setup simulated logger instance
    # In a real setup, the GovernanceLogger would be initialized to write to logs/governance.log
    class MockLogger:
        def log_decision(self, **kwargs):
            print(f"[MOCK LOGGING] Logged: {kwargs}")
            
    mock_log_instance = MockLogger()
    processor = ApprovalResponseProcessor(mock_log_instance)
    
    # Test cases
    print("--- Testing Valid Approve ---")
    processor.process("APPROVE: REQ-4928-XYZ", actor_id="TG_USER_123")
    
    print("
--- Testing Valid Deny ---")
    processor.process("deny: req-4929-abc", actor_id="TG_USER_456")
    
    print("
--- Testing Invalid Format ---")
    processor.process("Just some random text", actor_id="TG_USER_789")

    print("
--- Testing Invalid Verb ---")
    processor.process("REJECT: REQ-4930-DEF", actor_id="TG_USER_123")

# bin/approval_manager.py

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Assuming governance_logger is available or imported correctly
# from skills.governance_logger import log_decision

# Placeholder for logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApprovalManager:
    """Manages the lifecycle of system-wide approval requests."""

    def __init__(self, tg_gateway, config: Dict[str, Any]):
        self.tg_gateway = tg_gateway  # Reference to tg_gateway instance
        self.config = config
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.history: Dict[str, Dict[str, Any]] = {}
        self.risk_threshold = config.get("APPROVAL_RISK_THRESHOLD", 50.0)

    def generate_request_id(self) -> str:
        return str(uuid.uuid4())[:8] # Short, unique ID

    def submit_request(self, proposed_action: str, context: str, risk_score: float) -> Optional[str]:
        """Submits a new action proposal for potential approval."""
        if risk_score < self.risk_threshold:
            logger.info(f"Action below threshold ({risk_score:.2f} < {self.risk_threshold:.2f}). Executing directly.")
            # In a real system, this would trigger direct execution or a safe path
            return None

        request_id = self.generate_request_id()
        request_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "action": proposed_action,
            "context": context,
            "risk_score": risk_score,
            "status": "PENDING"
        }

        self.pending_requests[request_id] = request_data
        logger.warning(f"New high-risk request submitted: {request_id} (Risk: {risk_score:.2f}). Forwarding to gateway.")

        # Forward to Telegram Gateway for operator notification
        self.tg_gateway.send_approval_notification(request_data)
        return request_id

    def process_operator_decision(self, request_id: str, decision: str, actor_id: str):
        """Processes the decision received from the Telegram gateway."""
        if request_id not in self.pending_requests:
            logger.error(f"Received decision for unknown request ID: {request_id}")
            return

        request_data = self.pending_requests.pop(request_id)
        request_data["status"] = decision.upper()
        request_data["decision_timestamp"] = datetime.now().isoformat()
        request_data["actor_id"] = actor_id

        # Log the governance decision
        try:
            from skills.governance_logger import log_decision
            log_decision(request_data, actor_id, decision.upper())
        except ImportError:
            logger.error("Could not import governance_logger to log decision.")

        self.history[request_id] = request_data

        if decision.upper() == "APPROVE":
            logger.info(f"Request {request_id} APPROVED. Executing action: {request_data["action"][:50]}...")
            # EXECUTE ACTION HERE (e.g., call a shell runner or API connector)
            # return True
        else:
            logger.warning(f"Request {request_id} DENIED by {actor_id}. Action aborted.")
            # return False

# Example usage placeholder (not executed at module load)
# if __name__ == '__main__':
#     print("ApprovalManager initialized.")
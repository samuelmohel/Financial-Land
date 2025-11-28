import logging
import json
from config import settings
from datetime import datetime

# Configure a file handler for the audit trail
AUDIT_LOG_FILE = "audit_trail.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(AUDIT_LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(settings.APP_NAME)

def log_interaction(interaction_type: str, user_query: str, agent_response: dict = None):
    """
    Logs a detailed record of a user interaction and the Agent's actions.

    Args:
        interaction_type: e.g., "USER_QUERY", "TOOL_CALL", "RAG_RETRIEVAL", "FINAL_ANSWER".
        user_query: The original or current query being processed.
        agent_response: Full response object (tools used, answer, sources).
    """
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "type": interaction_type,
        "query": user_query,
        "response_details": agent_response if agent_response else {}
    }
    
    logger.info(json.dumps(log_data))
    
if __name__ == '__main__':
    # Example logging
    log_interaction("SYSTEM_STARTUP", "N/A")
    log_interaction("USER_QUERY", "What is the cash flow?")
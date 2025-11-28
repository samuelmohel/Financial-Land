from fastapi import APIRouter
from pydantic import BaseModel
from agent_controller import process_query_with_agent
import logging
from audit import log_interaction

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic schema for the request body
class QueryRequest(BaseModel):
    query: str

# Pydantic schema for the response body
class QueryResponse(BaseModel):
    answer: str
    tools_used: list[str]

@router.post("/query", response_model=QueryResponse, tags=["Agent"])
async def handle_financial_query(request: QueryRequest):
    """
    Main endpoint for sending complex financial questions to the AI Agent.
    """
    
    # Process the query using the sophisticated Agent Controller
    agent_result = process_query_with_agent(request.query)
    # Log the interaction for auditing
    try:
        log_interaction("USER_QUERY", request.query, agent_result)
    except Exception as e:
        logger.exception("Failed to log interaction: %s", e)
    
    return QueryResponse(
        answer=agent_result["final_answer"],
        tools_used=agent_result["used_tools"]
    )
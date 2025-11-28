# agent_controller.py

import logging
from config import settings
from llm_client import generate_content
from audit import log_interaction

# --- IMPORTANT: CORRECTED IMPORTS FOR TOOLS ---
# These imports assume the files are located in the 'tools/' subdirectory.
from tools.currency_tool import get_exchange_rate
from tools.finance_rag import generate_rag_answer
from tools.registry_check import verify_company_registry
# from audit import log_interaction # Placeholder import

logger = logging.getLogger(__name__)

# No SDK client at module level: we will use `llm_client.generate_content` for provider-agnostic calls

# Define the available tools (must match the function names imported)
tools = {
    "get_exchange_rate": get_exchange_rate,
    "generate_rag_answer": generate_rag_answer,
    "verify_company_registry": verify_company_registry
}

def process_query_with_agent(user_query: str) -> dict:
    """
    The main Agent function that decides on tool usage and executes the final logic.
    """
    if not client:
        logger.error("Agent client not initialized. Check GEMINI_API_KEY.")
        log_interaction("ERROR", user_query, {"error": "Gemini client not initialized"})
        return {"final_answer": "Agent system initialization failed. Check your GEMINI_API_KEY.", "used_tools": []}

    # 1. Initial Call: Ask the LLM to decide on a tool
    try:
        # Use LLM provider wrapper; provider might be Groq, Gemini, etc.
        response = generate_content(user_query, model=settings.RAG_MODEL)
    except Exception as e:
        # Replaces temporary debug print with a controlled return
        logger.exception("Agent execution error: %s", e)
        log_interaction("ERROR", user_query, {"error": str(e)})
        # log_interaction(user_query, "Error", {"message": str(e)}) 
        return {"final_answer": "Agent system error. Please check configuration.", "used_tools": []}

    # 2. Check for Tool Calls
    if getattr(response, 'function_calls', None):
        tool_results = {}
        
        # Execute all tool calls requested by the model
        for call in response.function_calls:
            tool_name = call.name
            tool_args = dict(call.args)

            function_to_call = tools.get(tool_name)

            if function_to_call:
                # Execute the function with the arguments provided by the LLM
                result = function_to_call(**tool_args)
                tool_results[tool_name] = result
                try:
                    log_interaction("TOOL_CALL", user_query, {"tool": tool_name, "result": result})
                except Exception:
                    logger.exception("Failed to log tool execution for %s", tool_name)
            else:
                tool_results[tool_name] = {"error": f"Tool '{tool_name}' not found."}

        # 3. Final Call: Send tool results back to the LLM for final synthesis
        
        tool_response_parts = []
        for tool_name, result in tool_results.items():
             tool_response_parts.append(
                genai.types.Part.from_function_response(
                    name=tool_name, 
                    response=result
                )
             )

        # Send back to Gemini to generate the final answer
        # Final LLM synthesis: use the configured provider again
        final_response = generate_content([user_query] + tool_response_parts, model=settings.RAG_MODEL)

        return {
            "final_answer": getattr(final_response, 'text', str(final_response)),
            "used_tools": list(tool_results.keys())
        }
        
    # 4. No Tool Call: Direct answer (General Knowledge/Chat)
    return {
        "final_answer": response.text,
        "used_tools": []
    }
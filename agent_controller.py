# agent_controller.py

import logging
from typing import Optional
from config import settings
from llm_client import generate_content
from audit import log_interaction
from pydantic import BaseModel, ValidationError
from utils.circuit_breaker import CircuitBreaker

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

# Circuit breaker for tools
tool_cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)

# Simple arg validation schemas for tools. Keys map to tool name -> {required: set(keys), types: {key: type}}
class GetExchangeRateArgs(BaseModel):
    source_currency: str
    target_currency: str


class GenerateRagArgs(BaseModel):
    user_query: str


class VerifyCompanyRegistryArgs(BaseModel):
    company_name: str


TOOL_ARG_MODELS = {
    "get_exchange_rate": GetExchangeRateArgs,
    "generate_rag_answer": GenerateRagArgs,
    "verify_company_registry": VerifyCompanyRegistryArgs,
}


TOOL_ARG_SCHEMAS = {
    "get_exchange_rate": {
        "required": {"source_currency", "target_currency"},
        "types": {"source_currency": str, "target_currency": str}
    },
    "generate_rag_answer": {
        "required": {"user_query"},
        "types": {"user_query": str}
    },
    "verify_company_registry": {
        "required": {"company_name"},
        "types": {"company_name": str}
    }
}


def validate_tool_args(tool_name: str, args: dict) -> tuple[bool, str, Optional[dict]]:
    """Validate tool args: check required keys and types. Returns (is_valid, error_message, validated_args).
       If validation passes, validated_args contains typed fields; otherwise None."""
    # Try Pydantic model validation first
    model = TOOL_ARG_MODELS.get(tool_name)
    if model:
        try:
            parsed = model.model_validate(args or {})
            return True, "", parsed.model_dump()
        except ValidationError as ve:
            # return first error string
            return False, str(ve), None

    # fallback to older schema validation if no model exists
    schema = TOOL_ARG_SCHEMAS.get(tool_name)
    if not schema:
        return False, f"No arg schema registered for tool '{tool_name}'", None

    required = schema.get("required", set())
    types_map = schema.get("types", {})

    # Check required keys
    missing = required - set(args.keys())
    if missing:
        return False, f"Missing required args: {', '.join(sorted(missing))}", None

    # Check types
    for k, expected in types_map.items():
        val = args.get(k)
        if val is None:
            continue
        if not isinstance(val, expected):
            return False, f"Arg '{k}' expected type {expected.__name__} but got {type(val).__name__}", None

    return True, "", args

def process_query_with_agent(user_query: str) -> dict:
    """
    The main Agent function that decides on tool usage and executes the final logic.
    """
    # No direct SDK client dependency here; use the provider-agnostic `generate_content` wrapper

    # 1. Initial Call: Ask the LLM to decide on a tool
    try:
        # Use LLM provider wrapper; provider might be Groq, Gemini, etc.
        # Provide tools to the LLM so that Groq-style providers can be instructed
        response = generate_content(user_query, model=settings.RAG_MODEL, tools=tools)
    except Exception as e:
        # Replaces temporary debug print with a controlled return
        logger.exception("Agent execution error: %s", e)
        log_interaction("ERROR", user_query, {"error": str(e)})
        # log_interaction(user_query, "Error", {"message": str(e)}) 
        return {"final_answer": "Agent system error. Please check configuration.", "used_tools": []}

    # 2. Check for Tool Calls
    if getattr(response, 'function_calls', None):
        tool_results = {}
        tool_errors: list[str] = []
        used_tools: list[str] = []
        
        # Execute all tool calls requested by the model
        for call in response.function_calls:
            # Support multiple call formats: object with attributes (e.g., Gemini SDK) or dict (Groq JSON)
            if isinstance(call, dict):
                tool_name = call.get('tool') or call.get('name')
                tool_args = dict(call.get('args') or {})
            else:
                tool_name = getattr(call, 'name', None)
                try:
                    tool_args = dict(getattr(call, 'args', {}))
                except Exception:
                    tool_args = {}

            function_to_call = tools.get(tool_name)

            if function_to_call:
                # Check circuit breaker for tool
                if tool_cb.is_open(tool_name):
                    logger.warning("Skipping tool %s because its circuit breaker is open", tool_name)
                    err_result = {"error": "Circuit breaker open"}
                    tool_results[tool_name] = err_result
                    tool_errors.append(f"{tool_name}: Circuit breaker open")
                    used_tools.append(tool_name)
                    continue
                # Validate args before execution
                is_valid, err, validated_args = validate_tool_args(tool_name, tool_args)
                if not is_valid:
                    logger.warning("Tool args invalid for %s: %s", tool_name, err)
                    err_result = {"error": f"Invalid args: {err}"}
                    tool_results[tool_name] = err_result
                    tool_errors.append(f"{tool_name}: {err}")
                    # record attempted tool
                    used_tools.append(tool_name)
                else:
                        logger.debug("Executing tool %s with args %s", tool_name, tool_args)
                        try:
                            result = function_to_call(**validated_args)
                        except Exception as e:
                            logger.exception("Tool execution %s failed: %s", tool_name, e)
                            err_result = {"error": str(e)}
                            tool_results[tool_name] = err_result
                            tool_errors.append(f"{tool_name}: {err_result['error']}")
                            try:
                                log_interaction("TOOL_CALL", user_query, {"tool": tool_name, "result": err_result})
                            except Exception:
                                logger.exception("Failed to log tool execution for %s", tool_name)
                            # record attempted tool
                            used_tools.append(tool_name)
                        else:
                            tool_results[tool_name] = result
                            used_tools.append(tool_name)
                            try:
                                log_interaction("TOOL_CALL", user_query, {"tool": tool_name, "result": result})
                            except Exception:
                                logger.exception("Failed to log tool execution for %s", tool_name)

        # 3. Final Call: Send tool results back to the LLM for final synthesis
        
        # Build a simple, provider-agnostic string for final synthesis
        tool_output_lines = []
        for tool_name, result in tool_results.items():
            tool_output_lines.append(f"{tool_name}: {result}")
        tool_output_text = "\n".join(tool_output_lines)
        combined_prompt = f"{user_query}\n\nTOOL_OUTPUTS:\n{tool_output_text}"
        # Final LLM synthesis: use the configured provider again (supports Groq/Gemini)
        final_response = generate_content(combined_prompt, model=settings.RAG_MODEL)

        return {
            "final_answer": getattr(final_response, 'text', str(final_response)),
            "used_tools": list(tool_results.keys()),
            "tool_errors": tool_errors
        }
        
    # 4. No Tool Call: Direct answer (General Knowledge/Chat)
    return {
        "final_answer": response.text,
        "used_tools": [],
        "tool_errors": []
    }
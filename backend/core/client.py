import os
import sys
from dotenv import load_dotenv
from litellm import completion

# Ensure dotenv is loaded quietly
load_dotenv()

# Configuration from environment
ACTIVE_MODEL_LOW = os.environ.get("ACTIVE_MODEL_LOW", "gemini/gemini-1.5-flash")
ACTIVE_MODEL_HIGH = os.environ.get("ACTIVE_MODEL_HIGH", "claude-3-5-sonnet-20240620")

# Silence LiteLLM logging unless needed
import litellm
litellm.set_verbose = False

def generate_with_fallback(system_prompt, messages, tools=None, model_tier="high", max_tokens=1000):
    """
    Unified generation wrapper with provider fallback support via LiteLLM.
    - model_tier="low": Uses ACTIVE_MODEL_LOW (fast/cheap).
    - model_tier="high": Uses ACTIVE_MODEL_HIGH with fallback logic.
    """
    
    # Prepare messages in OpenAI format (which LiteLLM expects)
    formatted_messages = []
    if system_prompt:
        formatted_messages.append({"role": "system", "content": system_prompt})
    formatted_messages.extend(messages)

    if model_tier == "low":
        try:
            return completion( # type: ignore
                model=ACTIVE_MODEL_LOW,
                messages=formatted_messages,
                max_tokens=max_tokens,
                tools=tools
            )
        except Exception as e:
            print(f"Error in low-tier generation ({ACTIVE_MODEL_LOW}): {e}")
            raise

    # High-tier generation with fallbacks
    # Prioritized sequence for high tier
    models_to_try = [
        ACTIVE_MODEL_HIGH,
        "claude-3-5-sonnet-20240620",
        "gemini/gemini-1.5-pro",
        "groq/llama-3.3-70b-versatile"
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    models_to_try = [x for x in models_to_try if not (x in seen or seen.add(x))]

    last_error = None
    for model in models_to_try:
        if not _has_api_key(model):
            continue
            
        try:
            return completion( # type: ignore
                model=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                tools=tools
            )
        except Exception as e:
            print(f"  (Fallback) Model {model} failed: {e}")
            last_error = e
            continue

    raise Exception(f"Critical: All high-tier model fallbacks failed. Last error: {last_error}")

def _has_api_key(model):
    """Check if the environment has the required key for a given model prefix."""
    if "claude" in model:
        return os.environ.get("CLAUDE_API") or os.environ.get("ANTHROPIC_API_KEY")
    if "gemini" in model:
        return os.environ.get("GEMINI_API_KEY")
    if "groq" in model:
        return os.environ.get("GROQ_API_KEY")
    # For any other model, assume LiteLLM can find the key (or it doesn't need one)
    return True

# Constants for backward compatibility during migration
MODEL = ACTIVE_MODEL_HIGH
def get_client():
    return None # Commands will be refactored to use generate_with_fallback

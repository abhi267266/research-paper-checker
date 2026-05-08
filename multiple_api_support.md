# Support Gemini & Groq with Two-Tier "Architectural Memory"

This plan implements multi-provider support (Anthropic, Gemini, Groq) using **LiteLLM** and introduces a highly token-efficient, two-tier model approach for codebase context. Instead of sending raw code context on every request, we will generate a one-time "Architectural Memory" summary.

## Core Strategy: The Two-Tier Pass

We will utilize two environment variables to control model selection:
1. **`ACTIVE_MODEL_LOW`**: Used for fast, cheap pre-processing (e.g., `gemini/gemini-1.5-flash` or `claude-3-haiku`).
2. **`ACTIVE_MODEL_HIGH`**: Used for the high-quality humanization and evaluation tasks (e.g., `claude-3-5-sonnet`, `gemini/gemini-1.5-pro`, or `groq/llama-3.1-70b-versatile`).

**The "Architectural Memory" Flow:**
- Before processing the paper, the tool runs a one-time **Pre-Pass**.
- It extracts raw codebase data and sends it to `ACTIVE_MODEL_LOW` to generate a **500-word High-Density Architecture Summary**.
- This summary acts as the "Memory" and is injected into the system prompt for all subsequent requests to `ACTIVE_MODEL_HIGH`. This reduces the context size per sentence from ~12,000 characters to just ~2,500 characters (~500 words).

## User Review Required

> [!IMPORTANT]
> - You will need to set `ACTIVE_MODEL_LOW` and `ACTIVE_MODEL_HIGH` in your `.env`. 
> - If `ACTIVE_MODEL_HIGH` fails or hits rate limits, the system will automatically fall back to the other available providers which will be provided by env as `FALLBACK_MODELS` it will conten a list of models separated by comma for high and low both it will use active model as first priority and then fallback models.
> - Tool schemas in `templates.py` will be migrated to the standard OpenAI/LiteLLM `parameters` format.

## Proposed Changes

### 1. Dependencies
#### [MODIFY] [requirements.txt](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/requirements.txt)
- Add `litellm`, `google-genai`, and `groq`.
- Remove `anthropic`.

### 2. Core Logic & Two-Tier Wrapper
#### [MODIFY] [client.py](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/core/client.py)
- Implement `generate_with_fallback(system_prompt, messages, tools=None, model_tier="high")`.
- If `model_tier="low"`, it uses `ACTIVE_MODEL_LOW`.
- If `model_tier="high"`, it uses `ACTIVE_MODEL_HIGH` with provider fallback logic (Claude -> Gemini -> Groq).

#### [MODIFY] [extractor.py](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/core/extractor.py)
- Add a new function `get_architectural_memory(codebase_path)`.
- This function first does a "smart extraction" (exported types only, no tests).
- It then calls `ACTIVE_MODEL_LOW` to condense that extraction into a persistent 500-word summary of the project's architecture, key entities, and "developer voice" moments.

#### [MODIFY] [templates.py](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/prompts/templates.py)
- Add `ARCHITECTURAL_SUMMARY_PROMPT` to guide the pre-pass.
- Update existing tool definitions (`SCORING_TOOLS`, etc.) to the OpenAI/LiteLLM format.

### 3. Command Refactoring
#### [MODIFY] [humanize.py](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/commands/humanize.py)
#### [MODIFY] [check.py](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/commands/check.py)
#### [MODIFY] [detect_ai_phrases.py](file:///Users/abhishekpathak/Documents/codebase/research-paper-humanizere/backend/commands/detect_ai_phrases.py)
- At the start of `execute()`, call `get_architectural_memory()` once.
- Pass this memory into the subsequent `generate_with_fallback()` calls using `ACTIVE_MODEL_HIGH`.
- Standardize tool and text response parsing for LiteLLM.

## Verification Plan

### Automated Tests
- `pytest backend/tests/` to ensure the new two-tier flow doesn't break existing logic.

### Manual Verification
1. **Memory Test:** Verify that the "Pre-Pass" runs exactly once and generates a coherent architectural summary.
2. **Fallback Test:** Unset `CLAUDE_API` and verify `ACTIVE_MODEL_HIGH` correctly falls back from Claude to Gemini/Groq while still using the cached "Memory" from the pre-pass.
3. **Token Usage:** Compare token counts before and after. The goal is a ~70% reduction in context tokens per sentence.

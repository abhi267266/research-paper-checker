import os
import litellm
from dotenv import load_dotenv

load_dotenv()

models = [
    "gemini/gemini-1.5-flash",
    "gemini/gemini-1.5-flash-latest",
    "gemini/gemini-1.5-flash-001",
    "gemini/gemini-1.5-flash-002",
    "gemini/gemini-1.5-pro",
    "gemini/gemini-1.5-pro-latest",
    "gemini/gemini-1.5-pro-001",
    "gemini/gemini-1.5-pro-002"
]

for m in models:
    try:
        response = litellm.completion( # type: ignore
            model=m,
            messages=[{"role": "user", "content": "say hi"}],
            max_tokens=10
        )
        print(f"SUCCESS: {m}")
    except Exception as e:
        print(f"FAILED: {m} -> {e}")

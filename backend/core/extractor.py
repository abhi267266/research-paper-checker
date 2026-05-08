import os
import re
from core.client import generate_with_fallback
from prompts.templates import ARCHITECTURAL_SUMMARY_PROMPT

def extract_codebase_context(codebase_path):
    """
    Performs a 'smart' extraction of the codebase:
    - Truncated README
    - Exported Go functions and structs only
    - Skips test files
    """
    if not codebase_path or not os.path.isdir(codebase_path):
        return ""
    
    extracted = []
    
    # 1. README (Truncated)
    readme_path = os.path.join(codebase_path, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
                extracted.append("--- README.md (Summary) ---")
                extracted.append(content[:500]) # Shrink to 500 chars
        except Exception:
            pass
            
    # 2. Source Files (Exported only, skip tests)
    go_files = []
    for root, dirs, files in os.walk(codebase_path):
        for file in files:
            if file.endswith(".go") and not file.endswith("_test.go"):
                go_files.append(os.path.join(root, file))
                
    for filepath in go_files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Match exported symbols only (Capitalized)
                funcs = re.findall(r'func\s+([A-Z][A-Za-z0-9_]+)\s*\(.*?\)', content)
                structs = re.findall(r'type\s+([A-Z][A-Za-z0-9_]+)\s+struct', content)
                
                if funcs or structs:
                    extracted.append(f"--- {os.path.basename(filepath)} ---")
                    if funcs: extracted.append("Exported Functions: " + ", ".join(funcs[:10]))
                    if structs: extracted.append("Exported Structs: " + ", ".join(structs[:10]))
        except Exception:
            pass
            
        total_len = sum(len(x) for x in extracted)
        if total_len > 4000: # Lowered ceiling from 12k to 4k
            break
            
    return "\n".join(extracted)[:4000]

def get_architectural_memory(codebase_path):
    """
    Generates a high-density architectural summary using the LOW tier model.
    This summary is cached and used for all humanization prompts.
    """
    raw_context = extract_codebase_context(codebase_path)
    if not raw_context:
        return "No codebase context available."

    print("🧠 Generating Architectural Memory (using low-tier model)...")
    
    try:
        response = generate_with_fallback(
            system_prompt=ARCHITECTURAL_SUMMARY_PROMPT,
            messages=[{"role": "user", "content": f"Here is the raw codebase extraction:\n\n{raw_context}"}],
            model_tier="low",
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Warning: Could not generate architectural memory: {e}. Falling back to raw context.")
        return raw_context[:2000]

import sys
import random
import json
from core.client import generate_with_fallback
from core.document import load_document
from prompts.templates import PLAGIARISM_CHECK_PROMPT, PLAGIARISM_TOOLS

def execute(args):
    _, sections = load_document(args.input)
    
    paragraphs_text = []
    
    main_content_started = False
    for section in sections:
        heading = section["heading"].lower()
        if "introduction" in heading or "full text" in heading:
            main_content_started = True
            
        if not main_content_started:
            continue
            
        for p in section["paragraphs"]:
            t = p.text.strip()
            if len(t) > 50: 
                paragraphs_text.append(t)
                
    if not paragraphs_text:
        print("No valid main-content paragraphs found to analyze.")
        sys.exit(0)
        
    print(f"Loaded {len(paragraphs_text)} main paragraphs. Sampling for token efficiency...")
    
    sample_size = min(len(paragraphs_text), max(20, int(len(paragraphs_text) * 0.15)))
    random.seed(42)  
    samples = random.sample(paragraphs_text, sample_size)
    
    eval_text = "\n\n---\n\n".join(samples)
    
    print("Submitting text analysis for plagiarism evaluation...")
    try:
        response = generate_with_fallback(
            system_prompt=PLAGIARISM_CHECK_PROMPT,
            messages=[{"role": "user", "content": f"Please evaluate the following document extracts for internal inconsistency or standard plagiarism markers:\n\n{eval_text}"}],
            tools=PLAGIARISM_TOOLS,
            model_tier="high",
            max_tokens=1000
        )
        
        if response and response.choices[0].message.tool_calls:
            for tc in response.choices[0].message.tool_calls:
                if tc.function.name == "report_plagiarism":
                    args_data = json.loads(tc.function.arguments)
                    score = args_data.get("score", 0)
                    reason = args_data.get("reason", "No reason provided.")
                    print("\n" + "━" * 35)
                    print(f"Plagiarism Score: {score}%")
                    print(f"Reason: {reason}")
                    print("━" * 35 + "\n")
                    return
                
        print("Error: Model did not return the expected tool call format.")
    except Exception as e:
        print(f"API Error evaluating plagiarism: {e}")

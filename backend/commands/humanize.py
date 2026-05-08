import time
import json
import sys
from core.client import generate_with_fallback
from core.document import load_document, save_document, split_sentences
from core.extractor import get_architectural_memory
from prompts.templates import SCORING_PROMPT, SCORING_TOOLS, HUMANIZATION_PROMPT

def execute(args):
    # 1. One-time architectural memory generation (Low tier)
    architectural_memory = get_architectural_memory(args.codebase)
    
    doc, sections = load_document(args.input)
    
    total_sentences_count = 0
    flagged_count = 0
    humanized_count = 0
    
    main_content_started = False
    
    for sect_idx, section in enumerate(sections, 1):
        heading = section["heading"].lower()
        
        if "introduction" in heading or "full text" in heading:
            main_content_started = True

        if not main_content_started:
            print(f"Skipping pre-intro section {sect_idx}/{len(sections)}: {section['heading'][:30]}...")
            continue
            
        paragraphs = section["paragraphs"]
        
        section_sentences = []
        for p in paragraphs:
            if not p.text.strip():
                continue
            for s in split_sentences(p.text):
                section_sentences.append({"paragraph": p, "text": s, "score": None, "new_text": None})
                
        if not section_sentences:
            continue
            
        total_sentences_count += len(section_sentences)
        
        batch_size = 15
        batches = [section_sentences[i:i + batch_size] for i in range(0, len(section_sentences), batch_size)]
        
        for batch_idx, batch in enumerate(batches, 1):
            print(f"Processing section {sect_idx}/{len(sections)}: {section['heading'][:30]}... — batch {batch_idx}/{len(batches)}...")
            
            sys_scoring = SCORING_PROMPT.format(heading_name=section['heading'])
            user_content = "Evaluate each of the following sentences. Please invoke the `evaluate_sentence` tool EXACTLY ONCE FOR EACH SENTENCE, maintaining the sequence.\n\n"
            for i, item in enumerate(batch, 1):
                user_content += f"[{i}] {item['text']}\n"
                
            retry = 3
            response = None
            while retry >= 0:
                try:
                    time.sleep(1)
                    response = generate_with_fallback(
                        system_prompt=sys_scoring,
                        messages=[{"role": "user", "content": user_content}],
                        tools=SCORING_TOOLS,
                        model_tier="high",
                        max_tokens=2048
                    )
                    break
                except Exception as e:
                    if retry > 0:
                        retry -= 1
                        print(f"Rate limit hit. Sleeping 15s. Retries left: {retry}")
                        time.sleep(15)
                    else:
                        print(f"  Warning: Batch scoring failed after retry: {e}")
            
            if response and response.choices[0].message.tool_calls:
                tool_calls = response.choices[0].message.tool_calls
                
                for item, tc in zip(batch, tool_calls):
                    try:
                        args_data = json.loads(tc.function.arguments)
                        score = args_data.get("score")
                        item["score"] = score
                        
                        if score is not None and score >= args.threshold:
                            flagged_count += 1
                            
                            h_retry = 3
                            while h_retry >= 0:
                                time.sleep(1)
                                try:
                                    sys_humanizer = HUMANIZATION_PROMPT.format(
                                        heading_name=section['heading'], 
                                        codebase_context=architectural_memory
                                    )
                                    humanize_resp = generate_with_fallback(
                                        system_prompt=sys_humanizer,
                                        messages=[{"role": "user", "content": f"Rewrite this sequence:\n\n{item['text']}"}],
                                        model_tier="high",
                                        max_tokens=1024
                                    )
                                    
                                    new_text = humanize_resp.choices[0].message.content
                                    if new_text:
                                        item["new_text"] = new_text.strip()
                                        humanized_count += 1
                                    break
                                except Exception as e:
                                    if h_retry > 0:
                                        h_retry -= 1
                                        print(f"Humanize rate limit. Sleeping 30s. Retries left: {h_retry}")
                                        time.sleep(30)
                                    else:
                                        print(f"  Warning: Humanization failed: {e}")
                    except Exception as e:
                        print(f"  Warning: Could not parse tool call: {e}")
                            
        for p in paragraphs:
            para_items = [s for s in section_sentences if s["paragraph"] == p]
            if not para_items:
                continue
            
            new_para_text = p.text
            for item in para_items:
                if item["new_text"]:
                    new_para_text = new_para_text.replace(item["text"], item["new_text"], 1)
            
            p.text = new_para_text
                
    save_document(args.out, args.input.endswith(".docx"), doc, sections)
                    
    print("\n" + "━" * 35)
    print("✓ Humanization Complete")
    print(f"  Total sentences evaluated: {total_sentences_count}")
    percentage = (flagged_count / total_sentences_count * 100) if total_sentences_count else 0
    print(f"  Flagged           : {flagged_count}  ({int(percentage)}%)")
    print(f"  Humanized         : {humanized_count}")
    print(f"  Saved to          : {args.out}")
    print("━" * 35 + "\n")

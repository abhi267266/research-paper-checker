import time
import sys
from core.client import generate_with_fallback
from core.document import load_document, save_document, split_sentences
from core.extractor import get_architectural_memory
from prompts.templates import FIX_PLAGIARISM_PROMPT

def execute(args):
    # 1. One-time architectural memory generation (Low tier)
    architectural_memory = get_architectural_memory(args.codebase)
    
    doc, sections = load_document(args.input)
    
    total_sentences_count = 0
    fixed_count = 0
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
                section_sentences.append({"paragraph": p, "text": s, "new_text": None})
                
        if not section_sentences:
            continue
            
        total_sentences_count += len(section_sentences)
        
        for idx, item in enumerate(section_sentences, 1):
            if len(item['text'].strip()) < 40:
                print(f"  Skipping short fragment/citation: {item['text'][:20]}...")
                continue

            print(f"Fixing section {sect_idx}/{len(sections)}: {section['heading'][:30]}... — sentence {idx}/{len(section_sentences)}")
            
            time.sleep(0.5)
            try:
                sys_prompt = FIX_PLAGIARISM_PROMPT.format(codebase_context=architectural_memory)
                fix_resp = generate_with_fallback(
                    system_prompt=sys_prompt,
                    messages=[{"role": "user", "content": f"Please re-engineer this academic text for improved syntactic flow and structural variety:\n\n{item['text']}"}],
                    model_tier="high",
                    max_tokens=1024
                )
                
                new_text = fix_resp.choices[0].message.content
                if new_text:
                    item["new_text"] = new_text.strip()
                    fixed_count += 1
            except Exception as e:
                print(f"  Warning: Fix synthesis failed: {e}")
                
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
    print("✓ Plagiarism Fix Complete")
    print(f"  Sentences Restructured: {fixed_count}/{total_sentences_count}")
    print(f"  Saved to              : {args.out}")
    print("━" * 35 + "\n")

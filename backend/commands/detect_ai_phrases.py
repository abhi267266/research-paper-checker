"""
detect_ai_phrases.py
────────────────────
Scans a document page-by-page and reports which pages contain
generic AI "assistant-mode" phrases (e.g. "Sure, I will do that",
"Certainly!", "I'd be happy to help", etc.).

Strategy
────────
- Pages are approximated by grouping ~WORDS_PER_PAGE words of body text.
- Each page is sent to the high-tier model individually using a
  structured tool call so the model can flag exact phrase snippets.
- The document is NEVER modified — this is a read-only analysis pass.
"""

import sys
import time
import json

from core.client import generate_with_fallback
from core.document import load_document
from prompts.templates import AI_PHRASE_CHECK_PROMPT, AI_PHRASE_TOOLS

# Approximate number of words per "page" when splitting body text.
WORDS_PER_PAGE = 300

# Polite delay between API calls (seconds) to avoid rate-limit bursts.
API_DELAY = 0.6


# ─── helpers ─────────────────────────────────────────────────────────────────

def _collect_body_paragraphs(sections: list) -> list[str]:
    """Return a flat list of non-empty paragraph texts from all sections."""
    paras: list[str] = []
    for section in sections:
        for p in section["paragraphs"]:
            text = p.text.strip() if hasattr(p, "text") else str(p).strip()
            if text:
                paras.append(text)
    return paras


def _build_pages(paragraphs: list[str], words_per_page: int) -> list[dict]:
    """
    Group paragraphs into approximate pages by word count.

    Returns a list of dicts:
        {"page_number": int, "text": str}
    """
    pages: list[dict] = []
    page_num = 1
    word_count = 0
    buffer: list[str] = []

    for para in paragraphs:
        words = len(para.split())
        buffer.append(para)
        word_count += words

    # Flush any remaining paragraphs as the last page.
    if buffer:
        pages.append({"page_number": page_num, "text": "\n\n".join(buffer)})

    return pages


def _analyse_page(page: dict) -> tuple[bool, list[str]]:
    """
    Send one page to the model and return (found, [flagged_phrases]).
    Uses the `report_ai_phrases` tool for structured output.
    """
    response = generate_with_fallback(
        system_prompt=AI_PHRASE_CHECK_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyse the following page of document text for generic AI chatbot "
                    f"phrases. Page number: {page['page_number']}.\n\n"
                    f"---\n\n{page['text']}\n\n---"
                ),
            }
        ],
        tools=AI_PHRASE_TOOLS,
        model_tier="high",
        max_tokens=512
    )

    if response and response.choices[0].message.tool_calls:
        for tc in response.choices[0].message.tool_calls:
            if tc.function.name == "report_ai_phrases":
                try:
                    args_data = json.loads(tc.function.arguments)
                    found: bool = args_data.get("found", False)
                    phrases: list[str] = args_data.get("phrases", [])
                    return found, phrases
                except Exception:
                    continue

    return False, []


# ─── entry point ─────────────────────────────────────────────────────────────

def execute(args):
    _, sections = load_document(args.input)

    # 1. Collect all paragraph text.
    paragraphs = _collect_body_paragraphs(sections)
    if not paragraphs:
        print("No text content found in the document.")
        sys.exit(0)

    # Respect the --page-size flag (fall back to the module default).
    page_size = getattr(args, "page_size", WORDS_PER_PAGE)

    # 2. Split into pages.
    pages = _build_pages(paragraphs, page_size)

    print(f"\n📄  Loaded {len(paragraphs)} paragraphs → split into {len(pages)} pages")
    print(f"🔍  Scanning each page individually for generic AI phrases…\n")
    print("─" * 60)

    flagged_pages: list[dict] = []  # {"page_number": int, "phrases": list[str]}

    # 3. Analyse each page one at a time.
    for page in pages:
        page_num = page["page_number"]
        word_count = len(page["text"].split())

        print(f"  ▶  Page {page_num}/{len(pages)}  ({word_count} words) …", end=" ", flush=True)

        try:
            time.sleep(API_DELAY)
            found, phrases = _analyse_page(page)
        except Exception as exc:
            print(f"⚠  API error: {exc}")
            continue

        if found and phrases:
            print(f"🚨  {len(phrases)} phrase(s) flagged!")
            flagged_pages.append({"page_number": page_num, "phrases": phrases})
        else:
            print("✅  Clean")

    # 4. Print the final summary report.
    print("\n" + "━" * 60)
    if not flagged_pages:
        print("✅  No generic AI phrases detected in any page.")
    else:
        print(f"🚨  Generic AI Phrases Detected on {len(flagged_pages)} page(s):\n")
        for entry in flagged_pages:
            pn = entry["page_number"]
            print(f"  📌  Page {pn}:")
            for phrase in entry["phrases"]:
                print(f"       • \"{phrase}\"")
            print()

        # Compact page-number list for quick reference.
        page_nums = ", ".join(str(e["page_number"]) for e in flagged_pages)
        print(f"  ⚡  Affected pages: {page_nums}")
    print("━" * 60 + "\n")

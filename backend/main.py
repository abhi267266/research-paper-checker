#!/usr/bin/env python3
import argparse
from commands import humanize, check, fix, detect_ai_phrases

def main():
    parser = argparse.ArgumentParser(description="AI Humanizer & Plagiarism Checker for Research Papers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    h_parser = subparsers.add_parser("humanize", help="Rewrite AI-sounding sentences and evade detectors.")
    h_parser.add_argument("input", help="Input .docx or .txt file")
    h_parser.add_argument("--threshold", type=int, default=5, help="Score threshold for humanization (default: 5)")
    h_parser.add_argument("--out", default="humanized_output.docx", help="Output file path")
    h_parser.add_argument("--codebase", default="/Users/abhishekpathak/github.com/abhi267266/quant-backtester", help="Path to codebase for context")
    
    c_parser = subparsers.add_parser("check-plagiarism", help="Check document for standard plagiarism copying.")
    c_parser.add_argument("input", help="Input .docx or .txt file")
    
    f_parser = subparsers.add_parser("fix-plagiarism", help="Completely restructure all sentences structurally to beat plagiarism matchers.")
    f_parser.add_argument("input", help="Input .docx or .txt file")
    f_parser.add_argument("--out", default="fixed_plagiarism_output.docx", help="Output file path")
    f_parser.add_argument("--codebase", default="/Users/abhishekpathak/github.com/abhi267266/quant-backtester", help="Path to codebase for context")

    ai_parser = subparsers.add_parser(
        "check-ai-phrases",
        help="Scan document page-by-page for generic AI chatbot phrases (e.g. 'Sure!', 'Certainly!') and report page numbers."
    )
    ai_parser.add_argument("input", help="Input .docx or .txt file")
    ai_parser.add_argument(
        "--page-size", type=int, default=300,
        help="Approximate number of words per page (default: 300)"
    )

    args = parser.parse_args()
    
    if args.command == "humanize":
        humanize.execute(args)
    elif args.command == "check-plagiarism":
        check.execute(args)
    elif args.command == "fix-plagiarism":
        fix.execute(args)
    elif args.command == "check-ai-phrases":
        detect_ai_phrases.execute(args)

if __name__ == "__main__":
    main()

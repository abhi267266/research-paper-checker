import os
import sys
import re

try:
    import docx
    from docx import Document
except ImportError:
    print("Error: 'python-docx' package not found. Please install it using `pip install python-docx`.")
    sys.exit(1)

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]

def load_document(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Input file '{file_path}' not found.")
        sys.exit(1)
        
    sections = []
    doc = None
    
    if file_path.endswith(".docx"):
        doc = Document(file_path)
        current_heading = "Default Content"
        current_paras = []
        
        for para in doc.paragraphs:
            if para.style and para.style.name and para.style.name.startswith("Heading"):
                if current_paras:
                    sections.append({"heading": current_heading, "paragraphs": current_paras})
                current_heading = para.text.strip() or para.style.name
                current_paras = [para]
            else:
                current_paras.append(para)
                
        if current_paras:
            sections.append({"heading": current_heading, "paragraphs": current_paras})
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        class DummyPara:
            def __init__(self, text):
                self.text = text
        current_paras = [DummyPara(p) for p in paras]
        sections.append({"heading": "Full Text", "paragraphs": current_paras})
    else:
        print("Unsupported file format. Use .docx or .txt")
        sys.exit(1)
        
    return doc, sections

def save_document(file_path, original_is_docx, doc, sections):
    if original_is_docx:
        try:
            doc.save(file_path)
        except Exception as e:
            print(f"Error saving to {file_path}: {e}")
            sys.exit(1)
    else:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for s in sections:
                    if s["heading"] != "Full Text":
                        f.write(s["heading"] + "\n\n")
                    for p in s["paragraphs"]:
                        f.write(p.text + "\n\n")
        except Exception as e:
            print(f"Error saving to {file_path}: {e}")
            sys.exit(1)

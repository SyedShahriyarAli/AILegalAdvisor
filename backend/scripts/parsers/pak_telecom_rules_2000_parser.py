"""
Parser for The Electronic Transactions Ordinance, 2002
Extracts sections, chapters, and clauses into structured JSON format 
matching the schema of constitution-1973.json
"""

import re
import os
import sys
import pdfplumber
import json
from typing import List, Optional, Dict, Any
from statistics import median

def _line_avg_font_size(ln: Dict) -> float:
    chars = ln.get("chars") or []
    if not chars:
        return 0.0
    sizes = [(c.get("size") or c.get("font_size") or 0.0) for c in chars]
    sizes = [s for s in sizes if s]
    return (sum(sizes) / len(sizes)) if sizes else 0.0

def _is_bold_char(c: Dict) -> bool:
    fn = (c.get("fontname") or "").lower()
    return "bold" in fn or "black" in fn or fn.endswith("bd")

def _extract_bold_text(ln: Dict) -> str:
    chars = ln.get("chars") or []
    if not chars:
        return ""
    bold_chars = [c.get("text", "") for c in chars if _is_bold_char(c)]
    return "".join(bold_chars).strip()

def _find_footnote_cutoff_y(page) -> Optional[float]:
    width = page.width
    height = page.height
    candidates: List[float] = []

    for ln in getattr(page, "lines", []):
        x0, x1 = ln.get("x0", 0.0), ln.get("x1", 0.0)
        y0, y1 = ln.get("y0", 0.0), ln.get("y1", 0.0)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        if h <= 1.0 and w >= width * 0.5 and y0 > height * 0.55:
            candidates.append((y0 + y1) / 2.0)

    for rc in getattr(page, "rects", []):
        x0, y0 = rc.get("x0", 0.0), rc.get("y0", 0.0)
        w, h = rc.get("width", 0.0), rc.get("height", 0.0)
        if h <= 1.2 and w >= width * 0.5 and y0 > height * 0.55:
            candidates.append(y0)

    if not candidates:
        return None
    cutoff = min(candidates)
    return cutoff + 1.0

def _estimate_body_font_threshold(lines: List[Dict], page_height: float) -> float:
    sizes: List[float] = []
    top_band = page_height * 0.7
    for ln in lines:
        if (ln.get("top") or 0.0) < top_band:
            s = _line_avg_font_size(ln)
            if s:
                sizes.append(s)

    if not sizes:
        return 0.0
    body_med = median(sizes)
    return body_med * 0.85

def _filter_page_lines(page_data: Dict) -> List[Dict]:
    lines = page_data.get("lines") or []
    cutoff_y = page_data.get("footnote_cutoff_y")
    min_body_font = page_data.get("min_body_font", 0.0)

    filtered: List[Dict] = []
    for ln in lines:
        top = ln.get("top", 0.0) or 0.0
        if cutoff_y is not None and top >= cutoff_y:
            continue
        avg_size = _line_avg_font_size(ln)
        if min_body_font and avg_size and avg_size < min_body_font:
            continue
        filtered.append(ln)
    return filtered

def extract_with_precise_layout(pdf_path: str) -> List[Dict]:
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(
                x_tolerance=1, y_tolerance=1, keep_blank_chars=False, use_text_flow=True
            )

            lines = []
            if hasattr(page, "chars"):
                char_groups = {}
                for char in page.chars:
                    y = round(char.get("top", 0), 1)
                    if y not in char_groups:
                        char_groups[y] = []
                    char_groups[y].append(char)

                for y in sorted(char_groups.keys()):
                    chars = sorted(char_groups[y], key=lambda c: c.get("x0", 0))
                    text = "".join(c.get("text", "") for c in chars)
                    if text.strip():
                        x0 = chars[0].get("x0", 0) if chars else 0
                        x1 = chars[-1].get("x1", 0) if chars else 0
                        lines.append(
                            {"text": text, "top": y, "x0": x0, "x1": x1, "chars": chars}
                        )

            cutoff_y = _find_footnote_cutoff_y(page)
            min_body_font = _estimate_body_font_threshold(lines, page.height)

            pages_data.append(
                {
                    "page_num": page_num + 1,
                    "width": page.width,
                    "height": page.height,
                    "words": words,
                    "lines": lines,
                    "text": page.extract_text(),
                    "footnote_cutoff_y": cutoff_y,
                    "min_body_font": min_body_font,
                }
            )
    return pages_data

def detect_sections_and_chapters(pages_data: List[Dict]) -> List[Dict]:
    sections = []
    current_part = None
    
    # Matches "PART I - GENERAL" or "PART II - LICENSING"
    chapter_pattern = re.compile(r"^\s*(PART[\s\-]+[A-Z]+(?:[\s\-]+(.+))?)\s*$", re.IGNORECASE)
    section_pattern = re.compile(r"^\s*(\d+[A-Z]*)\.\s+(.+)$")

    for page_data in pages_data:
        page_num = page_data["page_num"]
        lines = _filter_page_lines(page_data)

        for i, line in enumerate(lines):
            line_text = line.get("text", "").strip()
            line_top = line.get("top", 0.0)

            # Check for Part
            chapter_match = chapter_pattern.match(line_text)
            if chapter_match:
                current_part = chapter_match.group(1).strip()
                continue

            match = section_pattern.match(line_text)
            if not match:
                continue

            # We found a section.
            section_number = match.group(1)
            
            # The CONTENTS pages list sections. We want to skip the table of contents.
            # Pakistan Telecom Rules don't have a TOC, content starts on page 1.

            bold_title = _extract_bold_text(line)
            if not bold_title:
                bold_title = match.group(2).split("—")[0].split("\n")[0][:120].strip()
            else:
                bold_title = bold_title.split("—")[0].strip()
            
            # Remove section number from title if present
            bold_title = re.sub(r"^\s*\d+[A-Z]*\.\s*", "", bold_title).strip()

            sections.append(
                {
                    "section_number": section_number,
                    "title": bold_title,
                    "page_number": page_num,
                    "part": current_part,
                    "chapter": None,
                    "line_index": i,
                    "y_position": line_top if isinstance(line_top, (int, float)) else 0.0,
                }
            )

    return sections

def clean_section_content(content: str) -> str:
    if not content:
        return ""
    cleaned = content
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = cleaned.replace("\u202f", " ")
    cleaned = cleaned.replace("\u2007", " ")
    cleaned = cleaned.replace("\u2009", " ")

    cleaned = re.sub(r"(?mi)^\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"(?mi)^\s*Page\s+\d+\s+of\s+\d+\s*$", "", cleaned)

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"(?<=[\.\!\?\:\;])\s+(?=\(\s*\d+\s*\))", "\n", cleaned)
    cleaned = re.sub(r"(?<=[\.\!\?\:\;])\s+(?=\(\s*[a-z]\s*\))", "\n", cleaned)
    
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"\s*\*+\s*", " ", cleaned)

    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\s*\)\s*", ") ", cleaned)
    cleaned = re.sub(r"\s*\(\s*", " (", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()

def extract_clauses(content: str) -> List[Dict]:
    """
    Extract subsections and clauses (like (1), (2), (a), (b)) into a flat list
    to match the structure of constitution-1973.json's 'clauses'.
    """
    clauses = []
    if not content:
        return clauses

    # Find markers like (1), (2) or (a), (b)
    pattern = re.compile(r"(?s)(?<!\w)\(\s*([0-9a-z]+)\s*\)\s+")
    matches = list(pattern.finditer(content))
    
    if not matches:
        return clauses

    for idx, m in enumerate(matches):
        clause_id = m.group(1)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        clause_text = content[start:end].strip()

        if clause_text:
            clauses.append({"id": clause_id, "text": clause_text})

    return clauses

def extract_section_content(pages_data: List[Dict], sections: List[Dict]) -> List[Dict]:
    if not sections:
        return []

    sorted_sections = sorted(sections, key=lambda x: (x["page_number"], x["line_index"]))

    for i, section in enumerate(sorted_sections):
        page_num = section["page_number"]
        line_index = section["line_index"]
        content_lines: List[str] = []

        if i + 1 < len(sorted_sections):
            next_section = sorted_sections[i + 1]
            end_page = next_section["page_number"]
            end_line_index = next_section["line_index"]
        else:
            end_page = len(pages_data)
            end_line_index = float("inf")

        page_data = pages_data[page_num - 1]
        filtered_lines = _filter_page_lines(page_data)

        if line_index < len(filtered_lines):
            header_line = filtered_lines[line_index]
            header_text = header_line.get("text", "").strip()
            
            # The text might be "1. Short title.— (1) This Act may be..."
            # Try to grab anything after the em-dash or the title.
            em_dash_idx = header_text.find("—")
            if em_dash_idx != -1:
                after_title = header_text[em_dash_idx + 1:].strip()
                if after_title:
                    content_lines.append(after_title)
            else:
                bold_title = _extract_bold_text(header_line)
                if bold_title:
                    idx = header_text.find(bold_title)
                    if idx != -1:
                        after_title = header_text[idx + len(bold_title):].strip()
                        if after_title:
                            content_lines.append(after_title)

        for page_idx in range(page_num - 1, end_page):
            if page_idx >= len(pages_data):
                break

            current_page_data = pages_data[page_idx]
            current_page_num = current_page_data["page_num"]
            filtered_lines = _filter_page_lines(current_page_data)

            start_idx = 0
            end_idx = len(filtered_lines)

            if current_page_num == page_num:
                start_idx = line_index + 1
            if current_page_num == end_page and i + 1 < len(sorted_sections):
                end_idx = end_line_index

            for j in range(start_idx, end_idx):
                line_txt = filtered_lines[j].get("text", "").strip()
                # Skip chapters headers inside content
                if re.match(r"^\s*(CHAPTER[\s\-]+[A-Z0-9]+)\s*$", line_txt, re.IGNORECASE):
                    continue
                content_lines.append(line_txt)

        raw_content = "\n".join(content_lines).strip()
        cleaned_content = clean_section_content(raw_content)

        clauses = extract_clauses(cleaned_content)
        
        if clauses:
            # First clause marker
            first_match = re.search(r"(?s)(?<!\w)\(\s*[0-9a-z]+\s*\)\s+", cleaned_content)
            if first_match:
                main_content = cleaned_content[:first_match.start()].strip()
            else:
                main_content = cleaned_content
        else:
            main_content = cleaned_content

        section["content"] = main_content
        section["clauses"] = clauses

    return sorted_sections

def parse_pak_telecom_rules(pdf_path: str) -> Dict:
    print("Extracting PDF with layout analysis...")
    pages_data = extract_with_precise_layout(pdf_path)

    print("Detecting sections...")
    sections = detect_sections_and_chapters(pages_data)
    print(f"Found {len(sections)} sections")

    print("Extracting section content...")
    sections_with_content = extract_section_content(pages_data, sections)

    output = {
        "document": {
            "title": "Pakistan Telecommunication Rules, 2000",
            "year": 2000,
            "source_file": "Pakistan Telecom Rules.pdf",
            "sections": sections_with_content,
        }
    }

    return output

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "../../data/pdfs/Pakistan telecom rules.pdf")

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)

    print("Starting Pakistan Telecom Rules 2000 parsing...")
    result = parse_pak_telecom_rules(pdf_path)

    output_path = os.path.join(script_dir, "../../data/jsons/pakistan-telecom-rules-2000.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nParsing completed! Output saved to {output_path}")

    if result["document"]["sections"]:
        print("\nSample of first section:")
        print(json.dumps(result["document"]["sections"][0], indent=2, ensure_ascii=False))

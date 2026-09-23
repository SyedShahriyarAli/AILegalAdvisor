"""
Parser for Prevention of Electronic Crimes (Amendment) Act, 2025
Extracts sections, subsections, and clauses into structured JSON format
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from statistics import median
import re
import os
import sys
import pdfplumber
import json


@dataclass
class Section:
    section_number: str
    title: str
    content: str
    page_number: int = 0
    subsections: List[Dict[str, Any]] = None
    start_y: float = 0


def _line_avg_font_size(ln: Dict) -> float:
    """Calculate average font size of a line"""
    chars = ln.get("chars") or []
    if not chars:
        return 0.0
    sizes = [(c.get("size") or c.get("font_size") or 0.0) for c in chars]
    sizes = [s for s in sizes if s]
    return (sum(sizes) / len(sizes)) if sizes else 0.0


def _is_bold_char(c: Dict) -> bool:
    """Check if a character is bold"""
    fn = (c.get("fontname") or "").lower()
    return "bold" in fn or "black" in fn or fn.endswith("bd")


def _extract_bold_text(ln: Dict) -> str:
    """Extract only bold text from a line"""
    chars = ln.get("chars") or []
    if not chars:
        return ""

    bold_chars = [c.get("text", "") for c in chars if _is_bold_char(c)]
    return "".join(bold_chars).strip()


def _find_footnote_cutoff_y(page) -> Optional[float]:
    """Detect footnote separator line near bottom of page"""
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
    """Estimate minimum font size for body text"""
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
    """Remove footnotes and small font lines"""
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
    """Extract text with precise positioning using pdfplumber"""
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(
                x_tolerance=1, y_tolerance=1, keep_blank_chars=False, use_text_flow=True
            )

            lines = []
            if hasattr(page, "chars"):
                # Group characters by y-coordinate to form lines
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


def detect_sections(pages_data: List[Dict]) -> List[Dict]:
    """Detect sections with proper title extraction"""
    sections = []

    # Pattern to match sections: "section_number. Title"
    # Handles: "2.", "2A.", "26A.", etc.
    section_pattern = re.compile(r"^\s*(\d+[A-Z]*)\.\s+(.+)$")

    for page_data in pages_data:
        page_num = page_data["page_num"]
        raw_lines = page_data["lines"]
        lines = _filter_page_lines(page_data)

        for i, line in enumerate(lines):
            line_text = line.get("text", "").strip()
            line_top = line.get("top", 0.0)

            match = section_pattern.match(line_text)
            if not match:
                continue

            section_number = match.group(1)

            # Extract bold text as title
            bold_title = _extract_bold_text(line)
            if not bold_title:
                # Fallback: use first few words if no bold text
                bold_title = match.group(2).split("\n")[0][:60]

            sections.append(
                {
                    "section_number": section_number,
                    "title": bold_title,
                    "page_number": page_num,
                    "line_index": i,
                    "y_position": line_top
                    if isinstance(line_top, (int, float))
                    else 0.0,
                }
            )

    return sections


def extract_section_content(pages_data: List[Dict], sections: List[Dict]) -> List[Dict]:
    """Extract multi-line content for each section, separating content from subsections"""
    if not sections:
        return []

    sorted_sections = sorted(
        sections, key=lambda x: (x["page_number"], x["line_index"])
    )

    for i, section in enumerate(sorted_sections):
        page_num = section["page_number"]
        line_index = section["line_index"]
        content_lines: List[str] = []

        if i + 1 < len(sorted_sections):
            next_section = sorted_sections[i + 1]
            end_page = next_section["page_number"]
            end_line_index = next_section["line_index"]
        else:
            end_page = min(page_num + 20, len(pages_data))
            end_line_index = float("inf")

        # Get the section header line to extract the part after title
        page_data = pages_data[page_num - 1]
        filtered_lines = _filter_page_lines(page_data)

        if line_index < len(filtered_lines):
            header_line = filtered_lines[line_index]
            header_text = header_line.get("text", "").strip()
            # Extract the part after the bold title
            bold_title = _extract_bold_text(header_line)
            if bold_title:
                # Find where bold title ends in the full line and get the rest
                # Look for the bold title and get everything after it
                idx = header_text.find(bold_title)
                if idx != -1:
                    after_title = header_text[idx + len(bold_title) :].strip()
                    if after_title:
                        content_lines.append(after_title)

        # Collect content from remaining lines
        for page_idx in range(page_num - 1, len(pages_data)):
            if page_idx >= len(pages_data):
                break

            current_page_data = pages_data[page_idx]
            current_page_num = current_page_data["page_num"]
            filtered_lines = _filter_page_lines(current_page_data)

            if current_page_num < page_num:
                continue
            elif current_page_num > end_page:
                break

            start_idx = 0
            end_idx = len(filtered_lines)

            if current_page_num == page_num:
                start_idx = line_index + 1  # Start from line after header
            if current_page_num == end_page and i + 1 < len(sorted_sections):
                end_idx = end_line_index

            for j in range(start_idx, end_idx):
                content_lines.append(filtered_lines[j].get("text", "").strip())

        raw_content = "\n".join(content_lines).strip()
        cleaned_content = clean_section_content(raw_content)

        # Extract subsections first
        subsections = extract_subsections(cleaned_content)

        # If subsections exist, remove them from content
        if subsections:
            # Find the position of first subsection marker
            first_subsec_pattern = re.compile(
                r"(?s)(?<!\w)(?:\(\s*\d+\s*\)|\(\s*[a-z]\s*\))\s+"
            )
            match = first_subsec_pattern.search(cleaned_content)
            if match:
                # Content is everything before first subsection
                main_content = cleaned_content[: match.start()].strip()
            else:
                main_content = cleaned_content
        else:
            main_content = cleaned_content

        section["content"] = main_content
        section["subsections"] = subsections

    return sorted_sections


def clean_section_content(content: str) -> str:
    """Clean section content while preserving structure"""
    if not content:
        return ""

    cleaned = content

    # Normalize Unicode spaces
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = cleaned.replace("\u202f", " ")
    cleaned = cleaned.replace("\u2007", " ")
    cleaned = cleaned.replace("\u2009", " ")

    # Strip page numbers and headers
    cleaned = re.sub(r"(?mi)^\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"(?mi)^\s*THE GAZETTE OF PAKISTAN.*$", "", cleaned)
    cleaned = re.sub(r"(?mi)^\s*PART [I0-9]+\s*$", "", cleaned)

    # Normalize spaces but preserve newlines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    # Insert newlines before subsection markers
    cleaned = re.sub(r"(?<=[\.\!\?\:\;])\s+(?=\(\s*\d+\s*\))", "\n", cleaned)

    # Insert newlines before lettered clauses
    cleaned = re.sub(r"(?<=[\.\!\?\:\;])\s+(?=\(\s*[a-z]\s*\))", "\n", cleaned)

    # Tidy spaces around newlines
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)

    # Remove asterisk lines
    cleaned = re.sub(r"\s*\*+\s*", " ", cleaned)

    # Punctuation spacing
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\s*\)\s*", ") ", cleaned)
    cleaned = re.sub(r"\s*\(\s*", " (", cleaned)

    # Collapse excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def extract_subsections(content: str) -> List[Dict]:
    """
    Extract subsections (numbered) and clauses (lettered).
    If subsections don't exist but lettered clauses do, treat them as subsections.
    Structure:
      (1) Subsection text...
        (a) Clause a...
        (b) Clause b...
      (2) Another subsection...
    """
    subsections: List[Dict] = []
    if not content:
        return subsections

    # First check for numbered subsections
    subsection_pattern = re.compile(r"(?s)(?<!\w)\(\s*(\d+)\s*\)\s+")
    matches = list(subsection_pattern.finditer(content))

    # If no numbered subsections, check for lettered clauses
    if not matches:
        clause_pattern = re.compile(r"(?s)(?<!\w)\(\s*([a-z])\s*\)\s+")
        matches = list(clause_pattern.finditer(content))
        if matches:
            # Treat lettered clauses as subsections
            for idx, m in enumerate(matches):
                clause_id = m.group(1)
                start = m.end()
                end = (
                    matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
                )
                clause_text = content[start:end].strip()

                if clause_text:
                    subsections.append(
                        {"id": clause_id, "text": clause_text, "clauses": []}
                    )
            return subsections

    # Process numbered subsections
    for idx, m in enumerate(matches):
        subsec_id = m.group(1)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        subsec_text = content[start:end].strip()

        # Extract clauses from subsection
        clauses = extract_clauses_from_subsection(subsec_text)

        if clauses:
            clause_pattern = re.compile(r"(?s)(?<!\w)\(\s*[a-z]\s*\)\s+")
            first_clause = clause_pattern.search(subsec_text)
            if first_clause:
                subsec_text = subsec_text[:first_clause.start()].strip()

        subsections.append({"id": subsec_id, "text": subsec_text, "clauses": clauses})

    return subsections


def extract_clauses_from_subsection(subsec_text: str) -> List[Dict]:
    """Extract lettered clauses from subsection text"""
    clauses: List[Dict] = []
    if not subsec_text:
        return clauses

    # Match clause markers: (a), (b), (c), etc.
    clause_pattern = re.compile(r"(?s)(?<!\w)\(\s*([a-z])\s*\)\s+")

    matches = list(clause_pattern.finditer(subsec_text))
    if not matches:
        # No lettered clauses found
        return clauses

    for idx, m in enumerate(matches):
        clause_id = m.group(1)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(subsec_text)
        clause_text = subsec_text[start:end].strip()

        if clause_text:
            clauses.append({"id": clause_id, "text": clause_text})

    return clauses


def validate_and_order_sections(sections: List[Dict]) -> List[Dict]:
    """Validate section sequence and ordering"""
    if not sections:
        return []

    def section_key(section):
        num_str = section["section_number"]
        numeric_part = int("".join(filter(str.isdigit, num_str)) or 0)
        alpha_part = "".join(filter(str.isalpha, num_str))
        return (numeric_part, alpha_part)

    sorted_sections = sorted(sections, key=section_key)

    section_numbers = []
    for section in sorted_sections:
        try:
            num = int("".join(filter(str.isdigit, section["section_number"])))
            section_numbers.append(num)
        except:
            continue

    print(f"Found sections: {sorted(set(section_numbers))}")

    return sorted_sections


def parse_peca_act(pdf_path: str) -> Dict:
    """Main parsing function for PECA Act 2025"""

    print("Extracting PDF with layout analysis...")
    pages_data = extract_with_precise_layout(pdf_path)

    print("Detecting sections...")
    sections = detect_sections(pages_data)

    print(f"Found {len(sections)} sections")

    print("Validating section sequence...")
    validated_sections = validate_and_order_sections(sections)

    print("Extracting section content...")
    sections_with_content = extract_section_content(pages_data, validated_sections)

    # Create final structured output
    output = {
        "document": {
            "title": "Prevention of Electronic Crimes (Amendment) Act, 2025",
            "year": 2025,
            "act_number": "ACT NO. II OF 2025",
            "source_file": "PECA Amendment, 2025.pdf",
            "sections": sections_with_content,
        }
    }

    return output


def validate_parsing_result(parsed_data: Dict) -> Dict:
    """Validate the parsing results"""
    sections = parsed_data["document"]["sections"]

    section_numbers = []
    for section in sections:
        try:
            num = int("".join(filter(str.isdigit, section["section_number"])))
            section_numbers.append(num)
        except:
            continue

    validation_report = {
        "total_sections_found": len(sections),
        "section_numbers_range": (
            min(section_numbers) if section_numbers else 0,
            max(section_numbers) if section_numbers else 0,
        ),
        "sections_with_subsections": len([s for s in sections if s.get("subsections")]),
        "total_subsections": sum(len(s.get("subsections", [])) for s in sections),
        "validation_notes": [],
    }

    return validation_report


# Execute the parsing
if __name__ == "__main__":
    import sys
    import os

    # Use absolute path relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "../../data/pdfs/Peca-Act-2025.pdf")

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)

    print("Starting PECA Act 2025 parsing...")
    result = parse_peca_act(pdf_path)

    # Validate results
    validation = validate_parsing_result(result)
    print("\nValidation Report:")
    print(json.dumps(validation, indent=2))

    # Save results - use absolute path
    output_path = os.path.join(script_dir, "../../data/jsons/peca-amendment-2025.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nParsing completed! Output saved to {output_path}")

    # Print sample of first section
    if result["document"]["sections"]:
        print("\nSample of first section:")
        print(
            json.dumps(result["document"]["sections"][0], indent=2, ensure_ascii=False)
        )

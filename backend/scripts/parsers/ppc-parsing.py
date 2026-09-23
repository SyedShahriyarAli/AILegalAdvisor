from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from statistics import median
import re
import pdfplumber
import json


@dataclass
class Article:
    article_number: str
    title: str
    content: str
    chapter: Optional[str] = None
    part: Optional[str] = None
    page_number: int = 0
    clauses: List[Dict[str, str]] = None
    start_y: float = 0  # For validation


def _line_avg_font_size(ln: Dict) -> float:
    chars = ln.get("chars") or []
    if not chars:
        return 0.0
    sizes = [(c.get("size") or c.get("font_size") or 0.0) for c in chars]
    sizes = [s for s in sizes if s]
    return (sum(sizes) / len(sizes)) if sizes else 0.0


def _line_bold_text(ln: Dict) -> str:
    """
    Build a string using only bold glyphs, but reconstruct spaces based
    on character gaps and preserve actual space characters.
    """
    chars = ln.get("chars") or []
    if not chars:
        # Fallback to full text if chars missing
        return (ln.get("text") or "").strip()

    def is_bold_char(c: Dict) -> bool:
        fn = (c.get("fontname") or "").lower()
        return "bold" in fn or "black" in fn or fn.endswith("bd")

    result_parts = []
    current_word = []

    for i, c in enumerate(chars):
        text = c.get("text", "")

        # If it's a space character, add it directly
        if text.isspace():
            if current_word:
                result_parts.append("".join(current_word))
                current_word = []
            if not result_parts or result_parts[-1] != " ":
                result_parts.append(" ")
        elif is_bold_char(c):
            current_word.append(text)
        else:
            # Non-bold character - check if we need to add space based on position
            if current_word:
                # Check gap between this and previous bold character
                prev_bold_idx = None
                for j in range(i - 1, -1, -1):
                    if is_bold_char(chars[j]):
                        prev_bold_idx = j
                        break

                if prev_bold_idx is not None:
                    prev_char = chars[prev_bold_idx]
                    curr_x = float(c.get("x0", 0))
                    prev_x = float(prev_char.get("x1", 0))
                    gap = curr_x - prev_x
                    font_size = float(c.get("size", 12))

                    # If gap is significant, add the current word and a space
                    if gap > font_size * 0.3:
                        result_parts.append("".join(current_word))
                        current_word = []
                        if not result_parts or result_parts[-1] != " ":
                            result_parts.append(" ")

    # Add any remaining word
    if current_word:
        result_parts.append("".join(current_word))

    # Join and clean up
    result = "".join(result_parts).strip()
    return re.sub(r"\s+", " ", result)


def _find_footnote_cutoff_y(page) -> Optional[float]:
    """
    Detect a horizontal rule near the bottom of the page and return its y,
    so everything below it can be ignored.
    """
    width = page.width
    height = page.height
    candidates: List[float] = []

    # Vector lines (thin strokes)
    for ln in getattr(page, "lines", []):
        x0, x1 = ln.get("x0", 0.0), ln.get("x1", 0.0)
        y0, y1 = ln.get("y0", 0.0), ln.get("y1", 0.0)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        # Horizontal, long, near bottom half
        if h <= 1.0 and w >= width * 0.5 and y0 > height * 0.55:
            candidates.append((y0 + y1) / 2.0)

    # Thin rects also show up as rules
    for rc in getattr(page, "rects", []):
        x0, y0 = rc.get("x0", 0.0), rc.get("y0", 0.0)
        w, h = rc.get("width", 0.0), rc.get("height", 0.0)
        if h <= 1.2 and w >= width * 0.5 and y0 > height * 0.55:
            # y of a rect is its top
            candidates.append(y0)

    if not candidates:
        return None

    # Choose the uppermost rule within the bottom band (ignore anything too low like page border)
    # We want the first rule that typically separates footnotes: pick the smallest y among candidates
    # that are still in the lower portion (>= 60% page height), then keep a small safety margin.
    cutoff = min(candidates)
    return cutoff + 1.0


def _estimate_body_font_threshold(lines: List[Dict], page_height: float) -> float:
    """
    Estimate a conservative minimum font size for body text using lines from the top 70% of the page.
    Footnotes are typically smaller and near the bottom.
    """
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
    # Treat anything < 85% of median as too small (likely footnote)
    return body_med * 0.85


def _filter_page_lines(page_data: Dict) -> List[Dict]:
    """
    Remove lines below the footnote cutoff and lines with very small font sizes.
    """
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
                lines = page.extract_text_lines()

            # Detect a horizontal footnote rule and font threshold for this page
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


def detect_articles(pages_data: List[Dict]) -> List[Dict]:
    """Detect articles with proper title extraction (supports multi-line titles and article variants A-Z)"""
    articles = []
    # Enhanced pattern to capture article variants in both formats:
    # - Direct format: 63A, 496B, 310C (without hyphen)
    # - Hyphenated format: 225-A, 225-B (with hyphen)
    # - Split format: "225-" on one line, "A. title" on next line
    # Only matches single uppercase letters after numbers to avoid false positives
    article_pattern = re.compile(
        r"^\s*(?:\[\s*){0,3}\(?\s*(\d+(?:-?[A-Z]+)?)\s*\.\s*(.*)"
    )

    # Pattern for split articles where letter appears on separate line
    # More flexible patterns to handle various whitespace and formatting
    # Pattern 1: "225-" alone on a line (original)
    split_number_pattern = re.compile(r"^\s*(\d+\s*-)\s*$")
    # Pattern 2: "225- Title text..." where the title continues on the line
    split_number_with_text_pattern = re.compile(r"^\s*(\d+\s*-)\s+(.+)")
    split_letter_pattern = re.compile(r"^\s*([A-Z])\s*\.\s*(.*)")

    current_part = None
    current_chapter = None

    BOLD_MIN_FOR_TITLE = (
        0.18  # Require at least this much bold to treat a line as a title line
    )

    def line_metrics(ln: Dict) -> Dict[str, Any]:
        txt = ln.get("text", "").strip()
        chars = ln.get("chars") or []
        avg_size = _line_avg_font_size(ln)
        bold_ratio = 0.0
        if chars:
            bold_hits = 0
            for c in chars:
                fn = (c.get("fontname") or "").lower()
                if "bold" in fn or "black" in fn or fn.endswith("bd"):
                    bold_hits += 1
            bold_ratio = bold_hits / len(chars)
        letters = [ch for ch in txt if ch.isalpha()]
        caps_ratio = (
            (sum(1 for ch in letters if ch.isupper()) / len(letters))
            if letters
            else 0.0
        )
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", txt)
        titlecase_ratio = (
            (
                sum(
                    1
                    for w in words
                    if (w.isupper() or (w[0].isupper() and w[1:].islower()))
                )
                / len(words)
            )
            if words
            else 0.0
        )
        return {
            "text": txt,
            "top": ln.get("top", 0.0),
            "x0": ln.get("x0", 0.0),
            "x1": ln.get("x1", 0.0),
            "avg_size": avg_size,
            "bold_ratio": bold_ratio,
            "caps_ratio": caps_ratio,
            "titlecase_ratio": titlecase_ratio,
        }

    # Helper for short parenthetical continuation like "(Parliament)"
    def looks_parenthetical_heading(txt: str) -> bool:
        t = txt.strip()
        return (
            t.startswith("(")
            and t.endswith(")")
            and len(t) <= 60
            and not re.search(r"\d", t)
        )

    for page_data in pages_data:
        page_num = page_data["page_num"]
        raw_lines = page_data["lines"]
        # Filter out footnotes and tiny-font lines
        lines = _filter_page_lines(page_data)

        skip_next = False  # Flag to skip next line when processing split articles
        in_omitted_section = False  # Flag to track if we're in an omitted articles section
        
        for i, line in enumerate(lines):
            # Skip this line if it was already processed as part of a split article
            if skip_next:
                skip_next = False
                continue
            line_text = line.get("text", "").strip()
            line_top = line.get("top", 0.0)

            # Check if this line indicates start of omitted section
            if re.search(r'following was omitted|following was repealed', line_text, re.IGNORECASE):
                in_omitted_section = True
                continue
            
            # Reset omitted section flag if we see a new CHAPTER or normal article flow
            if line_text.startswith("CHAPTER ") and not in_omitted_section:
                in_omitted_section = False

            if line_text.startswith("PART "):
                current_part = line_text
                in_omitted_section = False
            elif line_text.startswith("CHAPTER "):
                current_chapter = line_text
                # Don't reset in_omitted_section here as omitted articles can be in a chapter

            match = article_pattern.match(line_text)
            
            # Also check for articles that appear mid-line after punctuation
            # e.g., "Pakistan. 237. Import or export..."
            if not match and re.search(r'\.\s+\d+\.\s+', line_text):
                # Split on sentence endings and try to match each part
                parts = re.split(r'(?<=[.!?])\s+(?=\d+\.)', line_text)
                for part_idx, part in enumerate(parts):
                    part_match = article_pattern.match(part)
                    if part_match:
                        match = part_match
                        break
            
            if not match:
                # Check for split article format where number ends with hyphen and letter is on next line
                # Try pattern 1: "225-" alone on a line
                split_match = split_number_pattern.match(line_text)
                # Try pattern 2: "225- Title text..." where title continues on same line
                split_match_with_text = split_number_with_text_pattern.match(line_text)
                
                if split_match or split_match_with_text:
                    if split_match:
                        number_part = split_match.group(1).strip()
                        title_part_first = ""  # No title text on first line
                    else:
                        number_part = split_match_with_text.group(1).strip()
                        title_part_first = split_match_with_text.group(2).strip()  # Title text from first line
                    
                    if i + 1 < len(lines):
                        next_line_text = lines[i + 1].get("text", "").strip()
                        letter_match = split_letter_pattern.match(next_line_text)
                        if letter_match:
                            # Create separate article number by combining number and letter
                            if not number_part.endswith("-"):
                                number_part += "-"
                            article_number = number_part + letter_match.group(1)
                            # Combine title parts from both lines
                            title_part_second = letter_match.group(2).strip()
                            if title_part_first:
                                article_first_line = title_part_first + " " + title_part_second
                            else:
                                article_first_line = title_part_second
                            skip_next = True  # Skip the next line since we've processed it
                        else:
                            continue
                    else:
                        continue
                else:
                    continue
            else:
                article_number = match.group(1)
                article_first_line = match.group(2).strip()

            # Check if this article is beyond 511 - skip omitted/repealed articles
            try:
                # Extract numeric part only (handles "225A", "225-A", "511" etc.)
                numeric_part = int(''.join(c for c in article_number if c.isdigit()))
                if numeric_part > 511:
                    continue  # Skip articles after 511 (omitted/repealed)
            except (ValueError, TypeError):
                pass  # Continue if article number doesn't have digits
            
            # Skip if we're in an omitted section
            if in_omitted_section:
                continue

            header_metrics = line_metrics(line)

            # Title-like predicate referencing header font (bigger/bolder than body)
            def is_probable_title(candidate: Dict[str, Any]) -> bool:
                txt = candidate["text"]
                if not txt:
                    return False
                if txt.startswith(("PART ", "CHAPTER ")):
                    return False
                # Exclude lines that look like article headers
                if re.match(r"^\s*(?:\[\s*){0,3}\s*\d+[A-Z]*\s*\.\s*", txt):
                    return False
                # Reject lines starting with digits, '[' or '-' (but allow '(' for headings)
                if re.match(r"^\s*[\[\-0-9]", txt):
                    return False
                if len(txt) < 3 or len(txt) > 130:
                    return False

                # NEW: Completely reject all-caps text as titles
                # Article titles are never in all caps in this document
                if candidate["caps_ratio"] >= 0.85:  # Text is almost entirely caps
                    return False

                # Strong heading signals (removed caps_ratio from here since we handle it above)
                strong_heading = (
                    candidate["bold_ratio"] >= 0.22
                    or candidate["avg_size"] >= (header_metrics["avg_size"] * 1.08)
                    or candidate["titlecase_ratio"] >= 0.60
                )

                # Sentence-like checks to avoid previous paragraph tails
                sentence_like = bool(
                    re.search(
                        r"\b(shall|may|be|is|are|was|were|has|have|had|will)\b",
                        txt,
                        re.I,
                    )
                )
                ends_with_sentence_punct = bool(re.search(r"[\.!?;:]\s*$", txt))

                # If it ends like a sentence or contains verbs, require strong heading cues
                if (ends_with_sentence_punct or sentence_like) and not strong_heading:
                    return False

                # If parenthetical heading like "(Parliament)", accept
                if looks_parenthetical_heading(txt):
                    return True

                # Otherwise, accept moderately short, neutral lines (typical headings) even if not strongly bold/bigger
                if not strong_heading:
                    wc = len(re.findall(r"[A-Za-z][A-Za-z'-]*", txt))
                    if (
                        2 <= wc <= 18
                        and not ends_with_sentence_punct
                        and not sentence_like
                    ):
                        return True

                return True if strong_heading else False

            # Collect contiguous title lines above the header, staying close vertically
            title_lines: List[Dict[str, Any]] = []
            max_lines_back = 4

            # Check if we found any all-caps lines that should be skipped
            found_caps_line = False

            for k in range(i - 1, max(-1, i - 1 - max_lines_back), -1):
                prev = lines[k]
                pm = line_metrics(prev)
                is_parenthetical = looks_parenthetical_heading(pm["text"])

                # Check if this line is all-caps (completely skip all-caps lines)
                is_all_caps = pm["caps_ratio"] >= 0.85

                if is_all_caps:
                    found_caps_line = True
                    # Skip this all-caps line and continue looking for proper title text below it
                    continue

                # Must look like a heading, or be a short parenthetical continuation
                if not (is_probable_title(pm) or is_parenthetical):
                    # If we found an all-caps line, continue looking for bold text below it
                    if found_caps_line:
                        continue
                    break

                # New guard: only accept bold lines as title (except short parenthetical)
                if not is_parenthetical and pm["bold_ratio"] < BOLD_MIN_FOR_TITLE:
                    # If we found an all-caps line, continue looking for bold text below it
                    if found_caps_line:
                        continue
                    break

                # vertical proximity (avoid pulling previous paragraph tail)
                if header_metrics["top"] - pm["top"] > 90:
                    break
                if title_lines and (title_lines[-1]["top"] - pm["top"] > 35):
                    break

                # Use only the bold text from this line (fallback to full text if empty or parenthetical)
                bold_only = (
                    _line_bold_text(prev) if not is_parenthetical else pm["text"]
                )
                text_to_use = bold_only if bold_only else pm["text"]
                title_lines.append({**pm, "text_to_use": text_to_use})

                # Reset the caps line flag since we found a valid title line
                found_caps_line = False

            if title_lines:
                article_title = " ".join(
                    t["text_to_use"] for t in reversed(title_lines)
                ).strip()
                article_title = re.sub(r"\s+", " ", article_title)
                # Remove newlines and backslashes from title
                article_title = (
                    article_title.replace("\n", " ")
                    .replace("\\n", " ")
                    .replace("\\", "")
                    .strip()
                )
                article_title = re.sub(r"\s+", " ", article_title)
            else:
                first_sentence = (
                    article_first_line.split(".")[0].strip()
                    if "." in article_first_line
                    else article_first_line
                )
                if len(first_sentence) < 200 and not first_sentence.startswith("("):
                    article_title = first_sentence
                else:
                    article_title = (
                        first_sentence[:100] + "..."
                        if len(first_sentence) > 100
                        else first_sentence
                    )
                # Remove newlines and backslashes from title
                article_title = (
                    article_title.replace("\n", " ")
                    .replace("\\n", " ")
                    .replace("\\", "")
                    .strip()
                )
                article_title = re.sub(r"\s+", " ", article_title)

            articles.append(
                {
                    "article_number": article_number,
                    "title": article_title,
                    "page_number": page_num,
                    "part": current_part,
                    "chapter": current_chapter,
                    "line_index": i,  # index in FILTERED lines
                    "y_position": line_top
                    if isinstance(line_top, (int, float))
                    else 0.0,
                }
            )

    return articles


def extract_article_content(pages_data: List[Dict], articles: List[Dict]) -> List[Dict]:
    """Extract accurate multi-line content for each article"""
    if not articles:
        return []
    sorted_articles = sorted(
        articles, key=lambda x: (x["page_number"], x["line_index"])
    )

    for i, article in enumerate(sorted_articles):
        page_num = article["page_number"]
        line_index = article["line_index"]
        content_lines: List[str] = []

        if i + 1 < len(sorted_articles):
            next_article = sorted_articles[i + 1]
            end_page = next_article["page_number"]
            end_line_index = next_article["line_index"]
        else:
            end_page = min(page_num + 10, len(pages_data))
            end_line_index = float("inf")

        for page_idx in range(page_num - 1, len(pages_data)):
            if page_idx >= len(pages_data):
                break

            current_page_data = pages_data[page_idx]
            current_page_num = current_page_data["page_num"]
            # Use the SAME filtering as detection (removes footnotes/tiny fonts)
            filtered_lines = _filter_page_lines(current_page_data)

            if current_page_num < page_num:
                continue
            elif current_page_num > end_page:
                break

            start_idx = 0
            end_idx = len(filtered_lines)

            if current_page_num == page_num:
                start_idx = line_index
            if current_page_num == end_page and i + 1 < len(sorted_articles):
                end_idx = min(end_line_index, len(filtered_lines))

            for j in range(start_idx, end_idx):
                if j < len(filtered_lines):
                    line_text = filtered_lines[j].get("text", "").strip()

                    # Include the header tail on the first line
                    if current_page_num == page_num and j == line_index:
                        header_match = re.match(
                            r"^\s*(?:\[\s*){0,3}\s*\d+[A-Z]*\s*\.\s*(.*)$", line_text
                        )
                        if header_match:
                            header_tail = header_match.group(1).strip()
                            if header_tail:
                                content_lines.append(header_tail)
                        continue

                    # Stop at structural markers
                    next_hdr = re.match(
                        r"^\s*(?:\[\s*){0,3}\s*\d+[A-Z]*\s*\.\s*", line_text
                    )
                    if (
                        line_text.startswith("PART ")
                        or line_text.startswith("CHAPTER ")
                        or (
                            next_hdr
                            and current_page_num == end_page
                            and j >= end_line_index
                        )
                    ):
                        break

                    content_lines.append(line_text)

        raw_content = "\n".join(content_lines).strip()
        cleaned_content = clean_article_content(raw_content)

        # Extract clauses first
        clauses = extract_clauses(cleaned_content)

        # Remove clause content from the main article content
        content_without_clauses = remove_clauses_from_content(cleaned_content, clauses)

        # Remove the title from the beginning of the content to avoid duplication
        content_without_title = remove_title_from_content(
            content_without_clauses, article["title"]
        )

        # Remove newlines and backslashes from content
        content_without_title = (
            content_without_title.replace("\n", " ")
            .replace("\\n", " ")
            .replace("\\", "")
            .strip()
        )
        content_without_title = re.sub(r"\s+", " ", content_without_title)

        article["content"] = content_without_title
        article["clauses"] = clauses

    return sorted_articles


def clean_article_content(content: str) -> str:
    """Clean article content while preserving line breaks for clause parsing."""
    if not content:
        return ""
    cleaned = content

    # Normalize odd Unicode spaces but keep line breaks
    cleaned = cleaned.replace("\u00a0", " ")  # NBSP
    cleaned = cleaned.replace("\u202f", " ")  # narrow NBSP
    cleaned = cleaned.replace("\u2007", " ")  # figure space
    cleaned = cleaned.replace("\u2009", " ")  # thin space

    # Strip running headers/footers and lone page numbers that break clause boundaries
    cleaned = re.sub(
        r"(?mi)^\s*\d+\s*$", "", cleaned
    )  # page numbers on their own lines
    cleaned = re.sub(r"(?mi)^\s*CONSTITUTION OF PAKISTAN\s*$", "", cleaned)

    # Normalize spaces but DO NOT collapse newlines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    # Insert a hard newline before clause markers that follow sentence-ending punctuation
    # e.g., "... choice. (2) Every ..." -> newline before (2)
    # Enhanced to handle numeric, alphabetic, and roman numeral clauses
    cleaned = re.sub(
        r"(?<=[\.\!\?\:\;])\s+(?=(?:\[\s*)?\(\s*(?:\d+|[a-z]|i{1,4}v?|iv|v|vi{1,3}|ix|x)\s*\)\]?\s)",
        "\n",
        cleaned,
    )

    # Also ensure clause markers at the start of text blocks get proper line breaks
    # This helps with clauses that appear after headings like "Illustrations"
    cleaned = re.sub(
        r"([A-Za-z])\s+(?=\(\s*(?:\d+|[a-z]|i{1,4}v?|iv|v|vi{1,3}|ix|x)\s*\))",
        r"\1\n",
        cleaned,
    )

    # Ensure "Illustrations" and similar headings get separated from following clauses
    cleaned = re.sub(
        r"(Illustrations?|Examples?|Notes?)\s*\n?\s*(?=\([a-z0-9ivx]+\))",
        r"\1\n",
        cleaned,
    )

    # Tidy spaces around newlines
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)

    # Remove ****** patterns but keep newlines
    cleaned = re.sub(r"\s*\*\s*\*\s*\*\s*\*\s*\*\s*\*\s*", " ", cleaned)

    # Punctuation spacing fixes
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\s*\)\s*", ") ", cleaned)
    cleaned = re.sub(r"\s*\(\s*", " (", cleaned)

    # Collapse excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def remove_title_from_content(content: str, title: str) -> str:
    """
    Remove the article title from the beginning of the content to avoid duplication.
    """
    if not content or not title:
        return content

    # Clean the title for comparison (remove special characters and normalize)
    title_clean = title.strip().rstrip(":").strip()

    # Split content into lines
    lines = content.split("\n")
    if not lines:
        return content

    # Check if the first line matches the title (with some flexibility)
    first_line = lines[0].strip().rstrip(":").strip()

    # Direct match
    if first_line == title_clean:
        # Remove the first line and return the rest
        return "\n".join(lines[1:]).strip()

    # Partial match (title might be at the beginning of the first line)
    if first_line.startswith(title_clean):
        # Remove the title portion from the first line
        remaining_text = lines[0][len(title_clean) :].strip().lstrip(":").strip()
        if remaining_text:
            lines[0] = remaining_text
            return "\n".join(lines).strip()
        else:
            return "\n".join(lines[1:]).strip()

    # If no match found, return content as is
    return content


def remove_clauses_from_content(content: str, clauses: List[Dict]) -> str:
    """
    Remove clause content from the main article content to avoid duplication.
    This removes the clause text but keeps the rest of the article content.
    """
    if not clauses or not content:
        return content

    # Create a copy of the content to modify
    cleaned_content = content

    # For each clause, try to find and remove its text from the content
    for clause in clauses:
        clause_id = clause["id"]
        clause_text = clause["text"]

        # Create patterns to match the clause in the content
        # Pattern 1: (a) followed by the clause text
        pattern1 = rf"\(\s*{re.escape(clause_id)}\s*\)\s*{re.escape(clause_text[:50])}"

        # Pattern 2: More flexible pattern for the whole clause block
        # Look for the clause marker followed by some of the text
        pattern2 = (
            rf"\(\s*{re.escape(clause_id)}\s*\)[^()]*?{re.escape(clause_text[:30])}"
        )

        # Try to remove the clause using the patterns
        for pattern in [pattern1, pattern2]:
            match = re.search(pattern, cleaned_content, re.IGNORECASE | re.DOTALL)
            if match:
                # Find the full clause text in the content
                start_pos = match.start()

                # Look for the end of this clause (start of next clause or end of content)
                remaining_content = cleaned_content[start_pos:]

                # Find next clause marker after this one
                next_clause_pattern = r"\(\s*[a-z0-9ivx]+\s*\)"
                next_match = None
                for next_match in re.finditer(
                    next_clause_pattern, remaining_content[10:], re.IGNORECASE
                ):
                    break

                if next_match:
                    end_pos = start_pos + 10 + next_match.start()
                else:
                    # If no next clause, remove to end or until we find "Explanation", etc.
                    end_markers = re.search(
                        r"\n\s*(Explanation|Note|Provided)",
                        remaining_content[10:],
                        re.IGNORECASE,
                    )
                    if end_markers:
                        end_pos = start_pos + 10 + end_markers.start()
                    else:
                        end_pos = len(cleaned_content)

                # Remove the clause text
                cleaned_content = (
                    cleaned_content[:start_pos] + cleaned_content[end_pos:]
                )
                break

    # Clean up any remaining formatting issues
    cleaned_content = re.sub(
        r"\n\s*\n\s*\n", "\n\n", cleaned_content
    )  # Remove excessive blank lines
    cleaned_content = re.sub(
        r"\s*Illustrations?\s*\n\s*$", "", cleaned_content
    )  # Remove trailing "Illustrations"
    cleaned_content = cleaned_content.strip()

    return cleaned_content


def extract_clauses(content: str) -> List[Dict]:
    """
    Extract clauses with various formats:
    - Numeric: (1), (2), (3), etc.
    - Alphabetic: (a), (b), (c), etc.
    - Roman numerals: (i), (ii), (iii), (iv), etc.

    Handles clauses that appear after headings like "Illustrations", "Examples", etc.
    """
    clauses: List[Dict] = []
    if not content:
        return clauses

    # Look for clause markers anywhere in the text, not just at line start
    # Pattern matches (letter), (number), or (roman numeral)
    clause_pattern = re.compile(
        r"\(\s*([0-9]+|[a-z]|i{1,4}|iv|v|vi{1,3}|ix|x)\s*\)\s*([A-Z])", re.IGNORECASE
    )

    # Find all clause markers and their positions
    matches = list(clause_pattern.finditer(content))

    if not matches:
        return clauses

    for i, match in enumerate(matches):
        clause_id = match.group(1).lower()
        start_pos = match.start()

        # Find where this clause ends (start of next clause or end of content)
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(content)

        # Extract the clause text
        clause_text = content[start_pos:end_pos].strip()

        # Remove the clause marker from the beginning and clean up
        clause_text = clause_pattern.sub("", clause_text, count=1).strip()

        # Clean up the text
        clause_text = re.sub(r"\n+", " ", clause_text)  # Replace newlines with spaces
        clause_text = re.sub(r"\s+", " ", clause_text)  # Normalize whitespace

        # Only include clauses with substantial content
        if len(clause_text) > 15:
            # Additional filtering to avoid capturing references
            # Skip if it looks like a reference (e.g., "and (b)" or "or (1)")
            previous_text = content[max(0, start_pos - 20) : start_pos].lower()
            if not re.search(r"\b(and|or|to|sections?|clauses?)\s*$", previous_text):
                clauses.append({"id": clause_id, "text": clause_text})

    return clauses


def validate_and_order_articles(articles: List[Dict]) -> List[Dict]:
    """Validate article sequence and ordering"""
    if not articles:
        return []

    # Sort by article number
    def article_key(article):
        num_str = article["article_number"]
        # Extract numeric part for sorting
        numeric_part = int("".join(filter(str.isdigit, num_str)) or 0)
        # Extract alphabetic part for secondary sorting
        alpha_part = "".join(filter(str.isalpha, num_str))
        return (numeric_part, alpha_part)

    sorted_articles = sorted(articles, key=article_key)

    # Validate sequence (should be roughly 1-280)
    article_numbers = []
    for article in sorted_articles:
        try:
            num = int("".join(filter(str.isdigit, article["article_number"])))
            article_numbers.append(num)
        except Exception:
            continue

    print(
        f"Found articles numbered: {sorted(set(article_numbers))[:20]}..."
    )  # Show first 20

    return sorted_articles


def detect_chapters_parts(pages_data: List[Dict]) -> Dict:
    """Detect chapter and part boundaries"""
    structure = {"chapters": [], "parts": []}

    chapter_pattern = re.compile(r"^(CHAPTER\s+[IVXLCDM0-9]+.*)", re.IGNORECASE)
    part_pattern = re.compile(r"^(PART\s+[0-9]+.*)", re.IGNORECASE)

    for page_data in pages_data:
        lines = page_data["lines"]
        page_num = page_data["page_num"]

        for line in lines:
            text = line.get("text", "").strip()

            chapter_match = chapter_pattern.match(text)
            part_match = part_pattern.match(text)

            if chapter_match:
                structure["chapters"].append(
                    {
                        "title": chapter_match.group(1),
                        "page": page_num,
                        "y_position": line.get("top", 0),
                    }
                )
            elif part_match:
                structure["parts"].append(
                    {
                        "title": part_match.group(1),
                        "page": page_num,
                        "y_position": line.get("top", 0),
                    }
                )

    return structure


def detect_schedule_amendments(pages_data: List[Dict]) -> List[Dict]:
    """
    Find amendment blocks that start with a bracketed reference like:
      [Article 41 (3)]
    and collect all subsequent lines (skipping bracketed SCHEDULE banners) until
    the next [Article ...] header or EOF. Returns a list of:
      { 'article_number': '41' or '63A', 'content': '...full block text...' }
    """
    amendments: List[Dict[str, Any]] = []

    article_ref_pat = re.compile(
        r"^\s*\[\s*Article\s+(\d+[A-Z]?)\s*(?:\([^)]+\))?\s*\]\s*$", re.IGNORECASE
    )
    schedule_banner_pat = re.compile(
        r"^\s*\[\s*[A-Z][A-Z\s\-]*SCHEDULE\s*\]\s*$", re.IGNORECASE
    )

    total_pages = len(pages_data)
    page_idx = 0

    while page_idx < total_pages:
        lines = _filter_page_lines(pages_data[page_idx])
        i = 0
        while i < len(lines):
            txt = (lines[i].get("text") or "").strip()
            m = article_ref_pat.match(txt)
            if not m:
                i += 1
                continue

            target_article = m.group(1).upper()  # e.g., '41', '63A'
            # Collect content from the line after the header across pages
            buffer: List[str] = []
            p = page_idx
            j = i + 1

            while p < total_pages:
                curr_lines = _filter_page_lines(pages_data[p])
                while j < len(curr_lines):
                    t = (curr_lines[j].get("text") or "").strip()
                    # Stop when the next amendment header starts
                    if article_ref_pat.match(t):
                        break
                    # Skip bracketed SCHEDULE banners; keep human-readable titles and numbered points
                    if schedule_banner_pat.match(t):
                        j += 1
                        continue
                    buffer.append(t)
                    j += 1
                # If we stopped because of next [Article ...], break outer loop
                if j < len(curr_lines) and article_ref_pat.match(
                    (curr_lines[j].get("text") or "").strip()
                ):
                    break
                # Move to next page
                p += 1
                j = 0

            raw_block = "\n".join(buffer).strip()
            if raw_block:
                # Clean but preserve numbering and newlines
                cleaned_block = clean_article_content(raw_block)
                amendments.append(
                    {"article_number": target_article, "content": cleaned_block}
                )

            # Continue scanning from where we stopped; if we broke due to a next header on same page, set i=j
            if p == page_idx:
                # next header was on the same page
                i = j
            else:
                # jump to page where we stopped and continue after the header line
                page_idx = p
                # will increment i at loop end; reset i to j to continue
                lines = (
                    _filter_page_lines(pages_data[page_idx])
                    if page_idx < total_pages
                    else []
                )
                i = j
            continue  # resume outer while

        page_idx += 1

    return amendments


def _normalize_article_key(s: str) -> str:
    return "".join(ch for ch in str(s).upper() if ch.isalnum())


def apply_schedule_amendments(
    articles: List[Dict], schedule_amendments: List[Dict]
) -> List[Dict]:
    """
    Append detected schedule amendments to their target article as clauses with id 'schedule-amendment-k'.
    """
    if not articles or not schedule_amendments:
        return articles

    # Build a map of existing base articles by normalized key (e.g., '63A', '41')
    art_map: Dict[str, Dict[str, Any]] = {}
    for a in articles:
        key = _normalize_article_key(a.get("article_number", ""))
        if key and key not in art_map:
            art_map[key] = a
            if not isinstance(a.get("clauses"), list):
                a["clauses"] = []

    for amend in schedule_amendments:
        tgt_key = _normalize_article_key(amend.get("article_number", ""))
        if not tgt_key or tgt_key not in art_map:
            continue
        base = art_map[tgt_key]
        text = (amend.get("content") or "").strip()
        if not text:
            continue
        existing = base.get("clauses") or []
        idx = (
            sum(
                1
                for c in existing
                if str(c.get("id", "")).startswith("schedule-amendment-")
            )
            + 1
        )
        existing.append({"id": f"schedule-amendment-{idx}", "text": text})
        base["clauses"] = existing

    return list(art_map.values())


def parse_constitution(pdf_path: str) -> Dict:
    """Main function with all fixes"""

    print("Extracting PDF with layout analysis...")
    pages_data = extract_with_precise_layout(pdf_path)

    print("Detecting articles...")
    articles = detect_articles(pages_data)

    print(f"Found {len(articles)} potential articles")

    print("Validating article sequence...")
    validated_articles = validate_and_order_articles(articles)

    print("Extracting article content...")
    articles_with_content = extract_article_content(pages_data, validated_articles)

    # Use base articles as-is; do not merge duplicate-number articles here
    merged_articles = articles_with_content

    # Detect schedule amendments like "[Article 41 (3)] ..." and attach to their base articles
    print("Detecting schedule amendments...")
    schedule_amendments = detect_schedule_amendments(pages_data)
    print(f"Found {len(schedule_amendments)} schedule amendments")

    print("Applying schedule amendments to base articles...")
    merged_articles = apply_schedule_amendments(merged_articles, schedule_amendments)

    # Find the page where article 511 appears
    article_511_page = None
    for art in merged_articles:
        if art['article_number'] == '511':
            article_511_page = art['page_number']
            break
    
    # Filter out omitted/repealed articles (those that appear after article 511's page)
    print(f"Filtering out omitted articles (articles after page {article_511_page})...")
    filtered_articles = []
    for art in merged_articles:
        # Keep articles up to and including the page where 511 appears
        if article_511_page is None or art['page_number'] <= article_511_page:
            filtered_articles.append(art)
    
    print(f"Articles after filtering: {len(filtered_articles)} (removed {len(merged_articles) - len(filtered_articles)} omitted articles)")

    # Create final structured output
    output = {
        "document": {
            "title": "Pakistan Penal Code",
            "year": 1860,
            "source_file": "Pakistan Penal Code.pdf",
            "articles": filtered_articles,
        }
    }

    return output


def determine_context(
    structure_elements: List[Dict], page_num: int, y_pos: float
) -> Optional[str]:
    """Determine which chapter/part an article belongs to"""
    # Find the most recent chapter/part before this article
    candidates = [
        elem
        for elem in structure_elements
        if elem["page"] < page_num
        or (elem["page"] == page_num and elem["y_position"] < y_pos)
    ]

    if candidates:
        return candidates[-1]["title"]
    return None


def validate_parsing_result(parsed_data: Dict) -> Dict:
    """Validate the parsing results"""
    articles = parsed_data["document"]["articles"]

    # Check for expected article range (1-280)
    article_numbers = []
    for a in articles:
        try:
            # Extract numeric part from article numbers like "225", "225A", "225-A"
            num = int("".join(filter(str.isdigit, a["article_number"])))
            article_numbers.append(num)
        except (ValueError, TypeError):
            continue
    expected_range = set(range(1, 281))
    found_range = set(article_numbers)
    missing_articles = expected_range - found_range

    # Validate content integrity
    validation_report = {
        "total_articles_found": len(articles),
        "article_numbers_range": (
            min(article_numbers) if article_numbers else 0,
            max(article_numbers) if article_numbers else 0,
        ),
        "missing_articles_count": len(missing_articles),
        "articles_with_clauses": len([a for a in articles if a["clauses"]]),
        "validation_notes": [],
    }

    if missing_articles:
        validation_report["validation_notes"].append(
            f"Missing articles: {sorted(missing_articles)[:10]}..."
        )

    return validation_report


# Execute the parsing
if __name__ == "__main__":
    # Build PDF path from settings instead of hard-coding
    pdf_path = "../data/pdfs/PPC.pdf"
    # if not pdf_path.exists():
    #     raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Parse the document
    result = parse_constitution(pdf_path)

    # Validate results
    validation = validate_parsing_result(result)
    print("Validation Report:", validation)

    # Save results
    with open("../data/jsons/pakistan-penal-code.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("Parsing completed successfully!")

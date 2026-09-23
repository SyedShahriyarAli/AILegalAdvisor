"""
extract_case_pdfs.py
────────────────────
Enriches every court-case JSON in cyber_cases/ with the full
judgment text extracted from the PDF linked in each record, and optionally
a heuristic ``winner`` field (petitioner / respondent / mixed / unknown).

- Works in-place: JSON files are updated; use ``--backup`` to copy to .json.bak first.
- Resume-safe: cases that already have successful pdf_data are skipped for download.
- Handles court-specific URL quirks (IHC viewer URL -> direct PDF link).

``winner`` is inferred from listing remarks and judgment text (approximate;
not a legal finding).

Usage:
    python scripts/scrapers/extract_case_pdfs.py
    python scripts/scrapers/extract_case_pdfs.py --dir path/to/jsons
    python scripts/scrapers/extract_case_pdfs.py --workers 10
    python scripts/scrapers/extract_case_pdfs.py --retry-errors   # re-try [ERROR:...] entries
    python scripts/scrapers/extract_case_pdfs.py --dry-run        # show what would be done
    python scripts/scrapers/extract_case_pdfs.py --winner-only    # fill winner from existing pdf_data only
    python scripts/scrapers/extract_case_pdfs.py --force-winner   # recompute winner

Requirements: pip install requests pdfplumber
"""

import io
import json
import re
import sys
import argparse
import shutil
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Try to import pdfplumber; give a clear error if missing
# ---------------------------------------------------------------------------
try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_WORKERS = 10
REQUEST_TIMEOUT = 45       # seconds per PDF
SAVE_EVERY      = 10       # checkpoint every N completed cases
MAX_PDF_CHARS   = 200_000  # trim very long PDFs to avoid DB bloat

# ---------------------------------------------------------------------------
# Heuristic winner inference (regex on remarks + judgment text)
# ---------------------------------------------------------------------------

_WINNER_MIXED = [
    (r"partially\s+allowed", 4),
    (r"partly\s+allowed", 4),
    (r"allowed\s+in\s+part", 4),
    (r"modified\s+the\s+sentence", 3),
    (r"partial\s+relief", 3),
]

_WINNER_POSITIVE = [
    (r"petition\s+is\s+allowed", 5),
    (r"writ\s+petition\s+is\s+allowed", 5),
    (r"this\s+writ\s+petition\s+is\s+allowed", 5),
    (r"this\s+petition\s+is\s+allowed", 5),
    (r"accordingly,?\s+this\s+writ\s+petition\s+is\s+allowed", 5),
    (r"\(petition\s+was\s+allowed", 4),
    (r"petition\s+was\s+allowed", 4),
    (r"impugned\s+notice.*set\s+aside", 4),
    (r"notice\s+.*\s+is\s+hereby\s+set\s+aside", 4),
    (r"hereby\s+set\s+aside", 3),
    (r"directed\s+to\s+be\s+released\s+on\s+bail", 4),
    (r"petitioner\s+was\s+granted\s+bail", 4),
    (r"granted\s+bail", 3),
    (r"appeal\s+is\s+allowed", 3),
]

_WINNER_NEGATIVE = [
    (r"bail\s+petition.*dismissed", 5),
    (r"this\s+bail\s+petition.*dismissed", 5),
    (r"writ\s+petition.*dismissed", 5),
    (r"this\s+writ\s+petition.*dismissed", 5),
    (r"instant\s+(?:writ\s+)?petition.*dismissed", 4),
    (r"petition\s+having\s+no\s+force.*dismissed", 4),
    (r"stands\s+dismissed", 3),
    (r"dismissed\s+in\s+limine", 3),
    (r"bail\s+refused", 4),
    (r"refused\s+bail", 4),
    (r"declined\s+to\s+grant\s+bail", 4),
    (r"declined\s+bail", 3),
    (r"no\s+force.*dismissed", 3),
]


def infer_winner(case: dict) -> str:
    """
    Rough classification: whether outcome favors the typical relief-seeker (petitioner).
    Uses remarks/listing fields plus head/tail of pdf_data. Returns one of:
    petitioner | respondent | mixed | unknown
    """
    pdf = (case.get("pdf_data") or "").strip()
    if not pdf or pdf.startswith("[ERROR"):
        return "unknown"

    parts = []
    for key in ("remarks", "matter", "description", "excerpt"):
        v = (case.get(key) or "").strip()
        if v:
            parts.append(v)
    parts.append(pdf[:4000])
    parts.append(pdf[-12000:])
    text = "\n".join(parts).lower()

    mixed_score = sum(w for pat, w in _WINNER_MIXED if re.search(pat, text, re.I))
    if mixed_score >= 4:
        return "mixed"

    pos = sum(w for pat, w in _WINNER_POSITIVE if re.search(pat, text, re.I))
    neg = sum(w for pat, w in _WINNER_NEGATIVE if re.search(pat, text, re.I))

    if pos == 0 and neg == 0:
        return "unknown"
    if mixed_score > 0 and pos > 0 and neg > 0:
        return "mixed"
    if pos > neg and neg > 0:
        return "mixed"
    if pos > neg:
        return "petitioner"
    if neg > pos:
        return "respondent"
    return "unknown"


def _winner_needs_update(case: dict, force_winner: bool) -> bool:
    if force_winner:
        return True
    w = (case.get("winner") or "").strip()
    return not w


def _apply_winner_to_case(case: dict, force_winner: bool) -> bool:
    """Set case['winner'] if needed. Returns True if the dict was updated."""
    pdf = (case.get("pdf_data") or "").strip()
    if not pdf or pdf.startswith("[ERROR"):
        if _winner_needs_update(case, force_winner):
            case["winner"] = "unknown"
            return True
        return False
    if not _winner_needs_update(case, force_winner):
        return False
    case["winner"] = infer_winner(case)
    return True


# ---------------------------------------------------------------------------
# Thread-local HTTP session
# ---------------------------------------------------------------------------
_thread_local = threading.local()

def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1, pool_maxsize=1, max_retries=3
        )
        s.mount("https://", adapter)
        s.mount("http://",  adapter)
        _thread_local.session = s
    return _thread_local.session

# ---------------------------------------------------------------------------
# PDF URL resolution — court-specific quirks
# ---------------------------------------------------------------------------

def _resolve_pdf_url(raw_url: str) -> str:
    """Convert viewer/redirect URLs to a direct PDF download link."""
    if not raw_url:
        return ""

    # IHC: judgment_link is a viewer URL; the actual PDF path is in ?jgmnt=
    if "mis.ihc.gov.pk/frmRdJgmnt.aspx" in raw_url:
        parsed = urllib.parse.urlparse(raw_url)
        params = urllib.parse.parse_qs(parsed.query)
        if "jgmnt" in params:
            path = params["jgmnt"][0]
            prefix = "https://mis.ihc.gov.pk"
            return prefix + path if path.startswith("/") else prefix + "/" + path

    # IHC download_link uses http:// but server requires https://
    if raw_url.startswith("http://mis.ihc.gov.pk"):
        raw_url = "https" + raw_url[4:]

    return raw_url

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_url: str) -> str:
    """Download a PDF and return its extracted text, or an [ERROR: ...] string."""
    if not pdf_url:
        return "[ERROR: No PDF URL]"

    url = _resolve_pdf_url(pdf_url)
    if not url:
        return "[ERROR: Could not resolve PDF URL]"

    try:
        session = _get_session()

        # LHC uses a self-signed cert — skip SSL verification for that domain
        verify_ssl = "lhc.gov.pk" not in url
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        resp = session.get(url, timeout=REQUEST_TIMEOUT, verify=verify_ssl)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        if "html" in content_type and "pdf" not in content_type:
            return "[ERROR: Server returned HTML, not a PDF]"

        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            pages = [pg.extract_text() or "" for pg in pdf.pages]

        text = "\n".join(pages).strip()
        if not text:
            return "[ERROR: PDF is a scanned image (no extractable text)]"

        # Trim to avoid storing megabytes per case
        if len(text) > MAX_PDF_CHARS:
            text = text[:MAX_PDF_CHARS] + "\n[TRUNCATED]"

        return text

    except requests.HTTPError as e:
        return f"[ERROR: HTTP {e.response.status_code} from {url}]"
    except requests.exceptions.ConnectionError:
        return f"[ERROR: Connection failed for {url}]"
    except requests.exceptions.Timeout:
        return f"[ERROR: Timeout ({REQUEST_TIMEOUT}s) for {url}]"
    except Exception as e:
        return f"[ERROR: {type(e).__name__} - {str(e)[:120]}]"

# ---------------------------------------------------------------------------
# Per-court pdf_link field resolution
# Different court JSONs store the PDF URL under different field names.
# ---------------------------------------------------------------------------

def _get_pdf_url(case: dict) -> str:
    """Return the PDF URL from a case dict, checking all known field names."""
    for field in ("pdf_link", "download_link", "judgment_link"):
        val = (case.get(field) or "").strip()
        if val:
            return val
    return ""

# ---------------------------------------------------------------------------
# Enrich a single JSON file in-place
# ---------------------------------------------------------------------------

def enrich_file(
    json_path: Path,
    workers: int,
    retry_errors: bool,
    dry_run: bool,
    winner_only: bool = False,
    force_winner: bool = False,
    backup: bool = False,
) -> dict:
    """Load, enrich, and save one court JSON file. Returns stats dict."""
    print(f"\n{'='*70}")
    print(f"File : {json_path.name}")
    print(f"{'='*70}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Normalise root structure to a list
    if isinstance(data, list):
        cases = data
        wrapper_key = None
    elif isinstance(data, dict):
        wrapper_key = next(
            (k for k in ("judgments", "cases", "data", "results")
             if k in data and isinstance(data[k], list)),
            None,
        )
        if wrapper_key:
            cases = data[wrapper_key]
        else:
            print(f"  [SKIP] Unrecognised JSON structure in {json_path.name}")
            return {"file": json_path.name, "total": 0, "enriched": 0, "skipped": 0,
                    "errors": 0, "winner_updates": 0}
    else:
        print(f"  [SKIP] Not a JSON array or object: {json_path.name}")
        return {"file": json_path.name, "total": 0, "enriched": 0, "skipped": 0,
                "errors": 0, "winner_updates": 0}

    total = len(cases)

    def save_checkpoint():
        payload = cases if wrapper_key is None else {**data, wrapper_key: cases}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

    # --- Winner-only mode: no PDF downloads ---
    if winner_only:
        pending_w = []
        for i, case in enumerate(cases):
            pdf = (case.get("pdf_data") or "").strip()
            if not pdf or pdf.startswith("[ERROR"):
                continue
            if _winner_needs_update(case, force_winner):
                pending_w.append(i)

        print(f"  Total        : {total}")
        print(f"  Winner pend. : {len(pending_w)}")
        if dry_run:
            print(f"  [DRY-RUN] Would set winner on {len(pending_w)} cases.")
            return {"file": json_path.name, "total": total, "enriched": 0,
                    "skipped": total - len(pending_w), "errors": 0,
                    "winner_updates": len(pending_w)}

        if not pending_w:
            print("  [DONE] No winner updates needed.")
            return {"file": json_path.name, "total": total, "enriched": 0,
                    "skipped": total, "errors": 0, "winner_updates": 0}

        if backup:
            bak = json_path.with_suffix(".json.bak")
            shutil.copy2(json_path, bak)
            print(f"  [BACKUP] {bak.name}")

        w_count = 0
        for i in pending_w:
            if _apply_winner_to_case(cases[i], force_winner):
                w_count += 1
        save_checkpoint()
        print(f"\n  [DONE] winner field set on {w_count} case(s).")
        return {
            "file": json_path.name,
            "total": total,
            "enriched": 0,
            "skipped": total - w_count,
            "errors": 0,
            "winner_updates": w_count,
        }

    # --- PDF extraction pending indices ---
    already_done = 0
    pending_indices = []

    for i, case in enumerate(cases):
        existing = case.get("pdf_data", "")
        if existing and not existing.startswith("[ERROR"):
            already_done += 1
        elif existing.startswith("[ERROR") and not retry_errors:
            already_done += 1  # keep existing error, don't retry unless asked
        else:
            pending_indices.append(i)

    print(f"  Total     : {total}")
    print(f"  Already OK: {already_done}")
    print(f"  Pending   : {len(pending_indices)}")

    if dry_run:
        would_pdf = len(pending_indices)
        would_w = sum(
            1 for c in cases
            if (c.get("pdf_data") or "").strip()
            and not (c.get("pdf_data") or "").startswith("[ERROR")
            and _winner_needs_update(c, force_winner)
        )
        print(f"  [DRY-RUN] Would download ~{would_pdf} PDFs; ~{would_w} winner field(s) to fill.")
        return {"file": json_path.name, "total": total, "enriched": 0,
                "skipped": already_done, "errors": 0, "winner_updates": 0}

    if pending_indices and backup:
        bak = json_path.with_suffix(".json.bak")
        shutil.copy2(json_path, bak)
        print(f"  [BACKUP] {bak.name}")

    done_count  = [0]
    error_count = [0]

    def process_one(idx: int):
        case = cases[idx]
        url  = _get_pdf_url(case)
        text = extract_pdf_text(url)
        return idx, text

    if pending_indices:
        lock = threading.Lock()
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_one, idx): idx for idx in pending_indices}

            for future in as_completed(futures):
                try:
                    idx, text = future.result()
                except Exception as e:
                    idx = futures[future]
                    text = f"[ERROR: worker exception - {e}]"

                is_error = text.startswith("[ERROR")

                with lock:
                    cases[idx]["pdf_data"] = text
                    done_count[0] += 1
                    if is_error:
                        error_count[0] += 1

                    elapsed = time.time() - start_time
                    rate    = done_count[0] / elapsed if elapsed > 0 else 0
                    remain  = len(pending_indices) - done_count[0]
                    eta     = int(remain / rate) if rate > 0 else 0

                    case_label = (
                        cases[idx].get("case_no")
                        or cases[idx].get("case_title", "")
                    )[:30]

                    if is_error:
                        print(f"  [{already_done + done_count[0]}/{total}] WARN  {case_label!r:32} -> {text[:60]}")
                    else:
                        print(f"  [{already_done + done_count[0]}/{total}] OK    {case_label!r:32} -> {len(text):,} chars  ETA:{eta}s")

                    if done_count[0] % SAVE_EVERY == 0:
                        save_checkpoint()

    # Infer winner for every row from remarks + pdf_data (single pass)
    winner_updates_total = 0
    for case in cases:
        if _apply_winner_to_case(case, force_winner):
            winner_updates_total += 1

    save_checkpoint()
    if pending_indices:
        print(f"\n  [DONE] {done_count[0] - error_count[0]} extracted,  "
              f"{error_count[0]} errors; winner updates (total): {winner_updates_total}; "
              f"file saved: {json_path.name}")
    else:
        print(f"\n  [DONE] No PDF downloads; winner updates: {winner_updates_total}; "
              f"file saved: {json_path.name}")

    return {
        "file":     json_path.name,
        "total":    total,
        "enriched": done_count[0] - error_count[0] if pending_indices else 0,
        "skipped":  already_done,
        "errors":   error_count[0] if pending_indices else 0,
        "winner_updates": winner_updates_total,
    }

# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enrich court-case JSON files with PDF text extracted from judgment links."
    )
    parser.add_argument(
        "--dir", type=Path, default=None,
        help="Directory containing court JSON files "
             "(default: backend/data/jsons/cyber_cases)",
    )
    parser.add_argument(
        "--file", type=Path, default=None,
        help="Process a single JSON file instead of the whole directory",
    )
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Concurrent download threads per file (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--retry-errors", action="store_true",
        help="Re-attempt cases that previously returned [ERROR: ...] text",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be processed without downloading anything",
    )
    parser.add_argument(
        "--winner-only", action="store_true",
        help="Only infer and write winner from existing pdf_data (no downloads)",
    )
    parser.add_argument(
        "--force-winner", action="store_true",
        help="Recompute winner even when already set",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Copy each JSON to .json.bak once before modifying",
    )
    args = parser.parse_args()

    if args.file:
        json_files = [args.file]
    else:
        cases_dir = args.dir or (
            Path(__file__).resolve().parents[2]
            / "data" / "jsons" / "cyber_cases"
        )
        if not cases_dir.is_dir():
            print(f"[ERROR] Directory not found: {cases_dir}")
            sys.exit(1)
        json_files = sorted(cases_dir.glob("*.json"))
        # Exclude backups that might have been written by a previous run
        json_files = [f for f in json_files if not f.name.endswith(".bak")]

    if not json_files:
        print("[ERROR] No JSON files found.")
        sys.exit(1)

    print("\n" + "="*70)
    print("PDF TEXT EXTRACTION FOR COURT CASES")
    print("="*70)
    print(f"Files        : {len(json_files)}")
    print(f"Workers      : {args.workers} per file")
    print(f"Retry        : {args.retry_errors}")
    print(f"Dry-run      : {args.dry_run}")
    print(f"Winner-only  : {args.winner_only}")
    print(f"Force winner : {args.force_winner}")
    print(f"Backup       : {args.backup}")

    all_stats = []
    for json_path in json_files:
        stats = enrich_file(
            json_path=json_path,
            workers=args.workers,
            retry_errors=args.retry_errors,
            dry_run=args.dry_run,
            winner_only=args.winner_only,
            force_winner=args.force_winner,
            backup=args.backup,
        )
        all_stats.append(stats)

    # Summary table
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"  {'File':<45} {'Total':>6} {'PDFok':>6} {'Skip':>6} {'Err':>6} {'Win':>6}")
    print(f"  {'-'*45} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    grand = {"total": 0, "enriched": 0, "skipped": 0, "errors": 0, "winner_updates": 0}
    for s in all_stats:
        wu = s.get("winner_updates", 0)
        print(f"  {s['file']:<45} {s['total']:>6} {s['enriched']:>6} "
              f"{s['skipped']:>6} {s['errors']:>6} {wu:>6}")
        for k in grand:
            grand[k] += s.get(k, 0)
    print(f"  {'TOTAL':<45} {grand['total']:>6} {grand['enriched']:>6} "
          f"{grand['skipped']:>6} {grand['errors']:>6} {grand['winner_updates']:>6}")
    print()
    if not args.dry_run:
        if args.winner_only:
            print("JSON files updated in-place with winner field where pdf_data exists.")
        else:
            print("JSON files have been updated in-place with pdf_data and winner.")
        print("Run ingest_cases.py afterwards to load the enriched data into Neo4j.")


if __name__ == "__main__":
    main()

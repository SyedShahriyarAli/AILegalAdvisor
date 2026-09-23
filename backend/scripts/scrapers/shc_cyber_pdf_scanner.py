"""
shc_cyber_pdf_scanner.py  (optimized v2)
─────────────────────────────────────────
Reads:  backend/data/jsons/shc_<YEAR>_all_cases.json   (default: 2025)
Scans each case's PDF for cyber crime keywords using:
  • Concurrent downloads  (ThreadPoolExecutor, configurable workers)
  • Connection pooling    (requests.Session per thread)
  • Resume support        (checkpoint file – safe to Ctrl+C and restart)
  • Incremental saving    (flushes matched cases every SAVE_EVERY hits)

Writes:
  backend/data/jsons/shc_<YEAR>_cyber_cases.json
  backend/data/jsons/shc_<YEAR>_scan_checkpoint.json   (auto-cleaned on finish)

Usage:
  python shc_cyber_pdf_scanner.py [YEAR] [--workers N]

  python shc_cyber_pdf_scanner.py 2025
  python shc_cyber_pdf_scanner.py 2025 --workers 15
"""

import os
import sys
import io
import json
import time
import argparse
import threading
import requests
import pdfplumber
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_WORKERS   = 10     # concurrent PDF downloads
REQUEST_TIMEOUT   = 25     # seconds per PDF download
SAVE_EVERY        = 50     # flush cyber cases to disk every N matches found
MAX_ERRORS        = 100    # abort after this many consecutive network errors

# ── Cyber keywords ─────────────────────────────────────────────────────────────
CYBER_PHRASES = [
    "cyber crime", "cybercrime", "cyber-crime",
    "prevention of electronic crimes", "peca",
    "electronic crimes act", "electronic crime",
    "cyber terrorism", "cyber stalking", "cyberstalking",
    "cyber fraud", "fia cyber", "cyberspace",
    "hacking", "unauthorised access", "unauthorized access",
    "online harassment", "digital crime", "internet crime",
    "cyber offense", "cyber offence",
    "section 3 peca", "section 4 peca", "section 9 peca",
    "section 10 peca", "section 11 peca", "section 14 peca",
    "section 15 peca", "section 16 peca", "section 17 peca",
    "section 18 peca", "section 19 peca", "section 20 peca",
    "section 21 peca", "section 22 peca", "electronic forgery",
    "identity theft", "data theft", "malicious code",
    "denial of service", "phishing", "ransomware",
    "child pornography", "obscene material online",
    "spamming", "spoofing", "cyber extortion",
    "nccia", "national cyber crime", "prevention of electronic crime",
]

# ── Thread-local HTTP session (one per worker thread) ─────────────────────────
_thread_local = threading.local()

def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        })
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=2,
        )
        s.mount("https://", adapter)
        s.mount("http://",  adapter)
        _thread_local.session = s
    return _thread_local.session


# ── PDF helpers ────────────────────────────────────────────────────────────────
def extract_text(pdf_url: str) -> tuple[str, str]:
    """
    Download PDF and extract text.
    Returns (text, status) where status is 'ok' | 'empty' | 'error:<msg>'
    """
    try:
        session = _get_session()
        resp = session.get(pdf_url, timeout=REQUEST_TIMEOUT, stream=False)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type and "pdf" not in content_type:
            return "", "empty"

        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            pages_text = [pg.extract_text() or "" for pg in pdf.pages]
        text = "\n".join(pages_text)
        return (text, "ok") if text.strip() else ("", "empty")

    except requests.HTTPError as e:
        return "", f"error:HTTP {e.response.status_code}"
    except Exception as e:
        return "", f"error:{type(e).__name__}"


def find_matches(text: str) -> list[str]:
    lower = text.lower()
    return [p for p in CYBER_PHRASES if p in lower]


def get_excerpt(text: str, phrase: str, window: int = 350) -> str:
    idx = text.lower().find(phrase)
    if idx == -1:
        return ""
    start = max(0, idx - window // 2)
    end   = min(len(text), idx + window // 2)
    return "..." + text[start:end].strip() + "..."


# ── Worker function ────────────────────────────────────────────────────────────
def scan_case(case: dict) -> dict | None:
    """
    Scan one case's PDF.
    Returns enriched case dict if cyber match, else None.
    """
    pdf_url = case.get("pdf_link", "").strip()
    if not pdf_url:
        return None

    text, status = extract_text(pdf_url)

    if status == "empty" or status.startswith("error"):
        return {"__status__": status, "record_id": case.get("record_id", "")}

    matched = find_matches(text)
    if not matched:
        return None

    excerpt = get_excerpt(text, matched[0])
    return {
        **case,
        "cyber_keywords_matched": matched,
        "excerpt": excerpt,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Checkpoint helpers ─────────────────────────────────────────────────────────
def load_checkpoint(ckpt_file: str) -> set[str]:
    """Return set of record_ids already scanned."""
    if os.path.exists(ckpt_file):
        with open(ckpt_file) as f:
            data = json.load(f)
        return set(data.get("scanned", []))
    return set()


def save_checkpoint(ckpt_file: str, scanned_ids: set[str]):
    with open(ckpt_file, "w") as f:
        json.dump({"scanned": list(scanned_ids), "updated": datetime.now(timezone.utc).isoformat()}, f)


# ── Main scanner ───────────────────────────────────────────────────────────────
def scan_cases(input_file: str, output_file: str, ckpt_file: str,
               workers: int = DEFAULT_WORKERS):

    with open(input_file, encoding="utf-8") as f:
        cases = json.load(f)

    # Resume: skip already-processed record_ids
    scanned_ids = load_checkpoint(ckpt_file)
    pending = [c for c in cases if c.get("record_id", c.get("sr_no")) not in scanned_ids]

    # Load already found cyber cases
    cyber_cases: list[dict] = []
    if os.path.exists(output_file):
        with open(output_file, encoding="utf-8") as f:
            cyber_cases = json.load(f)

    total     = len(cases)
    remaining = len(pending)
    errors    = 0
    skipped   = 0

    print(f"Total cases  : {total:,}")
    print(f"Already done : {total - remaining:,}  (checkpoint)")
    print(f"To scan      : {remaining:,}")
    print(f"Workers      : {workers}")
    print(f"Cyber found  : {len(cyber_cases)} so far")
    print("─" * 60)

    lock           = threading.Lock()
    done_count     = 0
    last_save_size = len(cyber_cases)
    start_time     = time.time()

    def flush():
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cyber_cases, f, indent=4, ensure_ascii=False)
        save_checkpoint(ckpt_file, scanned_ids)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(scan_case, c): c for c in pending}

        for future in as_completed(futures):
            case = futures[future]
            rid  = case.get("record_id", case.get("sr_no", "?"))

            with lock:
                done_count  += 1
                scanned_ids.add(rid)

                try:
                    result = future.result()
                except Exception as e:
                    errors += 1
                    result = {"__status__": f"error:{e}", "record_id": rid}

                # Progress line
                elapsed = time.time() - start_time
                rate    = done_count / elapsed if elapsed > 0 else 0
                eta_s   = int((remaining - done_count) / rate) if rate > 0 else 0
                eta_str = f"{eta_s//60}m{eta_s%60:02d}s"

                if result is None:
                    status_str = "—"
                elif result.get("__status__"):
                    status_str = f"⚠  {result['__status__']}"
                    skipped += 1
                else:
                    matched = result.get("cyber_keywords_matched", [])
                    status_str = f"✅ CYBER! {matched}"
                    cyber_cases.append(result)

                case_label = case.get("case_no", rid)[:55]
                print(
                    f"[{done_count:>5}/{remaining}] {case_label:<55} "
                    f"{status_str}  ETA:{eta_str}",
                    flush=True,
                )

                # Periodic flush
                if len(cyber_cases) >= last_save_size + SAVE_EVERY or done_count % 500 == 0:
                    flush()
                    last_save_size = len(cyber_cases)
                    print(f"  ── checkpoint saved ({done_count:,} done, {len(cyber_cases)} cyber) ──")

                if errors >= MAX_ERRORS:
                    print(f"Too many errors ({errors}). Stopping.")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

    # Final save
    flush()

    elapsed_total = int(time.time() - start_time)
    print("\n" + "=" * 60)
    print(f"Scan complete in {elapsed_total//60}m{elapsed_total%60:02d}s")
    print(f"  Total cases   : {total:,}")
    print(f"  Scanned       : {done_count:,}")
    print(f"  Skipped/empty : {skipped}")
    print(f"  Errors        : {errors}")
    print(f"  Cyber matches : {len(cyber_cases)}")
    print(f"  Output        : {output_file}")
    print("=" * 60)

    # Clean up checkpoint on full run
    if done_count >= remaining and os.path.exists(ckpt_file):
        os.remove(ckpt_file)
        print("Checkpoint file removed (full scan complete).")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan SHC case PDFs for cyber crime keywords.")
    parser.add_argument("year",    nargs="?", default="2025", help="Year to scan (default: 2025)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent workers (default: 10)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[2] / "data" / "jsons"
    base.mkdir(parents=True, exist_ok=True)

    input_json  = str(base / f"shc_{args.year}_all_cases.json")
    output_json = str(base / f"shc_{args.year}_cyber_cases.json")
    ckpt_json   = str(base / f"shc_{args.year}_scan_checkpoint.json")

    if not Path(input_json).exists():
        print(f"ERROR: Input file not found: {input_json}")
        print(f"Run shc_caselaw_2026_scraper.py {args.year} first.")
        sys.exit(1)

    scan_cases(input_json, output_json, ckpt_json, workers=args.workers)

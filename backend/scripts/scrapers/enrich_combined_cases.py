"""
enrich_combined_cases.py
────────────────────────
Reads:  backend/data/generated/all_courts_cyber_cases.json
Downloads the PDF for each case concurrently, extracts the text using pdfplumber,
and saves it to a new field 'pdf_data'.

Writes: backend/data/generated/all_courts_cyber_cases_enriched.json
"""

import os
import json
import io
import time
import requests
import pdfplumber
import threading
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_WORKERS = 15     # Concurrent downloads
REQUEST_TIMEOUT = 30     # Seconds per PDF download
SAVE_EVERY      = 20     # Save JSON every N completed cases

# ── Thread-local HTTP session (one per worker thread) ─────────────────────────
_thread_local = threading.local()

def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=3)
        s.mount("https://", adapter)
        s.mount("http://",  adapter)
        _thread_local.session = s
    return _thread_local.session

# ── PDF extraction ─────────────────────────────────────────────────────────────
def extract_pdf_text(pdf_url: str) -> str:
    """Download PDF and extract all text."""
    if not pdf_url:
        return ""
        
    try:
        session = _get_session()
        
        # LHC has SSL issues
        verify_ssl = not ("lhc.gov.pk" in pdf_url)
        
        # Suppress insecure request warnings if verify is False
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        resp = session.get(pdf_url, timeout=REQUEST_TIMEOUT, stream=False, verify=verify_ssl)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        if "html" in content_type and "pdf" not in content_type:
            return "[ERROR: URL returned HTML, not a PDF]"

        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            pages_text = [pg.extract_text() or "" for pg in pdf.pages]
            
        text = "\n".join(pages_text).strip()
        return text if text else "[ERROR: PDF appears to be a scanned image (no extractable text)]"

    except requests.HTTPError as e:
        return f"[ERROR: HTTP {e.response.status_code}]"
    except Exception as e:
        return f"[ERROR: {type(e).__name__} - {str(e)}]"

# ── Worker function ────────────────────────────────────────────────────────────
def process_case(case: dict) -> dict:
    """Process a single case."""
    # If already processed and successful, skip
    # Re-run if it has an error
    if "pdf_data" in case and not case["pdf_data"].startswith("[ERROR"):
        return case
        
    pdf_url = case.get("pdf_link", "").strip()
    
    if not pdf_url:
        case["pdf_data"] = "[ERROR: No PDF link provided]"
        return case
        
    # Fix IHC URLs
    if "mis.ihc.gov.pk/frmRdJgmnt.aspx" in pdf_url:
        parsed_url = urllib.parse.urlparse(pdf_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if "jgmnt" in query_params:
            jgmnt_path = query_params["jgmnt"][0]
            # Some paths might already start with a slash
            if jgmnt_path.startswith("/"):
                pdf_url = f"https://mis.ihc.gov.pk{jgmnt_path}"
            else:
                pdf_url = f"https://mis.ihc.gov.pk/{jgmnt_path}"
    
    extracted_text = extract_pdf_text(pdf_url)
    case["pdf_data"] = extracted_text
    return case

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    canonical_dir = Path(__file__).resolve().parents[2] / "data" / "jsons"
    generated_dir = Path(__file__).resolve().parents[2] / "data" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    input_file = generated_dir / "all_courts_cyber_cases.json"
    if not input_file.exists():
        input_file = canonical_dir / "all_courts_cyber_cases.json"
    output_file = generated_dir / "all_courts_cyber_cases_enriched.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    # Load input data
    with open(input_file, encoding="utf-8") as f:
        cases = json.load(f)

    # Load existing enriched data if we are resuming
    enriched_cases = []
    if output_file.exists():
        try:
            with open(output_file, encoding="utf-8") as f:
                enriched_cases = json.load(f)
        except Exception:
            pass

    # Map by a unique key to update existing records
    # Using enumerate index as fallback since some might lack unique IDs
    case_map = {}
    for i, c in enumerate(cases):
        unique_id = f"{c.get('court', '')}_{c.get('case_no', '')}_{i}"
        case_map[unique_id] = c

    for i, c in enumerate(enriched_cases):
        unique_id = f"{c.get('court', '')}_{c.get('case_no', '')}_{i}"
        if unique_id in case_map:
             case_map[unique_id] = c # Use the enriched version

    pending_tasks = [ (uid, c) for uid, c in case_map.items() if "pdf_data" not in c or c["pdf_data"].startswith("[ERROR") ]
    
    total = len(cases)
    remaining = len(pending_tasks)
    done = total - remaining
    
    print(f"Total cases: {total}")
    print(f"Already enriched: {done}")
    print(f"Pending: {remaining}")
    print("-" * 50)

    if remaining == 0:
        print("All cases are already enriched.")
        return

    lock = threading.Lock()
    done_in_session = 0
    start_time = time.time()

    def save_progress():
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(list(case_map.values()), f, indent=4, ensure_ascii=False)

    with ThreadPoolExecutor(max_workers=DEFAULT_WORKERS) as executor:
        # Submit tasks
        future_to_uid = {executor.submit(process_case, c): uid for uid, c in pending_tasks}
        
        for future in as_completed(future_to_uid):
            uid = future_to_uid[future]
            try:
                updated_case = future.result()
                with lock:
                    case_map[uid] = updated_case
                    done_in_session += 1
                    
                    elapsed = time.time() - start_time
                    rate = done_in_session / elapsed if elapsed > 0 else 0
                    eta_s = int((remaining - done_in_session) / rate) if rate > 0 else 0
                    
                    status_snippet = updated_case['pdf_data'][:30].replace('\\n', ' ')
                    if "[ERROR" in status_snippet:
                        print(f"[{done + done_in_session}/{total}] ⚠ {updated_case.get('court')} {updated_case.get('case_no', '')[:20]} -> {status_snippet}...")
                    else:
                        print(f"[{done + done_in_session}/{total}] ✅ {updated_case.get('court')} {updated_case.get('case_no', '')[:20]} -> {len(updated_case['pdf_data'])} chars extracted. ETA: {eta_s}s")
                    
                    # Periodic save
                    if done_in_session % SAVE_EVERY == 0:
                        save_progress()
                        
            except Exception as e:
                print(f"Task failed for {uid}: {e}")

    # Final save
    save_progress()
    print("-" * 50)
    print(f"Finished! Enriched data saved to: {output_file}")

if __name__ == "__main__":
    main()

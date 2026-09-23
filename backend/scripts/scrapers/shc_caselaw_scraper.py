"""
shc_caselaw_2026_scraper.py
────────────────────────────
Scrapes ALL 2026 cases from the Sindh High Court case-law portal
(https://caselaw.shc.gov.pk) and saves them to:
    backend/data/jsons/shc_2026_all_cases.json

Column mapping confirmed from live table inspection (16 cols total):
  col0 → record_id   col1 → sr_no       col2 → citation
  col4 → case_no     col6 → parties      col7 → bench
  col8 → date        pdf_link from <a> href
"""

import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

JS_EXTRACT = """
(year) => {
    const BASE = 'https://caselaw.shc.gov.pk/caselaw/';
    const rows = Array.from(document.querySelectorAll('#tblExport tbody tr'));
    return rows.map(row => {
        const cols = Array.from(row.querySelectorAll('td'));
        if (cols.length < 9) return null;

        const t = i => (cols[i]?.textContent || '').trim();

        // PDF / view link
        let pdfLink = '';
        for (const a of row.querySelectorAll('a')) {
            const href = a.getAttribute('href') || '';
            if (href.toLowerCase().includes('.pdf') || href.toLowerCase().includes('view')) {
                pdfLink = href.startsWith('http') ? href : BASE + href;
                break;
            }
        }

        return {
            record_id : t(0),
            sr_no     : t(1),
            citation  : t(2),
            case_no   : t(4),
            parties   : t(6),
            bench     : t(7),
            date      : t(8),
            year      : year,
            pdf_link  : pdfLink,
        };
    }).filter(Boolean);
}
"""


def scrape_shc(year: str = "2026"):
    url = "https://caselaw.shc.gov.pk/caselaw/pview.php?rpt=search"
    all_cases = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_navigation_timeout(120000)

        print("Opening SHC Case Law search page...")
        page.goto(url, wait_until="domcontentloaded")

        print("Waiting for #CASEYEAR field...")
        page.wait_for_selector("#CASEYEAR", timeout=60000)
        page.fill("#CASEYEAR", year)
        print(f"Typed '{year}' in Case Year field.")

        page.click("#AdvanceSearch")
        print("Search submitted. Waiting for results table...")

        try:
            page.wait_for_selector("#tblExport tbody tr", timeout=300000)  # 5 min
            time.sleep(5)  # let pagination settle
        except Exception as e:
            print(f"Timeout waiting for results: {e}")
            browser.close()
            return

        page_num = 1
        while True:
            rows = page.evaluate(JS_EXTRACT, year)
            print(f"  Page {page_num}: extracted {len(rows)} rows")
            all_cases.extend(rows)

            next_btn = page.locator(".paginate_button.next:not(.disabled)")
            if next_btn.count() > 0:
                print(f"  Moving to page {page_num + 1}...")
                next_btn.click()
                time.sleep(2)
                page_num += 1
            else:
                print(f"  Done. Total cases extracted: {len(all_cases)}")
                break

        browser.close()

    # ── Save to JSON ──────────────────────────────────────────────────────────
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "jsons"
    )
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"shc_{year}_all_cases.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Saved {len(all_cases)} cases → {output_file}")
    return output_file


if __name__ == "__main__":
    year_arg = sys.argv[1] if len(sys.argv) > 1 else "2026"
    scrape_shc(year=year_arg)

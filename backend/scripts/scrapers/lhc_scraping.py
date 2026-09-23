"""
Web scraper for Lahore High Court judgments
Scrapes all reported judgments from https://data.lhc.gov.pk/reported_judgments/judgments_approved_for_reporting
"""

import argparse
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from cyber_law_filter import (
    FILTER_PROFILE,
    attach_cyber_labels_to_judgment,
    lhc_cyber_classification,
    lhc_judgment_matches,
)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class LHCJudgmentScraper:
    def __init__(
        self,
        headless: bool = True,
        mode: str = "cyber",
        years: Optional[List[str]] = None,
    ):
        """Initialize the scraper with Chrome webdriver.

        mode: 'cyber' keeps only tech-law / cybercrime-related listings (metadata filter).
              'all' keeps every judgment (legacy behavior).
        years: if set, only these year values (must match dropdown values, e.g. '2024').
        """
        self.url = "https://data.lhc.gov.pk/reported_judgments/judgments_approved_for_reporting"
        self.driver = None
        self.headless = headless
        self.judgments = []
        self.mode = mode
        self.years_filter = years
        self.cyber_only = mode == "cyber"
        self.scrape_stats = {"total_seen": 0, "total_kept": 0}
        
    def setup_driver(self):
        """Setup Chrome webdriver with options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.page_load_strategy = 'none'  # Don't wait for full page load - just need DOM
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
    def close_driver(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()
            
    def get_available_years(self) -> List[str]:
        """Get all available years from the dropdown"""
        try:
            year_select = Select(self.driver.find_element(By.ID, "year"))
            years = [option.get_attribute("value") for option in year_select.options if option.get_attribute("value")]
            return years
        except Exception as e:
            print(f"Error getting years: {e}")
            return []
    
    def search_by_year(self, year: str):
        """Search judgments for a specific year"""
        try:
            # Wait for and select year
            year_select = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.ID, "year"))
            )
            select = Select(year_select)
            select.select_by_value(year)
            print(f"  Selected year: {year}")
            time.sleep(2)
            
            # Click submit button (it's an AJAX button with ID appjudgmentbtn)
            search_button = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.ID, "appjudgmentbtn"))
            )
            search_button.click()
            print(f"  Clicked submit, waiting for AJAX results...")
            
            # Wait for AJAX results to load
            time.sleep(10)
            
        except Exception as e:
            print(f"Error searching for year {year}: {e}")
    
    def extract_judgment_details(self, table_element) -> Dict:
        """Extract details from a single judgment table"""
        try:
            # Get all rows from this table
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 1:
                return None
            
            # First row contains the main data
            cells = rows[0].find_elements(By.TAG_NAME, "td")
            
            if len(cells) < 6:
                return None
            
            # Extract basic information
            sr_no = cells[0].text.strip()
            writ_petition = cells[1].text.strip()
            case_title = cells[2].text.strip()
            hon_judge = cells[3].text.strip()
            date_of_judgment = cells[4].text.strip()
            lhc_citation = cells[5].text.strip()
            
            # Extract PDF link if available
            pdf_link = None
            try:
                if len(cells) > 7:
                    pdf_element = cells[7].find_element(By.TAG_NAME, "a")
                    pdf_link = pdf_element.get_attribute("href")
            except NoSuchElementException:
                pass
            
            judgment = {
                "sr_no": sr_no,
                "case_title": case_title,
                "writ_petition": writ_petition,
                "date_of_judgment": date_of_judgment,
                "hon_judge": hon_judge,
                "lhc_citation": lhc_citation,
                "pdf_link": pdf_link,
                "scraped_at": datetime.now().isoformat()
            }
            
            return judgment
            
        except Exception as e:
            print(f"Error extracting judgment details: {e}")
            return None
    
    def scrape_current_page(self) -> Tuple[List[Dict], int, int]:
        """Scrape judgments from the current page.

        Returns (judgments, n_seen_raw, n_kept_after_filter).
        """
        judgments = []
        seen_raw = 0
        kept = 0
        
        try:
            # Wait for the results container
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "appjudgment"))
            )
            
            # Additional wait for AJAX content to fully load
            time.sleep(5)
            
            # Each judgment is in its own table within the appjudgment div
            app_div = self.driver.find_element(By.ID, "appjudgment")
            tables = app_div.find_elements(By.XPATH, ".//table[@width='100%']")
            
            print(f"  Found {len(tables)} tables")
            
            # Skip first table (it's the header)
            data_tables = tables[1:] if len(tables) > 1 else []
            
            for table in data_tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                # Each table has 2 rows: data row and tagline row
                if len(rows) >= 1:
                    judgment = self.extract_judgment_details(table)
                    if judgment:
                        seen_raw += 1
                        if self.cyber_only:
                            if not lhc_judgment_matches(judgment):
                                continue
                            cls = lhc_cyber_classification(judgment)
                            attach_cyber_labels_to_judgment(judgment, cls)
                        kept += 1
                        judgments.append(judgment)
                    
        except TimeoutException:
            print("  Timeout waiting for results")
        except Exception as e:
            print(f"  Error scraping page: {e}")
            import traceback
            traceback.print_exc()
            
        return judgments, seen_raw, kept
    
    def has_next_page(self) -> bool:
        """Check if there's a next page available"""
        try:
            # Look for pagination links
            next_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Next')]")
            return next_link.is_displayed()
        except NoSuchElementException:
            return False
    
    def go_to_next_page(self):
        """Navigate to the next page"""
        try:
            next_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Next')]")
            next_link.click()
            time.sleep(3)
        except Exception as e:
            print(f"Error navigating to next page: {e}")
    
    def scrape_all_pages_for_year(self, year: str) -> List[Dict]:
        """Scrape all pages for a given year"""
        print(f"Scraping year {year}...")
        year_judgments = []
        year_seen = 0
        year_kept = 0
        
        self.search_by_year(year)
        
        page_num = 1
        while True:
            print(f"  Scraping page {page_num}...")
            page_judgments, seen_page, kept_page = self.scrape_current_page()
            year_seen += seen_page
            year_kept += kept_page
            year_judgments.extend(page_judgments)
            if self.cyber_only:
                print(f"    Raw rows: {seen_page}, kept (cyber filter): {kept_page}")
            else:
                print(f"    Found {len(page_judgments)} judgments")
            
            if self.has_next_page():
                self.go_to_next_page()
                page_num += 1
            else:
                break
        
        self.scrape_stats["total_seen"] += year_seen
        self.scrape_stats["total_kept"] += year_kept
        if self.cyber_only:
            print(f"Year {year} summary: raw listings {year_seen}, kept after filter {year_kept}")
        print(f"Total judgments for {year}: {len(year_judgments)}")
        return year_judgments
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all judgments from all available years"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.setup_driver()
                print(f"Loading page (attempt {attempt + 1}/{max_retries})...")
                
                try:
                    self.driver.get(self.url)
                except Exception as e:
                    print(f"Page load error: {e}")
                    if attempt < max_retries - 1:
                        self.close_driver()
                        time.sleep(10)
                        continue
                    raise
                
                # Wait for page to load
                print("Waiting for page elements...")
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.ID, "year"))
                )
                print("Page loaded successfully")
                
                # Get all available years
                years = self.get_available_years()
                if self.years_filter:
                    allowed = set(self.years_filter)
                    years = [y for y in years if y in allowed]
                    print(f"Restricted to years {sorted(allowed)} -> {len(years)} to scrape: {years}")
                else:
                    print(f"Found {len(years)} years to scrape: {years}")
                
                self.scrape_stats = {"total_seen": 0, "total_kept": 0}
                
                # Scrape each year
                for year in years:
                    year_judgments = self.scrape_all_pages_for_year(year)
                    self.judgments.extend(year_judgments)
                    
                    # Return to main page for next year
                    print(f"Returning to main page...")
                    try:
                        self.driver.get(self.url)
                        time.sleep(5)
                    except Exception as e:
                        print(f"Error returning to main page: {e}")
                        break
                
                print(f"\nTotal judgments scraped: {len(self.judgments)}")
                break
                
            except Exception as e:
                print(f"Error during scraping (attempt {attempt + 1}): {e}")
                import traceback
                traceback.print_exc()
                if attempt < max_retries - 1:
                    print(f"Retrying in 15 seconds...")
                    self.close_driver()
                    time.sleep(15)
                else:
                    print(f"Failed after {max_retries} attempts")
                
            finally:
                if attempt == max_retries - 1 or len(self.judgments) > 0:
                    self.close_driver()
            
        return self.judgments
    
    def save_to_json(self, filename: str = "lhc_judgments.json"):
        """Save scraped judgments to a JSON file"""
        meta = {
            "source": self.url,
            "scraped_at": datetime.now().isoformat(),
            "total_count": len(self.judgments),
            "scrape_mode": self.mode,
        }
        if self.cyber_only:
            meta["domain_filter"] = "cyber_law"
            meta["filter_profile"] = FILTER_PROFILE
            meta["counts"] = {
                "raw_listings_seen": self.scrape_stats.get("total_seen", 0),
                "kept_after_filter": self.scrape_stats.get("total_kept", 0),
            }
        if self.years_filter:
            meta["years_filter"] = list(self.years_filter)

        output = {
            "metadata": meta,
            "judgments": self.judgments
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Data saved to {filename}")


def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(description="Lahore High Court judgment scraper")
    parser.add_argument(
        "--mode",
        choices=["all", "cyber"],
        default="cyber",
        help="cyber: keep only tech/cyber-law-related listings (default). all: no metadata filter.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: lhc_judgments.json or lhc_judgments_cyber.json when mode=cyber)",
    )
    parser.add_argument(
        "--year",
        action="append",
        dest="years",
        metavar="YEAR",
        default=None,
        help="Only scrape this year (repeatable). Must match site dropdown value e.g. 2024",
    )
    parser.add_argument("--headed", action="store_true", help="Run browser with UI (not headless)")
    args = parser.parse_args()

    out = args.output
    if not out:
        out = "lhc_judgments_cyber.json" if args.mode == "cyber" else "lhc_judgments.json"

    print("Starting LHC Judgment Scraper...")
    print("=" * 50)
    print(f"Mode: {args.mode}, output: {out}")
    if args.years:
        print(f"Years filter: {args.years}")

    scraper = LHCJudgmentScraper(
        headless=not args.headed,
        mode=args.mode,
        years=args.years,
    )
    judgments = scraper.scrape_all()
    
    if judgments:
        scraper.save_to_json(out)
        print("\nScraping completed successfully!")
    else:
        print("\nNo judgments were scraped.")


if __name__ == "__main__":
    main()

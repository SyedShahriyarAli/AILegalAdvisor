import urllib.request
import json
import os
import sys
from bs4 import BeautifulSoup

# Add current dir to path to import cyber_law_filter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cyber_law_filter import judgment_matches_cyber_law

def scrape_phc_judgments():
    url = "https://peshawarhighcourt.gov.pk/PHCCMS/reportedJudgments.php?action=search"
    print(f"Fetching data from {url}...")
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    html_content = response.read().decode('utf-8', errors='replace')
    
    print("Parsing HTML...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # The table has id "employee_list"
    table = soup.find('table', {'id': 'employee_list'})
    if not table:
        print("Error: Could not find the results table.")
        return
        
    tbody = table.find('tbody')
    rows = tbody.find_all('tr') if tbody else []
    print(f"Found {len(rows)} cases. Filtering for cyber law...")
    
    filtered_cases = []
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 9:
            continue
            
        s_no = cols[0].text.strip()
        case_title = cols[1].text.strip()
        remarks = cols[2].text.strip()
        other_citation = cols[3].text.strip()
        phc_neutral_citation = cols[4].text.strip()
        decision_date = cols[5].text.strip()
        category = cols[7].text.strip()
        
        # Extract Judgment PDF link
        judgment_link = ""
        a_tag = cols[8].find('a')
        if a_tag and a_tag.has_attr('href'):
            judgment_link = a_tag['href']
            
        # Strict cyber crime filtering
        blob = f"{case_title} {remarks}"
        blob_lower = blob.lower()
        strict_phrases = [
            "cyber crime", "cybercrime", "prevention of electronic crimes", 
            "peca", "electronic crimes act", "electronic crime",
            "cyber terrorism", "cyber stalking", "cyber fraud", "fia cyber"
        ]
        
        is_cyber_crime = any(phrase in blob_lower for phrase in strict_phrases)
        
        if is_cyber_crime:
            filtered_cases.append({
                "s_no": s_no,
                "case_title": case_title,
                "remarks": remarks,
                "other_citation": other_citation,
                "phc_neutral_citation": phc_neutral_citation,
                "decision_date": decision_date,
                "category": category,
                "judgment_link": judgment_link
            })
            
    print(f"Filtering complete. Found {len(filtered_cases)} cyber law related cases.")
    
    # Save to JSON
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'jsons')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'peshawar-high-court-cyber-cases.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_cases, f, indent=4, ensure_ascii=False)
        
    print(f"Saved results to {output_file}")

if __name__ == "__main__":
    scrape_phc_judgments()

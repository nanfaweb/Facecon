import urllib.request
import ssl
from bs4 import BeautifulSoup
import pandas as pd
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv('pgp_cleaned_full.csv')
candidates = df[df['genetic_data_status'].isin(['uploaded', 'planned'])]
print(f"Total candidates: {len(candidates)} (uploaded: {(candidates.genetic_data_status == 'uploaded').sum()}, planned: {(candidates.genetic_data_status == 'planned').sum()})")

sample_pids = candidates['participant_id'].head(6).tolist()

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AcademicResearchBot/1.0 (PGP Phenotype-Genotype Study; contact: research@pgp-study.edu)'
}

for pid in sample_pids:
    url = f'https://my.pgp-hms.org/profile/{pid}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
            soup = BeautifulSoup(html, 'html.parser')
            print(f"\n==================================================")
            print(f"PID: {pid} (HTTP {resp.status}) - {url}")
            print(f"==================================================")
            
            # Find all download links or files
            # Look for links with /profile/ or /user_file/ or download
            all_links = soup.find_all('a')
            print(f"Total <a> tags: {len(all_links)}")
            found_files = []
            for a in all_links:
                href = a.get('href', '')
                text = a.get_text(strip=True)
                if '/user_file/download/' in href or 'download' in href.lower() or '23andme' in text.lower() or 'ancestry' in text.lower() or 'family' in text.lower():
                    # check parent row or container
                    parent_text = a.parent.get_text(' ', strip=True) if a.parent else ''
                    found_files.append((text, href, parent_text))
            
            if found_files:
                for f_text, f_href, f_parent in found_files:
                    print(f"  Found Link: '{f_text}' -> {f_href}")
                    print(f"    Context: {f_parent[:150]}")
            else:
                print("  No file download links found in profile.")
                
            # Print sections/headings on the page
            headings = [h.get_text(strip=True) for h in soup.find_all(['h2', 'h3', 'h4'])]
            print(f"  Page Headings: {headings}")
            
    except Exception as e:
        print(f"\nPID: {pid} Error: {e}")
    time.sleep(1)

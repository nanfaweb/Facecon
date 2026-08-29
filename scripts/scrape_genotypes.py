import urllib.request
import ssl
from bs4 import BeautifulSoup
import pandas as pd
import time
import sys
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://my.pgp-hms.org'
INPUT_FILE = 'pgp_cleaned_full.csv'
OUTPUT_FILE = 'pgp_genotype_matches.csv'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AcademicResearchBot/1.0 (PGP Genotype-Phenotype Study; research@pgp-study.edu)'

# SSL Context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

def identify_genotype_file(soup):
    """
    Parses table rows looking for 23andMe, AncestryDNA, FamilyTreeDNA genotype files.
    Returns: (has_file, file_type, file_url, note)
    """
    # Look for tables under "Uploaded data" or any table with file downloads
    candidate_files = []
    
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for tr in rows:
            tds = tr.find_all('td')
            if not tds:
                continue
            row_text = ' '.join(td.get_text(' ', strip=True) for td in tds)
            row_lower = row_text.lower()
            
            # Find download link in row
            download_links = []
            for a in tr.find_all('a'):
                href = a.get('href', '')
                text = a.get_text(strip=True)
                if 'download' in href.lower() or 'download' in text.lower() or '/user_file/download/' in href or 'genome_download.php' in href:
                    download_links.append(urljoin(BASE_URL, href))
            
            if not download_links:
                continue
            
            # Check for target genotype data types / names
            # Skip BAM / FASTQ / Microbiome
            if any(k in row_lower for k in ['bam', 'fastq', 'microbiome', 'cram']):
                continue
                
            dl_url = download_links[0]
            
            if '23andme' in row_lower:
                candidate_files.append(('23andMe', dl_url, row_text))
            elif 'ancestry' in row_lower:
                candidate_files.append(('AncestryDNA', dl_url, row_text))
            elif 'family tree dna' in row_lower or 'familytree' in row_lower or 'ftdna' in row_lower:
                candidate_files.append(('FamilyTreeDNA', dl_url, row_text))
            elif 'complete genomics' in row_lower:
                # Complete genomics / whole genome master var / CGI
                # We can note it if no consumer array is present
                candidate_files.append(('Complete Genomics (CGI)', dl_url, row_text))
            elif 'vcf' in row_lower:
                candidate_files.append(('VCF', dl_url, row_text))
    
    # Priority selection: 23andMe > AncestryDNA > FamilyTreeDNA > other
    if candidate_files:
        for ftype in ['23andMe', 'AncestryDNA', 'FamilyTreeDNA']:
            for f in candidate_files:
                if f[0] == ftype:
                    return True, f[0], f[1], f"Found {f[0]} genotype file"
        # Fallback to first candidate if consumer array wasn't found
        first = candidate_files[0]
        return True, first[0], first[1], f"Found {first[0]} file"
        
    return False, None, None, "No microarray/genotype file listed on profile"

def main():
    print("=" * 80)
    print("PGP GENOTYPE SCRAPER & VERIFIER")
    print("=" * 80)
    
    # 1. Load input dataset
    df = pd.read_csv(INPUT_FILE)
    candidates = df[df['genetic_data_status'].isin(['uploaded', 'planned'])].copy()
    total_candidates = len(candidates)
    
    n_uploaded = (candidates['genetic_data_status'] == 'uploaded').sum()
    n_planned = (candidates['genetic_data_status'] == 'planned').sum()
    
    print(f"Loaded {len(df)} total participants from {INPUT_FILE}.")
    print(f"Filtered to {total_candidates} candidates:")
    print(f"  • 'uploaded': {n_uploaded}")
    print(f"  • 'planned': {n_planned}")
    print("Starting polite crawl with 2.0s delay per request...")
    print("-" * 80)
    
    results = []
    
    for i, (idx, row) in enumerate(candidates.iterrows(), 1):
        pid = row['participant_id']
        status_2018 = row['genetic_data_status']
        profile_url = f"{BASE_URL}/profile/{pid}"
        
        has_file = False
        file_type = None
        file_url = None
        status_note = ""
        
        try:
            req = urllib.request.Request(profile_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                if resp.status == 200:
                    html = resp.read().decode('utf-8', errors='replace')
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Check if profile is private or not found
                    page_text = soup.get_text()
                    if "You are not authorized to access this page" in page_text or "Private Profile" in page_text:
                        has_file = False
                        status_note = "Profile is private/restricted"
                    elif "Participant not found" in page_text or "The page you were looking for doesn't exist" in page_text:
                        has_file = False
                        status_note = "Participant profile does not exist"
                    else:
                        has_file, file_type, file_url, status_note = identify_genotype_file(soup)
                else:
                    status_note = f"HTTP status {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                status_note = "Profile 404 Not Found"
            elif e.code == 403:
                status_note = "Profile 403 Forbidden / Private"
            else:
                status_note = f"HTTP Error {e.code}"
        except Exception as e:
            status_note = f"Connection error: {str(e)[:50]}"
            
        results.append({
            'participant_id': pid,
            'genetic_data_status': status_2018,
            'has_genotype_file': has_file,
            'file_type': file_type if file_type else '',
            'file_url': file_url if file_url else '',
            'status_note': status_note
        })
        
        match_str = f"MATCH: {file_type} ({file_url})" if has_file else f"NO FILE ({status_note})"
        print(f"[{i:03d}/{total_candidates:03d}] {pid} (2018: {status_2018:<8}) -> {match_str}")
        
        # Polite delay
        time.sleep(2.0)
        
    df_out = pd.DataFrame(results)
    df_out.to_csv(OUTPUT_FILE, index=False)
    print("\n" + "=" * 80)
    print(f"Saved results to {OUTPUT_FILE}")
    print("=" * 80)
    
    # Generate Summary Breakdown
    print("\nSUMMARY OF GENOTYPE AVAILABILITY BREAKDOWN:")
    print("-" * 80)
    
    # Uploaded Group
    up_sub = df_out[df_out['genetic_data_status'] == 'uploaded']
    up_total = len(up_sub)
    up_confirmed = (up_sub['has_genotype_file'] == True).sum()
    up_discrepancy = up_total - up_confirmed
    
    print(f"1. Self-reported 'uploaded' group (Total: {up_total}):")
    print(f"   • Confirmed file present today: {up_confirmed} ({up_confirmed/up_total*100:.1f}%)")
    print(f"   • Discrepancy (self-reported uploaded, but no file found today): {up_discrepancy} ({up_discrepancy/up_total*100:.1f}%)")
    if up_confirmed > 0:
        print("   • Confirmed file types breakdown:")
        for ft, count in up_sub[up_sub['has_genotype_file'] == True]['file_type'].value_counts().items():
            print(f"     - {ft}: {count}")
            
    # Planned Group
    pl_sub = df_out[df_out['genetic_data_status'] == 'planned']
    pl_total = len(pl_sub)
    pl_confirmed = (pl_sub['has_genotype_file'] == True).sum()
    pl_none = pl_total - pl_confirmed
    
    print(f"\n2. Self-reported 'planned' group (Total: {pl_total}):")
    print(f"   • Followed through (confirmed file present today): {pl_confirmed} ({pl_confirmed/pl_total*100:.1f}%)")
    print(f"   • Still none / no file found: {pl_none} ({pl_none/pl_total*100:.1f}%)")
    if pl_confirmed > 0:
        print("   • Confirmed file types breakdown:")
        for ft, count in pl_sub[pl_sub['has_genotype_file'] == True]['file_type'].value_counts().items():
            print(f"     - {ft}: {count}")
            
    # Overall Combined
    total_confirmed = (df_out['has_genotype_file'] == True).sum()
    print(f"\n3. Overall Confirmed Genotype Files (Combined across both groups):")
    print(f"   • Total Confirmed Available: {total_confirmed} / {total_candidates} ({total_confirmed/total_candidates*100:.1f}%)")
    print("   • Overall file types breakdown:")
    for ft, count in df_out[df_out['has_genotype_file'] == True]['file_type'].value_counts().items():
        print(f"     - {ft}: {count}")
    print("=" * 80)

if __name__ == '__main__':
    main()

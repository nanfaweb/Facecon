import sys
import io
import gzip
import zipfile
import urllib.request
import ssl
import pandas as pd
import time

sys.stdout.reconfigure(encoding='utf-8')

INPUT_FILE = 'pgp_genotype_matches.csv'
OUTPUT_FILE = 'pgp_snp_coverage.csv'

# HIrisPlex-S Panel Definition (41 SNPs total)
# 1. Eye color model: 6 SNPs
EYE_SNPS = {
    'rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592'
}

# 2. Hair color model: 22 SNPs
HAIR_SNPS = {
    'rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592',
    'rs1805007', 'rs1805008', 'rs1805009', 'rs11547464', 'rs885479', 'rs2228479',
    'rs1110400', 'rs1805006', 'rs1805005', 'rs312262906', 'rs1042602', 'rs28777',
    'rs2402130', 'rs12821256', 'rs683', 'rs2378249'
}

# 3. Skin color model: 36 SNPs
SKIN_SNPS = {
    # 19 overlapping from HIrisPlex
    'rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592',
    'rs1805007', 'rs1805008', 'rs1805009', 'rs11547464', 'rs885479', 'rs2228479',
    'rs1110400', 'rs1805006', 'rs1805005', 'rs1042602', 'rs28777', 'rs2402130', 'rs683',
    # 17 skin-specific additions
    'rs3114908', 'rs10756819', 'rs17128291', 'rs2238289', 'rs6497292', 'rs1129038',
    'rs1667394', 'rs1126809', 'rs1470608', 'rs1800414', 'rs12441727', 'rs1545397',
    'rs1426654', 'rs6119471', 'rs6059655', 'rs3212355', 'rs8051733'
}

ALL_41_SNPS = EYE_SNPS | HAIR_SNPS | SKIN_SNPS

# SSL & Request Headers
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AcademicResearchBot/1.0 (PGP Genotype-Phenotype Study; research@pgp-study.edu)'
}

def parse_genotype_stream(file_stream, is_vcf=False):
    """
    Scans a text line generator/stream and extracts present rsIDs.
    Returns: (parse_success, set_of_present_rsids, total_snps_counted)
    """
    present_rsids = set()
    total_lines_read = 0
    
    try:
        for line in file_stream:
            total_lines_read += 1
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
                
            line_str = line.strip()
            if not line_str or line_str.startswith('#'):
                continue
                
            if is_vcf:
                # VCF format: CHROM POS ID REF ALT ...
                parts = line_str.split('\t')
                if len(parts) >= 3:
                    var_id = parts[2].strip()
                    if var_id and var_id != '.':
                        for single_id in var_id.split(';'):
                            s_id = single_id.strip().lower()
                            if s_id in ALL_41_SNPS:
                                present_rsids.add(s_id)
            else:
                # 23andMe / Ancestry / FTDNA: rsid chromosome position genotype
                # Tab, comma, or space separated
                parts = line_str.replace(',', '\t').split('\t')
                if parts:
                    rs_col = parts[0].strip().strip('"').lower()
                    if rs_col in ALL_41_SNPS:
                        present_rsids.add(rs_col)
                        
        parse_success = total_lines_read > 5
        return parse_success, present_rsids, total_lines_read
    except Exception as e:
        return False, present_rsids, total_lines_read

def download_and_parse(url, file_type):
    """
    Downloads file from URL and parses SNPs.
    Handles GZIP, ZIP, and Plain Text automatically.
    """
    req = urllib.request.Request(url, headers=HEADERS)
    is_vcf = (file_type == 'VCF')
    
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        # Check HTTP status
        if resp.status != 200:
            return False, set(), f"HTTP error {resp.status}"
            
        raw_bytes = resp.read()
        
        # Detect ZIP
        if raw_bytes.startswith(b'PK\x03\x04'):
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                namelist = zf.namelist()
                text_files = [n for n in namelist if not n.endswith('/') and not n.startswith('__MACOSX')]
                if not text_files:
                    return False, set(), "Empty zip file"
                with zf.open(text_files[0]) as inner_f:
                    text_stream = io.TextIOWrapper(inner_f, encoding='utf-8', errors='ignore')
                    success, snps, count = parse_genotype_stream(text_stream, is_vcf=is_vcf)
                    return success, snps, f"Zip parsed ({count} rows)"
                    
        # Detect GZIP
        elif raw_bytes.startswith(b'\x1f\x8b'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw_bytes)) as gz:
                text_stream = io.TextIOWrapper(gz, encoding='utf-8', errors='ignore')
                success, snps, count = parse_genotype_stream(text_stream, is_vcf=is_vcf)
                return success, snps, f"Gzip parsed ({count} rows)"
                
        # Plain text
        else:
            # Check if it's an HTML error page
            if b'<html' in raw_bytes[:200].lower() or b'<!doctype html' in raw_bytes[:200].lower():
                return False, set(), "Received HTML page instead of genotype file"
            text_stream = io.StringIO(raw_bytes.decode('utf-8', errors='ignore'))
            success, snps, count = parse_genotype_stream(text_stream, is_vcf=is_vcf)
            return success, snps, f"Text parsed ({count} rows)"

def main():
    print("=" * 80)
    print("HIrisPlex-S SNP COVERAGE ANALYZER (41 SNPs)")
    print("=" * 80)
    print(f"HIrisPlex-S Trait SNP Panel Breakdown:")
    print(f"  • Eye Color Model:  {len(EYE_SNPS)} SNPs (including rs12913832)")
    print(f"  • Hair Color Model: {len(HAIR_SNPS)} SNPs")
    print(f"  • Skin Color Model: {len(SKIN_SNPS)} SNPs")
    print(f"  • Total Unique SNPs: {len(ALL_41_SNPS)} SNPs")
    print("-" * 80)
    
    # 1. Load confirmed matches
    df_matches = pd.read_csv(INPUT_FILE)
    targets = df_matches[df_matches['has_genotype_file'] == True].copy()
    targets = targets[targets['file_type'].isin(['23andMe', 'FamilyTreeDNA', 'AncestryDNA', 'VCF'])].copy()
    
    total_targets = len(targets)
    print(f"Loaded {len(df_matches)} rows from {INPUT_FILE}.")
    print(f"Filtered to {total_targets} target participants (excluding CGI):")
    for ft, cnt in targets['file_type'].value_counts().items():
        print(f"  - {ft}: {cnt}")
    print("-" * 80)
    print("Downloading and analyzing SNP coverage per participant...")
    print("-" * 80)
    
    results = []
    
    for i, (idx, row) in enumerate(targets.iterrows(), 1):
        pid = row['participant_id']
        ftype = row['file_type']
        furl = row['file_url']
        
        parse_success = False
        eye_count = 0
        hair_count = 0
        skin_count = 0
        rs12913832_present = False
        log_msg = ""
        
        try:
            success, found_snps, msg = download_and_parse(furl, ftype)
            parse_success = success
            log_msg = msg
            
            if parse_success:
                eye_count = len(found_snps & EYE_SNPS)
                hair_count = len(found_snps & HAIR_SNPS)
                skin_count = len(found_snps & SKIN_SNPS)
                rs12913832_present = ('rs12913832' in found_snps)
        except Exception as e:
            parse_success = False
            log_msg = f"Download/parse error: {str(e)[:40]}"
            
        results.append({
            'participant_id': pid,
            'file_type': ftype,
            'parse_success': parse_success,
            'eye_snps_present': eye_count,
            'hair_snps_present': hair_count,
            'skin_snps_present': skin_count,
            'rs12913832_present': rs12913832_present
        })
        
        rs_tag = "rs12913832: YES" if rs12913832_present else "rs12913832: NO"
        if parse_success:
            print(f"[{i:02d}/{total_targets:02d}] {pid} ({ftype:<13}) -> OK | Eye: {eye_count}/6 | Hair: {hair_count:02d}/22 | Skin: {skin_count:02d}/36 | {rs_tag}")
        else:
            print(f"[{i:02d}/{total_targets:02d}] {pid} ({ftype:<13}) -> FAILED: {log_msg}")
            
        # Polite pause
        time.sleep(0.5)
        
    df_res = pd.DataFrame(results)
    df_res.to_csv(OUTPUT_FILE, index=False)
    print("\n" + "=" * 80)
    print(f"Saved SNP coverage results to: {OUTPUT_FILE}")
    print("=" * 80)
    
    # Summary per trait
    valid_parsed = df_res[df_res['parse_success'] == True]
    n_parsed = len(valid_parsed)
    
    print("\nHIRISPLEX-S SNP COVERAGE SUMMARY REPORT")
    print("-" * 80)
    print(f"Total Target Participants Crawled: {total_targets}")
    print(f"Successfully Parsed Genotype Files: {n_parsed} / {total_targets} ({n_parsed/total_targets*100:.1f}%)")
    print(f"Failed to Parse / Incompatible Format: {total_targets - n_parsed}")
    print("-" * 80)
    
    # 80% Thresholds:
    # Eye: >= 5 / 6 (83.3%)
    # Hair: >= 18 / 22 (81.8%)
    # Skin: >= 29 / 36 (80.6%)
    eye_80 = (valid_parsed['eye_snps_present'] >= 5).sum()
    eye_full = (valid_parsed['eye_snps_present'] == 6).sum()
    
    hair_80 = (valid_parsed['hair_snps_present'] >= 18).sum()
    hair_full = (valid_parsed['hair_snps_present'] == 22).sum()
    
    skin_80 = (valid_parsed['skin_snps_present'] >= 29).sum()
    skin_full = (valid_parsed['skin_snps_present'] == 36).sum()
    
    rs129_count = (valid_parsed['rs12913832_present'] == True).sum()
    
    print("1. EYE COLOR MODEL (6 SNPs total, including rs12913832):")
    print(f"   • Full Coverage (6/6 SNPs):      {eye_full} / {n_parsed} parsed ({eye_full/total_targets*100:.1f}% of all {total_targets})")
    print(f"   • >= 80% Coverage (>= 5/6 SNPs):  {eye_80} / {n_parsed} parsed ({eye_80/total_targets*100:.1f}% of all {total_targets})")
    print(f"   • Primary Predictor rs12913832:   {rs129_count} / {n_parsed} parsed ({rs129_count/total_targets*100:.1f}%)")
    
    print("\n2. HAIR COLOR MODEL (22 SNPs total):")
    print(f"   • Full Coverage (22/22 SNPs):    {hair_full} / {n_parsed} parsed ({hair_full/total_targets*100:.1f}% of all {total_targets})")
    print(f"   • >= 80% Coverage (>= 18/22 SNPs): {hair_80} / {n_parsed} parsed ({hair_80/total_targets*100:.1f}% of all {total_targets})")
    
    print("\n3. SKIN COLOR MODEL (36 SNPs total):")
    print(f"   • Full Coverage (36/36 SNPs):    {skin_full} / {n_parsed} parsed ({skin_full/total_targets*100:.1f}% of all {total_targets})")
    print(f"   • >= 80% Coverage (>= 29/36 SNPs): {skin_80} / {n_parsed} parsed ({skin_80/total_targets*100:.1f}% of all {total_targets})")
    print("=" * 80)

if __name__ == '__main__':
    main()

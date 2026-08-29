import sys
import io
import gzip
import zipfile
import urllib.request
import ssl
import json
import pandas as pd
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding='utf-8')

MATCHES_FILE = 'pgp_genotype_matches.csv'
CLEANED_FULL_FILE = 'pgp_cleaned_full.csv'
COVERAGE_OUTPUT_FILE = 'pgp_snp_coverage.csv'

# Panel Definitions
EYE_SNPS = ['rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592']

HAIR_SNPS = [
    'rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592',
    'rs1805007', 'rs1805008', 'rs1805009', 'rs11547464', 'rs885479', 'rs2228479',
    'rs1110400', 'rs1805006', 'rs1805005', 'rs312262906', 'rs1042602', 'rs28777',
    'rs2402130', 'rs12821256', 'rs683', 'rs2378249'
]

# Reduced Skin Panel (20 SNPs: 19 shared + rs1426654)
SKIN_REDUCED_SNPS = [
    'rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592',
    'rs1805007', 'rs1805008', 'rs1805009', 'rs11547464', 'rs885479', 'rs2228479',
    'rs1110400', 'rs1805006', 'rs1805005', 'rs1042602', 'rs28777', 'rs2402130', 'rs683',
    'rs1426654'
]

# Full 36 Skin Panel for comparison
SKIN_FULL_SNPS = [
    'rs12913832', 'rs1800407', 'rs12896399', 'rs16891982', 'rs1393350', 'rs12203592',
    'rs1805007', 'rs1805008', 'rs1805009', 'rs11547464', 'rs885479', 'rs2228479',
    'rs1110400', 'rs1805006', 'rs1805005', 'rs1042602', 'rs28777', 'rs2402130', 'rs683',
    'rs3114908', 'rs10756819', 'rs17128291', 'rs2238289', 'rs6497292', 'rs1129038',
    'rs1667394', 'rs1126809', 'rs1470608', 'rs1800414', 'rs12441727', 'rs1545397',
    'rs1426654', 'rs6119471', 'rs6059655', 'rs3212355', 'rs8051733'
]

ALL_TRACKED_SNPS = sorted(list(set(EYE_SNPS) | set(HAIR_SNPS) | set(SKIN_FULL_SNPS)))

# GRCh37 / hg19 Coordinates for all tracked SNPs (for VCF mapping)
GRCH37_COORDS = {
    'rs1042602': ('11', 88911696),
    'rs10756819': ('9', 16858084),
    'rs1110400': ('16', 89986130),
    'rs1126809': ('11', 89017961),
    'rs1129038': ('15', 28356859),
    'rs11547464': ('16', 89986091),
    'rs12203592': ('6', 396321),
    'rs12441727': ('15', 28271775),
    'rs12821256': ('12', 89328335),
    'rs12896399': ('14', 92773663),
    'rs12913832': ('15', 28365618),
    'rs1393350': ('11', 89011046),
    'rs1426654': ('15', 48426484),
    'rs1470608': ('15', 28288121),
    'rs1545397': ('15', 28187772),
    'rs1667394': ('15', 28530182),
    'rs16891982': ('5', 33951693),
    'rs17128291': ('14', 92882826),
    'rs1800407': ('15', 28230318),
    'rs1800414': ('15', 28197037),
    'rs1805005': ('16', 89985844),
    'rs1805006': ('16', 89985918),
    'rs1805007': ('16', 89986117),
    'rs1805008': ('16', 89986144),
    'rs1805009': ('16', 89986546),
    'rs2228479': ('16', 89985940),
    'rs2238289': ('15', 28453215),
    'rs2378249': ('20', 33218090),
    'rs2402130': ('14', 92801203),
    'rs28777': ('5', 33958959),
    'rs3114908': ('16', 89383725),
    'rs312262906': ('16', 89985751),
    'rs3212355': ('16', 89984378),
    'rs6059655': ('20', 32665748),
    'rs6119471': ('20', 32785212),
    'rs6497292': ('15', 28496195),
    'rs683': ('9', 12709305),
    'rs8051733': ('16', 90024206),
    'rs885479': ('16', 89986154)
}

# Inverted mapping: (chr_norm, pos) -> rsID
COORD_TO_RSID = {}
for rs, (c, p) in GRCH37_COORDS.items():
    c_clean = str(c).replace('chr', '').upper()
    COORD_TO_RSID[(c_clean, p)] = rs

# SSL Context & Headers
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AcademicResearchBot/1.0 (PGP Genotype-Phenotype Study; research@pgp-study.edu)'
}

def parse_genotype_lines(lines_iter, is_vcf=False):
    """
    Parses lines from a genotype file stream and extracts present rsIDs and their genotypes.
    Returns: (parse_success, dict_of_genotypes {rsid: genotype_str}, note)
    """
    genotypes = {}
    total_lines = 0
    
    for line in lines_iter:
        total_lines += 1
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        line_str = line.strip()
        if not line_str or line_str.startswith('#'):
            continue
            
        if is_vcf:
            parts = line_str.split('\t')
            if len(parts) >= 5:
                chrom = parts[0].replace('chr', '').strip().upper()
                try:
                    pos = int(parts[1].strip())
                except:
                    continue
                var_id = parts[2].strip().lower()
                ref = parts[3].strip()
                alt = parts[4].strip()
                
                # Determine rsID either by ID column or by genomic coordinate (hg19)
                target_rs = None
                if var_id and var_id in ALL_TRACKED_SNPS:
                    target_rs = var_id
                elif (chrom, pos) in COORD_TO_RSID:
                    target_rs = COORD_TO_RSID[(chrom, pos)]
                    
                if target_rs:
                    # Parse sample genotype if present
                    gt_call = f"{ref}/{alt}"
                    if len(parts) >= 10:
                        fmt = parts[8].split(':')
                        sample = parts[9].split(':')
                        if 'GT' in fmt:
                            gt_idx = fmt.index('GT')
                            gt_val = sample[gt_idx]
                            alleles = [ref] + alt.split(',')
                            if '/' in gt_val or '|' in gt_val:
                                sep = '/' if '/' in gt_val else '|'
                                indices = gt_val.split(sep)
                                try:
                                    gt_call = ''.join(alleles[int(ix)] for ix in indices if ix.isdigit())
                                except:
                                    pass
                    genotypes[target_rs] = gt_call
        else:
            # 23andMe / Ancestry / FTDNA table
            parts = line_str.replace(',', '\t').split('\t')
            if parts:
                rs_col = parts[0].strip().strip('"').lower()
                if rs_col in ALL_TRACKED_SNPS:
                    gt_val = parts[-1].strip().strip('"').upper()
                    genotypes[rs_col] = gt_val
                    
    if total_lines < 5:
        return False, {}, "Empty file (< 5 lines)"
    return True, genotypes, f"Parsed {total_lines} lines"

def fetch_and_parse_file(url, file_type):
    """
    Downloads and parses a file from URL.
    Handles direct files, Arvados HTML collection pages, ZIP, GZIP, and plain text.
    """
    is_vcf = (file_type == 'VCF')
    req = urllib.request.Request(url, headers=HEADERS)
    
    with urllib.request.urlopen(req, context=ctx, timeout=45) as resp:
        content = resp.read()
        final_url = resp.url
        
        # Check if response is an Arvados HTML collection page
        if content.startswith(b'<!DOCTYPE') or b'<html' in content[:200].lower():
            soup = BeautifulSoup(content.decode('utf-8', errors='ignore'), 'html.parser')
            # Look for item link
            item_a = soup.find('a', class_='item')
            if not item_a:
                # Find any link ending with .txt, .csv, .vcf, .gz, .zip
                for a in soup.find_all('a'):
                    href = a.get('href', '')
                    if any(ext in href.lower() for ext in ['.txt', '.csv', '.vcf', '.gz', '.zip', '.tsv']):
                        item_a = a
                        break
            if item_a:
                direct_url = urljoin(final_url, item_a['href'])
                req2 = urllib.request.Request(direct_url, headers=HEADERS)
                with urllib.request.urlopen(req2, context=ctx, timeout=45) as resp2:
                    content = resp2.read()
            else:
                return False, {}, "Unresolvable HTML collection page"
                
        # Check for mitochondrial FASTA
        if content.startswith(b'LOCUS') and b'mitochondrion' in content[:300].lower():
            return False, {}, "Mitochondrial FASTA sequence (permanently excluded)"
        if content.startswith(b'>') and (b'chrM' in content[:100] or b'mitochondria' in content[:100].lower()):
            return False, {}, "Mitochondrial FASTA sequence (permanently excluded)"
            
        # Parse ZIP
        if content.startswith(b'PK\x03\x04'):
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = [n for n in zf.namelist() if not n.endswith('/') and not n.startswith('__MACOSX')]
                if not namelist:
                    return False, {}, "Empty ZIP archive"
                with zf.open(namelist[0]) as inner_f:
                    text_stream = io.TextIOWrapper(inner_f, encoding='utf-8', errors='ignore')
                    return parse_genotype_lines(text_stream, is_vcf=is_vcf)
                    
        # Parse GZIP
        elif content.startswith(b'\x1f\x8b'):
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                text_stream = io.TextIOWrapper(gz, encoding='utf-8', errors='ignore')
                return parse_genotype_lines(text_stream, is_vcf=is_vcf)
                
        # Plain text
        else:
            text_stream = io.StringIO(content.decode('utf-8', errors='ignore'))
            return parse_genotype_lines(text_stream, is_vcf=is_vcf)

def main():
    print("=" * 80)
    print("PART 1: RECOVERY PASS & GENOTYPE PARSING")
    print("=" * 80)
    
    df_matches = pd.read_csv(MATCHES_FILE)
    targets = df_matches[df_matches['has_genotype_file'] == True].copy()
    targets = targets[targets['file_type'].isin(['23andMe', 'FamilyTreeDNA', 'AncestryDNA', 'VCF'])].copy()
    
    print(f"Total target candidate records: {len(targets)}")
    
    recovered_results = []
    participant_genotypes = {} # pid -> {rsid: gt}
    
    for i, (idx, row) in enumerate(targets.iterrows(), 1):
        pid = row['participant_id']
        ftype = row['file_type']
        furl = row['file_url']
        
        success, gts, note = False, {}, ""
        try:
            success, gts, note = fetch_and_parse_file(furl, ftype)
        except Exception as e:
            success = False
            note = f"Error: {str(e)[:40]}"
            
        eye_cnt = sum(1 for rs in EYE_SNPS if rs in gts)
        hair_cnt = sum(1 for rs in HAIR_SNPS if rs in gts)
        skin_red_cnt = sum(1 for rs in SKIN_REDUCED_SNPS if rs in gts)
        skin_full_cnt = sum(1 for rs in SKIN_FULL_SNPS if rs in gts)
        rs129_pres = ('rs12913832' in gts)
        
        participant_genotypes[pid] = gts
        
        recovered_results.append({
            'participant_id': pid,
            'file_type': ftype,
            'parse_success': success,
            'eye_snps_present': eye_cnt,
            'hair_snps_present': hair_cnt,
            'skin_snps_present': skin_red_cnt, # updated to reduced panel count
            'skin_full_snps_present': skin_full_cnt,
            'rs12913832_present': rs129_pres,
            'recovery_note': note
        })
        
        status_str = f"OK | Eye: {eye_cnt}/6 | Hair: {hair_cnt:02d}/22 | Skin(Red): {skin_red_cnt:02d}/20" if success else f"EXCLUDED/FAILED ({note})"
        print(f"[{i:02d}/{len(targets):02d}] {pid} ({ftype:<13}) -> {status_str}")
        time.sleep(0.3)
        
    df_cov_updated = pd.DataFrame(recovered_results)
    
    # Save updated coverage file (keeping standard requested columns)
    cov_export_cols = ['participant_id', 'file_type', 'parse_success', 'eye_snps_present', 'hair_snps_present', 'skin_snps_present', 'rs12913832_present']
    df_cov_updated[cov_export_cols].to_csv(COVERAGE_OUTPUT_FILE, index=False)
    print("\n" + "=" * 80)
    print(f"Updated {COVERAGE_OUTPUT_FILE} successfully.")
    print("=" * 80)
    
    # PART 2: Summary of coverage after recovery pass
    valid_df = df_cov_updated[df_cov_updated['parse_success'] == True]
    total_parsed = len(valid_df)
    
    print("\n" + "=" * 80)
    print("PART 2: REDEFINED COVERAGE METRICS (AFTER RECOVERY PASS)")
    print("=" * 80)
    print(f"Total Target Files: {len(df_cov_updated)}")
    print(f"Successfully Parsed & Recovered Files: {total_parsed} / {len(df_cov_updated)} ({total_parsed/len(df_cov_updated)*100:.1f}%)")
    print(f"Permanently Excluded (Mitochondrial FASTA / Unresolvable): {len(df_cov_updated) - total_parsed}")
    
    # Eye Model (6 SNPs)
    eye_80 = (valid_df['eye_snps_present'] >= 5).sum()
    eye_full = (valid_df['eye_snps_present'] == 6).sum()
    
    # Hair Model (22 SNPs)
    hair_80 = (valid_df['hair_snps_present'] >= 18).sum()
    hair_full = (valid_df['hair_snps_present'] == 22).sum()
    
    # Reduced Skin Model (20 SNPs)
    skin_80 = (valid_df['skin_snps_present'] >= 16).sum() # 16/20 = 80%
    skin_full = (valid_df['skin_snps_present'] == 20).sum() # 20/20 = 100%
    
    rs129_total = (valid_df['rs12913832_present'] == True).sum()
    
    print(f"\n1. Eye Color Model (6 SNPs total):")
    print(f"   • Full Coverage (6/6 SNPs):        {eye_full} / {total_parsed} parsed ({eye_full/len(df_cov_updated)*100:.1f}% of total)")
    print(f"   • >= 80% Coverage (>= 5/6 SNPs):    {eye_80} / {total_parsed} parsed ({eye_80/len(df_cov_updated)*100:.1f}% of total)")
    print(f"   • rs12913832 Present:               {rs129_total} / {total_parsed} parsed ({rs129_total/len(df_cov_updated)*100:.1f}% of total)")
    
    print(f"\n2. Hair Color Model (22 SNPs total):")
    print(f"   • Full Coverage (22/22 SNPs):      {hair_full} / {total_parsed} parsed ({hair_full/len(df_cov_updated)*100:.1f}% of total)")
    print(f"   • >= 80% Coverage (>= 18/22 SNPs):  {hair_80} / {total_parsed} parsed ({hair_80/len(df_cov_updated)*100:.1f}% of total)")
    
    print(f"\n3. Skin Color Model — Redefined Reduced Panel (20 SNPs total):")
    print(f"   • Full Coverage (20/20 SNPs):      {skin_full} / {total_parsed} parsed ({skin_full/len(df_cov_updated)*100:.1f}% of total)")
    print(f"   • >= 80% Coverage (>= 16/20 SNPs):  {skin_80} / {total_parsed} parsed ({skin_80/len(df_cov_updated)*100:.1f}% of total)")
    
    # PART 3: Join with phenotype labels and produce final per-trait datasets
    print("\n" + "=" * 80)
    print("PART 3: PRODUCING PER-TRAIT FINAL DATASETS")
    print("=" * 80)
    
    df_pheno = pd.read_csv(CLEANED_FULL_FILE)
    df_joined_all = pd.merge(df_cov_updated, df_pheno, on='participant_id', how='inner')
    
    # 1. EYE MODEL DATASET
    # Filter: eye_snps_present >= 5 (>= 80%) AND eye_color notna/not blank
    eye_eligible = df_joined_all[
        (df_joined_all['parse_success'] == True) &
        (df_joined_all['eye_snps_present'] >= 5) &
        (df_joined_all['eye_color'].notna()) &
        (df_joined_all['eye_color'].str.strip() != '')
    ].copy()
    
    eye_rows = []
    for idx, r in eye_eligible.iterrows():
        pid = r['participant_id']
        gts = participant_genotypes.get(pid, {})
        row_dict = {'participant_id': pid, 'eye_color': r['eye_color']}
        for snp in EYE_SNPS:
            row_dict[snp] = gts.get(snp, '')
        eye_rows.append(row_dict)
    df_eye_dataset = pd.DataFrame(eye_rows)
    df_eye_dataset.to_csv('eye_model_dataset.csv', index=False)
    print(f"1. Created eye_model_dataset.csv  -> Final N = {len(df_eye_dataset)} participants")
    print("   Label breakdown:", df_eye_dataset['eye_color'].value_counts().to_dict())
    
    # 2. HAIR MODEL DATASET
    # Filter: hair_snps_present >= 18 (>= 80%) AND hair_color notna/not blank
    hair_eligible = df_joined_all[
        (df_joined_all['parse_success'] == True) &
        (df_joined_all['hair_snps_present'] >= 18) &
        (df_joined_all['hair_color'].notna()) &
        (df_joined_all['hair_color'].str.strip() != '')
    ].copy()
    
    hair_rows = []
    for idx, r in hair_eligible.iterrows():
        pid = r['participant_id']
        gts = participant_genotypes.get(pid, {})
        row_dict = {'participant_id': pid, 'hair_color': r['hair_color']}
        for snp in HAIR_SNPS:
            row_dict[snp] = gts.get(snp, '')
        hair_rows.append(row_dict)
    df_hair_dataset = pd.DataFrame(hair_rows)
    df_hair_dataset.to_csv('hair_model_dataset.csv', index=False)
    print(f"\n2. Created hair_model_dataset.csv -> Final N = {len(df_hair_dataset)} participants")
    print("   Label breakdown:", df_hair_dataset['hair_color'].value_counts().to_dict())
    
    # 3. SKIN MODEL DATASET
    # Filter: skin_snps_present >= 16 (>= 80% of 20) AND ethnicity_skin_color notna/not blank/not unknown
    skin_eligible = df_joined_all[
        (df_joined_all['parse_success'] == True) &
        (df_joined_all['skin_snps_present'] >= 16) &
        (df_joined_all['ethnicity_skin_color'].notna()) &
        (df_joined_all['ethnicity_skin_color'].str.strip() != '') &
        (df_joined_all['ethnicity_skin_color'] != 'unknown')
    ].copy()
    
    skin_rows = []
    for idx, r in skin_eligible.iterrows():
        pid = r['participant_id']
        gts = participant_genotypes.get(pid, {})
        row_dict = {'participant_id': pid, 'skin_color': r['ethnicity_skin_color']}
        for snp in SKIN_REDUCED_SNPS:
            row_dict[snp] = gts.get(snp, '')
        skin_rows.append(row_dict)
    df_skin_dataset = pd.DataFrame(skin_rows)
    df_skin_dataset.to_csv('skin_model_dataset.csv', index=False)
    print(f"\n3. Created skin_model_dataset.csv -> Final N = {len(df_skin_dataset)} participants")
    print("   Label breakdown:", df_skin_dataset['skin_color'].value_counts().to_dict())
    
    print("\n" + "=" * 80)
    print("FINAL PER-TRAIT SUMMARY NUMBERS TO BUILD MODELS ON:")
    print("=" * 80)
    print(f"• Eye Model Dataset  (N = {len(df_eye_dataset)}): eye_model_dataset.csv")
    print(f"• Hair Model Dataset (N = {len(df_hair_dataset)}): hair_model_dataset.csv")
    print(f"• Skin Model Dataset (N = {len(df_skin_dataset)}): skin_model_dataset.csv")
    print("=" * 80)

if __name__ == '__main__':
    main()

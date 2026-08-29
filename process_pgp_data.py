import sys
import pandas as pd
import numpy as np

# Ensure utf-8 output in Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

FILE_1_PATH = 'PGPParticipantSurvey-20181010220019.csv'
FILE_2_PATH = 'PGPBasicPhenotypesSurvey2015-20181010214636.csv'

def normalize_participant_id(pid):
    if pd.isna(pid):
        return None
    pid_str = str(pid).strip()
    if not pid_str:
        return None
    if pid_str.lower().startswith('hu'):
        return 'hu' + pid_str[2:].upper()
    return pid_str

def normalize_sex(sex_gender, anatomical_sex):
    val = sex_gender
    if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() in ['no response', 'prefer not to answer', 'none']:
        val = anatomical_sex
    
    if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() in ['no response', 'prefer not to answer', 'none']:
        return 'unknown'
    
    s = str(val).strip().lower()
    if s in ['male', 'm']:
        return 'male'
    elif s in ['female', 'f']:
        return 'female'
    elif any(k in s for k in ['trans', 'genderqueer', 'non binary', 'nonbinary', 'agender', 'neutrois', 'queer', 'androgynous', 'intersex', 'no gender']):
        return 'other'
    else:
        return 'unknown'

def normalize_ethnicity(race_val):
    if pd.isna(race_val):
        return 'unknown'
    s = str(race_val).strip()
    if not s or s.lower() in ['no response', 'prefer not to answer', 'none', 'unspecified']:
        return 'unknown'
    
    parts = [p.strip() for p in s.split(',') if p.strip().lower() not in ['no response', 'prefer not to answer', 'none', '']]
    if len(parts) > 1:
        return 'multiple'
    elif len(parts) == 1:
        p = parts[0].lower()
        if 'white' in p or 'caucasian' in p:
            return 'white'
        elif 'asian' in p:
            return 'asian'
        elif 'black' in p or 'african' in p:
            return 'black'
        elif 'hispanic' in p or 'latino' in p:
            return 'hispanic_latino'
        elif 'american indian' in p or 'alaska' in p or 'native american' in p:
            return 'native_american'
        elif 'pacific islander' in p or 'hawaiian' in p:
            return 'pacific_islander'
        else:
            return 'other'
    return 'unknown'

def normalize_genetic_data_status(status_val):
    if pd.isna(status_val):
        return 'none'
    s = str(status_val).strip()
    if 'yes' in s.lower() or 'uploaded genetic data' in s.lower():
        return 'uploaded'
    elif 'plan to upload' in s.lower() or 'have genetic data and plan' in s.lower():
        return 'planned'
    elif 'no genetic data' in s.lower() or 'do not want to upload' in s.lower():
        return 'none'
    return 'none'

def normalize_eye_color(left_text, right_text, left_photo=None, right_photo=None):
    text = None
    if pd.notna(left_text) and str(left_text).strip() != '':
        text = str(left_text).strip()
    elif pd.notna(right_text) and str(right_text).strip() != '' and str(right_text).strip().lower() not in ['same', 'same as left', 'same.', '"same"']:
        text = str(right_text).strip()
    
    photo = left_photo if pd.notna(left_photo) else right_photo
    
    if text:
        t = text.lower().replace('"', '').replace("'", '').strip()
        if any(k in t for k in ['hazel', 'havel', 'haxel', 'hazek']):
            return 'hazel'
        elif any(k in t for k in ['green-brown', 'brown-green', 'green/brown', 'brown/green', 'green with brown', 'brown with green', 'green and brown', 'brown and green', 'brown center, green outside', 'brown center, hazel', 'green outline with hazel center']):
            return 'hazel'
        elif any(k in t for k in ['blue-green', 'blue/green', 'green-blue', 'green/blue', 'blue green', 'green blue', 'bluish-green', 'blue with tint of green']):
            return 'blue'
        elif any(k in t for k in ['blue-grey', 'blue-gray', 'grey-blue', 'gray-blue', 'grey/blue', 'blue/grey', 'blue grey', 'greyish blue', 'grayish blue', 'bluish-grey']):
            return 'blue'
        elif 'brown' in t or 'brn' in t:
            return 'brown'
        elif 'amber' in t:
            return 'amber'
        elif 'green' in t or 'olive' in t:
            return 'green'
        elif 'blue' in t or 'aqua' in t or 'teal' in t:
            return 'blue'
        elif 'grey' in t or 'gray' in t:
            return 'gray'
        elif 'black' in t:
            return 'black'
    
    if pd.notna(photo):
        try:
            p = int(float(photo))
            if 1 <= p <= 9:
                return 'blue'
            elif 10 <= p <= 12:
                return 'green'
            elif 13 <= p <= 16:
                return 'hazel'
            elif 17 <= p <= 24:
                return 'brown'
        except:
            pass
            
    return np.nan

def normalize_hair_color(hair_cat, hair_text):
    if pd.notna(hair_cat) and str(hair_cat).strip() != '':
        c = str(hair_cat).strip().lower()
        if c in ['brown', 'blonde', 'gray', 'black', 'white', 'red']:
            return c
        elif 'blond' in c:
            return 'blonde'
        elif 'grey' in c or 'gray' in c:
            return 'gray'
            
    if pd.notna(hair_text) and str(hair_text).strip() != '':
        t = str(hair_text).strip().lower()
        if 'brown' in t:
            return 'brown'
        elif 'blond' in t:
            return 'blonde'
        elif 'gray' in t or 'grey' in t or 'silver' in t or 'salt and pepper' in t:
            return 'gray'
        elif 'black' in t:
            return 'black'
        elif 'white' in t:
            return 'white'
        elif 'red' in t or 'auburn' in t or 'ginger' in t:
            return 'red'
            
    return np.nan

def main():
    # Load raw datasets
    df1_raw = pd.read_csv(FILE_1_PATH, encoding='utf-8', encoding_errors='replace')
    df2_raw = pd.read_csv(FILE_2_PATH, encoding='utf-8', encoding_errors='replace')
    
    # Process File 1
    f1_cols = [
        'Participant',
        'Sex/Gender',
        'Anatomical sex at birth',
        'Race/ethnicity',
        'Have you uploaded genetic data to your PGP participant profile?'
    ]
    df1 = df1_raw[f1_cols].copy()
    if 'Timestamp' in df1_raw.columns:
        df1['Timestamp'] = pd.to_datetime(df1_raw['Timestamp'], errors='coerce')
    
    df1['participant_id'] = df1['Participant'].apply(normalize_participant_id)
    df1['sex'] = df1.apply(lambda r: normalize_sex(r['Sex/Gender'], r['Anatomical sex at birth']), axis=1)
    df1['ethnicity'] = df1['Race/ethnicity'].apply(normalize_ethnicity)
    df1['genetic_data_status'] = df1['Have you uploaded genetic data to your PGP participant profile?'].apply(normalize_genetic_data_status)
    
    # Deduplicate keeping latest
    if 'Timestamp' in df1.columns:
        df1_clean = df1.sort_values('Timestamp').groupby('participant_id').last().reset_index()
    else:
        df1_clean = df1.groupby('participant_id').last().reset_index()
        
    df1_clean = df1_clean[['participant_id', 'sex', 'ethnicity', 'genetic_data_status']]
    
    # Process File 2
    df2 = df2_raw.copy()
    df2['participant_id'] = df2['Participant'].apply(normalize_participant_id)
    if 'Timestamp' in df2.columns:
        df2['Timestamp'] = pd.to_datetime(df2['Timestamp'], errors='coerce')
        df2 = df2.sort_values('Timestamp').groupby('participant_id').last().reset_index()
    else:
        df2 = df2.groupby('participant_id').last().reset_index()
        
    col_eye_l_text = '2.3 — Left Eye Color - Text Description'
    col_eye_r_text = '2.4 — Right Eye Color - Text Description'
    col_eye_l_photo = '2.1 — Left Eye (Photograph Number)  (full-size image: https://goo.gl/XQ2Voh)'
    col_eye_r_photo = '2.2 — Right Eye (Photograph Number)  (full-size image: https://goo.gl/XQ2Voh)'
    col_hair_cat = '3.1 — What is your natural hair color currently, when without artificial color or dye?'
    col_hair_text = '3.2 — Hair Color - Text Description'
    
    df2['eye_color'] = df2.apply(
        lambda r: normalize_eye_color(r.get(col_eye_l_text), r.get(col_eye_r_text), r.get(col_eye_l_photo), r.get(col_eye_r_photo)),
        axis=1
    )
    df2['hair_color'] = df2.apply(
        lambda r: normalize_hair_color(r.get(col_hair_cat), r.get(col_hair_text)),
        axis=1
    )
    
    df2_clean = df2[['participant_id', 'eye_color', 'hair_color']].copy()
    
    # Inner join
    df_joined = pd.merge(df1_clean, df2_clean, on='participant_id', how='inner')
    
    # Populate ethnicity_skin_color and rename/order columns
    df_joined['ethnicity_skin_color'] = df_joined['ethnicity']
    
    final_cols = ['participant_id', 'sex', 'ethnicity_skin_color', 'genetic_data_status', 'eye_color', 'hair_color']
    df_joined = df_joined[final_cols]
    
    # Save full cleaned CSV
    output_full_path = 'pgp_cleaned_full.csv'
    df_joined.to_csv(output_full_path, index=False)
    
    # Save priority CSV (genetic_data_status == 'uploaded')
    df_priority = df_joined[df_joined['genetic_data_status'] == 'uploaded'].copy()
    output_priority_path = 'pgp_cleaned_priority.csv'
    df_priority.to_csv(output_priority_path, index=False)
    
    # Compute counts before and after join for the summary comparison table
    # Before Join: File 1 Unique (df1_clean), File 2 Unique (df2_clean)
    # After Join: Joined (df_joined), Priority (df_priority)
    
    print("\n" + "="*80)
    print("FULL SUMMARY TABLE OF LOGS / NUMBERS (BEFORE VS AFTER JOIN)")
    print("="*80)
    
    rows = []
    
    # Overall metrics
    rows.append(("DATASET METRICS", "", "", "", ""))
    rows.append(("Total Raw Survey Responses (Rows)", f"{len(df1_raw):,}", f"{len(df2_raw):,}", "-", "-"))
    rows.append(("Unique Participants", f"{df1_raw['Participant'].str.strip().str.lower().nunique():,}", f"{df2_raw['Participant'].str.strip().str.lower().nunique():,}", f"{len(df_joined):,}", f"{len(df_priority):,}"))
    rows.append(("Survey Overlap (% of Unique File 2 in File 1)", "-", "-", f"{len(df_joined)/len(df2_clean)*100:.1f}%", "-"))
    
    # Genetic Data Status
    rows.append(("", "", "", "", ""))
    rows.append(("GENETIC DATA STATUS", "File 1 (Pre-Join)", "File 2 (Pre-Join)", "Joined Full", "Priority (Uploaded)"))
    for cat in ['none', 'planned', 'uploaded']:
        c_f1 = (df1_clean['genetic_data_status'] == cat).sum()
        c_join = (df_joined['genetic_data_status'] == cat).sum()
        c_prio = (df_priority['genetic_data_status'] == cat).sum()
        rows.append((f"  • {cat}", f"{c_f1:,}", "N/A", f"{c_join:,}", f"{c_prio:,}"))
        
    # Sex / Gender
    rows.append(("", "", "", "", ""))
    rows.append(("SEX / GENDER", "File 1 (Pre-Join)", "File 2 (Pre-Join)", "Joined Full", "Priority (Uploaded)"))
    for s in ['male', 'female', 'other', 'unknown']:
        c_f1 = (df1_clean['sex'] == s).sum()
        c_join = (df_joined['sex'] == s).sum()
        c_prio = (df_priority['sex'] == s).sum()
        rows.append((f"  • {s}", f"{c_f1:,}", "N/A", f"{c_join:,}", f"{c_prio:,}"))
        
    # Ethnicity / Skin Color Proxy
    rows.append(("", "", "", "", ""))
    rows.append(("ETHNICITY / SKIN COLOR", "File 1 (Pre-Join)", "File 2 (Pre-Join)", "Joined Full", "Priority (Uploaded)"))
    for eth in ['white', 'multiple', 'asian', 'hispanic_latino', 'black', 'unknown', 'native_american', 'pacific_islander', 'other']:
        c_f1 = (df1_clean['ethnicity'] == eth).sum()
        c_join = (df_joined['ethnicity_skin_color'] == eth).sum()
        c_prio = (df_priority['ethnicity_skin_color'] == eth).sum()
        if c_f1 > 0 or c_join > 0:
            rows.append((f"  • {eth}", f"{c_f1:,}", "N/A", f"{c_join:,}", f"{c_prio:,}"))
            
    # Eye Color
    rows.append(("", "", "", "", ""))
    rows.append(("EYE COLOR", "File 1 (Pre-Join)", "File 2 (Pre-Join)", "Joined Full", "Priority (Uploaded)"))
    for eye in ['brown', 'blue', 'hazel', 'green', 'gray', 'amber', 'black', 'Missing / Unusable']:
        if eye == 'Missing / Unusable':
            c_f2 = df2_clean['eye_color'].isna().sum()
            c_join = df_joined['eye_color'].isna().sum()
            c_prio = df_priority['eye_color'].isna().sum()
        else:
            c_f2 = (df2_clean['eye_color'] == eye).sum()
            c_join = (df_joined['eye_color'] == eye).sum()
            c_prio = (df_priority['eye_color'] == eye).sum()
        rows.append((f"  • {eye}", "N/A", f"{c_f2:,}", f"{c_join:,}", f"{c_prio:,}"))
        
    # Hair Color
    rows.append(("", "", "", "", ""))
    rows.append(("HAIR COLOR", "File 1 (Pre-Join)", "File 2 (Pre-Join)", "Joined Full", "Priority (Uploaded)"))
    for hair in ['brown', 'blonde', 'gray', 'black', 'red', 'white', 'Missing / Unusable']:
        if hair == 'Missing / Unusable':
            c_f2 = df2_clean['hair_color'].isna().sum()
            c_join = df_joined['hair_color'].isna().sum()
            c_prio = df_priority['hair_color'].isna().sum()
        else:
            c_f2 = (df2_clean['hair_color'] == hair).sum()
            c_join = (df_joined['hair_color'] == hair).sum()
            c_prio = (df_priority['hair_color'] == hair).sum()
        rows.append((f"  • {hair}", "N/A", f"{c_f2:,}", f"{c_join:,}", f"{c_prio:,}"))
        
    # Completeness Quality
    rows.append(("", "", "", "", ""))
    rows.append(("DATA COMPLETENESS QUALITY", "File 1 (Pre-Join)", "File 2 (Pre-Join)", "Joined Full", "Priority (Uploaded)"))
    f2_comp = (df2_clean['eye_color'].notna() & df2_clean['hair_color'].notna()).sum()
    join_comp = (df_joined['eye_color'].notna() & df_joined['hair_color'].notna() & (df_joined['ethnicity_skin_color'] != 'unknown')).sum()
    prio_comp = (df_priority['eye_color'].notna() & df_priority['hair_color'].notna() & (df_priority['ethnicity_skin_color'] != 'unknown')).sum()
    prio_pheno_only = (df_priority['eye_color'].notna() & df_priority['hair_color'].notna()).sum()
    
    rows.append(("Complete Eye + Hair", "N/A", f"{f2_comp:,} / {len(df2_clean):,} ({f2_comp/len(df2_clean)*100:.1f}%)", f"{((df_joined['eye_color'].notna()) & (df_joined['hair_color'].notna())).sum():,} / {len(df_joined):,}", f"{prio_pheno_only:,} / {len(df_priority):,} ({prio_pheno_only/len(df_priority)*100:.1f}%)"))
    rows.append(("100% Complete (Sex + Eth/Skin + Status + Eye + Hair)", "-", "-", f"{join_comp:,} / {len(df_joined):,} ({join_comp/len(df_joined)*100:.1f}%)", f"{prio_comp:,} / {len(df_priority):,} ({prio_comp/len(df_priority)*100:.1f}%)"))
    
    # Print Markdown Table to terminal
    print(f"{'Category / Metric':<40} | {'File 1 (Pre-Join)':<18} | {'File 2 (Pre-Join)':<18} | {'Joined Full':<14} | {'Priority (Uploaded)':<20}")
    print("-" * 120)
    for r in rows:
        if r[0] == "":
            print("-" * 120)
        elif r[1] == "File 1 (Pre-Join)":
            print(f"{r[0]:<40} | {r[1]:<18} | {r[2]:<18} | {r[3]:<14} | {r[4]:<20}")
        elif r[1] == "":
            print(f"** {r[0]} **")
        else:
            print(f"{r[0]:<40} | {r[1]:<18} | {r[2]:<18} | {r[3]:<14} | {r[4]:<20}")

if __name__ == '__main__':
    main()

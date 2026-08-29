import urllib.request
import ssl
import gzip
import zipfile
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'AcademicResearchBot/1.0 (PGP Study)'}

sample_urls = [
    ('hu016B28', '23andMe', 'https://my.pgp-hms.org/user_file/download/8'),
    ('hu005EB9', 'FamilyTreeDNA', 'https://my.pgp-hms.org/user_file/download/45'),
    ('hu15E54C', 'AncestryDNA', 'https://my.pgp-hms.org/user_file/download/3540'),
    ('hu094BE5', 'VCF', 'https://my.pgp-hms.org/user_file/download/1978')
]

for pid, ftype, url in sample_urls:
    print(f"Testing {pid} ({ftype}): {url}")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            content = resp.read()
            print(f"  Downloaded {len(content):,} bytes.")
            
            if content.startswith(b'\x1f\x8b'):
                print("  GZIP compressed")
                decomp = gzip.decompress(content)
                lines = decomp.decode('utf-8', errors='replace').splitlines()[:10]
            elif content.startswith(b'PK\x03\x04'):
                print("  ZIP compressed")
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    print("  Zip files:", z.namelist())
                    with z.open(z.namelist()[0]) as zf:
                        lines = zf.read().decode('utf-8', errors='replace').splitlines()[:10]
            else:
                print("  Plain text")
                lines = content.decode('utf-8', errors='replace').splitlines()[:10]
                
            for l in lines[:5]:
                print(f"    Line: {l[:100]}")
    except Exception as e:
        print(f"  Error: {e}")

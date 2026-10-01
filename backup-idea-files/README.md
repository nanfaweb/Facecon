# GenoFace

Genotype–phenotype analysis of eye and hair colour using Personal Genome Project (PGP) survey data and publicly available microarray genotypes. The goal is to build evaluation-ready datasets aligned with **HIrisPlex-S** prediction categories, then benchmark HIrisPlex-S and custom models against self-reported phenotypes.

**FYP proposal:** [`GenoFace_FYP1-D1_Proposal.docx`](GenoFace_FYP1-D1_Proposal.docx) (generated from the official template via `scripts/fill_proposal.py`).

## Repository layout

```
GenoFace/
├── csv-files/          # Raw surveys, intermediate pipeline outputs, pre-relabel datasets
├── scripts/            # Pipeline and relabeling scripts
├── eye_model_final.csv # HIrisPlex-aligned eye dataset (N=71)
├── hair_model_final.csv# HIrisPlex-aligned hair dataset (N=62)
├── METHODS_LOG.md      # Dated pipeline decisions and rationale
└── README.md
```

## Pipeline

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 1. Clean & join surveys | `scripts/process_pgp_data.py` | Raw PGP CSVs | `pgp_cleaned_full.csv`, `pgp_cleaned_priority.csv` |
| 2. Scrape genotype files | `scripts/scrape_genotypes.py` | `pgp_cleaned_full.csv` | `pgp_genotype_matches.csv` |
| 3. SNP coverage + build datasets | `scripts/run_recovery_and_build_datasets.py` | matches + cleaned | `pgp_snp_coverage.csv`, `*_model_dataset.csv` |
| 4. HIrisPlex-S relabeling | `scripts/relabel_hirisplex_categories.py` | `*_model_dataset.csv` | `eye_model_final.csv`, `hair_model_final.csv` |

Run steps 1–3 from the `csv-files/` directory (paths are relative to that folder). Step 4 reads the pre-relabel datasets from `csv-files/`; final outputs live at the repository root.

```bash
cd csv-files
python ../scripts/process_pgp_data.py
python ../scripts/scrape_genotypes.py
python ../scripts/run_recovery_and_build_datasets.py

# Relabel: run from repo root so outputs land alongside modeling artifacts
cd ..
python scripts/relabel_hirisplex_categories.py   # expects *_model_dataset.csv in cwd — copy or symlink from csv-files/ if needed
```

**Dependencies:** Python 3, pandas, numpy, beautifulsoup4

## Current status

**Completed:** End-to-end data pipeline through HIrisPlex-aligned final datasets.

| Dataset | N | Label classes |
|---------|---|---------------|
| Eye (`eye_model_final.csv`) | 71 | Blue (18), Intermediate (24), Brown (29) |
| Hair (`hair_model_final.csv`) | 62 | Blond (7), Brown (48), Red (3), Black (4) |

**HIrisPlex-S label mapping (eye):** blue→Blue, brown→Brown, hazel/green→Intermediate; gray/amber dropped (3 rows).

**HIrisPlex-S label mapping (hair):** blonde→Blond, brown→Brown, red→Red, black→Black; gray/white dropped (10 rows).

Pre-relabel snapshots are preserved in `csv-files/eye_model_dataset.csv` (N=74) and `csv-files/hair_model_dataset.csv` (N=72).

See [METHODS_LOG.md](METHODS_LOG.md) for documented decisions.

## SNP panels

| Trait | SNPs | Coverage threshold |
|-------|------|--------------------|
| Eye | 6 (rs12913832, rs1800407, rs12896399, rs16891982, rs1393350, rs12203592) | ≥5/6 (80%) |
| Hair | 22 (HIrisPlex-S hair panel) | ≥18/22 (80%) |
| Skin (exploratory) | 20 reduced panel | ≥16/20 (80%) |

## Data source

- PGP Participant Survey and Basic Phenotypes Survey (2015–2018 exports)
- Genotype files from [PGP Harvard profiles](https://my.pgp-hms.org)

# Facecon — Project Context

## What it is
Facecon: Genotype-to-3D-Face Prediction Pipeline. Predicts eye, hair, and skin colour from DNA and uses the predictions to generate a colourized 3D face. Does not attempt to infer facial geometry or identity from DNA — explicitly scoped to avoid overclaiming, in direct response to published critiques of prior DNA-to-face systems.

## Route structure
- **Route 1 (A+C+D) — committed, primary deliverable.** Predict colour traits (A), use FLAME as 3D template (C), map predicted colours onto it (D). No paired DNA-face data required.
- **Route 2 (Option B) — parallel, non-blocking, contingent.** Predicting actual face shape from DNA using the 3DFN dataset (FaceBase for 3D scans + dbGaP accession phs000949.v1.p1 for genotypes, 2,454 participants). Requires PI + institutional access; university has submitted the access request (FaceBase DUC/DAR + dbGaP eRA Commons/DAR, IRB confirmed required for FaceBase side). Do not build against this dataset until access is confirmed. If granted, treat as an FYP2 extension on top of a completed Route 1, not a replacement.

## Key rejected approaches (do not revisit without strong new justification)
- **Using HIrisPlex-S output as training labels** — rejected as circular (model would just learn to imitate HIrisPlex-S's own math, not predict real phenotypes). HIrisPlex-S is used only as (a) a comparison baseline on real labelled data, and (b) a direct prediction tool for skin colour (demo-only, no training).
- **Mapping self-reported ethnicity to skin colour** — rejected as a category error / stereotyping risk. Ethnicity is used only for (a) Stage C ancestry-based shape lookup, and (b) a one-time DNA-estimated-ancestry-vs-self-report QC check to catch pipeline/join errors. Never used to touch, validate, or infer any colour prediction.
- **"Facial reconstruction" framing** — rejected as overclaiming. Even Difface (best-resourced published attempt, ~9,674 people) achieved only Rank-1 identification 3.33%, EER 27.6%, AUC 80.7%, landmark error 3.52mm (2.93mm with added covariates). Project uses "prediction," not "reconstruction," throughout.
- **Full pivot to hair type/texture (curl) as primary trait** — considered, not adopted as core. Weak genetic signal (top variant explains ~6% of variance vs. strong pigmentation SNPs), no existing benchmark tool, and Stage D rendering would need hair-strand geometry, not just colour/texture. Remains a possible low-confidence stretch item only if time allows (TCHH/WNT10A/FRAS1/EDAR panel identified if pursued).

## Data pipeline — status and numbers
- **Original plan (OpenSNP) is dead**: permanently shut down 2025, data deleted. Pivoted to Harvard Personal Genome Project (PGP), open access, requires manual matching (no ready-made paired dataset).
- Other restricted sources evaluated and ruled out for this FYP timeline: UK Biobank (student rate exists, £500+VAT, needs supervisor as PI co-applicant, weeks to approve), dbGaP/AREDS (wrong trait — eye disease not eye colour — and PI-gated regardless).
- **Survey data**: Participant Survey (4,128 people; extracted fields: ID, sex/gender, race/ethnicity, genetic-data-upload status) + Phenotype Survey (1,185 people; eye/hair colour fields — no skin colour field exists in either survey, confirmed).
- **Joined**: 1,046 people total; genetic-data status breakdown: 63 self-reported "uploaded," 53 "planned" (2018 survey, treated as stale-in-both-directions signal, not ground truth).
- **Scraped both groups (116 total)**: 58/63 "uploaded" confirmed with live file today; 40/53 "planned" had since followed through. Combined confirmed: 98/116.
- **File type breakdown**: 23andMe 78, Complete Genomics (CGI) 10, FamilyTreeDNA 7, VCF 2, AncestryDNA 1. CGI set aside (needs separate `cgatools` pipeline) — core usable pool = 88.
- **Recovery pass** (fixed expired Arvados links, recovered position-only VCFs where possible): 86/88 parsed successfully (97.7%). 2 permanently excluded (1 VCF timeout, 1 mitochondrial-only file — wrong data type, not fixable).
- **SNP coverage** (HIrisPlex-S panels: eye 6 SNPs, hair 22 SNPs, skin 36→reduced to 20 shared+core SNPs since consumer arrays don't cover the 17 forensic-only skin SNPs): eye ≥80% coverage 75/88, hair ≥80% coverage 73/88 (0% at full 22/22 — redefine "full" as ≥18/22 in practice), skin reduced-panel ≥80% coverage 75/88 (irrelevant for training, see below).
- **Final trainable datasets** (pre-final-cleanup numbers): eye 74 (brown 29, blue 18, hazel 18, green 6, gray 2, amber 1), hair 72 (brown 48, gray 8, blonde 7, black 4, red 3, white 2).
- **Skin colour: NOT trainable.** Confirmed no ground-truth pigmentation field exists anywhere in PGP survey data — only ethnicity, which is not a valid substitute (different trait, different scale, ethical category-error risk). Skin colour is HIrisPlex-S-direct only (run on genotype files, 5-category output: Very Pale/Pale/Intermediate/Dark/Dark-to-Black), demonstration pipeline only, not evaluated as "our model."

## Confirmed HIrisPlex-S category schemes (from official webtool — align our labels to these exactly)
- **Eye colour: 3 categories** — Blue, Intermediate, Brown. Our "hazel" + "green" merge into **Intermediate** (not into a standalone "hazel" bucket). Drop gray/amber (n<3, not part of scheme). Note: HIrisPlex-S's own published performance table shows Intermediate has AUC 0.735 but sensitivity ~0.001 under top-1 prediction — a known structural weakness of the 3-class scheme at the "top pick" level, not a sign of a broken model if our own results show the same pattern.
- **Hair colour: 4 categories** — Blond, Brown, Red, Black. Gray/white are not part of the scheme and are excluded as an age-related confound (graying is a documented confound in the HIrisPlex literature; original/natural colour, not present-day colour, is the target trait). Age field (year of birth) available if a sharper age-based exclusion rule is wanted (e.g., only exclude gray/white for older participants, flag younger ones for manual review).

## Modelling plan (Route 1, Stage A)
- Per trait (eye, hair — not skin): baseline logistic regression on core SNP panel, comparison model (small XGBoost), both evaluated with **leave-one-out cross-validation** (required at this N, not k-fold).
- Run HIrisPlex-S directly on the same genotypes for comparison — report **agreement rate**, not a "beat HIrisPlex" claim (dataset size/quality can't support that claim credibly).
- Report accuracy **with confidence intervals**, not point estimates, given small N.
- SHAP analysis for explainability (core novelty anchor of the project — not an add-on).
- Calibration (Platt/isotonic) so stated confidence matches real-world correctness.

## Stage C/D (3D pipeline)
- FLAME = existing 3D head template (academic sign-up required). Head **shape** is a demographic average (by predicted ancestry + sex) built from FaceScape data — NOT inferred from the individual's DNA. This is a stated, explicit limitation, not hidden.
- Only eye/hair/skin **colour** is genuinely DNA-derived and mapped onto the template (texture/shader level).
- Ancestry-PCA QC check (self-report vs. DNA-estimated ancestry) — a data-integrity check to catch join/scraping errors, separate from and not used to inform colour predictions.
- Uncertainty rendering (confidence shown alongside face, and/or multiple sampled variants weighted by prediction probability) — this is the concrete, implemented answer to Wagner et al.'s critique of overconfident DNA-to-face systems. Must not be dropped from scope.

## Timeline
- FYP split into FYP1 and FYP2, each ~4 months. FYP1 runs to end of December.
- Research paper planned for next semester (~5 months out) — **a running methods log should be maintained continuously**, logging every decision (exclusions, panel choices, N at each filtering step, tooling friction) as it happens, not reconstructed later.

## Proposal document status
Sections drafted (IEEE format, IEEE IRB/FYP1-D1 template, target 3 pages incl. title page): Abstract, Introduction, Goals and Objectives, Scope of the Project, Initial Study and Work Done So Far, References. Final reference list (7 entries, renumbered 1–7): Wang et al. 2026 (19-SNP panel), Xiong et al. 2025 (facial GWAS), Jiao et al. 2025 (Difface), Wagner et al. 2025 (Difface critique), Personal Genome Project, HIrisPlex-S, FLAME. 3DFN/FaceBase/dbGaP references removed (not cited in-text, since Route 2 detail was deliberately excluded from the Scope section). G2PDiffusion reference removed earlier; corresponding in-text mention also removed to avoid a dangling citation.

## Tools confirmed working / in use
PLINK 2.0, scikit-learn, XGBoost, SHAP, PyTorch, PyTorch3D, FLAME, FaceScape, HIrisPlex-S (webtool), JupyterLab. All free for academic use.

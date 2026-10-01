"""Fill FYP1-D1 Project Proposal template with GenoFace content."""

import shutil
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / 'FYP1-D1 Project Proposal Template.docx'
OUTPUT = ROOT / 'GenoFace_FYP1-D1_Proposal.docx'

ABSTRACT = (
    'GenoFace is a genotype–phenotype study that predicts eye and hair colour from DNA '
    'using publicly available Personal Genome Project (PGP) data. The project builds a '
    'reproducible pipeline from raw PGP surveys and participant genotype files (23andMe, '
    'AncestryDNA, FamilyTreeDNA, VCF) to modeling-ready datasets aligned with HIrisPlex-S, '
    'a published forensic genetics tool. Ground-truth labels are derived from self-reported '
    'survey responses and mapped to HIrisPlex-S categories: eye colour (Blue, Intermediate, '
    'Brown) and hair colour (Blond, Brown, Red, Black). The completed pipeline produced '
    'final datasets of 71 participants for eye colour and 62 for hair colour. The next '
    'phase benchmarks HIrisPlex-S predictions against survey labels and trains simple machine '
    'learning baselines (e.g. logistic regression) for comparison, using stratified '
    'cross-validation and class-aware metrics. Skin colour prediction is excluded due to '
    'lack of direct ground-truth labels in the available surveys.'
)

INTRO_1 = (
    'Human visible traits such as eye and hair colour are influenced by genetic variation '
    'at specific SNP loci. In forensic science and genetic research, tools like HIrisPlex-S '
    'predict these traits from a small panel of SNPs. However, validating such tools on '
    'real-world data requires linked genotype and phenotype records, which are difficult to '
    'obtain at scale. The Personal Genome Project (PGP) provides a unique open dataset where '
    'participants contribute both self-reported phenotype surveys and publicly shared '
    'genotype files, making it suitable for building and evaluating prediction pipelines.'
)

INTRO_2 = (
    'GenoFace leverages PGP Harvard survey exports and profile genotype files to construct '
    'clean, HIrisPlex-S-compatible datasets for eye and hair colour. The project follows a '
    'multi-stage pipeline: survey cleaning and joining, online verification of genotype file '
    'availability, SNP extraction with coverage thresholds, label normalization to match '
    'HIrisPlex-S output classes, and planned model evaluation. By aligning labels and '
    'features with HIrisPlex-S exactly, the project enables a fair comparison between '
    'published predictions and custom models trained on the same PGP cohort.'
)

GOALS_INTRO = 'The main goals and objectives of GenoFace are as follows:'

OBJECTIVES = [
    'To collect, clean, and join PGP participant and basic phenotype surveys into a unified '
    'participant-level dataset with normalized eye and hair colour labels.',
    'To identify participants with publicly available genotype files and extract HIrisPlex-S '
    'SNP panels with at least 80% coverage per trait.',
    'To align phenotype labels with HIrisPlex-S prediction categories so evaluation uses a '
    'consistent label space (3 eye classes, 4 hair classes).',
    'To benchmark HIrisPlex-S predictions and train simple machine learning models '
    '(e.g. logistic regression) on the final datasets, reporting accuracy, confusion '
    'matrices, and macro F1 scores via stratified cross-validation.',
]

SCOPE_PARAS = [
    'The scope of GenoFace covers eye and hair colour prediction from SNP genotypes using '
    'publicly available PGP data. In scope: building a data pipeline (survey processing, '
    'genotype scraping and parsing, SNP coverage filtering, HIrisPlex-S label alignment); '
    'evaluating HIrisPlex-S against survey labels; training simple baseline models for '
    'comparison; and documenting methods, exclusions, and dataset statistics.',
    'Out of scope: skin colour modeling, because the available surveys provide no direct '
    'skin-colour ground truth (ethnicity is used only as an exploratory proxy and is excluded '
    'from training); deep learning models, due to limited sample size (N=71 for eye, N=62 for '
    'hair); collecting new primary data beyond existing PGP public records; and gray/white '
    'hair and gray/amber eye categories, which are excluded because they are not part of the '
    'HIrisPlex-S prediction scheme.',
]

WORK_DONE_PARAS = [
    'Significant progress has been made on the data pipeline and dataset preparation. The '
    'following phases are complete.',
    'Phase 1 — Survey processing: Loaded the PGP Participant Survey (4,128 rows) and Basic '
    'Phenotypes Survey (1,185 rows). Normalized participant IDs, sex, ethnicity, genetic-data '
    'status, and eye/hair colour labels. Inner-joined both surveys to produce 1,046 participants '
    'in pgp_cleaned_full.csv.',
    'Phase 2 — Genotype verification: Scraped PGP participant profiles to locate publicly '
    'available genotype files. Confirmed 98 files on profile; 86 were successfully parsed after '
    'filtering to consumer microarray formats (23andMe, AncestryDNA, FamilyTreeDNA, VCF).',
    'Phase 3 — SNP coverage and dataset building: Extracted HIrisPlex-S SNP panels from '
    'genotype files and applied coverage thresholds (eye: at least 5 of 6 SNPs; hair: at least '
    '18 of 22 SNPs). Built pre-relabel modeling datasets with 74 eye and 72 hair participants.',
    'Phase 4 — HIrisPlex-S label alignment: Relabeled phenotype categories to match HIrisPlex-S '
    'output exactly (eye: Blue, Intermediate, Brown; hair: Blond, Brown, Red, Black). Final '
    'datasets: eye_model_final.csv (N=71) and hair_model_final.csv (N=62). Methods documented '
    'in METHODS_LOG.md.',
    'Final class balance — Eye (N=71): Blue (18), Intermediate (24), Brown (29). Hair (N=62): '
    'Blond (7), Brown (48), Red (3), Black (4).',
    'Remaining work: run HIrisPlex-S benchmark predictions, train logistic regression and '
    'majority-class baselines, evaluate with stratified cross-validation, and complete the FYP '
    'report.',
]

REFERENCES = [
    'Walsh, S., et al. (2017). HIrisPlex-S system for eye, hair and skin colour prediction '
    'from DNA. Forensic Science International: Genetics, 29, 181–194.',
    'Personal Genome Project. Harvard Medical School. https://my.pgp-hms.org',
    'Church, G. M. (2005). The Personal Genome Project. Molecular Systems Biology, 1(1), '
    '2005.0030.',
    'Erasmus MC HIrisPlex-S webtool. https://hirisplex.erasmusmc.nl/',
]


def replace_paragraph_text(paragraph, text: str) -> None:
    """Replace paragraph text while keeping its style."""
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ''
    else:
        paragraph.text = text
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def insert_body_before(paragraph, text: str, style_name: str = 'Body Text'):
    """Insert a justified body paragraph immediately before the given paragraph."""
    new_para = paragraph.insert_paragraph_before(text)
    new_para.style = style_name
    new_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return new_para


def insert_bodies_before(paragraph, texts: list[str], style_name: str = 'Body Text'):
    """Insert multiple paragraphs in order, placed immediately before anchor paragraph."""
    for text in reversed(texts):
        paragraph = insert_body_before(paragraph, text, style_name)
    return paragraph


def find_paragraph(doc: Document, exact_text: str):
    for para in doc.paragraphs:
        if para.text.strip() == exact_text.strip():
            return para
    return None


def find_paragraph_startswith(doc: Document, prefix: str):
    for para in doc.paragraphs:
        if para.text.strip().startswith(prefix):
            return para
    return None


def paragraph_index(doc: Document, target) -> int:
    for i, para in enumerate(doc.paragraphs):
        if para._element is target._element:
            return i
    return -1


def fill_proposal() -> None:
    shutil.copy2(TEMPLATE, OUTPUT)
    doc = Document(str(OUTPUT))

    # Cover page — project name only; advisor/members left as placeholders
    replace_paragraph_text(doc.paragraphs[6], 'GenoFace')

    # Abstract
    replace_paragraph_text(doc.paragraphs[27], ABSTRACT)

    # Introduction
    replace_paragraph_text(doc.paragraphs[29], INTRO_1)
    goals_heading = find_paragraph(doc, 'Goals and Objectives')
    if goals_heading is None:
        raise RuntimeError('Could not find Goals and Objectives heading')
    insert_body_before(goals_heading, INTRO_2)

    # Goals and objectives
    goals_intro = find_paragraph_startswith(doc, 'Write the goals')
    if goals_intro is None:
        raise RuntimeError('Could not find Goals intro paragraph')
    replace_paragraph_text(goals_intro, GOALS_INTRO)

    objective_prefixes = [
        'To follow standard format',
        'To avoid Unsatisfactory',
        'Objective number 3',
        'Sample Objective number 4',
    ]
    for prefix, text in zip(objective_prefixes, OBJECTIVES):
        para = find_paragraph_startswith(doc, prefix)
        if para is None:
            raise RuntimeError(f'Could not find objective paragraph: {prefix}')
        replace_paragraph_text(para, text)

    # Scope
    scope_para = find_paragraph_startswith(doc, 'Clearly specify the scope')
    if scope_para is None:
        raise RuntimeError('Could not find Scope paragraph')
    replace_paragraph_text(scope_para, SCOPE_PARAS[0])
    work_heading = find_paragraph(doc, 'Initial Study and Work Done so Far')
    if work_heading is None:
        raise RuntimeError('Could not find Work Done heading')
    insert_body_before(work_heading, SCOPE_PARAS[1])

    # Work done so far
    work_para = find_paragraph_startswith(doc, 'Write about the work done')
    if work_para is None:
        raise RuntimeError('Could not find Work Done paragraph')
    replace_paragraph_text(work_para, WORK_DONE_PARAS[0])

    idx = paragraph_index(doc, work_para)
    if idx >= 0 and idx + 1 < len(doc.paragraphs):
        anchor = doc.paragraphs[idx + 1]
        insert_bodies_before(anchor, WORK_DONE_PARAS[1:])
    else:
        for text in WORK_DONE_PARAS[1:]:
            p = doc.add_paragraph(text, style='Body Text')
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # References
    doc.add_paragraph('References', style='Heading 1')
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph(f'{i}. {ref}', style='Body Text')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.save(str(OUTPUT))
    print(f'Created: {OUTPUT}')


if __name__ == '__main__':
    fill_proposal()

# Methods Log

## 2026-08-29 — HIrisPlex-S phenotype relabeling

Eye and hair colour labels in the model-ready genotype datasets were relabeled to match HIrisPlex-S's published prediction categories exactly, as confirmed via the official HIrisPlex-S webtool: eye colour uses three classes (Blue, Intermediate, Brown) and hair colour uses four classes (Blond, Brown, Red, Black). Survey-normalized labels in `eye_model_dataset.csv` and `hair_model_dataset.csv` were mapped accordingly (e.g., hazel and green merged to Intermediate; blonde standardized to Blond), while rows with categories outside the HIrisPlex-S scheme were excluded—gray and amber eye colours (3 rows) and gray and white hair colours (10 rows)—so that downstream evaluation compares against HIrisPlex-S on a consistent label space. Original dataset files were preserved unchanged; relabeled outputs were written to `eye_model_final.csv` (N=71) and `hair_model_final.csv` (N=62).

# Progress log

Last updated: 2026-10-01

## Current phase

Waiting for FaceBase / dbGaP access. Building the pipeline with synthetic data + FLAME.

## Immediate goals (before real data)

| # | Goal | Status |
|---|---|---|
| 1 | Install FLAME and generate meshes | Done |
| 2 | Synthetic scan → FLAME fitting test | Next |
| 3 | Synthetic genotype data pipeline | Not started |
| 4 | Simple SNP → MLP → FLAME baseline | Not started |
| 5 | Evaluation framework | Not started |
| 6 | Research questions + report drafts | In progress (proposal done) |
| 7 | Literature review matrix | Not started |

## Do not do yet

- Diffusion models
- Large Transformers
- Training on real 3DFN data (not available yet)

## Step log

### 2026-10-01
- Project folder set up: `FYP-Code`
- README and progress log created
- Installed Python 3.11 + `.venv` (torch, numpy, trimesh, scipy, chumpy)
- FLAME 2020 placed in `assets/flame/FLAME2020/`
- Converted `generic_model.pkl` → `generic_model_np.pkl` (5023 verts, 9976 faces)
- Generated sample meshes in `outputs/flame_meshes/`
- **Next:** Priority 2 — synthetic scan → FLAME fitting (recover shape params)

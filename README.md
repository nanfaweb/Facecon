# FaceCon (FYP)

Undergraduate Final Year Project: predict **3D facial shape** from **SNP genotype data**.

## Idea

```
SNPs → model → FLAME shape parameters → 3D face mesh → evaluation
```

## Planned data

- **3D faces:** FaceBase 3D Facial Norms (3DFN)
- **Genotypes:** dbGaP study `phs000949`

Controlled-access approval is still pending. Until then we use **synthetic data** and **FLAME** to build the pipeline.

## Face representation

We use **FLAME**. The model predicts FLAME shape/identity parameters (not raw XYZ vertices).

## Approach

1. Strong simple baselines first (mean face, demographics, Ridge, MLP)
2. Then more complex models only if useful
3. Difface is a reference, not something we copy as-is

## Status

See `PROGRESS.md` for current goals and the step log.

## Hardware

- Local: NVIDIA RTX 3050 (4 GB VRAM)
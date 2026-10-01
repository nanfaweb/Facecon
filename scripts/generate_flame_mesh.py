"""Generate random FLAME meshes (Priority 1 sanity check).

Usage (from repo root, venv active):
  python scripts/generate_flame_mesh.py
  python scripts/generate_flame_mesh.py --n 5 --seed 0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flame.flame_model import FLAME
from flame.mesh_utils import write_obj


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate random FLAME OBJ meshes")
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT / "assets" / "flame" / "FLAME2020" / "generic_model_np.pkl",
    )
    parser.add_argument("--n", type=int, default=3, help="Number of meshes")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-shape", type=int, default=100)
    parser.add_argument("--n-expr", type=int, default=50)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs" / "flame_meshes",
    )
    parser.add_argument("--shape-std", type=float, default=1.0)
    parser.add_argument("--expr-std", type=float, default=0.0, help="Keep 0 for identity-only")
    args = parser.parse_args()

    if not args.model.is_file():
        print(f"Model not found: {args.model}")
        print("Steps:")
        print("  1. Download FLAME 2020 from https://flame.is.tue.mpg.de/")
        print("  2. Copy generic_model.pkl -> assets/flame/")
        print("  3. python scripts/convert_flame_pickle.py")
        return 1

    device = torch.device("cpu")  # generation is cheap; keep CPU for Priority 1
    flame = FLAME(args.model, n_shape=args.n_shape, n_expr=args.n_expr).to(device)
    flame.eval()

    rng = np.random.default_rng(args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    meta = []
    print(f"FLAME vertices: {flame.num_vertices}")
    print(f"FLAME faces: {flame.faces.shape[0]}")

    with torch.no_grad():
        for i in range(args.n):
            shape = torch.tensor(
                rng.normal(0.0, args.shape_std, size=(1, args.n_shape)),
                dtype=torch.float32,
                device=device,
            )
            expression = torch.tensor(
                rng.normal(0.0, args.expr_std, size=(1, args.n_expr)),
                dtype=torch.float32,
                device=device,
            )
            verts = flame(shape, expression)[0].cpu().numpy()
            out_path = args.out_dir / f"flame_random_{i:03d}.obj"
            write_obj(out_path, verts, flame.faces)
            meta.append(
                {
                    "file": out_path.name,
                    "shape": shape.squeeze(0).cpu().tolist(),
                    "expression": expression.squeeze(0).cpu().tolist(),
                }
            )
            print(f"Wrote {out_path}")

    meta_path = args.out_dir / "params.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote {meta_path}")
    print("Open an .obj in MeshLab / Blender to view.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Convert official FLAME .pkl (may contain chumpy arrays) to a plain numpy pickle.

Run this once after downloading FLAME 2020 into assets/flame/FLAME2020/

Usage:
  python scripts/convert_flame_pickle.py
"""

from __future__ import annotations

import argparse
import pickle
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class _Ch(np.ndarray):
    """Stand-in for chumpy.ch.Ch so pickle can reconstruct arrays as numpy."""

    def __new__(cls, data=None, **kwargs):
        arr = np.array([] if data is None else data, dtype=np.float64)
        obj = np.asarray(arr).view(cls)
        return obj

    def __array_finalize__(self, obj):
        pass


def _install_chumpy_stub() -> None:
    """Allow unpickling FLAME files without installing chumpy."""
    if "chumpy" in sys.modules:
        return

    chumpy = types.ModuleType("chumpy")
    ch = types.ModuleType("chumpy.ch")
    ch_ch = types.ModuleType("chumpy.ch_ops")

    class Ch(_Ch):
        def __init__(self, *args, **kwargs):
            pass

    def array(x, **kwargs):
        return np.asarray(x)

    ch.Ch = Ch
    chumpy.Ch = Ch
    chumpy.array = array
    chumpy.ch = ch
    sys.modules["chumpy"] = chumpy
    sys.modules["chumpy.ch"] = ch
    sys.modules["chumpy.ch_ops"] = ch_ch


def _to_np(x):
    if hasattr(x, "todense"):
        return np.asarray(x.todense())
    return np.asarray(x)


def convert(input_path: Path, output_path: Path) -> None:
    try:
        import chumpy  # noqa: F401
    except ImportError:
        _install_chumpy_stub()

    with open(input_path, "rb") as f:
        raw = pickle.load(f, encoding="latin1")

    if not isinstance(raw, dict):
        raw = dict(raw.__dict__) if hasattr(raw, "__dict__") else dict(raw)

    out = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        try:
            out[key] = _to_np(value)
        except Exception:
            out[key] = value

    if "J_regressor" in out:
        out["J_regressor"] = _to_np(out["J_regressor"]).astype(np.float64)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Wrote {output_path}")
    print(f"  vertices: {out['v_template'].shape}")
    print(f"  shapedirs: {out['shapedirs'].shape}")
    print(f"  faces: {out['f'].shape}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert FLAME pkl to numpy-only pkl")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "assets" / "flame" / "FLAME2020" / "generic_model.pkl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "assets" / "flame" / "FLAME2020" / "generic_model_np.pkl",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Missing input: {args.input}")
        print("Download FLAME 2020 from https://flame.is.tue.mpg.de/")
        print("Extract into assets/flame/FLAME2020/")
        return 1

    convert(args.input, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

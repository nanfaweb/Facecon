"""Mesh helpers for FLAME outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np


def write_obj(path: Union[str, Path], vertices: np.ndarray, faces: np.ndarray) -> None:
    """Write a simple OBJ (1-based face indices)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    verts = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# FaceCon FLAME export\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        # FLAME faces are usually already 0-based
        for face in faces:
            f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")

"""Minimal FLAME head model in PyTorch (runtime does not need chumpy).

Expects a numpy-converted FLAME pickle under assets/flame/.
Download original models from https://flame.is.tue.mpg.de/ (sign up + license).
Then run: python scripts/convert_flame_pickle.py
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional, Union

import numpy as np
import torch
import torch.nn as nn


def _to_tensor(x, dtype=torch.float32) -> torch.Tensor:
    if isinstance(x, torch.Tensor):
        return x.to(dtype=dtype)
    return torch.tensor(np.asarray(x), dtype=dtype)


def load_flame_dict(model_path: Union[str, Path]) -> dict:
    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(
            f"FLAME model not found: {model_path}\n"
            "1) Download FLAME 2020 from https://flame.is.tue.mpg.de/\n"
            "2) Put generic_model.pkl in assets/flame/\n"
            "3) Run: python scripts/convert_flame_pickle.py"
        )
    with open(model_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict in {model_path}, got {type(data)}")
    required = ["v_template", "shapedirs", "posedirs", "J_regressor", "weights", "kintree_table", "f"]
    missing = [k for k in required if k not in data]
    if missing:
        raise KeyError(f"FLAME pickle missing keys: {missing}")
    return data


def batch_rodrigues(rot_vecs: torch.Tensor) -> torch.Tensor:
    """Axis-angle (N, 3) -> rotation matrices (N, 3, 3)."""
    batch_size = rot_vecs.shape[0]
    device, dtype = rot_vecs.device, rot_vecs.dtype
    angle = torch.norm(rot_vecs + 1e-8, dim=1, keepdim=True)
    rot_dir = rot_vecs / angle
    cos = torch.unsqueeze(torch.cos(angle), dim=1)
    sin = torch.unsqueeze(torch.sin(angle), dim=1)

    rx, ry, rz = torch.split(rot_dir, 1, dim=1)
    zeros = torch.zeros((batch_size, 1), dtype=dtype, device=device)
    K = torch.cat([zeros, -rz, ry, rz, zeros, -rx, -ry, rx, zeros], dim=1).view(batch_size, 3, 3)
    ident = torch.eye(3, dtype=dtype, device=device).unsqueeze(0)
    return ident + sin * K + (1 - cos) * torch.bmm(K, K)


def transform_mat(R: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
    """(B, 3, 3), (B, 3, 1) -> (B, 4, 4)."""
    return torch.cat([torch.cat([R, t], dim=2), torch.tensor([0, 0, 0, 1], device=R.device, dtype=R.dtype).view(1, 1, 4).repeat(R.shape[0], 1, 1)], dim=1)


def lbs(
    betas: torch.Tensor,
    pose: torch.Tensor,
    v_template: torch.Tensor,
    shapedirs: torch.Tensor,
    posedirs: torch.Tensor,
    J_regressor: torch.Tensor,
    parents: torch.Tensor,
    lbs_weights: torch.Tensor,
) -> torch.Tensor:
    """Return posed vertices (B, V, 3)."""
    batch_size = max(betas.shape[0], pose.shape[0])
    device, dtype = betas.device, betas.dtype

    v_shaped = v_template + torch.einsum("bl,mkl->bmk", betas, shapedirs)
    J = torch.einsum("bik,ji->bjk", v_shaped, J_regressor)

    ident = torch.eye(3, dtype=dtype, device=device)
    rot_mats = batch_rodrigues(pose.view(-1, 3)).view(batch_size, -1, 3, 3)

    pose_feature = (rot_mats[:, 1:, :, :] - ident).view(batch_size, -1)
    pose_offsets = torch.matmul(pose_feature, posedirs).view(batch_size, -1, 3)
    v_posed = pose_offsets + v_shaped

    # Relative joint locations
    rel_joints = J.clone()
    rel_joints[:, 1:] -= J[:, parents[1:]]

    transforms_mat = transform_mat(
        rot_mats.view(-1, 3, 3),
        rel_joints.reshape(-1, 3, 1),
    ).view(batch_size, -1, 4, 4)

    transform_chain = [transforms_mat[:, 0]]
    for i in range(1, parents.shape[0]):
        transform_chain.append(torch.matmul(transform_chain[parents[i]], transforms_mat[:, i]))
    transforms = torch.stack(transform_chain, dim=1)

    posed_joints = transforms[:, :, :3, 3]
    joints_homogen = torch.cat(
        [J, torch.zeros(batch_size, J.shape[1], 1, device=device, dtype=dtype)],
        dim=2,
    )
    init_bone = torch.matmul(transforms, joints_homogen.unsqueeze(-1))
    rel_transforms = transforms.clone()
    rel_transforms[:, :, :3, 3] = transforms[:, :, :3, 3] - init_bone[:, :, :3, 0]

    W = lbs_weights.unsqueeze(0).expand(batch_size, -1, -1)
    T = torch.matmul(W, rel_transforms.view(batch_size, -1, 16)).view(batch_size, -1, 4, 4)

    ones = torch.ones(batch_size, v_posed.shape[1], 1, device=device, dtype=dtype)
    v_homo = torch.matmul(T, torch.cat([v_posed, ones], dim=2).unsqueeze(-1))
    return v_homo[:, :, :3, 0]


class FLAME(nn.Module):
    """FLAME layer: shape + expression + pose -> vertices."""

    def __init__(
        self,
        model_path: Union[str, Path],
        n_shape: int = 100,
        n_expr: int = 50,
    ):
        super().__init__()
        data = load_flame_dict(model_path)

        v_template = _to_tensor(data["v_template"])
        shapedirs = _to_tensor(data["shapedirs"])
        n_basis = shapedirs.shape[-1]
        if n_basis < n_shape + n_expr:
            raise ValueError(
                f"shapedirs has {n_basis} components; need >= {n_shape + n_expr}"
            )
        shapedirs = shapedirs[:, :, : n_shape + n_expr]

        posedirs = np.asarray(data["posedirs"])
        # Common FLAME layout: (V, 3, P) -> (P, V*3)
        if posedirs.ndim == 3:
            v, _, p = posedirs.shape
            posedirs = np.transpose(posedirs, (2, 0, 1)).reshape(p, v * 3)
        posedirs = _to_tensor(posedirs)

        j_reg = data["J_regressor"]
        if hasattr(j_reg, "todense"):
            j_reg = j_reg.todense()
        J_regressor = _to_tensor(np.asarray(j_reg))
        weights = _to_tensor(data["weights"])

        kintree = np.asarray(data["kintree_table"])
        parents = torch.tensor(kintree[0].astype(np.int64), dtype=torch.long)
        parents[0] = -1
        faces = np.asarray(data["f"], dtype=np.int64)

        self.register_buffer("v_template", v_template)
        self.register_buffer("shapedirs", shapedirs)
        self.register_buffer("posedirs", posedirs)
        self.register_buffer("J_regressor", J_regressor)
        self.register_buffer("lbs_weights", weights)
        self.register_buffer("parents", parents)
        self.register_buffer("faces_tensor", torch.tensor(faces, dtype=torch.long))

        self.n_shape = n_shape
        self.n_expr = n_expr
        self.num_vertices = int(v_template.shape[0])

    @property
    def faces(self) -> np.ndarray:
        return self.faces_tensor.detach().cpu().numpy()

    def forward(
        self,
        shape: torch.Tensor,
        expression: Optional[torch.Tensor] = None,
        pose: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            shape: (B, n_shape) identity coefficients
            expression: (B, n_expr) optional
            pose: (B, 6) global orient + jaw, optional
        Returns:
            vertices (B, V, 3)
        """
        batch = shape.shape[0]
        device, dtype = shape.device, shape.dtype

        if expression is None:
            expression = torch.zeros(batch, self.n_expr, device=device, dtype=dtype)
        if pose is None:
            pose = torch.zeros(batch, 6, device=device, dtype=dtype)

        betas = torch.cat([shape, expression], dim=1)
        n_joints = self.J_regressor.shape[0]
        full_pose = torch.zeros(batch, n_joints * 3, device=device, dtype=dtype)
        full_pose[:, :3] = pose[:, :3]
        if n_joints > 1:
            full_pose[:, 3:6] = pose[:, 3:6]

        return lbs(
            betas,
            full_pose,
            self.v_template.unsqueeze(0).expand(batch, -1, -1),
            self.shapedirs,
            self.posedirs,
            self.J_regressor,
            self.parents,
            self.lbs_weights,
        )

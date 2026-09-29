"""Bounded rigid SE(3) tree transforms; explicit times, no covariance fusion."""
from __future__ import annotations
from dataclasses import dataclass
import math
from .canon import ContractError, timestamp
from .model import decimal_text

@dataclass(frozen=True)
class Transform:
    child: str
    parent: str
    matrix: tuple[tuple[float, ...], ...]
    valid_from: str
    valid_until: str
    evidence_cid: str

    def __post_init__(self) -> None:
        m = self.matrix
        if self.child == self.parent or len(m) != 4 or any(len(row) != 4 for row in m):
            raise ContractError("Transform requires distinct frames and a 4x4 matrix")
        if not all(math.isfinite(x) for row in m for x in row):
            raise ContractError("Transform contains nonfinite values")
        if any(abs(m[3][i] - (1 if i == 3 else 0)) > 1e-9 for i in range(4)):
            raise ContractError("Invalid homogeneous row")
        for i in range(3):
            for j in range(3):
                if abs(sum(m[k][i] * m[k][j] for k in range(3)) - (1 if i == j else 0)) > 1e-8:
                    raise ContractError("Rotation is not orthonormal")
        det = (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
               -m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
               +m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
        if abs(det - 1) > 1e-8:
            raise ContractError("Reflection or nonrigid transform is not supported")
        if timestamp(self.valid_until) <= timestamp(self.valid_from):
            raise ContractError("Empty transform validity")

class FrameTree:
    def __init__(self, transforms: list[Transform]) -> None:
        self.edges = {t.child: t for t in transforms}
        if len(self.edges) != len(transforms):
            raise ContractError("Multiple parents require an explicit transform selection outside this subset")
        for child in self.edges:
            seen = set()
            current = child
            while current in self.edges:
                if current in seen:
                    raise ContractError("Frame cycle")
                seen.add(current)
                current = self.edges[current].parent

    def to_ancestor(self, point: tuple[float, float, float], child: str, ancestor: str, at: str) -> dict:
        if len(point) != 3 or not all(math.isfinite(v) for v in point):
            raise ContractError("Point requires three finite components")
        vector = [*point, 1.0]
        path = []
        when = timestamp(at)
        current = child
        while current != ancestor:
            if current not in self.edges:
                raise ContractError("No declared ancestor transform path")
            edge = self.edges[current]
            if not (timestamp(edge.valid_from) <= when < timestamp(edge.valid_until)):
                raise ContractError("Transform is outside its validity interval")
            vector = [sum(edge.matrix[i][j]*vector[j] for j in range(4)) for i in range(4)]
            path.append(edge.evidence_cid)
            current = edge.parent
        return {"point": [decimal_text(round(v, 12)) for v in vector[:3]], "frame": ancestor,
                "transformEvidence": path, "uncertainty": "not-propagated-reference-subset"}

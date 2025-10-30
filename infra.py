from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Infra:
    """
    Représente une infrastructure de raccordement.

    Difficulté(infra) = longueur / nombre_de_maisons
    - Si nb_houses <= 0, on considère la difficulté infinie (math.inf).
    """
    infra_id: str
    length: float
    infra_type: str
    nb_houses: int

    def difficulty(self) -> float:
        if self.nb_houses is None or self.nb_houses <= 0:
            return math.inf
        return float(self.length) / float(self.nb_houses)

    def __str__(self) -> str:
        d = self.difficulty()
        d_str = "∞" if math.isinf(d) else f"{d:.3f}"
        return f"Infra({self.infra_id}, type={self.infra_type}, L={self.length}, N={self.nb_houses}, diff={d_str})"

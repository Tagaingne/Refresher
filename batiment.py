from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import math
from infra import Infra


@dataclass
class Batiment:
    """
    Représente un bâtiment et les infrastructures qui permettent de le raccorder.

    Difficulté(bâtiment) = somme des difficultés des infras associées.
    Si une infra a difficulté infinie, la difficulté du bâtiment est infinie.
    """
    id_building: str
    list_infras: List[Infra] = field(default_factory=list)

    def add_infra(self, infra: Infra) -> None:
        self.list_infras.append(infra)

    def difficulty(self) -> float:
        total = 0.0
        for infra in self.list_infras:
            d = infra.difficulty()
            if math.isinf(d):
                return math.inf
            total += d
        return total

    def __str__(self) -> str:
        d = self.difficulty()
        d_str = "∞" if math.isinf(d) else f"{d:.3f}"
        return f"Batiment({self.id_building}, nb_infras={len(self.list_infras)}, diff={d_str})"

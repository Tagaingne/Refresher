from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from infrastructure import Infra


@dataclass
class Batiment:
    """
    Représente un bâtiment à raccorder.
    - Difficulté(bâtiment) = somme des difficultés de ses infras impactées.
    """
    id_building: str
    list_infras: List[Infra] = field(default_factory=list)

    def get_building_difficulty(self) -> float:
        """Somme des difficultés de ses infras impactées (grâce à Infra.__radd__)."""
        return sum((infra for infra in self.list_infras if infra.is_impacted()), 0.0)

    def nb_maisons_total(self) -> int:
        """Total de prises via ses infras impactées (approx. par somme)."""
        return int(sum(infra.nb_houses for infra in self.list_infras if infra.is_impacted()))

    def longueur_totale(self) -> float:
        """Longueur totale des infras impactées utilisées par ce bâtiment (approx. par somme)."""
        return float(sum(infra.length for infra in self.list_infras if infra.is_impacted()))

    def has_impacted_infra(self) -> bool:
        """True si au moins une infra est encore à réparer."""
        return any(infra.is_impacted() for infra in self.list_infras)

    # Tri: plus facile d'abord (difficulté↑, nb maisons↓, longueur↑)
    def __lt__(self, other: "Batiment") -> bool:
        a = (self.get_building_difficulty(), -self.nb_maisons_total(), self.longueur_totale())
        b = (other.get_building_difficulty(), -other.nb_maisons_total(), other.longueur_totale())
        return a < b

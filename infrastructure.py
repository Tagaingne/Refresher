from __future__ import annotations
from dataclasses import dataclass
import math


def calculer_difficulte_infra(length: float, nb_houses: int) -> float:
    """
    Calcule la difficulté d'une infrastructure.
    Règle: difficulté = longueur / nb_maisons
           si nb_maisons <= 0, on renvoie +inf (infrastructure non rentable).
    """
    if nb_houses <= 0:
        return math.inf
    return float(length) / float(nb_houses)


@dataclass
class Infra:
    """
    Représente une infrastructure de raccordement (tronçon).
    - length: longueur agrégée du tronçon
    - infra_type: "infra_intacte" ou autre (impactée)
    - nb_houses: nombre total de maisons desservies par ce tronçon
    """
    infra_id: str
    length: float
    infra_type: str
    nb_houses: int

    def is_impacted(self) -> bool:
        """True si l'infra nécessite une réparation."""
        return self.infra_type != "infra_intacte"

    def repair_infra(self) -> None:
        """Marque l'infra comme réparée."""
        self.infra_type = "infra_intacte"

    def get_infra_difficulty(self) -> float:
        """Renvoie la difficulté via la fonction utilitaire."""
        return calculer_difficulte_infra(self.length, self.nb_houses)

    # Permet sum([infra1, infra2, ...]) -> somme des difficultés (grâce à sum qui fait 0 + infra)
    def __radd__(self, other: float) -> float:
        return float(other) + self.get_infra_difficulty()

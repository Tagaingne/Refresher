from __future__ import annotations

import math
import sys
from typing import Dict, List, Set, Tuple

import pandas as pd

from infra import Infra
from batiment import Batiment


# ==========================
# 1) Chargement & nettoyage
# ==========================
def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    if df.empty:
        raise ValueError("Le fichier Excel est vide.")
    return df


def harmonize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Harmonise les noms de colonnes pour correspondre à :
      - id_batiment
      - infra_id
      - length (depuis 'longueur')
      - infra_type
      - nb_houses (depuis 'nb_maisons')
    """
    # Tolérance à la casse
    col_lower = {c.lower(): c for c in df.columns}

    def get(name: str) -> str | None:
        return col_lower.get(name.lower())

    rename = {}
    if get("longueur"):
        rename[get("longueur")] = "length"
    if get("length"):
        rename[get("length")] = "length"
    if get("nb_maisons"):
        rename[get("nb_maisons")] = "nb_houses"
    if get("nb_houses"):
        rename[get("nb_houses")] = "nb_houses"
    if get("id_batiment"):
        rename[get("id_batiment")] = "id_batiment"
    if get("infra_id"):
        rename[get("infra_id")] = "infra_id"
    if get("infra_type"):
        rename[get("infra_type")] = "infra_type"

    df2 = df.rename(columns=rename)

    required = {"id_batiment", "infra_id", "length", "infra_type", "nb_houses"}
    missing = required - set(df2.columns)
    if missing:
        raise ValueError(
            f"Colonnes manquantes après harmonisation : {missing}. "
            f"Colonnes présentes : {list(df2.columns)}"
        )
    return df2


def nettoyage_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garde uniquement les lignes où l'infrastructure N'EST PAS intacte.
    """
    mask = df["infra_type"].astype(str).str.lower() != "infra_intacte"
    return df[mask].copy()


# ===================================
# 2) Construction des objets métier
# ===================================
def build_objects_from_df(df: pd.DataFrame) -> Dict[str, Batiment]:
    """
    Construit un dict {id_batiment: Batiment} peuplé d'objets Infra.
    """
    batiments: Dict[str, Batiment] = {}
    for row in df.itertuples(index=False):
        infra = Infra(
            infra_id=str(row.infra_id),
            length=float(row.length),
            infra_type=str(row.infra_type),
            nb_houses=int(row.nb_houses) if pd.notna(row.nb_houses) else 0,
        )
        bid = str(row.id_batiment)
        if bid not in batiments:
            batiments[bid] = Batiment(id_building=bid)
        batiments[bid].add_infra(infra)
    return batiments


# ===================================
# 3) Algorithme itératif demandé
# ===================================
def difficulty_with_repaired(b: Batiment, repaired_infra_ids: Set[str]) -> float:
    """
    Difficulté d'un bâtiment en ignorant les infras déjà réparées.
    - 0.0 si le bâtiment n'a plus rien à réparer.
    - inf si une infra restante a difficulty = inf.
    """
    total = 0.0
    has_remaining = False
    for infra in b.list_infras:
        if infra.infra_id in repaired_infra_ids:
            continue
        has_remaining = True
        d = infra.difficulty()
        if math.isinf(d):
            return math.inf
        total += d
    return 0.0 if not has_remaining else total


def plan_reparations(batiments: Dict[str, Batiment]) -> pd.DataFrame:
    """
    Implémente l'algorithme :
      - Créer une liste de tous les bâtiments impactés (remaining)
      - Créer une nouvelle liste vide (ordre)
      - Tant que remaining n'est pas vide :
          * récupérer le bâtiment le moins difficile (en ignorant les infras réparées)
          * réparer toutes ses infras
          * stocker le bâtiment dans la nouvelle liste
          * l'enlever de remaining
    """
    repaired: Set[str] = set()
    remaining: Set[str] = set(batiments.keys())
    ordre: List[dict] = []
    step = 1

    while remaining:
        # Calcul de la difficulté actuelle pour chacun
        diffs: List[Tuple[float, str]] = []
        already_done: List[str] = []
        for bid in list(remaining):
            d = difficulty_with_repaired(batiments[bid], repaired)
            if d == 0.0:
                already_done.append(bid)
            else:
                diffs.append((d, bid))

        # Retirer les bâtiments déjà entièrement réparés
        for bid in already_done:
            remaining.remove(bid)
            ordre.append({
                "step": step,
                "id_batiment": bid,
                "difficulty_at_pick": 0.0,
                "repaired_infras": 0,
            })
            step += 1

        if not remaining:
            break

        if not diffs:
            # Plus rien à faire (tous 0.0) — sécurité
            break

        # Choisir le moins difficile (inf > tout autre nombre, puis tie-break sur id)
        dmin, chosen = min(
            diffs,
            key=lambda t: (math.isinf(t[0]), t[0], t[1])
        )

        if math.isinf(dmin):
            raise ValueError(
                "Tous les bâtiments restants ont une difficulté infinie (nb_maisons <= 0 ?)."
            )

        # Réparer toutes ses infras
        repaired_now = 0
        for infra in batiments[chosen].list_infras:
            if infra.infra_id not in repaired:
                repaired.add(infra.infra_id)
                repaired_now += 1

        # Enregistrer et retirer de remaining
        remaining.remove(chosen)
        ordre.append({
            "step": step,
            "id_batiment": chosen,
            "difficulty_at_pick": round(float(dmin), 6),
            "repaired_infras": repaired_now,
        })
        step += 1

    df_order = pd.DataFrame(ordre).sort_values(by="step").reset_index(drop=True)
    return df_order


# ===================================
# 4) Reporting
# ===================================
def summarize_batiments(batiments: Dict[str, Batiment]) -> pd.DataFrame:
    rows: List[dict] = []
    for bid, b in batiments.items():
        d = b.difficulty()
        rows.append({
            "id_batiment": bid,
            "nb_infras": len(b.list_infras),
            "difficulte_batiment": math.inf if math.isinf(d) else round(float(d), 6),
        })
    df_sum = pd.DataFrame(rows)
    # tri: valeurs finies croissantes, 'inf' à la fin
    df_sum["__key__"] = df_sum["difficulte_batiment"].map(lambda x: float("inf") if x == math.inf else x)
    df_sum = df_sum.sort_values(by=["__key__", "id_batiment"]).drop(columns="__key__").reset_index(drop=True)
    return df_sum


def print_preview(batiments: Dict[str, Batiment], max_items: int = 10) -> None:
    print("\n=== Aperçu des bâtiments ===")
    for i, (bid, b) in enumerate(batiments.items()):
        if i >= max_items:
            print(f"... ({len(batiments) - max_items} autres)")
            break
        print(b)


# ===================================
# 5) main
# ===================================
def main():
    path = "reseau_en_arbre.xlsx"
    if len(sys.argv) > 1:
        path = sys.argv[1]

    print(f"📂 Lecture du fichier : {path}")
    df = load_excel(path)
    df = harmonize_columns(df)
    df = nettoyage_data(df)

    print(f"✅ Lignes après nettoyage (hors 'infra_intacte') : {len(df)}")

    batiments = build_objects_from_df(df)
    print_preview(batiments, max_items=10)

    # Résumé difficultés "brutes" (sans notion de réparation)
    df_resume = summarize_batiments(batiments)
    print("\n=== Résumé des difficultés par bâtiment (brut) ===")
    with pd.option_context("display.max_rows", 50, "display.width", 120):
        print(df_resume.head(20).to_string(index=False))

    # Plan de réparation (algorithme itératif demandé)
    print("\n=== Plan de réparation (bâtiment le moins difficile à chaque itération) ===")
    df_plan = plan_reparations(batiments)
    with pd.option_context("display.max_rows", 50, "display.width", 120):
        print(df_plan.head(20).to_string(index=False))

    # Exports
    df_resume.to_csv("difficulte_batiments.csv", index=False)
    df_plan.to_csv("ordre_reparation.csv", index=False)
    print("\n💾 Exports : 'difficulte_batiments.csv' et 'ordre_reparation.csv'")


if __name__ == "__main__":
    main()






























































# from __future__ import annotations
# import pandas as pd
# from typing import Dict, List, Tuple, Any
# from pathlib import Path

# import infrastructure   # contient : Infra, calculer_difficulte_infra
# import batiment         # contient : Batiment


# # Lecture et nettoyage des données

# def load_excel(path: str, sheet_name: str | None = None) -> pd.DataFrame:
   
#     # Charge un fichier Excel contenant les informations du réseau.

  
#     xls = pd.ExcelFile(path)
#     sheet = sheet_name or xls.sheet_names[0]
#     df = xls.parse(sheet).copy()

#     # Normalisation des types
#     for col in ("longueur", "nb_maisons"):
#         if col in df.columns:
#             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

#     df["id_batiment"] = df["id_batiment"].astype(str)
#     df["infra_id"] = df["infra_id"].astype(str)
#     df["infra_type"] = df["infra_type"].astype(str)
#     return df


# def nettoyage_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:

#     # Filtre les infrastructures intactes et extrait les bâtiments impactés.

#     required = {"infra_type", "id_batiment"}
#     missing = required.difference(df.columns)
#     if missing:
#         raise ValueError(f"Colonnes manquantes : {sorted(missing)}")

#     df_nettoye = df[df["infra_type"] != "infra_intacte"].copy()
#     liste_batiments = (
#         df_nettoye["id_batiment"].dropna().astype(str).unique().tolist()
#     )
#     liste_batiments_vide: list[str] = []
#     return df_nettoye, liste_batiments, liste_batiments_vide


# #  Création du modèle (objets Infra et Batiment)

# def build_model_from_df(
#     df: pd.DataFrame,
# ) -> Tuple[Dict[str, infrastructure.Infra], Dict[str, batiment.Batiment]]:
#     # Construit les objets Infra (mutualisés) et Batiment à partir du DataFrame.

#     required = ["id_batiment", "infra_id", "infra_type", "longueur", "nb_maisons"]
#     missing = [c for c in required if c not in df.columns]
#     if missing:
#         raise ValueError(f"Colonnes manquantes : {missing}")

#     df = df.copy()
#     df["longueur"] = pd.to_numeric(df["longueur"], errors="coerce").fillna(0.0)
#     df["nb_maisons"] = pd.to_numeric(df["nb_maisons"], errors="coerce").fillna(0).astype(int)

#     # Agrégation / mutualisation par infra
#     infra_agg = (
#         df.groupby(["infra_id", "infra_type"], dropna=False)
#         .agg(longueur=("longueur", "sum"), nb_houses=("nb_maisons", "sum"))
#         .reset_index()
#     )

#     # Création des objets Infra
#     infras: Dict[str, infrastructure.Infra] = {}
#     for _, row in infra_agg.iterrows():
#         infras[row["infra_id"]] = infrastructure.Infra(
#             infra_id=row["infra_id"],
#             length=float(row["longueur"]),
#             infra_type=str(row["infra_type"]),
#             nb_houses=int(row["nb_houses"]),
#         )

#     # Création des objets Batiment
#     batiments: Dict[str, batiment.Batiment] = {}
#     for bid, sub in df.groupby("id_batiment"):
#         infra_ids = sub["infra_id"].dropna().astype(str).unique().tolist()
#         batiments[str(bid)] = batiment.Batiment(
#             id_building=str(bid),
#             list_infras=[infras[i] for i in infra_ids if i in infras],
#         )

#     return infras, batiments



# # Fonctions de planification (phase 0 + boucle principale)
# def compute_phase0_buildings(df: pd.DataFrame) -> List[str]:
   
#     impacted_rows = df[df["infra_type"] != "infra_intacte"].copy()
#     all_bat = df["id_batiment"].astype(str).unique().tolist()
#     impacted_bat = impacted_rows["id_batiment"].astype(str).unique().tolist()
#     return sorted(list(set(all_bat) - set(impacted_bat)))


# def reste_des_infras_impactees(infras: Dict[str, infrastructure.Infra]) -> bool:
#     """
#     Vérifie s’il reste au moins une infrastructure à réparer.
#     """
#     return any(infra.is_impacted() for infra in infras.values())


# def planifier_raccordement(df: pd.DataFrame) -> Tuple[List[str], List[Dict[str, Any]]]:
   
#     infras, batiments = build_model_from_df(df)
#     phase0_buildings = compute_phase0_buildings(df)

#     plan: List[Dict[str, Any]] = []
#     etape = 1

#     while reste_des_infras_impactees(infras):
#         candidats = [b for b in batiments.values() if b.has_impacted_infra()]
#         if not candidats:
#             break

#         candidats.sort()
#         choisi = candidats[0]

#         diff = float(choisi.get_building_difficulty())
#         nb_h = int(choisi.nb_maisons_total())
#         long_tot = float(choisi.longueur_totale())

#         nb_reparees = 0
#         for infra in choisi.list_infras:
#             if infra.is_impacted():
#                 infra.repair_infra()
#                 nb_reparees += 1

#         plan.append(
#             {
#                 "etape": etape,
#                 "id_batiment": choisi.id_building,
#                 "difficulte_batiment": diff,
#                 "nb_infras_reparees": nb_reparees,
#                 "nb_maisons_total": nb_h,
#                 "longueur_totale": long_tot,
#             }
#         )
#         etape += 1

#     return phase0_buildings, plan



# if __name__ == "__main__":
#     # 1. Lecture du fichier Excel
#     df = load_excel("./reseau_en_arbre.xlsx")

#     # 2. Nettoyage (ta fonction d’origine, améliorée)
#     df_nettoye, liste_batiments, liste_vide = nettoyage_data(df)
#     print("Aperçu du DataFrame nettoyé :")
#     print(df_nettoye.head(), "\n")
#     print("Bâtiments impactés :", liste_batiments[:10], "\n")

#     # 3. Exécution du plan de raccordement
#     phase0, plan = planifier_raccordement(df)

#     # 4. Export CSV
#     outdir = Path(".")
#     pd.DataFrame({"id_batiment": phase0}).to_csv(outdir / "phase0.csv", index=False)
#     pd.DataFrame(plan).to_csv(outdir / "plan.csv", index=False)

#     print(f"Phase 0 (aucune réparation) : {len(phase0)} bâtiments")
#     print(f"Plan (étapes) : {len(plan)} entrées")
#     print(
#         f"→ Fichiers générés : "
#         f"{(outdir / 'phase0.csv').as_posix()} et {(outdir / 'plan.csv').as_posix()}"
#     )

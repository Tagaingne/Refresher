# import pandas as pd
# import infrastructure
# import batiment
# from typing import Dict, List, Tuple

# df = pd.read_excel("./reseau_en_arbre.xlsx")

# def netoyage_data(df):
#     # Récupérer uniquement les bâtiments impactés
#     df = df[df["infra_type"] != "infra_intacte"]
#     liste_batiments = df["id_batiment"].unique().tolist()
#     liste_batiments_vide = []

#     return df, liste_batiments, liste_batiments_vide


# # Appeler correctement la fonction
# df_nettoye, liste_batiments, liste_vide = netoyage_data(df)
# print(df_nettoye.head())


# print(liste_batiments)  



from __future__ import annotations
import pandas as pd
from typing import Dict, List, Tuple, Any
from pathlib import Path

import infrastructure   # contient : Infra, calculer_difficulte_infra
import batiment         # contient : Batiment


# Lecture et nettoyage des données

def load_excel(path: str, sheet_name: str | None = None) -> pd.DataFrame:
   
    # Charge un fichier Excel contenant les informations du réseau.

  
    xls = pd.ExcelFile(path)
    sheet = sheet_name or xls.sheet_names[0]
    df = xls.parse(sheet).copy()

    # Normalisation des types
    for col in ("longueur", "nb_maisons"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["id_batiment"] = df["id_batiment"].astype(str)
    df["infra_id"] = df["infra_id"].astype(str)
    df["infra_type"] = df["infra_type"].astype(str)
    return df


def nettoyage_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:

    # Filtre les infrastructures intactes et extrait les bâtiments impactés.

    required = {"infra_type", "id_batiment"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {sorted(missing)}")

    df_nettoye = df[df["infra_type"] != "infra_intacte"].copy()
    liste_batiments = (
        df_nettoye["id_batiment"].dropna().astype(str).unique().tolist()
    )
    liste_batiments_vide: list[str] = []
    return df_nettoye, liste_batiments, liste_batiments_vide


#  Création du modèle (objets Infra et Batiment)

def build_model_from_df(
    df: pd.DataFrame,
) -> Tuple[Dict[str, infrastructure.Infra], Dict[str, batiment.Batiment]]:
    # Construit les objets Infra (mutualisés) et Batiment à partir du DataFrame.

    required = ["id_batiment", "infra_id", "infra_type", "longueur", "nb_maisons"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    df = df.copy()
    df["longueur"] = pd.to_numeric(df["longueur"], errors="coerce").fillna(0.0)
    df["nb_maisons"] = pd.to_numeric(df["nb_maisons"], errors="coerce").fillna(0).astype(int)

    # Agrégation / mutualisation par infra
    infra_agg = (
        df.groupby(["infra_id", "infra_type"], dropna=False)
        .agg(longueur=("longueur", "sum"), nb_houses=("nb_maisons", "sum"))
        .reset_index()
    )

    # Création des objets Infra
    infras: Dict[str, infrastructure.Infra] = {}
    for _, row in infra_agg.iterrows():
        infras[row["infra_id"]] = infrastructure.Infra(
            infra_id=row["infra_id"],
            length=float(row["longueur"]),
            infra_type=str(row["infra_type"]),
            nb_houses=int(row["nb_houses"]),
        )

    # Création des objets Batiment
    batiments: Dict[str, batiment.Batiment] = {}
    for bid, sub in df.groupby("id_batiment"):
        infra_ids = sub["infra_id"].dropna().astype(str).unique().tolist()
        batiments[str(bid)] = batiment.Batiment(
            id_building=str(bid),
            list_infras=[infras[i] for i in infra_ids if i in infras],
        )

    return infras, batiments



# Fonctions de planification (phase 0 + boucle principale)
def compute_phase0_buildings(df: pd.DataFrame) -> List[str]:
   
    impacted_rows = df[df["infra_type"] != "infra_intacte"].copy()
    all_bat = df["id_batiment"].astype(str).unique().tolist()
    impacted_bat = impacted_rows["id_batiment"].astype(str).unique().tolist()
    return sorted(list(set(all_bat) - set(impacted_bat)))


def reste_des_infras_impactees(infras: Dict[str, infrastructure.Infra]) -> bool:
    """
    Vérifie s’il reste au moins une infrastructure à réparer.
    """
    return any(infra.is_impacted() for infra in infras.values())


def planifier_raccordement(df: pd.DataFrame) -> Tuple[List[str], List[Dict[str, Any]]]:
   
    infras, batiments = build_model_from_df(df)
    phase0_buildings = compute_phase0_buildings(df)

    plan: List[Dict[str, Any]] = []
    etape = 1

    while reste_des_infras_impactees(infras):
        candidats = [b for b in batiments.values() if b.has_impacted_infra()]
        if not candidats:
            break

        candidats.sort()
        choisi = candidats[0]

        diff = float(choisi.get_building_difficulty())
        nb_h = int(choisi.nb_maisons_total())
        long_tot = float(choisi.longueur_totale())

        nb_reparees = 0
        for infra in choisi.list_infras:
            if infra.is_impacted():
                infra.repair_infra()
                nb_reparees += 1

        plan.append(
            {
                "etape": etape,
                "id_batiment": choisi.id_building,
                "difficulte_batiment": diff,
                "nb_infras_reparees": nb_reparees,
                "nb_maisons_total": nb_h,
                "longueur_totale": long_tot,
            }
        )
        etape += 1

    return phase0_buildings, plan



if __name__ == "__main__":
    # 1. Lecture du fichier Excel
    df = load_excel("./reseau_en_arbre.xlsx")

    # 2. Nettoyage (ta fonction d’origine, améliorée)
    df_nettoye, liste_batiments, liste_vide = nettoyage_data(df)
    print("Aperçu du DataFrame nettoyé :")
    print(df_nettoye.head(), "\n")
    print("Bâtiments impactés :", liste_batiments[:10], "\n")

    # 3. Exécution du plan de raccordement
    phase0, plan = planifier_raccordement(df)

    # 4. Export CSV
    outdir = Path(".")
    pd.DataFrame({"id_batiment": phase0}).to_csv(outdir / "phase0.csv", index=False)
    pd.DataFrame(plan).to_csv(outdir / "plan.csv", index=False)

    print(f"Phase 0 (aucune réparation) : {len(phase0)} bâtiments")
    print(f"Plan (étapes) : {len(plan)} entrées")
    print(
        f"→ Fichiers générés : "
        f"{(outdir / 'phase0.csv').as_posix()} et {(outdir / 'plan.csv').as_posix()}"
    )

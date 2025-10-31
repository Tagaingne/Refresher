import os
import sys
import pandas as pd


def read_csv_required(path: str) -> pd.DataFrame:
    """Lit un fichier CSV et vérifie qu’il existe et n’est pas vide."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    if os.path.getsize(path) < 5:
        raise ValueError(f"Fichier vide : {path}")
    return pd.read_csv(path)


def read_excel_required(path: str, sheet_name=0) -> pd.DataFrame:
    """Lit un fichier Excel (.xlsx) et vérifie qu’il existe."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    return pd.read_excel(path, sheet_name=sheet_name)


def main(
    p_imp="./resultats_impactes.csv",
    p_reseau="./reseau_en_arbre.xlsx",
    p_bats="./batiments.csv",
    p_infra="./infra.csv",
    out="./jointure_batiments_impactes.csv",
    filtrer_infras_intactes=True,
):
    # 1️⃣ Charger les données
    df_imp = read_csv_required(p_imp)       # id_batiment, difficulte, nb_infras
    df_map = read_excel_required(p_reseau)  # id_batiment, nb_maisons, infra_id, infra_type, longueur
    df_bat = read_csv_required(p_bats)      # id_batiment, type_batiment, nb_maisons
    df_infra = read_csv_required(p_infra)   # id_infra, type_infra

    # 2️⃣ Harmoniser les clés
    if "id_infra" in df_infra.columns and "infra_id" not in df_infra.columns:
        df_infra = df_infra.rename(columns={"id_infra": "infra_id"})

    # 3️⃣ Vérification des colonnes nécessaires
    checks = {
        "resultats_impactes.csv": (df_imp, {"id_batiment"}),
        "reseau_en_arbre.xlsx": (df_map, {"id_batiment", "infra_id", "infra_type", "longueur"}),
        "batiments.csv": (df_bat, {"id_batiment", "type_batiment", "nb_maisons"}),
        "infra.csv": (df_infra, {"infra_id"}),
    }

    for fname, (df, required) in checks.items():
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans {fname}: {sorted(missing)}")

    # 4️⃣ Filtrer uniquement les bâtiments impactés
    ids_impactes = set(df_imp["id_batiment"].astype(str).unique())
    df_map["id_batiment"] = df_map["id_batiment"].astype(str)
    df_bat["id_batiment"] = df_bat["id_batiment"].astype(str)
    df_map_imp = df_map[df_map["id_batiment"].isin(ids_impactes)].copy()

    # Filtrer les infras intactes si demandé
    if filtrer_infras_intactes:
        df_map_imp = df_map_imp[df_map_imp["infra_type"] != "infra_intacte"]

    # 5️⃣ Joindre les infos bâtiment
    df_bat_sel = df_bat[["id_batiment", "type_batiment", "nb_maisons"]].copy()
    df_joint = pd.merge(df_map_imp, df_bat_sel, on="id_batiment", how="left", suffixes=("", "_bat"))

    # Si doublon nb_maisons, on garde celle du CSV bâtiment
    if "nb_maisons_bat" in df_joint.columns:
        df_joint["nb_maisons"] = df_joint["nb_maisons_bat"].fillna(df_joint["nb_maisons"])
        df_joint = df_joint.drop(columns=["nb_maisons_bat"])

    # 6️⃣ Joindre les infos infra
    df_joint = pd.merge(df_joint, df_infra, on="infra_id", how="left")

    # 7️⃣ Joindre la difficulté globale
    df_imp_sel = df_imp[["id_batiment", "difficulte", "nb_infras"]].copy()
    df_joint = pd.merge(df_joint, df_imp_sel, on="id_batiment", how="left")

    # 8️⃣ Réordonner les colonnes
    colonnes_avant = [
        "id_batiment", "type_batiment", "difficulte", "nb_infras",
        "infra_id", "infra_type", "type_infra", "longueur", "nb_maisons"
    ]
    colonnes = [c for c in colonnes_avant if c in df_joint.columns] + \
               [c for c in df_joint.columns if c not in colonnes_avant]
    df_joint = df_joint[colonnes]

    # 9️⃣ Sauvegarde
    df_joint.to_csv(out, index=False)
    print(f"✅ Fichier généré : {out}")
    print(f"Lignes : {len(df_joint)}  |  Bâtiments distincts : {df_joint['id_batiment'].nunique()}")
    print("Aperçu :")
    print(df_joint.head(10))


if __name__ == "__main__":
    # 🔸 tu peux mettre filtrer_infras_intactes=False pour garder toutes les infras
    main()

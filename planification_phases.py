# from __future__ import annotations

# import pandas as pd
# from typing import Dict
# import math

# # ====== FICHIERS ======
# INPUT = "./jointure_batiments_impactes.csv"
# OUT_PER_INFRA = "./plan_par_infra.csv"
# OUT_PHASES = "./phases_affectation.csv"
# OUT_LISTES = "./listes_par_phase.csv"

# # ====== BARÈMES (annexe + audio) ======
# COUT_MATERIEL_PAR_M: Dict[str, float] = {
#     "aerien": 500.0,
#     "semi-aerien": 750.0,
#     "fourreau": 900.0,
# }
# H_PAR_M_PAR_OUVRIER: Dict[str, float] = {
#     "aerien": 2.0,
#     "semi-aerien": 4.0,
#     "fourreau": 5.0,
# }
# TAUX_HORAIRE = 300.0 / 8.0  # 37.5 €/h
# MAX_OUVRIERS_PAR_INFRA = 4

# # Contrainte hôpital : 20 h d'autonomie, marge 20 % -> objectif calendrier = 16 h
# HOPITAL_DELAI_HEURES = 16.0

# # Sous-priorité (hôpital) par type d'infra : plus rapide d'abord
# ORDRE_INFRA_RAPIDITE = {"aerien": 0, "semi-aerien": 1, "fourreau": 2}

# # ====== IMPORT DES CLASSES ORIENTÉES OBJET ======
# from infra import Infra
# from batiment import Batiment


# # ====== NORMALISATION TEXTE (accents/casse) ======
# def normalize_series(s: pd.Series) -> pd.Series:
#     """
#     Minuscule, retire accents, supprime non-lettres -> 'hopital', 'ecole', 'habitation'
#     Exemple: 'Hôpital' -> 'hopital'
#     """
#     return (
#         s.astype(str)
#          .str.normalize("NFKD")
#          .str.encode("ascii", "ignore")
#          .str.decode("ascii")
#          .str.lower()
#          .str.replace(r"[^a-z]", "", regex=True)
#     )


# def normalize_infra_type(s: pd.Series) -> pd.Series:
#     """
#     Normalise type_infra aux clés attendues: 'aerien', 'semi-aerien', 'fourreau'
#     Gère variantes: 'semi aerien', 'semi_aerien', 'semi-aérien', etc.
#     """
#     base = (
#         s.astype(str)
#          .str.normalize("NFKD")
#          .str.encode("ascii", "ignore")
#          .str.decode("ascii")
#          .str.lower()
#          .str.replace(r"[\s_]+", "-", regex=True)  # espaces/underscores -> tirets
#     )
#     # Nettoyage final (par prudence)
#     base = base.str.replace(r"[^a-z\-]", "", regex=True)
#     # Map des variantes communes
#     mapping = {
#         "aerien": "aerien",
#         "semi-aerien": "semi-aerien",
#         "semiaerien": "semi-aerien",
#         "semi-aerien": "semi-aerien",
#         "fourreau": "fourreau",
#     }
#     return base.map(mapping).fillna(base)


# # ====== UTILITAIRES COÛT/DURÉE ======
# def duree_infra(longueur_m: float, type_infra_norm: str, nb_ouvriers: int = MAX_OUVRIERS_PAR_INFRA) -> float:
#     tpm = H_PAR_M_PAR_OUVRIER.get(type_infra_norm)
#     if tpm is None:
#         raise ValueError(f"type_infra non reconnu: {type_infra_norm}")
#     n = max(1, min(nb_ouvriers, MAX_OUVRIERS_PAR_INFRA))
#     return (float(longueur_m) * tpm) / n


# def couts_infra(longueur_m: float, type_infra_norm: str, nb_ouvriers: int = MAX_OUVRIERS_PAR_INFRA) -> tuple[float, float, float]:
#     cout_mat = float(longueur_m) * COUT_MATERIEL_PAR_M[type_infra_norm]
#     heures = duree_infra(longueur_m, type_infra_norm, nb_ouvriers)
#     cout_mo = heures * TAUX_HORAIRE
#     return cout_mat, cout_mo, cout_mat + cout_mo


# # ====== DIFFICULTÉ par BÂTIMENT via Infra/Batiment + __radd__ ======
# def difficulte_batiments(df_subset: pd.DataFrame) -> pd.Series:
#     """
#     difficulté(infra) = longueur / nb_maisons ; difficulté(bâtiment) = somme(difficultés infra)
#     Utilise Infra, Batiment et __radd__ pour que sum([Batiment]) renvoie la difficulté.
#     Attend colonnes: id_batiment, infra_id, type_infra_norm, longueur, nb_maisons
#     """
#     bats: Dict[str, Batiment] = {}
#     for _, row in df_subset.iterrows():
#         nb_mais = int(row["nb_maisons"]) if not pd.isna(row["nb_maisons"]) else 0

#         infra = Infra(
#             infra_id=str(row.get("infra_id", "")),
#             longueur=float(row["longueur"]),
#             infra_type=str(row["type_infra_norm"]),  # déjà normalisé
#             nb_maisons=nb_mais,
#         )
#         bid = str(row["id_batiment"])
#         if bid not in bats:
#             bats[bid] = Batiment(bid)
#         bats[bid].add_infra(infra)

#     # Grâce à __radd__, sum([b]) == b.difficulty()
#     diff = {bid: sum([b]) for bid, b in bats.items()}
#     return pd.Series(diff).sort_values()


# # ====== AFFECTATION DES PHASES ======
# def affecter_phases(df_calc: pd.DataFrame) -> pd.DataFrame:
#     """
#     Phase 0 : tout l'hôpital (priorité: aerien -> semi-aerien -> fourreau, puis durée croissante)
#     Phase 1 : toutes les écoles ; si coût < 40%, compléter avec habitations en difficulté croissante
#     Phases 2-4 : habitations restantes en difficulté croissante, cibles ≈ 20/20/20 % du coût restant
#     (répartition par blocs de bâtiments entiers)
#     """
#     df = df_calc.copy()
#     df["phase"] = None

#     # --- HÔPITAL : phase 0, ordre priorisé ---
#     mask_hop = df["type_batiment_norm"] == "hopital"
#     hop = df[mask_hop].copy()
#     if not hop.empty:
#         hop = hop.assign(_ord=hop["type_infra_norm"].map(ORDRE_INFRA_RAPIDITE).fillna(9))
#         hop = hop.sort_values(["_ord", "heures_4_ouvriers"], ascending=[True, True]).drop(columns="_ord")
#         df.loc[hop.index, "phase"] = 0

#     # --- Sépare le reste en écoles/habitations ---
#     reste = df[~mask_hop].copy()
#     eco = reste[reste["type_batiment_norm"] == "ecole"].copy()
#     hab = reste[reste["type_batiment_norm"] == "habitation"].copy()

#     # --- Phase 1 : écoles + top-up habitations (difficulté croissante) si < 40% ---
#     phase1_target = 0.40 * (eco["cout_total"].sum() + hab["cout_total"].sum())
#     cout_phase1 = 0.0

#     # Met toutes les écoles en phase 1
#     if not eco.empty:
#         df.loc[eco.index, "phase"] = 1
#         cout_phase1 += eco["cout_total"].sum()

#     # Complète avec habitations moins difficiles d'abord si besoin
#     if cout_phase1 < phase1_target and not hab.empty:
#         diff_series = difficulte_batiments(hab)
#         for b_id in diff_series.index:
#             bloc = hab[hab["id_batiment"] == b_id]
#             incr = bloc["cout_total"].sum()
#             df.loc[bloc.index, "phase"] = 1
#             cout_phase1 += incr
#             if cout_phase1 >= phase1_target:
#                 break

#     # --- Phases 2-4 : habitations restantes par difficulté croissante ---
#     hab_rest = df[(df["type_batiment_norm"] == "habitation") & (df["phase"].isna())].copy()
#     total_hab_rest = hab_rest["cout_total"].sum()
#     if total_hab_rest > 0:
#         cibles = {2: 0.20 * total_hab_rest, 3: 0.20 * total_hab_rest, 4: 0.20 * total_hab_rest}
#         cum = {2: 0.0, 3: 0.0, 4: 0.0}
#         phase = 2
#         diff_series_rest = difficulte_batiments(hab_rest)
#         for b_id in diff_series_rest.index:
#             bloc = hab_rest[hab_rest["id_batiment"] == b_id]
#             cout_bloc = bloc["cout_total"].sum()
#             while phase < 4 and cum[phase] + cout_bloc > cibles[phase]:
#                 phase += 1
#             if phase > 4:
#                 phase = 4
#             df.loc[bloc.index, "phase"] = phase
#             cum[phase] += cout_bloc

#     # Cas résiduels : phase 4
#     df["phase"] = df["phase"].fillna(4).astype(int)

#     # Lisibilité : remonter physiquement l'hôpital en tête et ordonné
#     hop_mask2 = df["phase"] == 0
#     if hop_mask2.any():
#         df_hop = df[hop_mask2].copy()
#         df_hop = df_hop.assign(_ord=df_hop["type_infra_norm"].map(ORDRE_INFRA_RAPIDITE).fillna(9))
#         df_hop = df_hop.sort_values(["_ord", "heures_4_ouvriers"], ascending=[True, True]).drop(columns="_ord")
#         df = pd.concat([df_hop, df[~hop_mask2]], ignore_index=True)

#     return df


# # ====== MAIN ======
# def main() -> None:
#     # 1) Charger le CSV consolidé
#     df = pd.read_csv(INPUT)

#     # Colonnes minimales attendues
#     required = {"id_batiment", "type_batiment", "type_infra", "infra_type", "longueur", "nb_maisons"}
#     missing = required - set(df.columns)
#     if missing:
#         raise ValueError(f"Colonnes manquantes dans {INPUT}: {sorted(missing)}")

#     # 2) Ne garder que les infras à remplacer (si la jointure contient encore 'infra_intacte')
#     df = df[df["infra_type"] != "infra_intacte"].copy()

#     # 3) Colonnes normalisées (sans altérer les originales pour l'export)
#     df["type_batiment_norm"] = normalize_series(df["type_batiment"])
#     df["type_infra_norm"] = normalize_infra_type(df["type_infra"])

#     # 4) Calcul par infra (coûts + heures avec 4 ouvriers) à partir des types normalisés
#     lignes = []
#     for _, r in df.iterrows():
#         t_infra_norm = str(r["type_infra_norm"])
#         if t_infra_norm not in COUT_MATERIEL_PAR_M:
#             raise ValueError(f"type_infra non reconnu: {t_infra_norm} (attendus: {list(COUT_MATERIEL_PAR_M)})")
#         L = float(r["longueur"])
#         cout_mat, cout_mo, cout_tot = couts_infra(L, t_infra_norm, MAX_OUVRIERS_PAR_INFRA)
#         h = duree_infra(L, t_infra_norm, MAX_OUVRIERS_PAR_INFRA)
#         lignes.append({
#             "id_batiment": r["id_batiment"],
#             "type_batiment": r["type_batiment"],
#             "type_batiment_norm": r["type_batiment_norm"],
#             "infra_id": r.get("infra_id", None),
#             "type_infra": r["type_infra"],
#             "type_infra_norm": t_infra_norm,
#             "infra_type": r["infra_type"],
#             "longueur": L,
#             "nb_maisons": r["nb_maisons"],
#             "heures_4_ouvriers": h,
#             "cout_materiel": cout_mat,
#             "cout_main_oeuvre": cout_mo,
#             "cout_total": cout_tot,
#         })
#     df_calc = pd.DataFrame(lignes)

#     # 5) Contrainte HÔPITAL (makespan = max des durées unitaires, équipes en parallèle illimitées)
#     hop = df_calc[df_calc["type_batiment_norm"] == "hopital"].copy()
#     print("=== CONTRAINTE HÔPITAL ===")
#     if not hop.empty:
#         max_h = hop["heures_4_ouvriers"].max()
#         print(f"Durée max d'une infra hôpital (4 ouvriers) : {max_h:.2f} h")
#         print(f"Objectif calendrier : ≤ {HOPITAL_DELAI_HEURES:.2f} h")
#         print("Résultat :", "OK ✅" if max_h <= HOPITAL_DELAI_HEURES else "⚠️ NON RESPECTÉ — au moins une infra dépasse 16 h même avec 4 ouvriers")
#     else:
#         print("Aucune infrastructure d'hôpital détectée.")

#     # 6) Affectation des phases (avec règles demandées)
#     df_phases = affecter_phases(df_calc)

#     # 7) Exports
#     df_phases.to_csv(OUT_PER_INFRA, index=False)

#     recap = (
#         df_phases.groupby("phase", as_index=False)
#                  .agg(
#                      cout_materiel=("cout_materiel", "sum"),
#                      cout_main_oeuvre=("cout_main_oeuvre", "sum"),
#                      cout_total=("cout_total", "sum"),
#                      nb_infras=("infra_id", "count"),
#                      heures=("heures_4_ouvriers", "sum"),
#                      nb_batiments=("id_batiment", "nunique"),
#                  )
#                  .sort_values("phase")
#     )
#     recap["part_du_cout"] = recap["cout_total"] / recap["cout_total"].sum()
#     recap.to_csv(OUT_PHASES, index=False)

#     listes = (df_phases
#               .groupby(["phase", "id_batiment"], as_index=False)
#               .agg(
#                   infras=("infra_id", lambda s: ",".join(map(str, sorted(set(s))))),
#                   cout_total=("cout_total", "sum"),
#                   cout_materiel=("cout_materiel", "sum"),
#                   cout_main_oeuvre=("cout_main_oeuvre", "sum"),
#                   heures=("heures_4_ouvriers", "sum"),
#               ))
#     listes.to_csv(OUT_LISTES, index=False)

#     # 8) Sorties console
#     print("\n=== RÉSUMÉ PHASES ===")
#     print(recap)

#     print("\n=== HÔPITAL — ordre de traitement (type plus rapide puis plus court) ===")
#     df_hop = df_phases[df_phases["phase"] == 0].copy()
#     if df_hop.empty:
#         print("Aucune infrastructure d'hôpital.")
#     else:
#         df_hop = df_hop.assign(_ord=df_hop["type_infra_norm"].map(ORDRE_INFRA_RAPIDITE).fillna(9))
#         df_hop = df_hop.sort_values(["_ord", "heures_4_ouvriers"], ascending=[True, True]).drop(columns="_ord")
#         cols_show = ["id_batiment", "infra_id", "type_infra", "longueur", "heures_4_ouvriers", "cout_total"]
#         print(df_hop[cols_show].to_string(index=False))

#     print("\n✅ Fichiers générés :")
#     print(f" - {OUT_PER_INFRA}")
#     print(f" - {OUT_PHASES}")
    


# if __name__ == "__main__":
#     main()









from __future__ import annotations
import pandas as pd
from infra import Infra
from batiment import Batiment

# --------- Fichiers ---------
INPUT = "./jointure_batiments_impactes.csv"
OUTPUT = "./rapport_batiments_objet.csv"
OUTPUT_SORTED = "./rapport_batiments_objet_trie.csv"

# --------- Barèmes ---------
RATE_MATERIAL = {"aerien": 500.0, "semi-aerien": 750.0, "fourreau": 900.0}
H_PER_M_PER_WORKER = {"aerien": 2.0, "semi-aerien": 4.0, "fourreau": 5.0}
WAGE = 300.0 / 8.0   # 37.5 €/h
TEAM_SIZE = 4
HOPITAL_DELAI_H = 16.0  # 20h - 20%

# --------- Normalisation ---------
def norm_text(s: str) -> str:
    import unicodedata, re
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9\-\s_]", "", s)
    return s.strip()

def norm_type_infra(t: str) -> str:
    t = norm_text(t).replace(" ", "-").replace("_", "-")
    mapping = {
        "aerien": "aerien",
        "semi-aerien": "semi-aerien",
        "semiaerien": "semi-aerien",
        "fourreau": "fourreau",
        "fouraux": "fourreau",   # tolère faute
    }
    return mapping.get(t, t)

def norm_type_bat(t: str) -> str:
    t = norm_text(t).replace(" ", "")
    if "hopital" in t:
        return "hopital"
    if "ecole" in t:
        return "ecole"
    return "habitation"

def main():
    # --- Chargement ---
    df = pd.read_csv(INPUT)

    # --- Colonnes minimales ---
    need = {"id_batiment", "infra_id", "type_infra", "type_batiment", "longueur"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"Colonnes manquantes dans {INPUT}: {sorted(miss)}")

    # --- Ne garder que les infras à remplacer (si flag présent) ---
    if "infra_type" in df.columns:
        df = df[df["infra_type"] != "infra_intacte"].copy()

    # --- Construction objets Batiment/Infra ---
    batiments: dict[str, Batiment] = {}
    for _, row in df.iterrows():
        b_id = str(row["id_batiment"])
        t_infra = norm_type_infra(row["type_infra"])
        t_bat = norm_type_bat(row.get("type_batiment", "habitation"))
        L = float(row["longueur"])
        nb_mais = int(row.get("nb_maisons", 1)) if pd.notna(row.get("nb_maisons", 1)) else 1

        # Crée l'objet Infra
        infra = Infra(
            infra_id=str(row["infra_id"]),
            longueur=L,
            infra_type=t_infra,
            nb_maisons=nb_mais,
        )

        # Ajoute au bon Batiment
        if b_id not in batiments:
            batiments[b_id] = Batiment(b_id)
            # on stocke le type du bâtiment
            setattr(batiments[b_id], "type_batiment", t_bat)
        batiments[b_id].add_infra(infra)

    # --- Calculs par bâtiment ---
    results = []
    for bid, b in batiments.items():
        t_bat = getattr(b, "type_batiment", "habitation")
        cout_mat = cout_mo = 0.0
        makespan = 0.0

        for infra in b.list_infras:
            t = norm_type_infra(infra.infra_type)
            if t not in RATE_MATERIAL or t not in H_PER_M_PER_WORKER:
                raise ValueError(f"type_infra non reconnu: {t} (attendus: {list(RATE_MATERIAL)})")
            L = float(infra.longueur)

            # Heures-homme (indépendant du nb d'ouvriers), durée calendaire (avec 4 ouvriers/infra)
            person_hours = L * H_PER_M_PER_WORKER[t]
            cal_hours = person_hours / TEAM_SIZE

            # Coûts
            mat = L * RATE_MATERIAL[t]
            mo = person_hours * WAGE

            cout_mat += mat
            cout_mo += mo
            makespan = max(makespan, cal_hours)

        results.append({
            "id_batiment": bid,
            "type_batiment": t_bat,
            "nb_infras": len(b.list_infras),
            "duree_makespan_h": round(makespan, 2),
            "cout_materiel": round(cout_mat, 2),
            "cout_main_oeuvre": round(cout_mo, 2),
            "cout_total": round(cout_mat + cout_mo, 2),
        })

    df_bats = pd.DataFrame(results)

    # --- Vérification hôpital (makespan <= 16 h) ---
    hop = df_bats[df_bats["type_batiment"] == "hopital"]
    if not hop.empty:
        max_h = float(hop["duree_makespan_h"].max())
        if max_h <= HOPITAL_DELAI_H:
            print(f"✅ Hôpital OK (makespan {max_h:.2f} h ≤ 16 h)")
        else:
            print(f"⚠️ Hôpital NON conforme ({max_h:.2f} h > 16 h)")

    # --- Affectation des phases ---
    phases: dict[int, list[str]] = {}

    # Phase 0 : hôpital
    phases[0] = df_bats[df_bats["type_batiment"] == "hopital"]["id_batiment"].tolist()

    # Calcul du "reste" (hors hôpital) pour les quotas 40/20/20
    reste = df_bats[~df_bats["id_batiment"].isin(phases[0])].copy()
    reste_cost = float(reste["cout_total"].sum())

    # Phase 1 : ~40% du coût du reste (on prend les plus coûteux d'abord pour atteindre plus vite la cible)
    phases[1] = []
    cum = 0.0
    for _, r in reste.sort_values("cout_total", ascending=False).iterrows():
        if cum >= 0.40 * reste_cost:
            break
        phases[1].append(r["id_batiment"])
        cum += float(r["cout_total"])

    # Phases 2,3,4 : ~20% chacune du reste
    phase_rest = [bid for bid in reste["id_batiment"] if bid not in phases[1]]
    df_rest = df_bats[df_bats["id_batiment"].isin(phase_rest)].copy()
    # ordre ascendant pour mieux remplir les quotas finement
    df_rest = df_rest.sort_values("cout_total", ascending=True)

    target = 0.20 * reste_cost
    phases[2], phases[3], phases[4] = [], [], []
    c2 = c3 = c4 = 0.0
    for _, r in df_rest.iterrows():
        bid = r["id_batiment"]; c = float(r["cout_total"])
        # on remplit la phase au plus "vide" en respectant la cible souple
        if c2 + c <= target or (c2 <= c3 and c2 <= c4):
            phases[2].append(bid); c2 += c
        elif c3 + c <= target or (c3 <= c4):
            phases[3].append(bid); c3 += c
        else:
            phases[4].append(bid); c4 += c

    # Application des phases
    def find_phase(bid: str) -> int:
        for ph, lst in phases.items():
            if bid in lst:
                return ph
        return 4

    df_bats["phase"] = df_bats["id_batiment"].map(find_phase).astype(int)

    # --- Tri final : phase 0 -> 1 -> 2 -> 3 -> 4, puis coût décroissant
    ordre_phase = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
    df_bats["__phase_order"] = df_bats["phase"].map(ordre_phase).fillna(99).astype(int)
    df_bats = df_bats.sort_values(["__phase_order", "cout_total"], ascending=[True, False]).drop(columns="__phase_order")

    # --- Exports ---
    df_bats.to_csv(OUTPUT, index=False)
    df_bats.to_csv(OUTPUT_SORTED, index=False)

    print(f"✅ Rapport généré : {OUTPUT}")
    print(f"✅ Rapport trié (phase 0→4, coût décroissant) : {OUTPUT_SORTED}")
    print("\nAperçu :")
    print(df_bats.head(12).to_string(index=False))

if __name__ == "__main__":
    main()

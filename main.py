import pandas as pd
import infrastructure
import batiment
from typing import Dict, List, Tuple

df = pd.read_excel("./reseau_en_arbre.xlsx")

def netoyage_data(df):
    # Récupérer uniquement les bâtiments impactés
    df = df[df["infra_type"] != "infra_intacte"]
    liste_batiments = df["id_batiment"].unique().tolist()
    liste_batiments_vide = []

    return df, liste_batiments, liste_batiments_vide


# Appeler correctement la fonction
df_nettoye, liste_batiments, liste_vide = netoyage_data(df)
print(df_nettoye.head())


print(liste_batiments)  
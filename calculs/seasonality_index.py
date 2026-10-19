from __future__ import annotations

import pandas as pd
import numpy as np

MOIS_NOMS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


def annees_completes_saisonnalite(
    donnees: pd.DataFrame,
    annee_debut: int,
    annee_fin: int,
    annee_cloture: int | None = None,
    mois_cloture: int | None = None,
) -> list[int]:
    """Années réalisées réellement complètes (les 12 mois présents)."""
    realise = donnees.loc[
        donnees["nature"].eq("Réalisé") & donnees["mois"].between(1, 12)
    ]
    if realise.empty:
        return []

    if annee_cloture is None or mois_cloture is None:
        annee_cloture = int(realise["annee"].max())
        mois_cloture = int(
            realise.loc[realise["annee"].eq(annee_cloture), "mois"].max()
        )

    # Nombre de mois distincts réalisés par année
    mois_par_annee = (
        realise.loc[realise["annee"].between(annee_debut, annee_fin)]
        .drop_duplicates(["annee", "mois"])
        .groupby("annee")["mois"]
        .nunique()
    )

    resultat: list[int] = []
    for annee in sorted(mois_par_annee.index):
        annee = int(annee)
        # Année de clôture partielle : exclue
        if annee == annee_cloture and mois_cloture < 12:
            continue
        # N'accepter que les années avec les 12 mois
        if int(mois_par_annee.loc[annee]) == 12:
            resultat.append(annee)
    return resultat


def calculer_indices_saisonnalite(
    donnees: pd.DataFrame,
    valeur: str,
    annee_debut: int,
    annee_fin: int,
    annee_cloture: int | None = None,
    mois_cloture: int | None = None,
) -> pd.DataFrame:
    """
    Calcule l'IS avec la méthode Excel (moyenne des ratios annuels).
    """
    if annee_fin <= annee_debut:
        raise ValueError("L’année de fin doit être supérieure à l’année de début.")
    
    colonnes_requises = {"annee", "mois", "nature", valeur}
    manquantes = colonnes_requises.difference(donnees.columns)
    if manquantes:
        raise ValueError(
            "Colonnes manquantes pour calculer la saisonnalité : "
            + ", ".join(sorted(manquantes))
        )

    annees = annees_completes_saisonnalite(
        donnees, annee_debut, annee_fin, annee_cloture, mois_cloture
    )
    grille_mois = pd.Index(range(1, 13), name="mois")

    if not annees:
        return pd.DataFrame(
            {
                "Mois": MOIS_NOMS,
                "Volume moyen": 0.0,
                "Nombre de périodes": 0,
                "Indice saisonnier": float("nan"),
            }
        )

    # 1. Filtrer uniquement le réalisé sur les années complètes
    selection = donnees.loc[
        donnees["nature"].eq("Réalisé")
        & donnees["annee"].isin(annees)
        & donnees["mois"].between(1, 12)
    ]

    # 2. SOMME PAR MOIS POUR CHAQUE ANNÉE (C'est ce qui manquait pour gérer les sous-totaux et les articles)
    volumes = (
        selection.groupby(["annee", "mois"])[valeur]
        .sum()
        .unstack("mois")
        .reindex(index=annees, columns=range(1, 13))
        .fillna(0.0)
    )

    # 3. Moyenne mensuelle de chaque année (pour le ratio)
    moyennes_annuelles = volumes.sum(axis=1) / 12.0
    moyennes_annuelles = moyennes_annuelles.replace(0, np.nan) # Éviter division par zéro

    # 4. Calcul des ratios (Volume du mois / Moyenne de l'année)
    ratios = volumes.div(moyennes_annuelles, axis=0)

    # 5. Moyenne des ratios sur les années (Méthode Excel)
    indices = ratios.mean(axis=0).fillna(0.0)

    # 6. Normalisation finale pour que la somme des 12 indices fasse 12
    somme_indices = float(indices.sum())
    if somme_indices > 0:
        indices = indices * 12.0 / somme_indices

    # 7. Volume moyen mensuel pour l'affichage
    ventes_mensuelles_moyennes = volumes.mean(axis=0)

    return pd.DataFrame(
        {
            "Mois": MOIS_NOMS,
            "Volume moyen": ventes_mensuelles_moyennes.to_numpy(),
            "Nombre de périodes": len(annees),
            "Indice saisonnier": indices.to_numpy(),
        }
    )


def calculer_matrice_indices_saisonnalite(
    donnees: pd.DataFrame,
    valeur: str,
    annees: list[int],
) -> pd.DataFrame:
    """Coefficients mensuels par année."""
    colonnes_requises = {"annee", "mois", "nature", valeur}
    manquantes = colonnes_requises.difference(donnees.columns)
    if manquantes:
        raise ValueError(
            "Colonnes manquantes pour calculer la saisonnalité : "
            + ", ".join(sorted(manquantes))
        )

    annees_ordonnees = sorted(set(annees))
    grille_mois = pd.Index(range(1, 13), name="mois")
    selection = donnees.loc[
        donnees["nature"].eq("Réalisé")
        & donnees["annee"].isin(annees_ordonnees)
        & donnees["mois"].between(1, 12)
    ]
    
    volumes = (
        selection.groupby(["annee", "mois"])[valeur]
        .sum()
        .unstack("mois")
        .reindex(index=annees_ordonnees, columns=range(1, 13))
        .fillna(0.0)
    )
    
    moyennes = volumes.sum(axis=1) / 12.0
    indices = volumes.div(moyennes.replace(0, np.nan), axis=0).fillna(0.0)
    
    indices.index = [str(annee) for annee in indices.index]
    indices.columns = [MOIS_NOMS[m - 1] for m in indices.columns]
    indices.index.name = "Année"
    
    return indices.T.reset_index().rename(columns={"index": "Mois"})

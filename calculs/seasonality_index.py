from __future__ import annotations

import pandas as pd

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
    """Années réalisées complètes (les 12 mois présents) entre annee_debut et annee_fin.

    Une année n'est retenue que si elle contient réellement les 12 mois
    en nature "Réalisé". L'année de clôture arrêtée avant décembre est exclue.
    """
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
    """Coefficients saisonniers mensuels, moyenne 1,00 sur les 12 mois.

    Coefficient du mois = volume moyen du mois / volume mensuel moyen global.
    Les années incomplètes (moins de 12 mois réalisés) sont exclues.
    La renormalisation finale garantit que sum(IS) = 12 et mean(IS) = 1.
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

    selection = donnees.loc[
        donnees["nature"].eq("Réalisé")
        & donnees["annee"].isin(annees)
        & donnees["mois"].between(1, 12)
    ]

    # Somme par (année, mois), années × mois en lignes
    volumes_mensuels = (
        selection.groupby(["annee", "mois"])[valeur]
        .sum()
        .reindex(
            pd.MultiIndex.from_product(
                [annees, grille_mois], names=["annee", "mois"]
            ),
            fill_value=0.0,
        )
        .rename("volume")
        .reset_index()
    )

    nombre_annees = len(annees)
    ventes_mensuelles_moyennes = (
        volumes_mensuels.groupby("mois")["volume"].sum().div(nombre_annees)
    ).reindex(grille_mois)

    moyenne_mensuelle_globale = volumes_mensuels["volume"].sum() / (
        nombre_annees * 12
    )

    if moyenne_mensuelle_globale <= 0:
        return pd.DataFrame(
            {
                "Mois": MOIS_NOMS,
                "Volume moyen": ventes_mensuelles_moyennes.to_numpy(),
                "Nombre de périodes": nombre_annees,
                "Indice saisonnier": float("nan"),
            }
        )

    indices = ventes_mensuelles_moyennes.div(moyenne_mensuelle_globale)

    # ✚ Renormalisation finale : moyenne des 12 IS = 1,00 exactement
    somme_indices = float(indices.sum())
    if somme_indices > 0:
        indices = indices * 12.0 / somme_indices

    return pd.DataFrame(
        {
            "Mois": MOIS_NOMS,
            "Volume moyen": ventes_mensuelles_moyennes.to_numpy(),
            "Nombre de périodes": nombre_annees,
            "Indice saisonnier": indices.to_numpy(),
        }
    )


def calculer_matrice_indices_saisonnalite(
    donnees: pd.DataFrame,
    valeur: str,
    annees: list[int],
) -> pd.DataFrame:
    """Coefficients mensuels par année (une colonne par année).

    Normalise chaque année indépendamment : moyenne = 1 par année.
    """
    colonnes_requises = {"annee", "mois", "nature", valeur}
    manquantes = colonnes_requises.difference(donnees.columns)
    if manquantes:
        raise ValueError(
            "Colonnes manquantes pour calculer la saisonnalité : "
            + ", ".join(sorted(manquantes))
        )

    annees_ordonnees = sorted(set(annees))
    grille_mois = pd.Index(range(1, 13), name="mois")
    grille = pd.MultiIndex.from_product(
        [annees_ordonnees, grille_mois],
        names=["annee", "mois"],
    )
    selection = donnees.loc[
        donnees["nature"].eq("Réalisé")
        & donnees["annee"].isin(annees_ordonnees)
        & donnees["mois"].between(1, 12)
    ]
    volumes_mensuels = (
        selection.groupby(["annee", "mois"])[valeur]
        .sum()
        .reindex(grille, fill_value=0.0)
        .unstack("annee")
        .reindex(columns=annees_ordonnees)
    )
    moyennes_annuelles = volumes_mensuels.sum(axis=0).div(12)
    indices = volumes_mensuels.div(
        moyennes_annuelles.where(moyennes_annuelles.gt(0)),
        axis="columns",
    )

    # ✚ Renormalisation par année : moyenne = 1,00 par colonne
    for annee in indices.columns:
        col = indices[annee]
        if col.notna().any() and float(col.sum()) > 0:
            indices[annee] = col * 12.0 / float(col.sum())

    indices.index = [MOIS_NOMS[mois - 1] for mois in indices.index]
    indices.index.name = "Mois"
    indices.columns = [str(annee) for annee in indices.columns]
    return indices.reset_index()

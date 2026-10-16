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
    """Années réalisées complètes (12 mois) comprises entre annee_debut et annee_fin.

    Une année n'est complète que si elle est entièrement réalisée : l'année de
    clôture arrêtée avant décembre (ex. janvier–septembre 2026) est exclue.
    Si annee_cloture / mois_cloture ne sont pas fournis, le dernier mois réalisé
    présent dans `donnees` sert de clôture.
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
    annees_presentes = sorted(
        int(a)
        for a in realise.loc[
            realise["annee"].between(annee_debut, annee_fin), "annee"
        ].unique()
    )
    return [
        a
        for a in annees_presentes
        if a < annee_cloture or (a == annee_cloture and mois_cloture >= 12)
    ]


def calculer_indices_saisonnalite(
    donnees: pd.DataFrame,
    valeur: str,
    annee_debut: int,
    annee_fin: int,
    annee_cloture: int | None = None,
    mois_cloture: int | None = None,
) -> pd.DataFrame:
    """Coefficients saisonniers mensuels autour de 1, sur les années COMPLÈTES.

    Coefficient du mois = volume moyen du mois / volume mensuel moyen (12 mois).
    1,00 = mois moyen ; 1,40 = mois 40 % au-dessus de la moyenne.

    Les années incomplètes (année de clôture arrêtée avant décembre) sont
    exclues : leurs mois manquants compteraient pour zéro et tireraient vers le
    bas les coefficients de ces mois (et vers le haut tous les autres).
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
    volumes_mensuels = (
        selection.groupby(["annee", "mois"])[valeur]
        .sum()
        .reindex(
            pd.MultiIndex.from_product([annees, grille_mois], names=["annee", "mois"]),
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
    indices = (
        ventes_mensuelles_moyennes.div(moyenne_mensuelle_globale)
        if moyenne_mensuelle_globale > 0
        else pd.Series(float("nan"), index=grille_mois)
    )
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
    """Return monthly seasonality coefficients with one column per year."""
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
    indices.index = [MOIS_NOMS[mois - 1] for mois in indices.index]
    indices.index.name = "Mois"
    indices.columns = [str(annee) for annee in indices.columns]
    return indices.reset_index()

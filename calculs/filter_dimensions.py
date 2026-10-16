"""Dimensions des filtres (positionnement, occasion, format, contenance, région).

Reconstitué à partir de l'usage dans app.py :
- assurer_dimensions_filtres(df, catalogue_par_article, types) complète les colonnes
  de filtre à partir du catalogue (Classeur2.xlsx, feuille « Ref actif »), clé = article.
- options_filtre_cascade(df, col, filtres, selections) renvoie les choix possibles d'un
  filtre compte tenu des sélections faites dans les AUTRES filtres.
"""
from __future__ import annotations

import pandas as pd

NON_RENSEIGNE = "Non renseigné"
VALEURS_VIDES = {"", "nan", "none", "nat", "<na>", NON_RENSEIGNE.lower()}

DIMENSIONS_TEXTE = ["positionnement", "occasion", "conditionnement", "region"]
# Triées avec key=float dans app.trier() : doivent rester numériques (NaN si inconnues).
DIMENSIONS_NUMERIQUES = ["contenance_ci", "contenance_hl"]

# Région de chaque agence. À COMPLÉTER si le filtre « Région » doit être utilisé :
# {"01-Tanjombato": "Analamanga", ...}. Vide = « Non renseigné ».
REGION_PAR_AGENCE: dict[str, str] = {}


def _est_vide(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.lower().isin(VALEURS_VIDES)


def assurer_dimensions_filtres(
    df: pd.DataFrame,
    catalogue_par_article: dict,
    types: dict | None = None,
) -> pd.DataFrame:
    """Garantit la présence des colonnes de filtre, complétées depuis le catalogue.

    - Les valeurs déjà renseignées dans df sont conservées (fonction idempotente).
    - Les valeurs manquantes sont prises dans le catalogue via l'article (minuscules, sans espaces).
    - Contenances numériques (NaN si inconnues) ; autres dimensions en texte,
      « Non renseigné » si inconnues.
    - Les codes d'occasion présents dans `types` (SS, CU, IC, FC) sont normalisés en majuscules.
    """
    resultat = df.copy()
    if "article" in resultat.columns:
        cles = resultat["article"].astype(str).str.strip().str.lower()
    else:
        cles = pd.Series("", index=resultat.index)

    for dim in DIMENSIONS_TEXTE:
        if dim in resultat.columns:
            courant = resultat[dim].astype(str).str.strip()
            vide = _est_vide(resultat[dim])
        else:
            courant = pd.Series(NON_RENSEIGNE, index=resultat.index)
            vide = pd.Series(True, index=resultat.index)

        if dim == "region":
            if "agence" in resultat.columns:
                depuis_ref = resultat["agence"].astype(str).map(REGION_PAR_AGENCE)
            else:
                depuis_ref = pd.Series(NON_RENSEIGNE, index=resultat.index)
        else:
            correspondances = {
                art: meta.get(dim) for art, meta in catalogue_par_article.items()
            }
            depuis_ref = cles.map(correspondances)
        depuis_ref = depuis_ref.where(
            depuis_ref.notna() & ~_est_vide(depuis_ref.fillna("")), NON_RENSEIGNE
        ).astype(str).str.strip()
        resultat[dim] = courant.mask(vide, depuis_ref)

    for dim in DIMENSIONS_NUMERIQUES:
        if dim in resultat.columns:
            courant = pd.to_numeric(resultat[dim], errors="coerce")
        else:
            courant = pd.Series(float("nan"), index=resultat.index)
        correspondances = {
            art: pd.to_numeric(meta.get(dim), errors="coerce")
            for art, meta in catalogue_par_article.items()
        }
        resultat[dim] = courant.fillna(cles.map(correspondances)).astype(float)

    if types:
        codes = {str(c).upper() for c in types}
        for col in ("occasion", "type_format"):
            if col in resultat.columns:
                majuscules = resultat[col].astype(str).str.strip().str.upper()
                resultat[col] = resultat[col].where(~majuscules.isin(codes), majuscules)

    return resultat


def options_filtre_cascade(
    df: pd.DataFrame,
    col: str,
    filtres: list[tuple[str, str]],
    selections: dict[str, list],
) -> list:
    """Valeurs possibles de `col`, restreintes par les sélections des autres filtres."""
    if col not in df.columns:
        return []
    masque = pd.Series(True, index=df.index)
    for autre_col, _ in filtres:
        if autre_col == col or autre_col not in df.columns:
            continue
        choix = selections.get(autre_col) or []
        if choix:
            masque &= df[autre_col].isin(choix)
    valeurs = df.loc[masque, col].dropna().unique().tolist()
    try:
        return sorted(valeurs)
    except TypeError:
        return sorted(valeurs, key=str)

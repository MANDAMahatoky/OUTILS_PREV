"""Lecture / import mensuel : mois, lignes brutes DATA_BRUT, remplacement de périodes.

Reconstitué à partir de l'usage dans app.py.
- normaliser_mois : noms de mois (fr/en, abrégés, accents) ou numéros -> numéro de mois.
  Les nombres sont renvoyés tels quels (app.nettoyer_annees_mois repère ensuite les
  colonnes annee/mois inversées, par ex. mois = 2026).
- normaliser_lignes_data_brut : feuille « Export » de DATA_BRUT.xlsx lue SANS en-tête ->
  tableau avec la bonne ligne d'en-tête, sans lignes vides ni lignes de total.
  ⚠ À valider avec le vrai DATA_BRUT.xlsx (mise en page non vue lors de l'écriture).
- remplacer_periodes_importees : un import remplace ses périodes (annee, mois) et conserve le reste.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

_MOIS = {
    "janvier": 1, "janv": 1, "jan": 1, "january": 1,
    "fevrier": 2, "fevr": 2, "fev": 2, "feb": 2, "february": 2,
    "mars": 3, "mar": 3, "march": 3,
    "avril": 4, "avr": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "june": 6,
    "juillet": 7, "juil": 7, "jul": 7, "july": 7,
    "aout": 8, "aug": 8, "august": 8,
    "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10,
    "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}


def _sans_accents(texte: str) -> str:
    return unicodedata.normalize("NFD", texte).encode("ascii", "ignore").decode("utf-8")


def _mois_valeur(valeur: object) -> float:
    if valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
        return np.nan
    if hasattr(valeur, "month") and not isinstance(valeur, (int, float, str)):
        return float(valeur.month)  # date / Timestamp
    if isinstance(valeur, (int, float, np.integer, np.floating)) and not isinstance(valeur, bool):
        return float(valeur)
    texte = str(valeur).strip()
    if not texte:
        return np.nan
    try:
        return float(texte.replace(",", "."))
    except ValueError:
        pass
    cle = re.sub(r"[^a-z]", "", _sans_accents(texte).lower())
    if not cle:
        return np.nan
    if cle in _MOIS:
        return float(_MOIS[cle])
    for debut in (cle[:4], cle[:3]):
        if debut in _MOIS:
            return float(_MOIS[debut])
    return np.nan


def normaliser_mois(serie: pd.Series) -> pd.Series:
    """Numéro de mois (float, NaN si illisible) pour chaque valeur de la série."""
    return pd.Series([_mois_valeur(v) for v in serie], index=serie.index, dtype=float)


_LIBELLES_ENTETE = {
    "agence", "agences", "segment", "segments", "marque", "marques",
    "produit", "produits", "article", "articles", "format", "parfum",
}


def _nom_simple(valeur: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _sans_accents(str(valeur).lower())).strip("_")


def _libelle_colonne(valeur: object, position: int) -> str:
    if valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
        return f"colonne_{position}"
    if isinstance(valeur, pd.Timestamp):
        return valeur.strftime("%Y-%m")
    texte = str(valeur).strip()
    return texte if texte else f"colonne_{position}"


def normaliser_lignes_data_brut(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Repère la ligne d'en-tête, la promeut, retire lignes vides et lignes de total."""
    brut = df_raw.reset_index(drop=True)
    meilleur_idx, meilleur_score = 0, 0
    for i in range(min(len(brut), 25)):
        score = sum(_nom_simple(c) in _LIBELLES_ENTETE for c in brut.iloc[i].tolist())
        if score > meilleur_score:
            meilleur_idx, meilleur_score = i, score

    libelles: list[str] = []
    for position, valeur in enumerate(brut.iloc[meilleur_idx].tolist()):
        libelle = _libelle_colonne(valeur, position)
        if libelle in libelles:  # doublons : garder les deux, suffixer le second
            libelle = f"{libelle}.{position}"
        libelles.append(libelle)

    donnees = brut.iloc[meilleur_idx + 1:].copy()
    donnees.columns = libelles
    donnees = donnees.dropna(how="all")

    colonnes_texte = [c for c in donnees.columns if _nom_simple(c) in _LIBELLES_ENTETE]
    if colonnes_texte:
        est_total = pd.Series(False, index=donnees.index)
        for col in colonnes_texte:
            est_total |= donnees[col].astype(str).str.contains(
                r"\btotal\b", case=False, regex=True, na=False
            )
        donnees = donnees.loc[~est_total]
    return donnees.reset_index(drop=True)


def remplacer_periodes_importees(
    historique: pd.DataFrame, nouvel_import: pd.DataFrame
) -> tuple[pd.DataFrame, int]:
    """Remplace dans l'historique les périodes (annee, mois) présentes dans l'import.

    Retourne (historique mis à jour, nombre de périodes remplacées ou ajoutées).
    """
    periodes_import = {
        (int(a), int(m))
        for a, m in nouvel_import[["annee", "mois"]].drop_duplicates().itertuples(index=False, name=None)
    }
    cles_historique = pd.Series(
        list(zip(historique["annee"].astype(int), historique["mois"].astype(int))),
        index=historique.index,
    )
    conserve = historique.loc[~cles_historique.isin(periodes_import)]
    resultat = pd.concat([conserve, nouvel_import], ignore_index=True, sort=False)
    resultat = resultat.sort_values(["annee", "mois"], kind="stable").reset_index(drop=True)
    return resultat, len(periodes_import)

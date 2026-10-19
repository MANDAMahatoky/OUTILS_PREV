"""Lecture / import mensuel : mois, lignes brutes DATA_BRUT, remplacement de périodes.

Deux formats de fichier sont acceptés :

A) Format "long" classique
   Une ligne d'en-tête nommée (Article, Agence, Segment, Mois, Année, HL, ...)
   est repérée dans les 25 premières lignes puis promue en en-tête de colonnes.
   Comportement d'origine, conservé à l'identique.

B) Format "pivoté sans en-tête" (cas de DATA_BRUT.xlsx, feuille « Export »)
   7 colonnes positionnelles sans ligne d'en-tête :
       [annee, mois, segment, produit, agence, nature, hl]
   Converti en format long, avec ajout des colonnes attendues en aval
   (periode, colis, article, origine).

- normaliser_mois : noms de mois (fr/en, abrégés, accents) ou numéros -> numéro de mois.
  Les nombres sont renvoyés tels quels (app.nettoyer_annees_mois repère ensuite les
  colonnes annee/mois inversées, par ex. mois = 2026).
- normaliser_lignes_data_brut : point d'entrée unique. Détecte le format puis
  délègue à la branche A ou B.
- remplacer_periodes_importees : un import remplace ses périodes (annee, mois)
  et conserve le reste.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Normalisation des mois
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Format A : en-tête nommé (comportement d'origine)
# ---------------------------------------------------------------------------

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


def _normaliser_format_entete(df_raw: pd.DataFrame) -> pd.DataFrame:
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


# ---------------------------------------------------------------------------
# Format B : pivoté sans en-tête (DATA_BRUT.xlsx, feuille « Export »)
# ---------------------------------------------------------------------------

# Ordre positionnel attendu des colonnes (0..6)
_COLONNES_PIVOT = ["annee", "mois", "segment", "produit", "agence", "nature", "hl"]

# Alias de "nature" -> valeurs canoniques de l'app
_NATURE_MAP = {
    "total": "Réalisé",
    "realise": "Réalisé", "reel": "Réalisé", "actual": "Réalisé",
    "prevision": "Prévision", "prev": "Prévision", "forecast": "Prévision",
    "budget": "Prévision", "objectif": "Prévision",
}


def _cle_nature(valeur: object) -> str:
    """Clé normalisée de 'nature' : minuscule, sans accents, sans séparateurs."""
    s = _sans_accents(str(valeur).strip().lower())
    return re.sub(r"[^a-z]", "", s)


def _detecter_format_pivote(brut: pd.DataFrame) -> bool:
    """Heuristique : pas d'en-tête nommé + colonnes 0/1/6 typiques du pivot."""
    if brut.empty or brut.shape[1] < 7:
        return False

    # La première ligne ne doit pas contenir de libellé d'en-tête connu
    premiere = {_nom_simple(c) for c in brut.iloc[0].tolist()}
    if premiere & _LIBELLES_ENTETE:
        return False

    # Colonne 0 : années plausibles
    annee0 = pd.to_numeric(brut.iloc[:, 0], errors="coerce")
    if annee0.between(1990, 2100).sum() < max(1, int(len(brut) * 0.3)):
        return False

    # Colonne 1 : mois lisibles
    mois1 = normaliser_mois(brut.iloc[:, 1])
    if mois1.notna().sum() < max(1, int(len(brut) * 0.3)):
        return False

    # Colonne 6 : numérique
    hl6 = pd.to_numeric(brut.iloc[:, 6], errors="coerce")
    if hl6.notna().sum() < max(1, int(len(brut) * 0.3)):
        return False

    return True


def _normaliser_format_pivote(brut: pd.DataFrame) -> pd.DataFrame:
    """[annee, mois, segment, produit, agence, nature, hl] -> format long."""
    # Renommage positionnel
    rename = {
        brut.columns[i]: col
        for i, col in enumerate(_COLONNES_PIVOT[: brut.shape[1]])
    }
    df = brut.rename(columns=rename).copy()

    # Si `hl` n'est pas numérique, on tente de repérer la bonne colonne
    if "hl" not in df.columns or pd.to_numeric(df.get("hl"), errors="coerce").notna().sum() == 0:
        candidates = [
            c for c in df.columns
            if c not in {"annee", "mois", "segment", "produit", "agence", "nature"}
            and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.8
        ]
        if not candidates:
            raise ValueError(
                "Format pivoté : aucune colonne numérique exploitable pour 'hl'. "
                f"Colonnes vues : {list(df.columns)}."
            )
        df["hl"] = df[candidates[-1]]

    # Filtrage des lignes non exploitables
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
    df["mois"] = normaliser_mois(df["mois"])
    df = df[df["annee"].notna() & df["mois"].notna()].copy()
    df["annee"] = df["annee"].astype(int)
    df["mois"] = df["mois"].astype(int)

    df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)

    # Colonnes texte
    for c in ("segment", "produit", "agence", "nature"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
        else:
            df[c] = "Non renseigné"

    # Retire les lignes de total
    masque_total = (
        df["segment"].str.contains(r"\btotal\b", case=False, regex=True, na=False)
        | df["produit"].str.contains(r"\btotal\b", case=False, regex=True, na=False)
        | df["agence"].str.contains(r"\btotal\b", case=False, regex=True, na=False)
    )
    df = df[~masque_total].copy()

    # Normalisation de `nature` vers Réalisé / Prévision
    if "nature" in df.columns:
        cles = df["nature"].map(_cle_nature)
        df["nature"] = cles.map(_NATURE_MAP).fillna(df["nature"])
        # Si la valeur reste inconnue, on la laisse telle quelle (pas d'invention)
        df.loc[df["nature"].astype(str).str.strip().eq(""), "nature"] = "Réalisé"

    # Période
    df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)

    # Colonnes attendues en aval
    if "colis" not in df.columns:
        df["colis"] = 0.0
    if "origine" not in df.columns:
        df["origine"] = "Donnée source"
    if "article" not in df.columns:
        # Fallback synthétique : produit - segment
        df["article"] = (
            df["produit"].astype(str).str.strip()
            + " - "
            + df["segment"].astype(str).str.strip()
        )

    keep = [
        "annee", "mois", "periode", "segment", "produit", "agence",
        "nature", "hl", "colis", "article", "origine",
    ]
    df = df[[c for c in keep if c in df.columns]]

    # Diagnostic récupérable via df.attrs
    df.attrs["format_detecte"] = "pivot_sans_entete"
    df.attrs["colonnes_positionnelles"] = dict(enumerate(_COLONNES_PIVOT))

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def normaliser_lignes_data_brut(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Détecte le format et applique la normalisation adaptée.

    - Format B (pivoté sans en-tête) : détecté en priorité, converti en long.
    - Format A (en-tête nommé)        : promotion de la meilleure ligne d'en-tête.
    """
    if df_raw is None or df_raw.empty:
        return df_raw

    brut = df_raw.reset_index(drop=True)

    if _detecter_format_pivote(brut):
        return _normaliser_format_pivote(brut)

    return _normaliser_format_entete(brut)


# ---------------------------------------------------------------------------
# Remplacement de périodes dans l'historique
# ---------------------------------------------------------------------------

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

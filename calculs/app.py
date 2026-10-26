from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CONFIGURATION & CONSTANTES
# ==============================================================================

st.set_page_config(
    page_title="Suivi & Prévision SARR (S&OP)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

RACINE = Path(__file__).resolve().parent
DOSSIERS = [RACINE, RACINE.parent, Path.cwd()]
FICHIERS_CANDIDATS = ["DATA_BRUT.xlsx"]

COLONNES = [
    "annee", "mois", "periode", "agence", "region", "segment", "produit", "parfum", "format",
    "type_format", "article", "nature", "origine", "colis", "hl", "positionnement", "occasion",
    "conditionnement", "contenance_ci", "contenance_hl",
]

MOIS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]
MOIS_COMPLETS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_NOMS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

COULEUR_REALISE = "#9E6315EF"
COULEUR_PREVISION = "#9BD69E"

FILTRES = [
    ("article", "🛒 Article"),
    ("positionnement", "📍 Positionnement"),
    ("occasion", "🎯 Occasion"),
    ("conditionnement", "📦 Format"),
    ("contenance_ci", "📏 Contenance (CI)"),
    ("contenance_hl", "🧪 Contenance (hl)"),
    ("agence", "🏢 Agence"),
    ("region", "🗺️ Région"),
]

AGENCES_REFERENCE = [
    "01-Tanjombato", "03-Usine-Diego", "04-Tulear", "05-Fianarantsoa", "06-Ihosy",
    "07-Majunga", "08-Manakara", "09-Tamatave", "11-Andranomahery", "12-Antsirabe",
    "18-Ambanja", "19-Sambava", "21-Nosy-be", "23-Morondova", "24-Fort-Dauphin",
]

REGION_PAR_AGENCE = {
    "01-Tanjombato": "Centre", "03-Usine-Diego": "Nord", "04-Tulear": "Sud",
    "05-Fianarantsoa": "Sud", "06-Ihosy": "Sud", "07-Majunga": "Nord",
    "08-Manakara": "Sud", "09-Tamatave": "Est", "11-Andranomahery": "Centre",
    "12-Antsirabe": "Centre", "18-Ambanja": "Nord", "19-Sambava": "Nord",
    "21-Nosy-be": "Nord", "23-Morondova": "Nord", "24-Fort-Dauphin": "Sud",
}

TYPES = {
    "SS": "SS (Single serve)", "CU": "CU (Convivial Units)",
    "IC": "IC (Individual/Immediat Consumption)", "FC": "FC (Family/Future Consumption)",
}

# ==============================================================================
# 2. RÉFÉRENTIEL EXACT
# ==============================================================================

def _generer_catalogue_exact():
    data_raw = [
        ("Booster Appel-Mix 50CL VER", "PREMIUM", "CU (Convivial Units)"),
        ("Booster Tornado 50CL VER VER", "PREMIUM", "CU (Convivial Units)"),
        ("Caprice Ananas 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("Caprice Ananas 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Caprice Ananas 30 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Bonbon Anglais 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("Caprice Bonbon Anglais 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Caprice Bonbon Anglais 30 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Bonbon Anglais 33 cl CAN", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Bonbon Anglais 35 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Bonbon Anglais 50 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Grenadine 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("Caprice Grenadine 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Caprice Grenadine 30 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Grenadine 33 cl CAN", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Grenadine 35 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Grenadine 50 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Orange 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("Caprice Orange 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Caprice Orange 30 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Orange 33 cl CAN", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Orange 35 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Orange 50 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Citron 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("Caprice Citron 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Caprice Citron 30 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Caprice Citron 50 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Tonic 100 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Tonic 30 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("World Cola 100cl VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("World Cola 100cl WOCO VER", "MILIEU", "FC (Family/Future Consumption)"),
        ("World Cola 150cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("World Cola 30cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("World Cola 30cl WOCO VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("World Cola 33 cl CAN", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("World Cola 35cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("World Cola 50cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Beaufort 33 CL CAN", "MILIEU", "SS (Single serve)"),
        ("Beaufort 33CL VER", "PREMIUM", "SS (Single serve)"),
        ("FRESH 33 cl CAN", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("THB Fresh 33 cl VER", "ENTREE", "SS (Single serve)"),
        ("THB Fresh 65 cl VER", "ENTREE", "CU (Convivial Units)"),
        ("Gold 8 50 cl CAN", "PREMIUM", "SS (Single serve)"),
        ("Gold 8 50 cl VER", "PREMIUM", "SS (Single serve)"),
        ("Gold Blanche 33cl VER", "PREMIUM", "SS (Single serve)"),
        ("Gold Blanche 50 cl CAN", "PREMIUM", "SS (Single serve)"),
        ("Gold Blanche 50 cl VER", "PREMIUM", "SS (Single serve)"),
        ("Gold Blonde 33 cl VER", "PREMIUM", "SS (Single serve)"),
        ("Gold Blonde 50 cl CAN", "PREMIUM", "SS (Single serve)"),
        ("Gold Blonde 50 cl VER", "PREMIUM", "SS (Single serve)"),
        ("Gold Blonde 65 cl VER", "PREMIUM", "CU (Convivial Units)"),
        ("Queen s 65 cl VER", "PREMIUM", "CU (Convivial Units)"),
        ("THB Pilsener 33 cl VER", "MILIEU", "SS (Single serve)"),
        ("THB Pilsener 50 cl CAN", "MILIEU", "CU (Convivial Units)"),
        ("THB Pilsener 65 cl VER", "MILIEU", "CU (Convivial Units)"),
        ("Cristal 100 cl VER", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("Cristal 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Cristal 30 cl VER", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("Cristal 50 cl VER", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("Cristalline 100 cl PET", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("Cristalline 200 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
        ("Eau vive 150 cl PET", "MILIEU", "FC (Family/Future Consumption)"),
        ("Eau vive 50 cl PET", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("Eau vive 50 cl VER", "MILIEU", "IC (Individual/Immediat Consumption)"),
        ("FOSA 50 cl CAN", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("XXL 30cl BOB VER", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("XXL 30cl VER", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("XXL 33 cl CAN", "PREMIUM", "IC (Individual/Immediat Consumption)"),
        ("XXL 35cl PET", "PREMIUM", "IC (Individual/Immediat Consumption)"),
    ]

    data = []
    for art, pos, occ in data_raw:
        art_lower = art.lower()
        if "cristal" in art_lower or "eau" in art_lower: segment = "EAUX"
        elif any(x in art_lower for x in ["gold", "thb", "beaufort", "queen", "booster"]): segment = "BIERES"
        else: segment = "BOISSONS"

        fmt = art.split()[-1].upper() if art.split()[-1].upper() in ["VER", "PET", "CAN"] else "VER"
        if "WOCO" in art_lower: fmt = "VER"
        if "BOB" in art_lower: fmt = "VER"

        match = re.search(r"(\d+)\s*cl", art_lower)
        c_cl = int(match.group(1)) if match else 50
        c_hl = c_cl * 0.0001

        data.append({
            "article": art, "segment": segment, "produit": art.split()[0], "parfum": art,
            "positionnement": pos, "occasion": occ, "conditionnement": fmt,
            "format": f"{c_cl} cl {fmt}", "contenance_ci": c_cl, "contenance_hl": c_hl,
            "type_format": occ, "type_format_lib": occ,
        })
    return pd.DataFrame(data)

CATALOGUE = _generer_catalogue_exact()
CATALOGUE_PAR_ARTICLE = {meta["article"].lower().strip(): meta for meta in CATALOGUE.to_dict(orient="records")}
ARTICLES_REFERENTIEL = CATALOGUE["article"].tolist()

# ==============================================================================
# 3. UTILITAIRES
# ==============================================================================

def _sans_accents(texte: str) -> str:
    return unicodedata.normalize("NFD", texte).encode("ascii", "ignore").decode("utf-8")

def normaliser_nom(nom: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", _sans_accents(str(nom).strip().lower())).strip("_")

def normaliser_agence(valeur: object) -> str:
    nom = str(valeur).strip()
    cle = normaliser_nom(nom)
    for a in AGENCES_REFERENCE:
        if normaliser_nom(a) == cle or normaliser_nom(a.split("-", 1)[1]) == cle:
            return a
    if re.fullmatch(r"\d+(_0)?", cle):
        return next((a for a in AGENCES_REFERENCE if a.startswith(f"{int(cle.split('_', 1)[0]):02d}-")), nom)
    return nom

def region_depuis_agence(valeur: object) -> str:
    return REGION_PAR_AGENCE.get(normaliser_agence(valeur), "Non renseigné")

def assurer_dimensions_filtres(df: pd.DataFrame, catalogue: dict, types: dict) -> pd.DataFrame:
    for col in ["positionnement", "occasion", "conditionnement", "contenance_ci", "contenance_hl", "region", "type_format"]:
        if col not in df.columns: df[col] = "Non renseigné"
        if df[col].dtype != object: df[col] = df[col].astype(object)
        if catalogue:
            champ = "type_format_lib" if col == "type_format" else col
            articles = df["article"].astype(str).str.lower().str.strip()
            correspondances = {a: m.get(champ, "Non renseigné") for a, m in catalogue.items()}
            masque_vide = df[col].astype(str).str.strip().isin(["", "Non renseigné", "nan", "None", "0.0", "0"])
            df.loc[masque_vide, col] = articles[masque_vide].map(correspondances).fillna("Non renseigné")
        df[col] = df[col].astype(str).str.strip()
    return df

def options_filtre_cascade(df: pd.DataFrame, col: str, filtres: list, selections: dict) -> list:
    if col not in df.columns: return []
    df_filtre = df.copy()
    for c, _ in filtres:
        if c != col and selections.get(c) and c in df_filtre.columns:
            df_filtre = df_filtre[df_filtre[c].isin(selections[c])]
    options = df_filtre[col].dropna().unique().tolist()
    if col in ["article", "positionnement", "occasion", "conditionnement", "contenance_ci", "contenance_hl"]:
        options = list(set(options) | set(CATALOGUE[col].dropna().unique().tolist()))
    return options

# ==============================================================================
# 4. LECTURE DES DONNÉES (Étape 1)
# ==============================================================================

_MOIS_MAP = {
    "janvier": 1, "janv": 1, "jan": 1, "january": 1, "fevrier": 2, "fevr": 2, "fev": 2, "feb": 2,
    "february": 2, "mars": 3, "mar": 3, "march": 3, "avril": 4, "avr": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5, "juin": 6, "jun": 6, "june": 6, "juillet": 7, "juil": 7, "jul": 7, "july": 7,
    "aout": 8, "aug": 8, "august": 8, "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10, "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}

def normaliser_mois(valeur) -> float:
    if pd.isna(valeur): return np.nan
    if isinstance(valeur, (int, float)): return float(valeur)
    texte = str(valeur).strip().lower()
    try: return float(texte.replace(",", "."))
    except ValueError: pass
    cle = re.sub(r"[^a-z]", "", _sans_accents(texte))
    return float(_MOIS_MAP.get(cle, np.nan))

def _detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    mois1 = df.iloc[:, 1].map(normaliser_mois)
    return annee0.between(1990, 2100).sum() > len(df) * 0.3 and mois1.notna().sum() > len(df) * 0.3

def _extraire_article(nature_str: str) -> str:
    match = re.match(r"^\d+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def _resoudre_article(produit: str, segment: str) -> str:
    produit_clean = str(produit).strip()
    if not produit_clean: return produit_clean
    candidats = [produit_clean.lower()]
    seg = str(segment).strip() if segment else ""
    if seg:
        candidats.append(f"{produit_clean} {seg}".lower())
        suffixe = f" {seg.lower()}"
        if candidats[0].endswith(suffixe): candidats.append(candidats[0][: -len(suffixe)].strip())
    for cle in candidats:
        if cle in CATALOGUE_PAR_ARTICLE: return CATALOGUE_PAR_ARTICLE[cle]["article"]
    return produit_clean

def normaliser_lignes_data_brut(df_raw: pd.DataFrame, articles_referentiel: list[str]) -> pd.DataFrame:
    if _detecter_format_pivote(df_raw):
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "hl"])}
        df = df_raw.rename(columns=rename).copy()
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
        df["mois"] = df["mois"].map(normaliser_mois)
        df = df.dropna(subset=["annee", "mois"]).copy()
        df["mois"] = df["mois"].astype(int)
        df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)
        for c in ("segment", "produit", "agence", "nature"):
            df[c] = df[c].astype(str).str.strip()
        masque_total = (
            df["segment"].str.contains("total", case=False, na=False)
            | df["produit"].str.contains("total", case=False, na=False)
            | df["agence"].str.contains("total", case=False, na=False)
            | df["nature"].str.contains("total", case=False, na=False)
        )
        df = df[~masque_total].copy()
        df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
        df["colis"] = 0.0
        df["origine"] = "Donnée source"
        df["article"] = df["nature"].apply(_extraire_article)
        df["article"] = df["article"].apply(lambda a: _resoudre_article(a, ""))
        return df.reset_index(drop=True)
    return df_raw

def lire_et_normaliser(contenu: bytes | None, nom: str, chemin: str | None, annee_cloture: int, mois_cloture: int) -> pd.DataFrame:
    if contenu is None and chemin is None: raise ValueError("Aucun contenu fourni.")
    nom_fichier = Path(nom if contenu is not None else chemin or "").name.lower()
    est_data_brut = nom_fichier == "data_brut.xlsx"

    if contenu is not None:
        flux = io.BytesIO(contenu)
        if nom.lower().endswith(".csv"):
            df_raw = pd.read_csv(flux, sep=None, encoding="utf-8-sig", engine="python")
        else:
            feuilles = pd.ExcelFile(flux).sheet_names
            feuille = next((f for f in feuilles if normaliser_nom(f) == "export"), feuilles[0]) if est_data_brut else 0
            df_raw = pd.read_excel(flux, sheet_name=feuille, header=None) if est_data_brut else pd.read_excel(flux, sheet_name=feuille)
    else:
        chemin_str = str(chemin)
        if chemin_str.lower().endswith(".csv"):
            df_raw = pd.read_csv(chemin_str, sep=None, encoding="utf-8-sig", engine="python")
        else:
            feuilles = pd.ExcelFile(chemin_str).sheet_names
            feuille = next((f for f in feuilles if normaliser_nom(f) == "export"), feuilles[0]) if est_data_brut else 0
            df_raw = pd.read_excel(chemin_str, sheet_name=feuille, header=None) if est_data_brut else pd.read_excel(chemin_str, sheet_name=feuille)

    df = normaliser_lignes_data_brut(df_raw, ARTICLES_REFERENTIEL) if est_data_brut else df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_map = {"annee": "annee", "mois": "mois", "agence": "agence", "agences": "agence", "segment": "segment", "produit": "produit", "marque": "produit", "article": "article", "articles": "article", "nature": "nature", "hl": "hl", "volume": "hl", "colis": "colis"}
    df = df.rename(columns={c: col_map[normaliser_nom(c)] for c in df.columns if normaliser_nom(c) in col_map})
    df = df.loc[:, ~df.columns.duplicated()].copy()

    defaut = {"annee": 2026, "mois": 1, "periode": "2026-01", "agence": "Non renseigné", "region": "Non renseigné", "segment": "Non renseigné", "produit": "Non renseigné", "parfum": "Non renseigné", "format": "Non renseigné", "type_format": "Non renseigné", "article": "Non renseigné", "nature": "Prévision", "colis": 0.0, "hl": 0.0, "origine": "Donnée source", "positionnement": "Non renseigné", "occasion": "Non renseigné", "conditionnement": "Non renseigné", "contenance_ci": 0.0, "contenance_hl": 0.0}
    for k, v in defaut.items():
        if k not in df.columns: df[k] = v

    df = df[COLONNES].copy()
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").fillna(2026).astype(int)
    df["mois"] = df["mois"].map(normaliser_mois).fillna(1).astype(int)
    df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
    df["agence"] = df["agence"].map(normaliser_agence)
    df["region"] = df["agence"].map(region_depuis_agence)
    for c in ["colis", "hl"]: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    df = assurer_dimensions_filtres(df, CATALOGUE_PAR_ARTICLE, TYPES)
    df = df[~df["article"].str.lower().isin(["", "non renseigné", "total", "nan"])].copy()
    
    # Étape 3 : Séparation Réalisé vs Prévision en fonction du cutoff
    cond_realise = (df["annee"] < annee_cloture) | ((df["annee"] == annee_cloture) & (df["mois"] <= mois_cloture))
    df["nature"] = np.where(cond_realise, "Réalisé", "Prévision")
    return df

# ==============================================================================
# 5. MOTEUR DE CALCUL (SARR, INDICES, MOMENTUM, PREVISION) - Étapes 3, 4 & 5
# ==============================================================================

def moteur_saar_complet(df_brut: pd.DataFrame, annee_cutoff: int, mois_cutoff: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applique le calcul SARR, Indices, Momentum et Prévisions selon le diagramme."""
    
    # 1. Isoler le réalisé pour construire l'historique
    df_hist = df_brut[df_brut["nature"] == "Réalisé"].copy()
    
    # 2. Calcul des Indices (Moy_Mois / Moy_Ann)
    # Pivot : index=(agence, article, mois), columns=annee, values=hl
    pivot = df_hist.pivot_table(
        index=["agence", "article", "mois"], 
        columns="annee", 
        values="hl", 
        aggfunc="sum"
    ).fillna(0.0)
    
    # Moyenne par mois (sur les années dispo) -> Moy_Mois
    pivot["Moy_Mois"] = pivot.mean(axis=1)
    
    # Moyenne annuelle par (agence, article) -> Moy_Ann
    moy_ann = df_hist.groupby(["agence", "article", "annee"])["hl"].sum().groupby(["agence", "article"]).mean() / 12.0
    
    # Fusion et calcul de l'indice
    pivot = pivot.reset_index()
    pivot = pivot.merge(moy_ann.rename("Moy_Ann"), on=["agence", "article"], how="left")
    pivot["Indice"] = np.where(pivot["Moy_Ann"] > 0, pivot["Moy_Mois"] / pivot["Moy_Ann"], 1.0)
    
    # Normalisation de l'indice pour que la somme des 12 mois = 12.0
    pivot["Sum_Indice"] = pivot.groupby(["agence", "article"])["Indice"].transform("sum")
    pivot["Indice"] = np.where(pivot["Sum_Indice"] > 0, pivot["Indice"] / pivot["Sum_Indice"] * 12.0, 1.0)
    
    # Sauvegarde des indices sous forme de dict pour lookup rapide
    dict_indices = pivot.set_index(["agence", "article", "mois"])["Indice"].to_dict()
    
    # 3. Calcul du SARR sur l'historique
    # SARR = Volume / Indice
    df_hist["Indice"] = df_hist.apply(lambda r: dict_indices.get((r["agence"], r["article"], r["mois"]), 1.0), axis=1)
    df_hist["SARR"] = df_hist["hl"] / df_hist["Indice"]
    
    # 4. Calcul Momentum et Base (nécessite un tri chronologique)
    df_hist = df_hist.sort_values(["agence", "article", "annee", "mois"])
    
    # Momentum : AVERAGE(SARR_M - SARR_M-1, ...) sur les 3 derniers mois
    df_hist["SARR_prev1"] = df_hist.groupby(["agence", "article"])["SARR"].shift(1)
    df_hist["SARR_prev2"] = df_hist.groupby(["agence", "article"])["SARR"].shift(2)
    df_hist["SARR_prev3"] = df_hist.groupby(["agence", "article"])["SARR"].shift(3)
    
    df_hist["Delta1"] = df_hist["SARR"] - df_hist["SARR_prev1"]
    df_hist["Delta2"] = df_hist["SARR_prev1"] - df_hist["SARR_prev2"]
    df_hist["Delta3"] = df_hist["SARR_prev2"] - df_hist["SARR_prev3"]
    
    df_hist["Momentum"] = df_hist[["Delta1", "Delta2", "Delta3"]].mean(axis=1).fillna(0.0)
    
    # Base : MAX(SARR_M, AVERAGE(SARR_M-1, M-2, M-3))
    df_hist["Moy_3_derniers"] = df_hist[["SARR_prev1", "SARR_prev2", "SARR_prev3"]].mean(axis=1)
    df_hist["Base"] = np.maximum(df_hist["SARR"], df_hist["Moy_3_derniers"].fillna(0.0))
    
    # 5. Génération des Prévisions
    # On extrait les dernières infos connues (dernier mois réalisé) par (agence, article)
    dernier_etat = df_hist.sort_values(["annee", "mois"]).groupby(["agence", "article"]).last().reset_index()
    
    projections = []
    annees_a_projeter = range(annee_cutoff, annee_cutoff + 3) # On projette sur 2-3 ans max pour le rolling
    
    for _, row in dernier_etat.iterrows():
        ag, art = row["agence"], row["article"]
        base = row["Base"]
        momentum = row["Momentum"]
        
        # FIX : Le momentum est un écart de rythme mensuel. 
        # On le divise par 12 pour le lisser sur l'année et éviter les pics aberrants.
        momentum_lisse = momentum / 12.0
        
        for an in annees_a_projeter:
            for mo in range(1, 13):
                if an == annee_cutoff and mo <= mois_cutoff:
                    continue # Déjà dans le réalisé
                
                indice_mois = dict_indices.get((ag, art, mo), 1.0)
                
                # Formule du diagramme : Prévision = (Indice * Base) + Momentum
                prev_hl = (indice_mois * base) + momentum_lisse
                prev_hl = max(0.0, prev_hl) # Pas de volumes négatifs
                
                projections.append({
                    "annee": an,
                    "mois": mo,
                    "periode": f"{an}-{mo:02d}",
                    "agence": ag,
                    "article": art,
                    "region": row["region"],
                    "segment": row["segment"],
                    "produit": row["produit"],
                    "parfum": row["parfum"],
                    "format": row["format"],
                    "type_format": row["type_format"],
                    "nature": "Prévision",
                    "origine": "Moteur SARR",
                    "colis": 0.0,
                    "hl": prev_hl,
                    "positionnement": row["positionnement"],
                    "occasion": row["occasion"],
                    "conditionnement": row["conditionnement"],
                    "contenance_ci": row["contenance_ci"],
                    "contenance_hl": row["contenance_hl"]
                })
                
    df_prev = pd.DataFrame(projections)
    
    if not df_prev.empty:
        df_prev = df_prev.reindex(columns=df_brut.columns)
    
    # On renvoie le dataframe complet (réalisé + prévisions) et le dataframe des indices
    df_final = pd.concat([df_hist[df_brut.columns], df_prev], ignore_index=True)
    return df_final, pivot[["agence", "article", "mois", "Indice"]]

# ==============================================================================
# 6. AFFICHAGE & UI
# ==============================================================================

st.markdown("""
<style>
:root { --red: #d7193f; --green: #0e8a4a; }
.stApp { background: radial-gradient(1000px 400px at 100% -10%, #fff1f4, transparent), radial-gradient(1000px 400px at 0% 110%, #eaf7f0, transparent), #fff; }
.block-container { max-width: 1440px; padding: 2rem 4vw; }
.titre { font-size: 2.5rem; font-weight: 800; color: #121017; }
.titre::after { content: ""; display: block; width: 72px; height: 4px; margin-top: .8rem; background: linear-gradient(90deg, var(--red) 50%, var(--green) 50%); border-radius: 99px; }
div[data-testid="stMetric"] { background: #fff; border: 1px solid #e2e0e6; border-radius: 16px; padding: 1.25rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,.03); border-top: 4px solid var(--red); }
div[data-testid="stColumn"]:nth-child(even) div[data-testid="stMetric"] { border-top-color: var(--green); }
div[data-testid="stMetric"] label { font-weight: 700; color: #5c5665; text-transform: uppercase; font-size: 0.78rem; }
div[data-testid="stMetricValue"] { font-weight: 800; color: #121017; }
</style>
""", unsafe_allow_html=True)

def nombre(x: float, dec: int) -> str: return f"{x:,.{dec}f}".replace(",", " ")

def afficher_vue(df: pd.DataFrame, mode: str, dec: int = 0, hauteur=350):
    if mode == "Tableau":
        st.dataframe(df.round(dec), width="stretch")
        return
    df_graphique = df.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df_graphique.empty: return st.info("Aucune valeur numérique.")
    
    nom_axe = df_graphique.index.name or "Période"
    df_melt = df_graphique.reset_index().melt(id_vars=nom_axe, var_name="Série", value_name="Valeur")
    df_melt[nom_axe] = df_melt[nom_axe].astype(str)
    ordre_index = df_graphique.index.astype(str).tolist()
    
    if mode == "Courbes":
        chart = alt.Chart(df_melt).mark_line(interpolate="monotone", point=alt.OverlayMarkDef(filled=True, size=35)).encode(
            x=alt.X(f"{nom_axe}:N", sort=ordre_index, title=nom_axe),
            y=alt.Y("Valeur:Q", title="Volume"),
            color=alt.Color("Série:N", scale=alt.Scale(scheme="tableau10"), legend=alt.Legend(title=None)),
            tooltip=[nom_axe, "Série", alt.Tooltip("Valeur:Q", format=",.2f")]
        )
        st.altair_chart(chart.properties(height=hauteur), use_container_width=True)
    elif mode == "Histogramme":
        chart = alt.Chart(df_melt).mark_bar().encode(
            x=alt.X(f"{nom_axe}:N", sort=ordre_index, title=nom_axe),
            y=alt.Y("Valeur:Q", title="Volume"),
            color=alt.Color("Série:N", scale=alt.Scale(scheme="tableau10"), legend=alt.Legend(title=None)),
            tooltip=[nom_axe, "Série", alt.Tooltip("Valeur:Q", format=",.2f")]
        )
        st.altair_chart(chart.properties(height=hauteur), use_container_width=True)

def trier(valeurs, col):
    v = [x for x in valeurs if pd.notna(x)]
    if col in {"contenance_ci", "contenance_hl"}: return sorted(v, key=lambda x: float(x) if str(x).replace('.','',1).isdigit() else 999)
    if col == "conditionnement": return sorted(v, key=lambda x: ({"CAN": 0, "PET": 1, "VER": 2}.get(str(x), 99), str(x)))
    return sorted(v)

# ==============================================================================
# 7. INITIALISATION & UI PRINCIPALE
# ==============================================================================

FICHIERS_EXISTANTS = [d / f for d in DOSSIERS for f in FICHIERS_CANDIDATS if (d / f).exists()]

st.markdown('<div class="titre">Moteur S&OP : Prévision SARR & Rolling Forecast</div>', unsafe_allow_html=True)

st.sidebar.header("📁 Source & Import")
if st.sidebar.button("Réinitialiser les imports"):
    for cle in list(st.session_state.keys()):
        if cle.startswith("f_") or cle in ("df_courant", "empreinte_import", "sais_deb", "sais_fin"):
            del st.session_state[cle]
    st.rerun()

importe = st.sidebar.file_uploader("Importer un fichier (.csv / .xlsx)", type=["csv", "xlsx"])
chemin = FICHIERS_EXISTANTS[0] if FICHIERS_EXISTANTS else None

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cutoff S&OP")
col_c1, col_c2 = st.sidebar.columns(2)
annee_cloture = col_c1.number_input("Année Clôture", min_value=2000, max_value=2036, value=2026)
mois_cloture = col_c2.selectbox("Mois Pivot", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {MOIS[m-1]}")

st.sidebar.markdown("---")
st.sidebar.header("🎯 Cible & Affichage")
annee_cible = st.sidebar.number_input("Année Cible", min_value=2000, max_value=2040, value=int(annee_cloture) + 1)
objectif_global = st.sidebar.number_input("Objectif Annuel (HL)", min_value=0.0, value=1000000.0, step=10000.0)

val_choix = st.sidebar.radio("Métrique", options=["hl", "colis"], format_func=lambda x: "Hectolitres (hl)" if x == "hl" else "Colis (cs)", horizontal=True)
dec = st.sidebar.number_input("Décimales", min_value=0, max_value=4, value=0)
mode_affichage = st.sidebar.selectbox("Mode d'affichage", options=["Tableau", "Courbes", "Histogramme"], index=1)

# --- Chargement des données ---
df_brut = None
if importe is not None:
    contenu_import = importe.getvalue()
    empreinte = hashlib.sha256(contenu_import).hexdigest()
    if st.session_state.get("empreinte_import") != empreinte:
        st.session_state["df_courant"] = lire_et_normaliser(contenu_import, importe.name, None, int(annee_cloture), int(mois_cloture))
        st.session_state["empreinte_import"] = empreinte
    df_brut = st.session_state.get("df_courant")
elif "df_courant" in st.session_state:
    df_brut = st.session_state["df_courant"]
elif chemin:
    df_brut = lire_et_normaliser(None, "", str(chemin), int(annee_cloture), int(mois_cloture))
    st.session_state["df_courant"] = df_brut

if df_brut is None or df_brut.empty:
    st.warning("⚠️ Aucune donnée. Importez un fichier via la barre latérale.")
    st.stop()

# --- Filtres UI ---
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres")
if st.sidebar.button("🔄 Réinitialiser les filtres"):
    for col, _ in FILTRES:
        if f"f_{col}" in st.session_state: del st.session_state[f"f_{col}"]
    st.rerun()

selections_filtres = {col: st.session_state.get(f"f_{col}", []) for col, _ in FILTRES}
for col, label in FILTRES:
    if col not in df_brut.columns: continue
    options = options_filtre_cascade(df_brut, col, FILTRES, selections_filtres)
    options = [o for o in options if pd.notna(o) and str(o).strip().lower() not in ("", "nan", "none")]
    if col == "agence": options = sorted({*AGENCES_REFERENCE, *[str(o) for o in options]})
    else: options = trier(options, col)
    if not options: continue
    cle = f"f_{col}"
    if cle in st.session_state: st.session_state[cle] = [v for v in st.session_state[cle] if v in options]
    selections_filtres[col] = st.sidebar.multiselect(label, options, key=cle, placeholder="Tous")

recherche = st.sidebar.text_input("🔎 Recherche article", "")

# --- ÉTAPE 1, 2, 3, 4, 5 : EXECUTION DU MOTEUR ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Moteur SARR")
activer_moteur = st.sidebar.checkbox("Activer le calcul SARR & Prévisions", value=True)

if activer_moteur:
    with st.spinner("Calcul des indices, SARR, Momentum et Prévisions..."):
        df_brut_calcule, df_indices = moteur_saar_complet(df_brut, int(annee_cloture), int(mois_cloture))
else:
    df_brut_calcule = df_brut.copy()
    df_indices = pd.DataFrame()

# Application des filtres APRÈS le calcul
d = df_brut_calcule.copy()
for col, _ in FILTRES:
    if selections_filtres[col]: d = d[d[col].isin(selections_filtres[col])]
if recherche: d = d[d["article"].str.contains(recherche, case=False, na=False)]

# --- ÉTAPE 6 : CALCUL DU GAP ---
# On sépare Réalisé et Prévisions
d_real = d[d["nature"] == "Réalisé"]
d_prev = d[d["nature"] == "Prévision"]

vol_real = float(d_real[d_real["annee"] == annee_cloture][val_choix].sum())
vol_prev_ytd = float(d_prev[d_prev["annee"] == annee_cloture][val_choix].sum())
total_projete = vol_real + vol_prev_ytd
gap = objectif_global - total_projete

# --- KPI ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Réalisé à date (YTD)", f"{nombre(vol_real, dec)} {val_choix}")
k2.metric(f"Prévisions ({MOIS[mois_cloture-1]} → Déc)", f"{nombre(vol_prev_ytd, dec)} {val_choix}")
k3.metric("Total Projeté (Fin d'année)", f"{nombre(total_projete, dec)} {val_choix}")
k4.metric("GAP vs Objectif", f"{nombre(gap, dec)} {val_choix}", delta=f"{gap:,.0f}" if gap != 0 else None)

# --- ONGLETS ---
st.markdown("---")
tab_comp, tab_gap, tab_detail, tab_is = st.tabs(["📊 Prévision vs Réalisé", "🎯 GAP vs Objectif", "🔍 Détail des cumuls", "📈 Indices Saisonniers"])

# ==============================================================================
# ONGLET 1 : PRÉVISION VS RÉALISÉ
# ==============================================================================
with tab_comp:
    st.subheader(f"Évolution des volumes : Réalisé vs Prévision (Cible : {annee_cible})")
    
    df_comp = d.groupby(["annee", "nature"])[val_choix].sum().unstack("nature").fillna(0.0)
    toutes_annees = list(range(int(df_comp.index.min()), int(annee_cible) + 1))
    df_comp = df_comp.reindex(toutes_annees).fillna(0.0)

    if "Réalisé" not in df_comp.columns: df_comp["Réalisé"] = 0.0
    if "Prévision" not in df_comp.columns: df_comp["Prévision"] = 0.0

    for idx in df_comp.index:
        if idx < annee_cloture and df_comp.loc[idx, "Prévision"] == 0: df_comp.loc[idx, "Prévision"] = np.nan
        if idx > annee_cloture and df_comp.loc[idx, "Réalisé"] == 0: df_comp.loc[idx, "Réalisé"] = np.nan

    df_comp.index.name = "Année"
    df_comp = df_comp.reset_index()
    df_comp["Année"] = df_comp["Année"].astype(str)

    if mode_affichage == "Tableau":
        st.dataframe(df_comp.set_index("Année").round(dec), width="stretch")
    else:
        df_melt = df_comp.melt(id_vars="Année", var_name="Type", value_name="Volume").dropna(subset=["Volume"])
        chart = alt.Chart(df_melt).mark_line(
            interpolate="monotone", point=alt.OverlayMarkDef(filled=True, size=80)
        ).encode(
            x=alt.X("Année:N", sort=df_comp["Année"].tolist(), title="Année"),
            y=alt.Y("Volume:Q", title=f"Volume total ({val_choix})"),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Réalisé", "Prévision"], range=[COULEUR_REALISE, COULEUR_PREVISION]), legend=alt.Legend(title="Type")),
            strokeDash=alt.StrokeDash("Type:N", scale=alt.Scale(domain=["Réalisé", "Prévision"], range=[[1, 0], [5, 5]]), legend=None),
            tooltip=["Année", "Type", alt.Tooltip("Volume:Q", format=",.0f")]
        )
        st.altair_chart(chart.properties(height=450, width="container"), use_container_width=True)

# ==============================================================================
# ONGLET 2 : GAP VS OBJECTIF
# ==============================================================================
with tab_gap:
    st.subheader("Analyse du GAP par Article")
    st.write("Le GAP est calculé comme : **Objectif Global - (Réalisé à date + Prévisions)**. Un GAP positif signifie qu'il manque du volume pour atteindre l'objectif.")
    
    if not d_real.empty and not d_prev.empty:
        # Réalisé par article
        real_art = d_real[d_real["annee"] == annee_cloture].groupby("article")[val_choix].sum().rename("Réalisé")
        prev_art = d_prev[d_prev["annee"] == annee_cloture].groupby("article")[val_choix].sum().rename("Prévisions")
        
        df_gap_art = pd.concat([real_art, prev_art], axis=1).fillna(0.0)
        df_gap_art["Total Projeté"] = df_gap_art["Réalisé"] + df_gap_art["Prévisions"]
        
        # On répartit l'objectif global au prorata du poids des articles
        total_proj_global = df_gap_art["Total Projeté"].sum()
        df_gap_art["Poids"] = df_gap_art["Total Projeté"] / total_proj_global if total_proj_global > 0 else 1.0 / len(df_gap_art)
        df_gap_art["Objectif Estimé"] = df_gap_art["Poids"] * objectif_global
        df_gap_art["GAP"] = df_gap_art["Objectif Estimé"] - df_gap_art["Total Projeté"]
        
        # Alerte si GAP < 0
        df_gap_art["Alerte"] = np.where(df_gap_art["GAP"] < 0, "🔴 Sous l'objectif", "🟢 Sur l'objectif")
        
        df_gap_art = df_gap_art.sort_values("GAP", ascending=True).reset_index()
        
        st.dataframe(
            df_gap_art.style.format({
                "Réalisé": "{:,.0f}",
                "Prévisions": "{:,.0f}",
                "Total Projeté": "{:,.0f}",
                "Objectif Estimé": "{:,.0f}",
                "GAP": "{:,.0f}",
                "Poids": "{:.1%}"
            }),
            width="stretch",
            hide_index=True
        )
    else:
        st.info("Aucune donnée de prévision pour calculer le GAP.")

# ==============================================================================
# ONGLET 3 : DÉTAIL DES CUMULS
# ==============================================================================
with tab_detail:
    st.subheader("Détail des volumes par agence et article")
    
    if not d.empty:
        pivot_detail = d.pivot_table(
            index=["agence", "article"], 
            columns=["annee", "nature"], 
            values=val_choix, 
            aggfunc="sum"
        ).fillna(0.0)
        
        # Aplatir les colonnes
        pivot_detail.columns = [f"{annee} - {nature}" for annee, nature in pivot_detail.columns]
        
        st.dataframe(pivot_detail.round(dec), width="stretch", height=500)
    else:
        st.info("Aucune donnée pour les filtres actifs.")

# ==============================================================================
# ONGLET 4 : INDICES SAISONNIERS (FIX MATPLOTLIB)
# ==============================================================================
with tab_is:
    st.subheader("Indices Saisonniers (Moy_Mois / Moy_Ann)")
    
    if not df_indices.empty:
        st.write("Voici les indices calculés par Agence, Article et Mois. Un indice de 1.0 correspond à la moyenne annuelle.")
        
        # Filtre dynamique sur l'agence pour l'affichage
        agence_is = st.selectbox("Filtrer par agence", options=["Toutes"] + sorted(df_indices["agence"].unique().tolist()))
        df_is_filtre = df_indices if agence_is == "Toutes" else df_indices[df_indices["agence"] == agence_is]
        
        pivot_is = df_is_filtre.pivot_table(index="article", columns="mois", values="Indice", aggfunc="first").fillna(1.0)
        pivot_is.columns = [MOIS[c-1] for c in pivot_is.columns]
        
        # FIX : Remplacement de .style.background_gradient (qui requiert matplotlib) 
        # par un formateur texte simple, ou affichage standard.
        st.dataframe(
            pivot_is.round(2).style.format("{:.2f}"), 
            width="stretch"
        )
    else:
        st.info("Les indices n'ont pas été calculés.")

# --- Export Excel ---
st.markdown("---")
tampon = io.BytesIO()
with pd.ExcelWriter(tampon, engine="openpyxl") as xl:
    if not d.empty:
        d.to_excel(xl, index=False, sheet_name="Données SARR")
    if not df_indices.empty:
        df_indices.to_excel(xl, index=False, sheet_name="Indices Saisonniers")
    if 'df_gap_art' in locals() and not df_gap_art.empty:
        df_gap_art.to_excel(xl, index=False, sheet_name="Analyse GAP")

st.download_button(
    "📥 Télécharger l'export complet (.xlsx)",
    data=tampon.getvalue(),
    file_name=f"Export_SOP_{annee_cible}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)

from __future__ import annotations

import io
import hashlib
import os
import sys
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# On garde uniquement filter_dimensions si vous l'avez, sinon on peut l'intégrer plus tard
try:
    from .filter_dimensions import assurer_dimensions_filtres, options_filtre_cascade
except ImportError:
    try:
        from filter_dimensions import assurer_dimensions_filtres, options_filtre_cascade
    except ImportError as erreur_import:
        st.error("Fichier `filter_dimensions.py` introuvable. Il est nécessaire pour les filtres.")
        st.stop()

# ==============================================================================
# 1. CONFIGURATION & CONSTANTES
# ==============================================================================

st.set_page_config(
    page_title="Suivi & Prévision SAAR (S&OP)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

RACINE = Path(__file__).resolve().parent
DOSSIERS = [RACINE, RACINE.parent, Path.cwd()]

FICHIERS_CANDIDATS = ["DATA_BRUT.xlsx"]

COLONNES = [
    "annee", "mois", "periode", "agence", "region", "segment", "produit", "parfum", "format",
    "type_format", "article", "nature", "origine", "colis", "hl",
    "coeff_janvier", "coeff_fevrier", "coeff_mars", "coeff_avril", "coeff_mai",
    "coeff_juin", "coeff_juillet", "coeff_aout", "coeff_septembre",
    "coeff_octobre", "coeff_novembre", "coeff_decembre"
]

MOIS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]
MOIS_COMPLETS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_NOMS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

COULEUR_REALISE = "#9E6315EF"
COULEUR_PREVISION = "#9BD69E"
HAUSSE_SAISONNIERE_PREVISION = {6: 1.20, 12: 1.20}

COEFFICIENTS_SAISONNIERS = [
    f"coeff_{mois}" for mois in ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
]

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
    "IC": "IC (Individual/Immediat Consumption)", "FC": "FC (Family/Future Consumption)"
}

# ==============================================================================
# 2. FONCTIONS DE LECTURE ET FORMATAGE (ex monthly_import.py)
# ==============================================================================

_MOIS_MAP = {
    "janvier": 1, "janv": 1, "jan": 1, "january": 1, "fevrier": 2, "fevr": 2, "fev": 2, "feb": 2,
    "february": 2, "mars": 3, "mar": 3, "march": 3, "avril": 4, "avr": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5, "juin": 6, "jun": 6, "june": 6, "juillet": 7, "juil": 7, "jul": 7, "july": 7,
    "aout": 8, "aug": 8, "august": 8, "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10, "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}

def _sans_accents(texte: str) -> str:
    return unicodedata.normalize("NFD", texte).encode("ascii", "ignore").decode("utf-8")

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

def normaliser_lignes_data_brut(df_raw: pd.DataFrame, articles_referentiel: list[str]) -> pd.DataFrame:
    """Convertit le fichier brut en format long."""
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
        
        # Nettoyage des lignes "Total"
        masque_total = df["segment"].str.contains("total", case=False) | df["produit"].str.contains("total", case=False) | df["agence"].str.contains("total", case=False)
        df = df[~masque_total].copy()
        
        # Période et colonnes manquantes
        df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
        df["colis"] = 0.0
        df["origine"] = "Donnée source"
        
        # Matching article (simple)
        df["article"] = df["produit"] + " " + df["segment"]
        return df.reset_index(drop=True)
    return df_raw

# ==============================================================================
# 3. CALCULS SAISONNALITÉ (ex seasonality_index.py - Méthode Excel)
# ==============================================================================

def annees_completes_saisonnalite(donnees: pd.DataFrame, annee_debut: int, annee_fin: int, annee_cloture: int, mois_cloture: int) -> list[int]:
    realise = donnees.loc[donnees["nature"].eq("Réalisé") & donnees["mois"].between(1, 12)]
    if realise.empty: return []
    
    mois_par_annee = (realise.loc[realise["annee"].between(annee_debut, annee_fin)]
                      .drop_duplicates(["annee", "mois"]).groupby("annee")["mois"].nunique())
    
    res = []
    for annee in sorted(mois_par_annee.index):
        annee = int(annee)
        if annee == annee_cloture and mois_cloture < 12: continue
        if int(mois_par_annee.loc[annee]) == 12: res.append(annee)
    return res

def calculer_indices_saisonnalite(donnees: pd.DataFrame, valeur: str, annee_debut: int, annee_fin: int, annee_cloture: int, mois_cloture: int) -> pd.DataFrame:
    """Méthode Excel : Moyenne des ratios annuels."""
    annees = annees_completes_saisonnalite(donnees, annee_debut, annee_fin, annee_cloture, mois_cloture)
    grille_mois = pd.Index(range(1, 13), name="mois")
    
    if not annees:
        return pd.DataFrame({"Mois": MOIS_NOMS, "Volume moyen": 0.0, "Nombre de périodes": 0, "Indice saisonnier": float("nan")})

    selection = donnees.loc[donnees["nature"].eq("Réalisé") & donnees["annee"].isin(annees) & donnees["mois"].between(1, 12)]
    
    # Somme par mois (crucial pour éviter les doublons d'articles)
    volumes = selection.groupby(["annee", "mois"])[valeur].sum().unstack("mois").reindex(index=annees, columns=range(1, 13)).fillna(0.0)
    
    moyennes_annuelles = volumes.sum(axis=1) / 12.0
    moyennes_annuelles = moyennes_annuelles.replace(0, np.nan)
    
    ratios = volumes.div(moyennes_annuelles, axis=0)
    indices = ratios.mean(axis=0).fillna(0.0)
    
    somme_indices = float(indices.sum())
    if somme_indices > 0: indices = indices * 12.0 / somme_indices

    return pd.DataFrame({
        "Mois": MOIS_NOMS,
        "Volume moyen": volumes.mean(axis=0).to_numpy(),
        "Nombre de périodes": len(annees),
        "Indice saisonnier": indices.to_numpy(),
    })

# ==============================================================================
# 4. CHARGEMENT DU RÉFÉRENTIEL & UTILITAIRES
# ==============================================================================

@st.cache_data
def charger_referentiel():
    chemins_ref = [RACINE / "Classeur2.xlsx", Path.cwd() / "Classeur2.xlsx"]
    f_ref = next((p for p in chemins_ref if p.exists()), None)
    if f_ref:
        df_ref = pd.read_excel(f_ref, sheet_name="Ref actif")
        catalogue = []
        for _, r in df_ref.iterrows():
            art = str(r['Article']).strip()
            pos = str(r['Positionnement']).strip()
            occ = str(r['Occasion']).strip()
            fmt = str(r['Format']).strip()
            c_cl = r['Contenance (Cl)']
            segment = "BIERES" if any(b in art.lower() for b in ["beer", "thb", "gold", "queen", "beaufort"]) else ("EAUX" if "cristal" in art.lower() or "eau" in art.lower() else "BOISSONS")
            catalogue.append({
                "segment": segment, "produit": art.split()[0], "parfum": art, "format": f"{c_cl} cl {fmt}",
                "type_format": occ, "article": art, "positionnement": pos, "occasion": occ,
                "conditionnement": fmt, "contenance_ci": c_cl, "contenance_hl": r['Contenance (hl)'],
                "type_format_lib": occ
            })
        return pd.DataFrame(catalogue)
    return pd.DataFrame()

CATALOGUE = charger_referentiel()
CATALOGUE_PAR_ARTICLE = {meta["article"].lower().strip(): meta for meta in CATALOGUE.to_dict(orient="records")}
ARTICLES_REFERENTIEL = CATALOGUE["article"].dropna().astype(str).str.strip().tolist() if not CATALOGUE.empty else []

def normaliser_nom(nom: str) -> str:
    s = _sans_accents(str(nom).strip().lower())
    return re.sub(r'[^a-z0-9_]+', '_', s).strip('_')

AGENCES_PAR_CLE = {normaliser_nom(a): a for a in AGENCES_REFERENCE}
AGENCES_PAR_CLE.update({normaliser_nom(a.split("-", 1)[1]): a for a in AGENCES_REFERENCE})

def normaliser_agence(valeur: object) -> str:
    nom = str(valeur).strip()
    cle = normaliser_nom(nom)
    agence = AGENCES_PAR_CLE.get(cle)
    if agence: return agence
    if re.fullmatch(r"\d+(_0)?", cle):
        code = f"{int(cle.split('_', 1)[0]):02d}"
        return next((a for a in AGENCES_REFERENCE if a.startswith(f"{code}-")), nom)
    return nom

def region_depuis_agence(valeur: object) -> str:
    return REGION_PAR_AGENCE.get(normaliser_agence(valeur), "Non renseigné")

def _lire_csv_robuste(flux):
    return pd.read_csv(flux, sep=None, encoding="utf-8-sig", engine="python")

# ==============================================================================
# 5. CHARGEMENT DES DONNÉES ET NETTOYAGE
# ==============================================================================

def lire_et_normaliser(contenu: bytes | None, nom: str, chemin: str | None, annee_cloture: int, mois_cloture: int) -> pd.DataFrame:
    nom_fichier = Path(nom if contenu is not None else chemin or "").name.lower()
    est_data_brut = nom_fichier == "data_brut.xlsx"
    
    # Lecture du fichier
    if contenu is not None:
        flux = io.BytesIO(contenu)
        if nom.lower().endswith(".csv"): df_raw = _lire_csv_robuste(flux)
        else:
            feuilles = pd.ExcelFile(flux).sheet_names
            feuille = next((f for f in feuilles if normaliser_nom(f) == "export"), feuilles[0]) if est_data_brut else 0
            df_raw = pd.read_excel(flux, sheet_name=feuille, header=None) if est_data_brut else pd.read_excel(flux, sheet_name=feuille)
    else:
        chemin_str = str(chemin)
        if chemin_str.lower().endswith(".csv"): df_raw = _lire_csv_robuste(chemin_str)
        else:
            feuilles = pd.ExcelFile(chemin_str).sheet_names
            feuille = next((f for f in feuilles if normaliser_nom(f) == "export"), feuilles[0]) if est_data_brut else 0
            df_raw = pd.read_excel(chemin_str, sheet_name=feuille, header=None) if est_data_brut else pd.read_excel(chemin_str, sheet_name=feuille)

    # Conversion format long si DATA_BRUT
    df = normaliser_lignes_data_brut(df_raw, ARTICLES_REFERENTIEL) if est_data_brut else df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    
    # Renommage des colonnes
    col_map = {"annee": "annee", "mois": "mois", "agence": "agence", "agences": "agence", "segment": "segment", 
               "produit": "produit", "marque": "produit", "article": "article", "articles": "article", "nature": "nature", 
               "hl": "hl", "volume": "hl", "colis": "colis"}
    df = df.rename(columns={c: col_map[normaliser_nom(c)] for c in df.columns if normaliser_nom(c) in col_map})
    
    # Colonnes de base
    defaut = {"annee": 2026, "mois": 1, "periode": "2026-01", "agence": "Non renseigné", "region": "Non renseigné", "segment": "Non renseigné", "produit": "Non renseigné", "parfum": "Non renseigné", "format": "Non renseigné", "type_format": "Non renseigné", "article": "Non renseigné", "nature": "Prévision", "colis": 0.0, "hl": 0.0, "origine": "Donnée source"}
    for k, v in defaut.items():
        if k not in df.columns: df[k] = v

    df = df[COLONNES].copy()
    
    # Nettoyage
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").fillna(2026).astype(int)
    df["mois"] = df["mois"].map(normaliser_mois).fillna(1).astype(int)
    df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
    df["agence"] = df["agence"].map(normaliser_agence)
    df["region"] = df["agence"].map(region_depuis_agence)
    
    for c in ["colis", "hl"]: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    
    # Enrichissement via référentiel
    articles = df["article"].map(str).str.strip().str.lower()
    for c_dim in ["segment", "produit", "parfum", "format", "type_format", "positionnement", "occasion", "conditionnement", "contenance_ci", "contenance_hl"]:
        if c_dim not in df.columns: df[c_dim] = "Non renseigné"
        champ = "type_format_lib" if c_dim == "type_format" else c_dim
        correspondances = {a: m.get(champ, "Non renseigné") for a, m in CATALOGUE_PAR_ARTICLE.items()}
        df[c_dim] = df[c_dim].mask(df[c_dim].isin(["", "Non renseigné", "nan", "None"]), articles.map(correspondances).fillna("Non renseigné"))

    df = assurer_dimensions_filtres(df, CATALOGUE_PAR_ARTICLE, TYPES)
    df["region"] = df["agence"].map(region_depuis_agence) # Sécurité
    
    # Filtre des articles valides
    df = df[~df["article"].str.lower().isin(["", "non renseigné", "total", "nan"])].copy()
    
    # Forcer nature
    cond_realise = (df["annee"] < annee_cloture) | ((df["annee"] == annee_cloture) & (df["mois"] <= mois_cloture))
    df["nature"] = np.where(cond_realise, "Réalisé", "Prévision")
    
    return df

@st.cache_data(show_spinner="Chargement des données...")
def charger_et_normaliser(contenu, nom, chemin, annee_cloture, mois_cloture):
    return lire_et_normaliser(contenu, nom, chemin, annee_cloture, mois_cloture)

# ==============================================================================
# 6. MOTEUR SAAR (Prévisions)
# ==============================================================================

@st.cache_data(show_spinner="Calcul des prévisions SAAR...")
def appliquer_projection_saar(df: pd.DataFrame, annee_cloture: int, mois_cloture: int, annee_cible: int, taux_croissance: float) -> pd.DataFrame:
    if annee_cible < annee_cloture: return df
    
    cles = ["agence", "article"]
    dimensions = ["agence", "region", "segment", "produit", "parfum", "format", "type_format", "article", "origine", "positionnement", "occasion", "conditionnement", "contenance_ci", "contenance_hl"]

    realise_ytd = df.loc[(df["nature"] == "Réalisé") & (df["annee"] == annee_cloture) & (df["mois"] <= mois_cloture)]
    if realise_ytd.empty: return df

    cumul_ytd = realise_ytd.groupby(cles)[["hl", "colis"]].sum()
    derniere_ligne = realise_ytd.sort_values(["annee", "mois"]).drop_duplicates(cles, keep="last").set_index(cles)

    df_ref = df.loc[df["annee"].isin([2024, 2025]) & (df["nature"] == "Réalisé")]
    profils_ref = {}
    if not df_ref.empty:
        volumes_mensuels = df_ref.groupby([*cles, "mois"])["hl"].sum().unstack("mois").fillna(0.0).reindex(columns=range(1, 13), fill_value=0.0).clip(lower=0.0)
        totaux = volumes_mensuels.sum(axis=1)
        profils = volumes_mensuels.div(totaux.where(totaux > 0), axis=0) * 12.0
        profils_ref = {c: p.to_numpy(dtype=float) for c, p in profils.iterrows() if totaux.loc[c] > 0}

    volumes_annee_precedente = df.loc[df["annee"] == annee_cible - 1].groupby([*cles, "mois"])[["hl", "colis"]].sum()
    taux_annuel = 1.0 + max(taux_croissance, 1.0) / 100.0
    facteur_croissance = taux_annuel ** (annee_cible - annee_cloture)
    
    projections = []
    for cle, volumes in cumul_ytd.iterrows():
        cle = cle if isinstance(cle, tuple) else (cle,)
        profil = profils_ref.get(cle, np.ones(12, dtype=float))
        if profil[:mois_cloture].sum() <= 0: profil = np.ones(12, dtype=float)
        
        poids_ecoule = profil[:mois_cloture].sum()
        base_hl = max(0.0, float(volumes["hl"]) / poids_ecoule * 12.0)
        base_colis = max(0.0, float(volumes["colis"]) / poids_ecoule * 12.0)
        ligne_ref = derniere_ligne.loc[cle]

        for mois in range(1, 13):
            if annee_cible == annee_cloture and mois <= mois_cloture: continue
            facteur_mois = HAUSSE_SAISONNIERE_PREVISION.get(mois, 1.0)
            
            ligne = {col: cle[cles.index(col)] if col in cles else ligne_ref[col] for col in dimensions}
            cle_mois_prec = (*cle, mois)
            
            if cle_mois_prec in volumes_annee_precedente.index:
                plancher = volumes_annee_precedente.loc[cle_mois_prec]
                vol_hl_min, vol_colis_min = max(0.0, float(plancher["hl"])), max(0.0, float(plancher["colis"]))
            else:
                vol_hl_min = base_hl * taux_annuel ** max(0, annee_cible - 1 - annee_cloture) * profil[mois - 1] / 12.0
                vol_colis_min = base_colis * taux_annuel ** max(0, annee_cible - 1 - annee_cloture) * profil[mois - 1] / 12.0

            ligne.update({
                "annee": annee_cible, "mois": mois, "periode": f"{annee_cible}-{mois:02d}", "nature": "Prévision",
                "hl": max(vol_hl_min, base_hl * facteur_croissance * profil[mois - 1] / 12.0) * facteur_mois,
                "colis": max(vol_colis_min, base_colis * facteur_croissance * profil[mois - 1] / 12.0) * facteur_mois,
            })
            projections.append(ligne)

    if not projections: return df

    nouvelles_previsions = pd.DataFrame(projections).reindex(columns=df.columns)
    masque_existant = (df["annee"] == annee_cible) & (df["nature"] == "Prévision")
    if annee_cible == annee_cloture: masque_existant &= df["mois"].gt(mois_cloture)
    
    return pd.concat([df.loc[~masque_existant], nouvelles_previsions], ignore_index=True)

@st.cache_data(show_spinner="Reconstitution des prévisions historiques...")
def reconstituer_previsions_historiques(df: pd.DataFrame, annee_cloture: int, taux_croissance: float) -> pd.DataFrame:
    annees_presentes = set(df["annee"].unique())
    mois_par_annee = df.groupby("annee")["mois"].agg(["min", "max"])
    annees_completes = {int(a) for a, p in mois_par_annee.iterrows() if p["min"] == 1 and p["max"] == 12}
    
    previsions = []
    previsions_par_annee = {}
    facteur_min = 1.0 + max(taux_croissance, 1.0) / 100.0

    for annee_cible in sorted(annees_presentes):
        annee_precedente = int(annee_cible) - 1
        if annee_cible >= annee_cloture or annee_precedente not in annees_completes: continue
        
        historique = df.loc[df["annee"] < annee_cible].copy()
        historique["nature"] = "Réalisé"
        projection = appliquer_projection_saar(historique, annee_precedente, 12, int(annee_cible), taux_croissance)
        
        prevision = projection.loc[projection["annee"].eq(annee_cible) & projection["nature"].eq("Prévision")].copy()
        references = previsions_par_annee[annee_precedente].groupby(["agence", "article"])[["hl", "colis"]].sum() if annee_precedente in previsions_par_annee else df.loc[df["annee"].eq(annee_precedente)].groupby(["agence", "article"])[["hl", "colis"]].sum()
        
        for cle, indices in prevision.groupby(["agence", "article"]).groups.items():
            if cle not in references.index: continue
            ref = references.loc[cle]
            for col in ("hl", "colis"):
                vol_prevu = prevision.loc[indices, col].sum()
                vol_min = max(0.0, float(ref[col])) * facteur_min
                if vol_prevu > 0 and vol_prevu < vol_min:
                    prevision.loc[indices, col] *= vol_min / vol_prevu
                    
        prevision["nature"] = "Prévision reconstituée"
        previsions_par_annee[int(annee_cible)] = prevision
        previsions.append(prevision)

    return pd.concat(previsions, ignore_index=True) if previsions else df.iloc[0:0]

# ==============================================================================
# 7. AFFICHAGE ET INTERFACE (Streamlit)
# ==============================================================================

# --- CSS PERSONNALISÉ ---
st.markdown("""
<style>
:root { --red: #d7193f; --green: #0e8a4a; --bg: #faf9fc; }
.stApp { background: radial-gradient(1000px 400px at 100% -10%, #fff1f4, transparent), radial-gradient(1000px 400px at 0% 110%, #eaf7f0, transparent), #fff; }
.block-container { max-width: 1440px; padding: 2rem 4vw; }
.titre { font-size: 2.5rem; font-weight: 800; color: #121017; }
.titre::after { content: ""; display: block; width: 72px; height: 4px; margin-top: .8rem; background: linear-gradient(90deg, var(--red) 50%, var(--green) 50%); border-radius: 99px; }
div[data-testid="stMetric"] { background: #fff; border: 1px solid #e2e0e6; border-radius: 16px; padding: 1.25rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,.03); border-top: 4px solid var(--red); }
div[data-testid="stMetric"] label { font-weight: 700; color: #5c5665; text-transform: uppercase; font-size: 0.78rem; }
div[data-testid="stMetricValue"] { font-weight: 800; color: #121017; }
</style>
""", unsafe_allow_html=True)

def nombre(x: float, dec: int) -> str: return f"{x:,.{dec}f}".replace(",", " ")
def etiquette(periode: str) -> str:
    p = str(periode).split("-")
    return f"{MOIS[int(p[1]) - 1]}-{p[0][-2:]}" if len(p) == 2 and p[1].isdigit() else str(periode)

def tableau(df: pd.DataFrame, **kw):
    try: st.dataframe(df, width="stretch", **kw)
    except Exception: st.dataframe(df, width='stretch', **kw)

def afficher_vue(df: pd.DataFrame, mode: str, dec: int = 0, couleur=None, hauteur=350):
    if mode == "Tableau": tableau(df.round(dec)); return
    df_graphique = df.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df_graphique.empty: st.info("Aucune valeur numérique."); return
    
    if mode == "Courbes":
        nom_axe = df_graphique.index.name or "Période"
        donnees = df_graphique.rename_axis(nom_axe).reset_index().melt(id_vars=nom_axe, var_name="Série", value_name="Valeur")
        donnees[nom_axe] = donnees[nom_axe].astype(str)
        graphique = alt.Chart(donnees).mark_line(interpolate="monotone", point=alt.OverlayMarkDef(filled=True, size=35)).encode(
            x=alt.X(f"{nom_axe}:N", sort=df_graphique.index.astype(str).tolist(), title=nom_axe),
            y=alt.Y("Valeur:Q", title="Volume"),
            tooltip=[nom_axe, "Série", alt.Tooltip("Valeur:Q", format=",.2f")]
        )
        if couleur: graphique = graphique.encode(color=alt.Color("Série:N", scale=alt.Scale(domain=df_graphique.columns.tolist(), range=couleur), legend=alt.Legend(title=None)))
        st.altair_chart(graphique.properties(height=hauteur), width="stretch")
    else:
        st.bar_chart(df_graphique, color=couleur, height=hauteur)

def trier(valeurs, col):
    v = [x for x in valeurs if pd.notna(x)]
    if col in {"contenance_ci", "contenance_hl"}: return sorted(v, key=lambda x: float(x) if str(x).replace('.','',1).isdigit() else 999)
    if col == "conditionnement": return sorted(v, key=lambda x: ({"CAN": 0, "PET": 1, "VER": 2}.get(str(x), 99), str(x)))
    return sorted(v)

# ==============================================================================
# 8. INITIALISATION ET BOUCLE PRINCIPALE
# ==============================================================================

FICHIERS_EXISTANTS = [d / f for d in DOSSIERS for f in FICHIERS_CANDIDATS if (d / f).exists()]

st.markdown('<div class="titre">Moteur S&OP : Prévision SAAR & Rolling Forecast</div>', unsafe_allow_html=True)

# --- Sidebar : Import & Paramètres ---
st.sidebar.header("📁 Source & Import")
if st.sidebar.button("Réinitialiser les imports"):
    st.session_state.clear()
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
mois_cible_str = st.sidebar.selectbox("Mois Cible", options=["Tous les mois"] + MOIS_COMPLETS, index=0)
mois_cible_num = None if mois_cible_str == "Tous les mois" else MOIS_COMPLETS.index(mois_cible_str) + 1

val_choix = st.sidebar.radio("Métrique", options=["hl", "colis"], format_func=lambda x: "Hectolitres (hl)" if x == "hl" else "Colis (cs)", horizontal=True)
dec = st.sidebar.number_input("Décimales", min_value=0, max_value=4, value=0)
mode_affichage = st.sidebar.selectbox("Vue", options=["Tableau", "Courbes", "Histogramme"])

# --- Chargement des données ---
df_brut = None
if importe is not None:
    contenu_import = importe.getvalue()
    empreinte = hashlib.sha256(contenu_import).hexdigest()
    if st.session_state.get("empreinte_import") != empreinte:
        st.session_state["df_courant"] = charger_et_normaliser(contenu_import, importe.name, None, int(annee_cloture), int(mois_cloture))
        st.session_state["empreinte_import"] = empreinte
    df_brut = st.session_state.get("df_courant")
elif "df_courant" in st.session_state:
    df_brut = st.session_state["df_courant"]
elif chemin:
    df_brut = charger_et_normaliser(None, "", str(chemin), int(annee_cloture), int(mois_cloture))
    st.session_state["df_courant"] = df_brut

if df_brut is None or df_brut.empty:
    st.warning("⚠️ Aucune donnée. Importez un fichier via la barre latérale.")
    st.stop()

# --- Application des filtres ---
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
    
    if col == "agence": options = [a for a in AGENCES_REFERENCE if a in set(options)]
    else: options = trier(options, col)
    
    if not options: continue
    cle = f"f_{col}"
    if cle in st.session_state: st.session_state[cle] = [v for v in st.session_state[cle] if v in options]
    selections_filtres[col] = st.sidebar.multiselect(label, options, key=cle, placeholder="Tous")

d = df_brut.copy()
for col, _ in FILTRES:
    if selections_filtres[col]: d = d[d[col].isin(selections_filtres[col])]
recherche = st.sidebar.text_input("🔎 Recherche article", "")
if recherche: d = d[d["article"].str.contains(recherche, case=False, na=False)]

# --- SAAR & Cumuls ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Moteur SAAR")
activer_saar = st.sidebar.checkbox("Activer la projection SAAR", value=True)
afficher_prev_hist = st.sidebar.checkbox("Afficher les prévisions historiques", value=True)
taux_saar = st.sidebar.number_input("Hausse annuelle minimale (%)", min_value=1.0, value=1.0, step=0.5)

df_previsions_hist = df_brut.iloc[0:0].copy()
df_previsions_toutes = df_brut.iloc[0:0].copy()

if activer_saar:
    df_previsions_toutes = reconstituer_previsions_historiques(df_brut, int(annee_cloture) + 1, float(taux_saar))
    if afficher_prev_hist:
        df_previsions_hist = df_previsions_toutes.loc[df_previsions_toutes["annee"].lt(annee_cloture)].copy()
    
    if annee_cible >= annee_cloture:
        for a_proj in range(int(annee_cloture) + 1, int(annee_cible) + 1):
            df_brut = appliquer_projection_saar(df_brut, int(annee_cloture), int(mois_cloture), a_proj, float(taux_saar))

d_tendance = pd.concat([d, df_previsions_hist], ignore_index=True).replace("Prévision reconstituée", "Prévision")

# --- IS & Affichage ---
annees_reelles = sorted(int(a) for a in df_brut.loc[df_brut["nature"].eq("Réalisé"), "annee"].unique())
annees_debut_possibles = annees_reelles[:-1]

indices_saisonnalite = pd.DataFrame()
if annees_debut_possibles:
    st.markdown("### Indice de saisonnalité — période d’analyse")
    c1, c2 = st.columns(2)
    annee_debut = c1.selectbox("Année début", options=annees_debut_possibles, index=0, key="sais_deb")
    annees_fin = [a for a in annees_reelles if a > annee_debut]
    if st.session_state.get("sais_fin") not in annees_fin: st.session_state["sais_fin"] = annees_fin[-1]
    annee_fin = c2.selectbox("Année fin", options=annees_fin, key="sais_fin")
    
    # Calcul de l'IS (uniquement sur les lignes sans "Total")
    d_is = d.loc[~d["article"].astype(str).str.lower().str.contains("total", na=False)]
    indices_saisonnalite = calculer_indices_saisonnalite(d_is, val_choix, int(annee_debut), int(annee_fin), int(annee_cloture), int(mois_cloture))
else:
    st.info("Il faut au moins deux années de réalisés pour l'IS.")

# --- KPI Cumuls ---
ANNEE_DEBUT_CUMUL = 2024
m_real = (d["nature"].eq("Réalisé") & d["annee"].ge(ANNEE_DEBUT_CUMUL) & (d["annee"].lt(annee_cloture) | (d["annee"].eq(annee_cloture) & d["mois"].le(mois_cloture))))
m_prev = (d["nature"].eq("Prévision") & d["annee"].eq(annee_cloture) & d["mois"].gt(mois_cloture))

vol_real = float(d.loc[m_real, val_choix].sum())
vol_prev = float(d.loc[m_prev, val_choix].sum())
vol_total = vol_real + vol_prev

k1, k2, k3 = st.columns(3)
k1.metric("Cumul réalisé à date", f"{nombre(vol_real, dec)} {val_choix}")
k2.metric(f"Cumul prévision ({MOIS[mois_cloture]} → déc)", f"{nombre(vol_prev, dec)} {val_choix}")
k3.metric("Cumul total", f"{nombre(vol_total, dec)} {val_choix}")

# --- Onglets ---
st.markdown("---")
tab_d, tab_is = st.tabs(["📊 Détail des cumuls", "📈 Indice saisonnier"])

with tab_d:
    st.subheader("Détail par article et agence")
    dims = ["article", "agence", "segment", "produit"]
    base = d.loc[m_real | m_prev].copy()
    if not base.empty:
        base["col_cumul"] = np.where(base["nature"].eq("Réalisé"), base["annee"].map(lambda a: f"Réalisé {a}"), "Prévision")
        pivot = base.pivot_table(index=dims, columns="col_cumul", values=val_choix, aggfunc="sum").fillna(0.0).reset_index()
        tableau(pivot.round(dec), height=400)
    else:
        st.info("Aucune donnée pour les filtres actifs.")

with tab_is:
    st.subheader("Indice de saisonnalité par mois")
    if not indices_saisonnalite.empty and indices_saisonnalite["Indice saisonnier"].notna().any():
        st.bar_chart(indices_saisonnalite.set_index("Mois")[["Indice saisonnier"]], height=350)
        st.dataframe(indices_saisonnalite.round(2), width="stretch", hide_index=True)
    else:
        st.info("Données insuffisantes pour calculer l'IS.")

# --- Export ---
st.markdown("---")
tampon = io.BytesIO()
with pd.ExcelWriter(tampon, engine="openpyxl") as xl:
    if not d.empty: d.to_excel(xl, index=False, sheet_name="Données Filtrées")
    if not df_previsions_toutes.empty: df_previsions_toutes.to_excel(xl, index=False, sheet_name="Prévisions Historiques")
    if not indices_saisonnalite.empty: indices_saisonnalite.to_excel(xl, index=False, sheet_name="Saisonnalité")

st.download_button("📥 Télécharger l'export complet (.xlsx)", data=tampon.getvalue(), file_name=f"Export_SOP_{annee_cible}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

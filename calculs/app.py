import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 1 : Données Brutes", layout="wide")
st.title("Étape 1 : Ingestion & Enrichissement (Périmètre Référentiel)")

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def normaliser_mois(valeur) -> int:
    if pd.isna(valeur): return 1
    if isinstance(valeur, (int, float)): return int(valeur)
    mois_map = {
        "janvier": 1, "janv": 1, "jan": 1, "fevrier": 2, "fevr": 2, "fev": 2, 
        "mars": 3, "mar": 3, "avril": 4, "avr": 4, "mai": 5, "juin": 6, "jun": 6, 
        "juillet": 7, "juil": 7, "jul": 7, "aout": 8, "aug": 8, "septembre": 9, 
        "sept": 9, "sep": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11, 
        "decembre": 12, "dec": 12
    }
    texte = unicodedata.normalize("NFD", str(valeur)).encode("ascii", "ignore").decode("utf-8").lower().strip()
    return mois_map.get(texte, 1)

def extraire_article(nature_str: str) -> str:
    if pd.isna(nature_str): return ""
    match = re.match(r"^\d+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

# ==============================================================================
# LECTURE DES FICHIERS
# ==============================================================================
def lire_referentiel(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    # On lit l'onglet 'Ref actif'
    df_ref = pd.read_excel(flux, sheet_name="Ref actif")
    
    # Uniformisation des noms de colonnes
    df_ref = df_ref.rename(columns={
        "Article": "article", 
        "Positionnement": "positionnement",
        "Occasion": "occasion",
        "Contenance (hl)": "contenance_hl"
    })
    
    colonnes_voulues = ["article", "positionnement", "occasion", "contenance_hl"]
    for col in colonnes_voulues:
        if col not in df_ref.columns:
            df_ref[col] = 0.0 if "contenance" in col else "Non renseigné"
                
    df_ref = df_ref[colonnes_voulues].copy()
    df_ref["article"] = df_ref["article"].astype(str).str.strip()
    return df_ref

def lire_ventes(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    df_raw = pd.read_excel(flux, sheet_name=0, header=None)
    
    if detecter_format_pivote(df_raw):
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "hl"])}
        df = df_raw.rename(columns=rename).copy()
        
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
        df["mois"] = df["mois"].apply(normaliser_mois)
        df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)
        
        # Suppression des lignes "Total" et des lignes vides
        masque_total = (
            df["segment"].astype(str).str.contains("total", case=False, na=False) |
            df["produit"].astype(str).str.contains("total", case=False, na=False) |
            df["agence"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].isna()
        )
        df = df[~masque_total].copy()
        
        # Extraction de l'article
        df["article"] = df["nature"].apply(extraire_article)
        df["agence"] = df["agence"].astype(str).str.strip()
        
        df["annee"] = df["annee"].fillna(2026).astype(int)
        df["mois"] = df["mois"].fillna(1).astype(int)
        
        return df
    else:
        return pd.DataFrame()

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"], key="ventes")
with col2:
    fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"], key="ref")

if fichier_ventes is not None and fichier_ref is not None:
    with st.spinner("Lecture et filtrage sur le référentiel..."):
        df_ventes = lire_ventes(fichier_ventes.getvalue())
        df_ref = lire_referentiel(fichier_ref.getvalue())
        
        # FIX : On utilise how="inner" pour ne garder QUE les articles présents dans le référentiel
        df_enrichi = df_ventes.merge(df_ref, on="article", how="inner")
        
        # Sécurité pour les valeurs manquantes
        df_enrichi["positionnement"] = df_enrichi["positionnement"].fillna("Non renseigné")
        df_enrichi["occasion"] = df_enrichi["occasion"].fillna("Non renseigné")
        df_enrichi["contenance_hl"] = df_enrichi["contenance_hl"].fillna(0.0)
        
    st.success(f"✅ Données fusionnées et filtrées avec succès ! {len(df_enrichi):,} lignes prêtes pour l'analyse.".replace(",", " "))
    
    # --- Vérifications ---
    st.subheader("Vérifications de base")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Lignes de ventes initiales", f"{len(df_ventes):,}".replace(",", " "))
    
    # On affiche la différence
    lignes_supprimees = len(df_ventes) - len(df_enrichi)
    kpi2.metric("Lignes conservées (Réf.)", f"{len(df_enrichi):,}".replace(",", " "), 
                delta=f"-{lignes_supprimees:,} lignes hors réf.".replace(",", " "), delta_color="inverse")
    
    kpi3.metric("Articles uniques", df_enrichi["article"].nunique())
    kpi4.metric("Volume total (HL)", f"{df_enrichi['hl'].sum():,.0f}".replace(",", " "))
    
    st.info("ℹ️ Le tableau a été filtré pour ne conserver que les articles présents dans votre fichier `Classeur2.xlsx`.")
    
    # --- Aperçu ---
    st.subheader("Aperçu du DataFrame enrichi (Périmètre Référentiel)")
    st.dataframe(df_enrichi.head(100), width="stretch")

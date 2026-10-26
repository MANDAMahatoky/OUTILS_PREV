import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 2 : Périmètre", layout="wide")
st.title("Étape 2 : Création du Data_Périmètre")

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def normaliser_mois(valeur) -> int:
    if pd.isna(valeur): return 1
    if isinstance(valeur, (int, float)): return int(valeur)
    mois_map = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
    texte = unicodedata.normalize("NFD", str(valeur)).encode("ascii", "ignore").decode("utf-8").lower().strip()
    return mois_map.get(texte, 1)

def extraire_article(nature_str: str) -> str:
    if pd.isna(nature_str): return ""
    match = re.match(r"^[^-]+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

def creer_cle_article(nom_article) -> str:
    if pd.isna(nom_article): return ""
    texte = unicodedata.normalize("NFD", str(nom_article)).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r'[^a-z0-9]', '', texte.lower())

# ==============================================================================
# LECTURE DES FICHIERS (Étape 1)
# ==============================================================================
def lire_referentiel(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    df_ref = pd.read_excel(flux, sheet_name="Ref actif")
    df_ref = df_ref.rename(columns={"Article": "article_original", "Positionnement": "positionnement", "Occasion": "occasion", "Contenance (hl)": "contenance_hl"})
    for col in ["article_original", "positionnement", "occasion", "contenance_hl"]:
        if col not in df_ref.columns: df_ref[col] = 0.0 if "contenance" in col else "Non renseigné"
    df_ref = df_ref[["article_original", "positionnement", "occasion", "contenance_hl"]].copy()
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    df_ref["cle_article"] = df_ref["article_original"].apply(creer_cle_article)
    return df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)

def lire_ventes(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    df_raw = pd.read_excel(flux, sheet_name=0, header=None)
    rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "hl"])}
    df = df_raw.rename(columns=rename).copy()
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["mois"] = df["mois"].apply(normaliser_mois)
    df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)
    
    masque_total = (
        df["segment"].astype(str).str.contains("total", case=False, na=False) | df["produit"].astype(str).str.contains("total", case=False, na=False) |
        df["agence"].astype(str).str.contains("total", case=False, na=False) | df["nature"].astype(str).str.contains("total", case=False, na=False) |
        df["nature"].isna()
    )
    df = df[~masque_total].copy()
    df["article_original"] = df["nature"].apply(extraire_article)
    df["agence"] = df["agence"].astype(str).str.strip()
    df["annee"] = df["annee"].fillna(2026).astype(int)
    df["mois"] = df["mois"].fillna(1).astype(int)
    df["cle_article"] = df["article_original"].apply(creer_cle_article)
    return df

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"], key="ventes")
with col2:
    fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"], key="ref")

if fichier_ventes is not None and fichier_ref is not None:
    # 1. Chargement et Fusion (Étape 1)
    with st.spinner("Chargement des données..."):
        df_ventes = lire_ventes(fichier_ventes.getvalue())
        df_ref = lire_referentiel(fichier_ref.getvalue())
        
        df_enrichi = df_ref.merge(df_ventes, on="cle_article", how="left")
        
        # Nettoyage post-fusion
        df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
        df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
        df_enrichi["hl"] = df_enrichi["hl"].fillna(0.0)
        df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
        df_enrichi["article"] = df_enrichi["article_original_x"]
        
        # Sélection des colonnes finales
        df_enrichi = df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "article", "positionnement", "occasion", "contenance_hl"]]

    # ==============================================================================
    # 2. FILTRAGE (Étape 2 - Data_Périmètre)
    # ==============================================================================
    st.sidebar.header("🔍 Filtres de Périmètre")
    
    # On prépare les listes d'options (en ignorant "Aucune vente" pour les agences)
    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    articles_dispo = sorted(df_enrichi["article"].unique())
    pos_dispo = sorted(df_enrichi["positionnement"].unique())
    occ_dispo = sorted(df_enrichi["occasion"].unique())

    # Création des filtres
    sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")
    sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
    sel_pos = st.sidebar.multiselect("📍 Positionnement", options=pos_dispo, placeholder="Tous")
    sel_occ = st.sidebar.multiselect("🎯 Occasion", options=occ_dispo, placeholder="Toutes")

    # Application des filtres (Logique du diagramme : Si vide -> Tout, Sinon -> Sous-ensemble)
    df_perimetre = df_enrichi.copy()

    if sel_agences:
        df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]
    if sel_articles:
        df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_pos:
        df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_pos)]
    if sel_occ:
        df_perimetre = df_perimetre[df_perimetre["occasion"].isin(sel_occ)]

    # ==============================================================================
    # 3. AFFICHAGE DES RÉSULTATS
    # ==============================================================================
    st.success("✅ Étape 1 & 2 complétées avec succès !")
    
    st.subheader("Impact du filtrage (Data_Périmètre)")
    kpi1, kpi2, kpi3 = st.columns(3)
    
    lignes_initiales = len(df_enrichi)
    lignes_filtrees = len(df_perimetre)
    
    kpi1.metric("DataFrame Enrichi (Base)", f"{lignes_initiales:,} lignes".replace(",", " "))
    kpi2.metric("Data_Périmètre (Filtré)", f"{lignes_filtrees:,} lignes".replace(",", " "))
    kpi3.metric("Volume Total Filtré", f"{df_perimetre['hl'].sum():,.0f} HL".replace(",", " "))
    
    if lignes_initiales == lignes_filtrees:
        st.info("ℹ️ Aucun filtre n'est appliqué. Le Data_Périmètre est identique au DataFrame Enrichi (Data = Tout).")
    else:
        st.info(f"ℹ️ Filtres appliqués : {lignes_initiales - lignes_filtrees:,} lignes exclues (Data = Sous-ensemble).".replace(",", " "))
    
    st.subheader("Aperçu du Data_Périmètre")
    st.dataframe(df_perimetre.head(100), width="stretch")

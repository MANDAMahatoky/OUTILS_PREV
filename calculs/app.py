import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 3 : Réalisé", layout="wide")
st.title("Étape 3 : Séparation du Réalisé et Calcul du Cumul")

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
# LECTURE DES FICHIERS
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
    with st.spinner("Chargement des données..."):
        df_ventes = lire_ventes(fichier_ventes.getvalue())
        df_ref = lire_referentiel(fichier_ref.getvalue())
        
        # Fusion (Étape 1)
        df_enrichi = df_ref.merge(df_ventes, on="cle_article", how="left")
        df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
        df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
        df_enrichi["hl"] = df_enrichi["hl"].fillna(0.0)
        df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
        df_enrichi["article"] = df_enrichi["article_original_x"]
        
        df_enrichi = df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "article", "positionnement", "occasion"]]

    # --- Paramètres de Cutoff (Étape 2 & 3) ---
    st.sidebar.header("⚙️ Paramètres S&OP")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtre de Périmètre")
    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    sel_agence = st.sidebar.multiselect("Agence", options=agences_dispo, placeholder="Toutes")

    # --- Séparation Réalisé / Prévision ---
    condition_realise = (df_enrichi["annee"] < annee_cloture) | ((df_enrichi["annee"] == annee_cloture) & (df_enrichi["mois"] <= mois_cloture))
    
    df_realise = df_enrichi[condition_realise].copy()
    df_prevision = df_enrichi[~condition_realise].copy()

    if sel_agence:
        df_realise = df_realise[df_realise["agence"].isin(sel_agence)]
        df_prevision = df_prevision[df_prevision["agence"].isin(sel_agence)]

    # --- Calcul du Réalisé Cumulé (Table_Réalisé) ---
    df_cumul_realise = df_realise.groupby(["annee", "mois", "agence", "article"])["hl"].sum().reset_index()
    
    # ==============================================================================
    # AFFICHAGE DES RÉSULTATS
    # ==============================================================================
    st.success(f"✅ Données séparées avec succès pour un Cutoff au {mois_cloture}/{annee_cloture}.")
    
    st.subheader("Résumé de l'Étape 3")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Volume Réalisé Total", f"{df_realise['hl'].sum():,.0f} HL")
    kpi2.metric(f"Volume Réalisé YTD ({annee_cloture})", f"{df_realise[df_realise['annee'] == annee_cloture]['hl'].sum():,.0f} HL")
    kpi3.metric("Volume Futur (Prévisions)", f"{df_prevision['hl'].sum():,.0f} HL")

    tab1, tab2 = st.tabs(["📊 Table_Réalisé (Cumulé)", "🔮 Données Futures (à projeter)"])
    
    with tab1:
        st.write("Voici la table aggrégée du réalisé. **L'affichage est arrondi à 0 décimale, exactement comme dans Excel.**")
        
        # FIX : Utilisation de st.column_config qui est beaucoup plus stable
        st.dataframe(
            df_cumul_realise,
            column_config={
                "hl": st.column_config.NumberColumn("Volume (HL)", format="%.0f")
            }
        )
        
    with tab2:
        st.dataframe(
            df_prevision,
            column_config={
                "hl": st.column_config.NumberColumn("Volume (HL)", format="%.0f")
            }
        )

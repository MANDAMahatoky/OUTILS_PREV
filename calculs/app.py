import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 1 : Données Brutes", layout="wide")
st.title("Étape 1 : Ingestion & Enrichissement")

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
    match = re.match(r"^\d+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

# FIX : Fonction pour créer une clé de jointure "blindée"
def creer_cle_article(nom_article) -> str:
    if pd.isna(nom_article): return ""
    # 1. Enlever les accents
    texte = unicodedata.normalize("NFD", str(nom_article)).encode("ascii", "ignore").decode("utf-8")
    # 2. Mettre en minuscules et enlever TOUT ce qui n'est pas une lettre ou un chiffre
    # (Supprime les espaces, les tirets, les points, etc.)
    texte = re.sub(r'[^a-z0-9]', '', texte.lower())
    return texte

# ==============================================================================
# LECTURE DES FICHIERS
# ==============================================================================
def lire_referentiel(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    df_ref = pd.read_excel(flux, sheet_name="Ref actif")
    
    df_ref = df_ref.rename(columns={
        "Article": "article_original", 
        "Positionnement": "positionnement",
        "Occasion": "occasion",
        "Contenance (hl)": "contenance_hl"
    })
    
    colonnes_voulues = ["article_original", "positionnement", "occasion", "contenance_hl"]
    for col in colonnes_voulues:
        if col not in df_ref.columns:
            df_ref[col] = 0.0 if "contenance" in col else "Non renseigné"
                
    df_ref = df_ref[colonnes_voulues].copy()
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    
    # On crée la clé de jointure
    df_ref["cle_article"] = df_ref["article_original"].apply(creer_cle_article)
    
    # On supprime les doublons sur la clé
    df_ref = df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)
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
        
        masque_total = (
            df["segment"].astype(str).str.contains("total", case=False, na=False) |
            df["produit"].astype(str).str.contains("total", case=False, na=False) |
            df["agence"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].isna()
        )
        df = df[~masque_total].copy()
        
        df["article_original"] = df["nature"].apply(extraire_article)
        df["agence"] = df["agence"].astype(str).str.strip()
        
        df["annee"] = df["annee"].fillna(2026).astype(int)
        df["mois"] = df["mois"].fillna(1).astype(int)
        
        # On crée la clé de jointure
        df["cle_article"] = df["article_original"].apply(creer_cle_article)
        
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
    with st.spinner("Lecture et fusion des données..."):
        df_ventes = lire_ventes(fichier_ventes.getvalue())
        df_ref = lire_referentiel(fichier_ref.getvalue())
        
        # FIX : On fait la jointure sur la clé blindée (cle_article)
        df_enrichi = df_ref.merge(df_ventes, on="cle_article", how="left")
        
        # Gestion des articles sans ventes
        df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
        df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
        df_enrichi["hl"] = df_enrichi["hl"].fillna(0.0)
        df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
        
        # On utilise l'article du référentiel comme nom officiel
        df_enrichi["article"] = df_enrichi["article_original_x"]
        
        # On nettoie les colonnes pour l'affichage
        df_enrichi = df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "article", "positionnement", "occasion", "contenance_hl"]]
        
    st.success("✅ Données prêtes !")
    
    # --- Vérifications ---
    st.subheader("Vérifications de base")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Lignes de ventes initiales", f"{len(df_ventes):,}".replace(",", " "))
    kpi2.metric("Lignes après fusion", f"{len(df_enrichi):,}".replace(",", " "))
    kpi3.metric("Articles uniques", df_enrichi["article"].nunique())
    kpi4.metric("Volume total (HL)", f"{df_enrichi['hl'].sum():,.0f}".replace(",", " "))
    
    if df_enrichi["article"].nunique() == len(df_ref):
        st.success(f"🎉 Parfait ! Les {len(df_ref)} articles du référentiel sont présents, et leurs ventes ont bien été récupérées.")
    else:
        st.warning(f"⚠️ Le tableau contient {df_enrichi['article'].nunique()} articles uniques.")
    
    # Diagnostic pour voir les articles SANS ventes
    articles_sans_ventes = df_enrichi[df_enrichi["agence"] == "Aucune vente"]["article"].unique()
    if len(articles_sans_ventes) > 0:
        st.info(f"ℹ️ Il y a {len(articles_sans_ventes)} articles dans votre référentiel qui n'ont eu **aucune vente** dans le fichier DATA_BRUT (ou dont le nom est vraiment trop différent).")
        with st.expander("🔍 Voir les articles sans ventes"):
            st.write(list(articles_sans_ventes))
    else:
        st.success("🔥 100% des articles du référentiel ont trouvé leurs ventes !")
            
    # --- Aperçu ---
    st.subheader("Aperçu du DataFrame enrichi")
    st.dataframe(df_enrichi.head(100), width="stretch")

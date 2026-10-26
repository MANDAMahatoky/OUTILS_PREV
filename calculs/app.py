import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 1 : Données Brutes", layout="wide")
st.title("Étape 1 : Ingestion & Enrichissement des Données")

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
    if pd.isna(nature_str): return "Non renseigné"
    match = re.match(r"^\d+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

# ==============================================================================
# LECTURE DES DEUX FICHIERS
# ==============================================================================
def lire_referentiel(contenu_excel: bytes) -> pd.DataFrame:
    """Lit le fichier Classeur2.xlsx et nettoie les colonnes."""
    flux = io.BytesIO(contenu_excel)
    df_ref = pd.read_excel(flux, sheet_name="Ref actif")
    
    # On garde uniquement les colonnes utiles
    colonnes_voulues = ["Article", "Positionnement", "Occasion", "Contenance (hl)"]
    
    # Vérifier que les colonnes existent (au cas où l'utilisateur change les noms)
    for col in colonnes_voulues:
        if col not in df_ref.columns:
            if col == "Contenance (hl)":
                df_ref["Contenance (hl)"] = 0.0
            else:
                df_ref[col] = "Non renseigné"
                
    df_ref = df_ref[colonnes_voulues].copy()
    df_ref = df_ref.rename(columns={"Article": "article", "Contenance (hl)": "contenance_hl"})
    
    # Nettoyage de l'article pour faciliter la jointure
    df_ref["article"] = df_ref["article"].astype(str).str.strip()
    return df_ref

def lire_ventes(contenu_excel: bytes) -> pd.DataFrame:
    """Lit le fichier DATA_BRUT.xlsx et extrait les données."""
    flux = io.BytesIO(contenu_excel)
    df_raw = pd.read_excel(flux, sheet_name=0, header=None)
    
    if detecter_format_pivote(df_raw):
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "hl"])}
        df = df_raw.rename(columns=rename).copy()
        
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
        df["mois"] = df["mois"].apply(normaliser_mois)
        df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)
        
        # Suppression des lignes "Total" (les vrais totaux du tableau, pas les articles)
        masque_total = (
            df["segment"].astype(str).str.contains("total", case=False, na=False) |
            df["produit"].astype(str).str.contains("total", case=False, na=False) |
            df["agence"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].astype(str).str.contains("total", case=False, na=False)
        )
        df = df[~masque_total].copy()
        
        # Extraction de l'article
        df["article"] = df["nature"].apply(extraire_article)
        df["agence"] = df["agence"].astype(str).str.strip()
        
        # Conservation des lignes avec NaN (remplacement par défaut pour ne rien perdre)
        df["annee"] = df["annee"].fillna(2026).astype(int)
        df["mois"] = df["mois"].fillna(1).astype(int)
        
        return df
    else:
        st.error("Format de fichier de ventes non reconnu.")
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
        # 1. Lecture
        df_ventes = lire_ventes(fichier_ventes.getvalue())
        df_ref = lire_referentiel(fichier_ref.getvalue())
        
        # 2. Fusion
        df_enrichi = df_ventes.merge(df_ref, on="article", how="left")
        
        # Remplissage des valeurs manquantes après jointure
        df_enrichi["positionnement"] = df_enrichi["positionnement"].fillna("Non renseigné")
        df_enrichi["occasion"] = df_enrichi["occasion"].fillna("Non renseigné")
        df_enrichi["contenance_hl"] = df_enrichi["contenance_hl"].fillna(0.0)
        
    st.success("✅ Données fusionnées avec succès !")
    
    # --- Vérifications ---
    st.subheader("Vérifications de base")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Lignes de ventes", len(df_ventes))
    kpi2.metric("Lignes après fusion", len(df_enrichi))
    kpi3.metric("Articles uniques", df_enrichi["article"].nunique())
    kpi4.metric("Volume total (HL)", f"{df_enrichi['hl'].sum():,.0f}")
    
    if len(df_ventes) == len(df_enrichi):
        st.success("🎉 Aucune ligne de vente n'a été perdue lors de la fusion.")
    else:
        st.error("⚠️ Attention : Des lignes ont été perdues ou dupliquées lors de la fusion.")
    
    # Diagnostic des articles non trouvés
    non_renseignes = df_enrichi[df_enrichi["positionnement"] == "Non renseigné"]
    if not non_renseignes.empty:
        st.warning(f"⚠️ {len(non_renseignes)} lignes n'ont pas trouvé leur correspondance dans le Référentiel (Classeur2).")
        articles_manquants = non_renseignes["article"].unique()
        st.write("🔍 **Articles non trouvés (Top 10) :**")
        st.write(articles_manquants[:10])
    else:
        st.success("🎉 100% des articles ont été trouvés dans le Référentiel !")
        
    # --- Aperçu ---
    st.subheader("Aperçu du DataFrame enrichi")
    st.dataframe(df_enrichi.head(100), width="stretch")

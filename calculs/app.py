import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 2 : Périmètre", layout="wide")
st.title("Étape 2 : Création du Data_Périmètre (Filtrage)")

# ==============================================================================
# RÉFÉRENTIEL (Simulé)
# ==============================================================================
def generer_catalogue_complet():
    data_raw = [
        ("Cristalline 100 cl PET", "PREMIUM", "IC"),
        ("Cristalline 200 cl PET", "PREMIUM", "FC"),
        ("Caprice Orange 33 cl CAN", "MILIEU", "IC"),
        ("Caprice Orange 100 cl VER", "MILIEU", "FC"),
        ("Gold Blonde 65 cl VER", "PREMIUM", "CU"),
        # (Liste raccourcie pour l'exemple, ajoutez le reste si besoin)
    ]
    return pd.DataFrame(data_raw, columns=["article", "positionnement", "occasion"])

CATALOGUE = generer_catalogue_complet()

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def normaliser_nom(nom: str) -> str:
    texte = unicodedata.normalize("NFD", str(nom)).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9_]+", "_", texte.strip().lower()).strip("_")

def normaliser_mois(valeur) -> int:
    if pd.isna(valeur): return 1
    if isinstance(valeur, (int, float)): return int(valeur)
    mois_map = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
    texte = unicodedata.normalize("NFD", str(valeur)).encode("ascii", "ignore").decode("utf-8").lower().strip()
    return mois_map.get(texte, 1)

def extraire_article(nature_str: str) -> str:
    match = re.match(r"^\d+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

# ==============================================================================
# ÉTAPE 1 : INGESTION
# ==============================================================================
def charger_et_enrichir(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    df_raw = pd.read_excel(flux, sheet_name=0, header=None)
    
    if detecter_format_pivote(df_raw):
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "hl"])}
        df = df_raw.rename(columns=rename).copy()
        
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
        df["mois"] = df["mois"].apply(normaliser_mois)
        df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)
        
        masque_total = (
            df["segment"].astype(str).str.contains("total", case=False, na=False) |
            df["produit"].astype(str).str.contains("total", case=False, na=False) |
            df["agence"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].astype(str).str.contains("total", case=False, na=False)
        )
        df = df[~masque_total].copy()
        
        df["article"] = df["nature"].apply(extraire_article)
        df["agence"] = df["agence"].astype(str).str.strip()
        
        df = df.dropna(subset=["annee", "mois"])
        df["annee"] = df["annee"].astype(int)
        df["mois"] = df["mois"].astype(int)
        
    else:
        df_raw = pd.read_excel(flux, sheet_name=0)
        df_raw.columns = [normaliser_nom(c) for c in df_raw.columns]
        df = df_raw.rename(columns={"volume": "hl", "quantite": "hl"}).copy()
        df["annee"] = pd.to_numeric(df.get("annee", 2026), errors="coerce").fillna(2026).astype(int)
        df["mois"] = df.get("mois", 1).apply(normaliser_mois)
        df["article"] = df.get("article", "Non renseigné").astype(str).str.strip()
        df["agence"] = df.get("agence", "Non renseigné").astype(str).str.strip()
        df["hl"] = pd.to_numeric(df.get("hl", 0.0), errors="coerce").fillna(0.0)

    # Nettoyage des articles "nan" ou vides
    df = df[df["article"].str.lower().isin(["nan", ""]) == False].copy()

    # Fusion avec le Référentiel
    df = df.merge(CATALOGUE, on="article", how="left")
    df["positionnement"] = df["positionnement"].fillna("Non renseigné")
    df["occasion"] = df["occasion"].fillna("Non renseigné")
    
    # Ajout de la région (simulée ici, à adapter avec votre vraie map)
    df["region"] = "Non renseigné" 
    
    return df

# ==============================================================================
# ÉTAPE 2 : FILTRAGE (PÉRIMÈTRE)
# ==============================================================================
st.sidebar.header("🔍 Filtres (Étape 2)")
fichier = st.sidebar.file_uploader("Fichier Excel (.xlsx)", type=["xlsx"])

if fichier is not None:
    # On charge les données de l'étape 1
    df_brut = charger_et_enrichir(fichier.getvalue())
    
    # --- Création des filtres dynamiques ---
    filtres = {}
    
    # 1. Filtre Article
    articles_dispo = sorted(df_brut["article"].dropna().unique().tolist())
    filtres["article"] = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
    
    # 2. Filtre Agence
    agences_dispo = sorted(df_brut["agence"].dropna().unique().tolist())
    filtres["agence"] = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")
    
    # 3. Filtre Positionnement
    pos_dispo = sorted(df_brut["positionnement"].dropna().unique().tolist())
    filtres["positionnement"] = st.sidebar.multiselect("📍 Positionnement", options=pos_dispo, placeholder="Tous")

    # --- Application des filtres (Data_Périmètre) ---
    df_perimetre = df_brut.copy()
    
    for col, selection in filtres.items():
        if selection: # Si le filtre n'est pas vide
            df_perimetre = df_perimetre[df_perimetre[col].isin(selection)]
            
    # --- Affichage des résultats ---
    st.success(f"✅ Données brutes : {len(df_brut)} lignes.")
    st.info(f"🎯 Data_Périmètre (filtré) : {len(df_perimetre)} lignes.")
    
    st.subheader("Aperçu du Data_Périmètre")
    st.dataframe(df_perimetre.head(50), width="stretch")
    
    # Diagnostics
    col1, col2, col3 = st.columns(3)
    col1.metric("Articles dans le périmètre", df_perimetre["article"].nunique())
    col2.metric("Agences dans le périmètre", df_perimetre["agence"].nunique())
    col3.metric("Volume dans le périmètre (HL)", f"{df_perimetre['hl'].sum():,.0f}")

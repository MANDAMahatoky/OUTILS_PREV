import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étapes 1, 2 & 3 : S&OP", layout="wide")
st.title("Étapes 1, 2 & 3 : Données, Périmètre et Réalisé")

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

# FIX : Application exacte de votre arborescence de segments
def attribuer_segment(article: str) -> str:
    art_lower = str(article).lower()
    
    # 5-ALCOMIX (Booster et alcoomix divers)
    if "booster" in art_lower or "alcoomix" in art_lower:
        return "5-ALCOMIX"
    
    # 2-BG (Caprice, Tonic, World Cola, etc.)
    elif any(x in art_lower for x in ["caprice", "tonic", "world cola", "d jino", "youzou", "coca", "fanta", "sprite"]):
        return "2-BG"
    
    # 1-BIERES
    elif any(x in art_lower for x in ["beaufort", "fresh", "thb", "gold", "queen", "skol", "castel", "libertalia"]):
        return "1-BIERES"
    
    # 4-EAUX
    elif any(x in art_lower for x in ["cristal", "cristalline", "eau vive", "eau"]):
        return "4-EAUX"
    
    # 3-ENERGY
    elif any(x in art_lower for x in ["xxl", "fosa"]):
        return "3-ENERGY"
    
    # 4-JUS
    elif any(x in art_lower for x in ["judor", "jus"]):
        return "4-JUS"
    
    # 7-VIN
    elif any(x in art_lower for x in ["vin"]):
        return "7-VIN"
    
    # 6-NEGOCE
    elif any(x in art_lower for x in ["negoce"]):
        return "6-NEGOCE"
        
    else:
        return "AUTRE / INCONNU"

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
    
    # --------------------------------------------------------------------------
    # ÉTAPE 1 : CHARGEMENT & ENRICHISSEMENT
    # --------------------------------------------------------------------------
    with st.spinner("Étape 1 : Chargement..."):
        df_ventes = lire_ventes(fichier_ventes.getvalue())
        df_ref = lire_referentiel(fichier_ref.getvalue())
        
        df_enrichi = df_ref.merge(df_ventes, on="cle_article", how="left")
        
        # Remplissage des vides
        df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
        df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
        df_enrichi["hl"] = df_enrichi["hl"].fillna(0.0)
        df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
        df_enrichi["article"] = df_enrichi["article_original_x"]
        
        # Application de la règle métier stricte
        df_enrichi["segment"] = df_enrichi["article"].apply(attribuer_segment)
        
        df_enrichi = df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "article", "positionnement", "occasion"]]

    # --------------------------------------------------------------------------
    # ÉTAPE 2 : PÉRIMÈTRE (Filtrage en cascade)
    # --------------------------------------------------------------------------
    st.sidebar.header("🔍 Étape 2 : Périmètre")
    
    # 1. Filtre Segment
    segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
    sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
    
    # 2. Filtre Article (en cascade)
    df_temp_pour_articles = df_enrichi.copy()
    if sel_segments:
        df_temp_pour_articles = df_temp_pour_articles[df_temp_pour_articles["segment"].isin(sel_segments)]
    articles_dispo = sorted(df_temp_pour_articles["article"].unique())
    sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
    
    # 3. Autres filtres
    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")
    
    pos_dispo = sorted(df_enrichi["positionnement"].unique())
    sel_pos = st.sidebar.multiselect("📍 Positionnement", options=pos_dispo, placeholder="Tous")
    
    occ_dispo = sorted(df_enrichi["occasion"].unique())
    sel_occ = st.sidebar.multiselect("🎯 Occasion", options=occ_dispo, placeholder="Toutes")

    # --- Application finale des filtres (Data_Périmètre) ---
    df_perimetre = df_enrichi.copy()
    if sel_segments:
        df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles:
        df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences:
        df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]
    if sel_pos:
        df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_pos)]
    if sel_occ:
        df_perimetre = df_perimetre[df_perimetre["occasion"].isin(sel_occ)]

    # --------------------------------------------------------------------------
    # ÉTAPE 3 : RÉALISÉ CUMULÉ
    # --------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Étape 3 : Cutoff S&OP")
    
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    # Séparation Réalisé / Prévision
    condition_realise = (df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cloture))
    df_realise = df_perimetre[condition_realise].copy()
    df_prevision = df_perimetre[~condition_realise].copy()

    # Table_Réalisé
    df_cumul_realise = df_realise.groupby(["annee", "mois", "agence", "article"])["hl"].sum().reset_index()

    # --------------------------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------------------------
    st.success("✅ Étapes 1, 2 et 3 complétées !")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Data Enrichi (Étape 1)", f"{len(df_enrichi):,.0f} lignes".replace(",", " "))
    col_b.metric("Data Périmètre (Étape 2)", f"{len(df_perimetre):,.0f} lignes".replace(",", " "))
    col_c.metric("Volume Réalisé (Étape 3)", f"{df_realise['hl'].sum():,.0f} HL".replace(",", " "))

    tab_etape1, tab_etape2, tab_etape3 = st.tabs(["📋 Étape 1 (Data Enrichi)", "📊 Étape 2 (Data_Périmètre)", "📈 Étape 3 (Table_Réalisé)"])
    
    with tab_etape1:
        st.write("Voici les 69 articles avec leur Segment (selon votre arborescence exacte) :")
        st.dataframe(df_enrichi[["article", "segment", "positionnement"]].drop_duplicates().head(100), use_container_width=True)
        
    with tab_etape2:
        st.write("Voici les données après application de vos filtres en cascade (Étape 2).")
        st.dataframe(df_perimetre.head(100), use_container_width=True)
        
    with tab_etape3:
        st.write(f"Voici le cumul du réalisé jusqu'à {mois_cloture}/{annee_cloture} (Étape 3).")
        st.dataframe(
            df_cumul_realise.head(100),
            column_config={
                "hl": st.column_config.NumberColumn("Volume Réalisé (HL)", format="%.0f")
            },
            use_container_width=True
        )

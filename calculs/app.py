import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étapes 1 à 4 : S&OP", layout="wide")
st.title("Étapes 1 à 4 : Données, Périmètre, Réalisé & SARR")

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def normaliser_mois(valeur) -> int:
    if pd.isna(valeur): return 1
    if isinstance(valeur, (int, float)): return int(valeur)
    mois_map = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
    texte = unicodedata.normalize("NFD", str(valeur)).encode("ascii", "ignore").decode("utf-8").lower().strip()
    return mois_map.get(texte, 1)

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

# ==============================================================================
# ÉTAPE 1 : CHARGEMENT ET ENRICHISSEMENT (MIS EN CACHE)
# ==============================================================================
@st.cache_data(show_spinner="Chargement des fichiers et fusion...")
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes) -> pd.DataFrame:
    # 1. Lecture du Référentiel
    flux_ref = io.BytesIO(ref_bytes)
    df_ref = pd.read_excel(flux_ref, sheet_name="Ref actif")
    df_ref = df_ref.rename(columns={"Article": "article_original", "Positionnement": "positionnement", "Occasion": "occasion", "Contenance (hl)": "contenance_hl"})
    
    for col in ["article_original", "positionnement", "occasion", "contenance_hl"]:
        if col not in df_ref.columns: df_ref[col] = 0.0 if "contenance" in col else "Non renseigné"
        
    df_ref = df_ref[["article_original", "positionnement", "occasion", "contenance_hl"]].copy()
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    df_ref["cle_article"] = df_ref["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    df_ref = df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)

    # 2. Lecture des Ventes
    flux_ventes = io.BytesIO(ventes_bytes)
    df_raw = pd.read_excel(flux_ventes, sheet_name=0, header=None)
    
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
        
        df["article_original"] = df["nature"].astype(str).str.replace(r'^[^-]+-', '', regex=True).str.strip()
        df["agence"] = df["agence"].astype(str).str.strip()
        df["annee"] = df["annee"].fillna(2026).astype(int)
        df["mois"] = df["mois"].fillna(1).astype(int)
        df["cle_article"] = df["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    else:
        return pd.DataFrame()

    # 3. Fusion
    df_enrichi = df_ref.merge(df, on="cle_article", how="left")
    
    # 4. Remplissage des vides
    df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
    df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
    df_enrichi["hl"] = df_enrichi["hl"].fillna(0.0)
    df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
    df_enrichi["article"] = df_enrichi["article_original_x"]
    
    # 5. Attribution du Segment
    conditions = [
        df_enrichi["article"].str.contains("booster|alcoomix", case=False, na=False),
        df_enrichi["article"].str.contains("caprice|tonic|world cola|d jino|youzou|coca|fanta|sprite", case=False, na=False),
        df_enrichi["article"].str.contains("beaufort|fresh|thb|gold|queen|skol|castel|libertalia", case=False, na=False),
        df_enrichi["article"].str.contains("cristal|cristalline|eau vive|eau", case=False, na=False),
        df_enrichi["article"].str.contains("xxl|fosa", case=False, na=False),
        df_enrichi["article"].str.contains("judor|jus", case=False, na=False),
        df_enrichi["article"].str.contains("vin", case=False, na=False),
        df_enrichi["article"].str.contains("negoce", case=False, na=False)
    ]
    choices = ["5-ALCOMIX", "2-BG", "1-BIERES", "4-EAUX", "3-ENERGY", "4-JUS", "7-VIN", "6-NEGOCE"]
    df_enrichi["segment"] = np.select(conditions, choices, default="AUTRE / INCONNU")
    
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "article", "positionnement", "occasion"]]

# ==============================================================================
# ÉTAPE 4 : CALCUL DES INDICES ET DU SARR (MIS EN CACHE)
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et du SARR...")
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cloture: int):
    # On isole le réalisé (strictement supérieur à 0 pour ne pas fausser les moyennes avec les articles non vendus)
    condition_realise = (df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cloture))
    df_realise = df_perimetre[condition_realise & (df_perimetre["hl"] > 0)].copy()

    if df_realise.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 1. Nombre d'années par (Agence, Article)
    nb_annees = df_realise.groupby(['agence', 'article'])['annee'].nunique().reset_index().rename(columns={'annee': 'nb_annees'})

    # 2. Moy_Mois = SUM(Vol_Mois) / Nb_Annees
    vol_mois = df_realise.groupby(['agence', 'article', 'mois'])['hl'].sum().reset_index()
    moy_mois = vol_mois.merge(nb_annees, on=['agence', 'article'])
    moy_mois['Moy_Mois'] = moy_mois['hl'] / moy_mois['nb_annees']

    # 3. Moy_Ann = SUM(Vol_Total) / (Nb_Annees * 12)
    vol_total = df_realise.groupby(['agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'vol_total'})
    moy_ann = vol_total.merge(nb_annees, on=['agence', 'article'])
    moy_ann['Moy_Ann'] = moy_ann['vol_total'] / (moy_ann['nb_annees'] * 12)

    # 4. Calcul de l'Indice
    indices = moy_mois.merge(moy_ann[['agence', 'article', 'Moy_Ann']], on=['agence', 'article'])
    indices['Indice'] = indices['Moy_Mois'] / indices['Moy_Ann'].replace(0, np.nan)
    indices['Indice'] = indices['Indice'].fillna(1.0) # Sécurité si Moy_Ann = 0

    table_indices = indices[['agence', 'article', 'mois', 'Indice']]

    # 5. Calcul du SARR
    # On rattache l'indice à tout le df_perimetre (pour avoir aussi le SARR sur le réalisé)
    df_sarr = df_perimetre.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    return table_indices, df_sarr

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"], key="ventes")
with col2:
    fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"], key="ref")

if fichier_ventes is not None and fichier_ref is not None:
    
    # Étape 1
    df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue())

    # Étape 2
    st.sidebar.header("🔍 Étape 2 : Périmètre")
    segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
    
    if 'previous_segments' not in st.session_state:
        st.session_state.previous_segments = []
        
    sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
    
    if sel_segments != st.session_state.previous_segments:
        st.session_state.sel_articles = []
        st.session_state.previous_segments = sel_segments

    df_temp = df_enrichi.copy()
    if sel_segments:
        df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
    
    articles_dispo = sorted(df_temp["article"].unique())
    sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous", key="sel_articles")
    
    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")
    
    df_perimetre = df_enrichi.copy()
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    # Étape 3 & 4
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Étape 3 & 4 : Cutoff & SARR")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    # Appel du moteur (Étape 4)
    table_indices, df_sarr = calculer_indices_et_sarr(df_perimetre, annee_cloture, mois_cloture)

    condition_realise = (df_sarr["annee"] < annee_cloture) | ((df_sarr["annee"] == annee_cloture) & (df_sarr["mois"] <= mois_cloture))
    df_realise = df_sarr[condition_realise].copy()
    
    # --------------------------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------------------------
    st.success("✅ Étapes 1 à 4 complétées !")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Data Périmètre", f"{len(df_perimetre):,.0f} lignes".replace(",", " "))
    col_b.metric("Volume Réalisé", f"{df_realise['hl'].sum():,.0f} HL".replace(",", " "))
    col_c.metric("Nombre d'indices calculés", f"{len(table_indices):,.0f}")

    tab_etape2, tab_etape3, tab_etape4 = st.tabs(["📊 Étape 2 (Data_Périmètre)", "📈 Étape 3 (Table_Réalisé)", "🧮 Étape 4 (Indices & SARR)"])
    
    with tab_etape2:
        st.dataframe(df_perimetre.head(100), use_container_width=True)
        
    with tab_etape3:
        st.write(f"Voici le cumul du réalisé jusqu'à {mois_cloture}/{annee_cloture} (Étape 3).")
        df_cumul = df_realise.groupby(["annee", "mois", "agence", "article"])["hl"].sum().reset_index()
        st.dataframe(
            df_cumul.head(100),
            column_config={"hl": st.column_config.NumberColumn("Volume Réalisé (HL)", format="%.0f")},
            use_container_width=True
        )

    with tab_etape4:
        st.write("Voici les tables calculées (Étape 4).")
        st.markdown("#### Table des Indices Saisonniers")
        st.write("L'indice représente le poids du mois par rapport à la moyenne annuelle (1.0 = moyenne).")
        
        # Affichage d'un extrait des indices
        pivot_indices = table_indices.pivot_table(index="article", columns="mois", values="Indice", aggfunc="mean").fillna(1.0)
        st.dataframe(pivot_indices.style.format("{:.2f}"), use_container_width=True)

        st.markdown("#### Table SARR")
        st.write("Le SARR est le volume lissé (désaisonnalisé).")
        st.dataframe(
            df_sarr[["annee", "mois", "agence", "article", "hl", "Indice", "SARR"]].head(100),
            column_config={
                "hl": st.column_config.NumberColumn("Volume (HL)", format="%.0f"),
                "Indice": st.column_config.NumberColumn("Indice", format="%.2f"),
                "SARR": st.column_config.NumberColumn("SARR (HL)", format="%.0f")
            },
            use_container_width=True
        )

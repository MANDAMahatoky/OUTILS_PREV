import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 4 : Indices & SARR", layout="wide")
st.title("Étape 4 : Calcul des Indices et du SARR")

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
MOIS_NOMS = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

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
# ÉTAPE 1 : CHARGEMENT ET ENRICHISSEMENT
# ==============================================================================
@st.cache_data(show_spinner="Chargement des données...")
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes) -> pd.DataFrame:
    flux_ref = io.BytesIO(ref_bytes)
    df_ref = pd.read_excel(flux_ref, sheet_name="Ref actif")
    df_ref = df_ref.rename(columns={"Article": "article_original", "Positionnement": "positionnement", "Occasion": "occasion", "Contenance (hl)": "contenance_hl", "Contenance (Cl)": "contenance_cl"})
    for col in ["article_original", "positionnement", "occasion", "contenance_hl", "contenance_cl"]:
        if col not in df_ref.columns: df_ref[col] = 0.0 if "contenance" in col else "Non renseigné"
    df_ref = df_ref[["article_original", "positionnement", "occasion", "contenance_hl", "contenance_cl"]].copy()
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    df_ref["cle_article"] = df_ref["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    df_ref = df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)

    flux_ventes = io.BytesIO(ventes_bytes)
    df_raw = pd.read_excel(flux_ventes, sheet_name=0, header=None)
    
    if detecter_format_pivote(df_raw):
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
        df["article_original"] = df["nature"].astype(str).str.replace(r'^[^-]+-', '', regex=True).str.strip()
        df["agence"] = df["agence"].astype(str).str.strip()
        df["annee"] = df["annee"].fillna(2026).astype(int)
        df["mois"] = df["mois"].fillna(1).astype(int)
        df["cle_article"] = df["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    else:
        return pd.DataFrame()

    df_enrichi = df_ref.merge(df, on="cle_article", how="left")
    df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
    df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
    df_enrichi["hl"] = df_enrichi["hl"].fillna(0.0)
    df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
    df_enrichi["article"] = df_enrichi["article_original_x"]
    
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
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "hl", "article", "positionnement", "occasion"]]

# ==============================================================================
# ÉTAPE 4 : CALCUL DES INDICES ET DU SARR
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et projection...")
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cloture: int, lisser_indices: bool):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame()

    # 1. Calcul des indices sur les années complètes
    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    if df_hist.empty: df_hist = df_realise.copy()
        
    grille_hist = pd.MultiIndex.from_product([df_hist['agence'].unique(), df_hist['article'].unique(), df_hist['annee'].unique(), range(1, 13)], names=['agence', 'article', 'annee', 'mois']).to_frame(index=False)
    df_hist_grille = grille_hist.merge(df_hist, on=['agence', 'article', 'annee', 'mois'], how='left')
    df_hist_grille['hl'] = df_hist_grille['hl'].fillna(0.0)
    
    nb_annees = df_hist_grille.groupby(['agence', 'article'])['annee'].nunique().reset_index().rename(columns={'annee': 'nb_annees'})
    vol_mois = df_hist_grille.groupby(['agence', 'article', 'mois'])['hl'].sum().reset_index()
    moy_mois = vol_mois.merge(nb_annees, on=['agence', 'article'])
    moy_mois['Moy_Mois'] = moy_mois['hl'] / moy_mois['nb_annees']
    
    vol_total = df_hist_grille.groupby(['agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'vol_total'})
    moy_ann = vol_total.merge(nb_annees, on=['agence', 'article'])
    moy_ann['Moy_Ann'] = moy_ann['vol_total'] / (moy_ann['nb_annees'] * 12)

    indices = moy_mois.merge(moy_ann[['agence', 'article', 'Moy_Ann']], on=['agence', 'article'])
    indices['Indice'] = indices['Moy_Mois'] / indices['Moy_Ann'].replace(0, np.nan)
    
    # FIX : Lissage des indices si l'option est cochée
    if lisser_indices:
        # Si l'indice est 0 (mois sans vente), on le remplace par 1.0
        indices['Indice'] = indices['Indice'].replace(0, 1.0)
    
    indices['Indice'] = indices['Indice'].fillna(1.0)
    table_indices = indices[['agence', 'article', 'mois', 'Indice']]

    # 2. Projection des mois manquants
    df_ytd = df_realise[df_realise["annee"] == annee_cloture].copy()
    df_projete = df_ytd.copy()
    
    ytd_totaux = df_ytd.groupby(['agence', 'article']).agg(
        vol_ytd=('hl', 'sum'), segment=('segment', 'first'), produit=('produit', 'first'), 
        positionnement=('positionnement', 'first'), occasion=('occasion', 'first')
    ).reset_index()
    
    for _, row in ytd_totaux.iterrows():
        ag, art = row['agence'], row['article']
        coefs_ecoules = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] <= mois_cloture)]['Indice'].sum()
        if coefs_ecoules == 0: coefs_ecoules = mois_cloture
        
        vol_annuel_proj = (row['vol_ytd'] / coefs_ecoules) * 12
        
        for m in range(mois_cloture + 1, 13):
            coef_data = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]
            coef_mois = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
            vol_projete = (vol_annuel_proj / 12) * coef_mois
            
            df_projete = pd.concat([df_projete, pd.DataFrame([{
                'annee': annee_cloture, 'mois': m, 'segment': row['segment'], 'produit': row['produit'], 
                'agence': ag, 'hl': vol_projete, 'article': art, 'positionnement': row['positionnement'], 'occasion': row['occasion']
            }])], ignore_index=True)
    
    df_final = pd.concat([df_realise, df_projete], ignore_index=True).drop_duplicates(subset=['annee', 'mois', 'agence', 'article'])
    df_sarr = df_final.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)
    
    return table_indices, df_sarr

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
with col2:
    fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"])

if fichier_ventes is not None and fichier_ref is not None:
    df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue())

    # --- PÉRIMÈTRE ---
    st.sidebar.header("🔍 Filtres")
    segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
    sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
    
    df_temp = df_enrichi.copy()
    if sel_segments: df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
    articles_dispo = sorted(df_temp["article"].unique())
    sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
    
    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")

    df_perimetre = df_enrichi.copy()
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    # --- CUTOFF & OPTIONS ---
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Cutoff & Options")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
    
    # Option de lissage
    lisser_indices = st.sidebar.checkbox("Lisser les coefficients à 0 (remplacer par 1.0)", value=True, help="Si un mois n'a pas eu de vente dans l'historique, mettre un indice de 1.0 au lieu de 0.0.")

    # --- CALCULS ---
    table_indices, df_sarr = calculer_indices_et_sarr(df_perimetre, annee_cloture, mois_cloture, lisser_indices)

    # --- AFFICHAGE ---
    st.success("✅ Étape 4 complétée : Indices et SARR générés.")
    
    tab_indices, tab_sarr = st.tabs(["📊 Table des Indices (Coefficients)", "📈 Table du SARR"])

    with tab_indices:
        st.subheader("Coefficients Saisonniers (Indices)")
        if not table_indices.empty:
            pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
            # Renommer les colonnes pour l'affichage
            pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
            st.dataframe(pivot_indices.style.format("{:.2f}"), use_container_width=True)
        else:
            st.info("Aucun indice calculé.")

    with tab_sarr:
        st.subheader("Table du SARR (Volume / Indice)")
        if not df_sarr.empty:
            st.dataframe(
                df_sarr[["annee", "mois", "agence", "article", "hl", "Indice", "SARR"]].sort_values(["annee", "mois", "agence", "article"]),
                column_config={
                    "hl": st.column_config.NumberColumn("Volume (HL)", format="%.2f"),
                    "Indice": st.column_config.NumberColumn("Indice", format="%.2f"),
                    "SARR": st.column_config.NumberColumn("SARR (HL)", format="%.2f")
                },
                use_container_width=True
            )
        else:
            st.info("Aucune donnée SARR.")

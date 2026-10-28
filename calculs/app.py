import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import math

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision : Étapes 1 à 4 et 5.1 / 5.2")

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
MOIS_NOMS = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

def excel_round(val, decimals=1):
    # Reproduit l'arrondi Excel (0.85 devient 0.9 et pas 0.8)
    if pd.isna(val): return val
    factor = 10 ** decimals
    return math.floor(val * factor + 0.5) / factor

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
    df_enrichi["contenance_cl"] = pd.to_numeric(df_enrichi["contenance_cl"], errors="coerce").fillna(100.0)
    
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
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "hl", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# ÉTAPE 4 : CALCUL DES INDICES ET DU SARR
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et du SARR...")
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, fenetre_histo: str, methode_coef: str):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame()

    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    if df_hist.empty: df_hist = df_realise.copy()

    annee_max = annee_cloture - 1
    if fenetre_histo == "3 dernières années": annee_min = annee_max - 2
    elif fenetre_histo == "2 dernières années": annee_min = annee_max - 1
    else: annee_min = df_hist['annee'].min()
    df_hist = df_hist[df_hist['annee'] >= annee_min].copy()

    # Filtre années complètes (12 mois)
    mois_par_annee = df_hist.groupby(['agence', 'article', 'annee'])['mois'].nunique().reset_index()
    annees_completes = mois_par_annee[mois_par_annee['mois'] == 12][['agence', 'article', 'annee']]
    df_hist_complet = df_hist.merge(annees_completes, on=['agence', 'article', 'annee'], how='inner')
    if df_hist_complet.empty: df_hist_complet = df_hist.copy()

    vols = df_hist_complet.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols_annuels = vols.sum(axis=1)
    
    if methode_coef == "Moyenne des Ratios":
        ratios = vols.div(vols_annuels / 12.0, axis=0).replace([np.inf, -np.inf], np.nan)
        indices = ratios.groupby(['agence', 'article']).mean().fillna(1.0)
    else:
        # Méthode Ratio des Sommes (Formule Excel)
        vols_mois_cumules = vols.groupby(['agence', 'article']).sum()
        vols_annuels_cumules = vols_annuels.groupby(['agence', 'article']).sum()
        indices = vols_mois_cumules.div(vols_annuels_cumules / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    # On garde la précision maximale pour le calcul
    table_indices = indices.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')

    # On calcule le SARR avec la précision maximale
    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)
    
    # Pour l'affichage, on ajoute une colonne arrondie comme Excel
    table_indices['Indice_Aff'] = table_indices['Indice'].apply(lambda x: excel_round(x, 1))
    
    return table_indices, df_sarr

# ==============================================================================
# ÉTAPES 5.1 & 5.2 : MOMENTUM ET BASE
# ==============================================================================
@st.cache_data(show_spinner="Calcul du Momentum et de la Base...")
def calculer_momentum_et_base(df_sarr: pd.DataFrame):
    df_sarr_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    
    resultats_5_1_5_2 = []
    
    for (ag, art), group in df_sarr_sorted.groupby(['agence', 'article']):
        # Récupération M-1, M-2, M-3
        ligne_m1 = group[group['rang'] == 1]
        ligne_m2 = group[group['rang'] == 2]
        ligne_m3 = group[group['rang'] == 3]
        
        if not ligne_m1.empty and not ligne_m2.empty:
            sarr_m1 = ligne_m1['SARR_HL'].values[0]
            sarr_m2 = ligne_m2['SARR_HL'].values[0]
            sarr_m3 = ligne_m3['SARR_HL'].values[0] if not ligne_m3.empty else 0
            
            # 5.1 Momentum : SARR(M-1) - SARR(M-2)
            momentum = sarr_m1 - sarr_m2
            
            # 5.2 Base : MAX( SARR M-1, MOYENNE(SARR M-1, M-2, M-3) )
            moyenne_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
            base = max(sarr_m1, moyenne_3_mois)
        else:
            sarr_m1 = sarr_m2 = sarr_m3 = 0
            momentum = 0
            base = 0
            
        resultats_5_1_5_2.append({
            "agence": ag, "article": art, 
            "SARR M-1": sarr_m1,
            "SARR M-2": sarr_m2,
            "SARR M-3": sarr_m3,
            "Momentum_HL": momentum,
            "Moyenne 3 Mois": np.mean([sarr_m1, sarr_m2, sarr_m3]),
            "Base_HL": base
        })
        
    return pd.DataFrame(resultats_5_1_5_2)

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

    # --- PÉRIMÈTRE (Filtres) ---
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
    mois_cutoff = st.sidebar.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=9, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
    
    # PAR DÉFAUT : 2 DERNIÈRES ANNÉES ET RATIO DES SOMMES (POUR COLLER A EXCEL)
    fenetre_histo = st.sidebar.radio("Période pour les Coefs", options=["2 dernières années", "3 dernières années", "Tout l'historique"], index=0)
    methode_coef = st.sidebar.radio("Méthode de calcul", options=["Ratio des Sommes", "Moyenne des Ratios"], index=0)
    
    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["HL", "Cols"], index=0)

    # --- CALCULS ---
    table_indices, df_sarr = calculer_indices_et_sarr(df_perimetre, annee_cloture, fenetre_histo, methode_coef)
    
    if df_sarr.empty:
        st.warning("⚠️ Impossible de calculer le SARR (manque de données).")
        st.stop()

    df_5_1_5_2 = calculer_momentum_et_base(df_sarr)

    st.success(f"✅ Modèle calculé avec succès.")
    
    # ONGLETS
    tab_indices, tab_sarr, tab_momentum, tab_base = st.tabs([
        "4. Table des Indices", 
        "4. Table du SARR", 
        "5.1 Momentum", 
        "5.2 Base"
    ])

    with tab_indices:
        st.subheader("Coefficients Saisonniers (Indices)")
        st.write("💡 L'affichage est arrondi à 1 décimale comme dans Excel, mais le calcul du SARR utilise la valeur exacte non arrondie.")
        
        # ICI ON AFFICHE LA COLONNE ARRONDIE POUR L'ECRAN
        pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice_Aff', aggfunc='first').fillna(1.0)
        pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
        st.dataframe(pivot_indices.style.format("{:.1f}"), use_container_width=True)

    with tab_sarr:
        st.subheader(f"Table du SARR (en {unite_affichage})")
        df_sarr_display = df_sarr[["annee", "mois", "agence", "article", "hl", "Indice", "SARR_HL"]].sort_values(["annee", "mois", "agence", "article"])
        st.dataframe(
            df_sarr_display,
            column_config={
                "hl": st.column_config.NumberColumn("Volume (HL)", format="%.2f"),
                "Indice": st.column_config.NumberColumn("Coef (précis)", format="%.4f"), # On montre la précision ici
                "SARR_HL": st.column_config.NumberColumn("SARR (HL)", format="%.2f")
            },
            use_container_width=True, height=400
        )

    with tab_momentum:
        st.subheader("5.1 : Table du Momentum (M-1) - (M-2)")
        if unite_affichage == "Cols":
            df_5_1_5_2["Momentum_Aff"] = df_5_1_5_2["Momentum_HL"] * 100
            st.dataframe(
                df_5_1_5_2[["agence", "article", "SARR M-1", "SARR M-2", "Momentum_Aff"]],
                column_config={
                    "SARR M-1": st.column_config.NumberColumn("SARR M-1 (HL)", format="%.2f"),
                    "SARR M-2": st.column_config.NumberColumn("SARR M-2 (HL)", format="%.2f"),
                    "Momentum_Aff": st.column_config.NumberColumn("Momentum (Cols)", format="%.2f"),
                },
                use_container_width=True
            )
        else:
            st.dataframe(
                df_5_1_5_2[["agence", "article", "SARR M-1", "SARR M-2", "Momentum_HL"]],
                column_config={
                    "SARR M-1": st.column_config.NumberColumn("SARR M-1 (HL)", format="%.2f"),
                    "SARR M-2": st.column_config.NumberColumn("SARR M-2 (HL)", format="%.2f"),
                    "Momentum_HL": st.column_config.NumberColumn("Momentum (HL)", format="%.2f"),
                },
                use_container_width=True
            )

    with tab_base:
        st.subheader("5.2 : Table de la Base")
        st.write("Formule : `MAX( SARR M-1, MOYENNE(SARR M-1, M-2, M-3) )`.")
        
        if unite_affichage == "Cols":
            df_5_1_5_2["Base_Aff"] = df_5_1_5_2["Base_HL"] * 100
            st.dataframe(
                df_5_1_5_2[["agence", "article", "SARR M-1", "SARR M-2", "SARR M-3", "Moyenne 3 Mois", "Base_Aff"]],
                column_config={
                    "SARR M-1": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                    "SARR M-2": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                    "SARR M-3": st.column_config.NumberColumn("SARR M-3", format="%.2f"),
                    "Moyenne 3 Mois": st.column_config.NumberColumn("Moyenne M-1/M-2/M-3", format="%.2f"),
                    "Base_Aff": st.column_config.NumberColumn("Base (Cols)", format="%.2f"),
                },
                use_container_width=True
            )
        else:
            st.dataframe(
                df_5_1_5_2[["agence", "article", "SARR M-1", "SARR M-2", "SARR M-3", "Moyenne 3 Mois", "Base_HL"]],
                column_config={
                    "SARR M-1": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                    "SARR M-2": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                    "SARR M-3": st.column_config.NumberColumn("SARR M-3", format="%.2f"),
                    "Moyenne 3 Mois": st.column_config.NumberColumn("Moyenne M-1/M-2/M-3", format="%.2f"),
                    "Base_HL": st.column_config.NumberColumn("Base (HL)", format="%.2f"),
                },
                use_container_width=True
            )

import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Validation Momentum (5.1)", layout="wide")
st.title("Étape 5.1 : Validation du Momentum (Dynamique)")

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
# ÉTAPES 3, 4 ET 5.1 : CALCUL DU MOMENTUM
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et du Momentum...")
def calculer_momentum(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, fenetre_histo: str, methode_coef: str):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- ÉTAPE 4 : INDICES ET SARR ---
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
        vols_mois_cumules = vols.groupby(['agence', 'article']).sum()
        vols_annuels_cumules = vols_annuels.groupby(['agence', 'article']).sum()
        indices = vols_mois_cumules.div(vols_annuels_cumules / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    table_indices = indices.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')

    # Table de debug pour voir les ratios annuels (utile pour comparer avec Excel)
    debug_ratios = ratios.reset_index().melt(id_vars=['agence', 'article', 'annee'], var_name='mois', value_name='Ratio_Annuel')

    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    # --- ÉTAPE 5.1 : MOMENTUM = SARR(M-1) - SARR(M-2) ---
    df_sarr_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    
    resultats_momentum = []
    
    for (ag, art), group in df_sarr_sorted.groupby(['agence', 'article']):
        ligne_m1 = group[group['rang'] == 1]
        ligne_m2 = group[group['rang'] == 2]
        
        if not ligne_m1.empty and not ligne_m2.empty:
            hl_m1 = ligne_m1['hl'].values[0]
            coef_m1 = ligne_m1['Indice'].values[0]
            sarr_m1 = ligne_m1['SARR_HL'].values[0]
            
            hl_m2 = ligne_m2['hl'].values[0]
            coef_m2 = ligne_m2['Indice'].values[0]
            sarr_m2 = ligne_m2['SARR_HL'].values[0]
        else:
            hl_m1 = coef_m1 = sarr_m1 = 0
            hl_m2 = coef_m2 = sarr_m2 = 0
            
        momentum = sarr_m1 - sarr_m2
        
        resultats_momentum.append({
            "agence": ag, "article": art, 
            "Vente M-1 (HL)": hl_m1,
            "Coef M-1": coef_m1,
            "SARR M-1 (HL)": sarr_m1, 
            "Vente M-2 (HL)": hl_m2,
            "Coef M-2": coef_m2,
            "SARR M-2 (HL)": sarr_m2, 
            "Momentum_HL": momentum
        })
        
    df_momentum = pd.DataFrame(resultats_momentum)
    return table_indices, df_momentum, debug_ratios

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

    # --- ÉTAPE 2 : PÉRIMÈTRE ---
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
    
    fenetre_histo = st.sidebar.radio("Période pour les Coefs", options=["2 dernières années", "3 dernières années", "Tout l'historique"], index=0)
    methode_coef = st.sidebar.radio("Méthode de calcul", options=["Moyenne des Ratios", "Ratio des Sommes"], index=0)
    
    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["HL", "Cols"], index=0)

    # --- CALCULS ---
    table_indices, df_momentum, debug_ratios = calculer_momentum(df_perimetre, annee_cloture, mois_cutoff, fenetre_histo, methode_coef)

    if df_momentum.empty:
        st.warning("⚠️ Impossible de calculer le momentum (manque de données).")
        st.stop()

    st.success("✅ Étape 5.1 (Momentum) calculée avec succès.")
    
    st.subheader("Table de calcul du Momentum")
    st.write(f"Le mois M correspond à ton Cutoff : **{MOIS_NOMS[mois_cutoff-1]} {annee_cloture}**.")
    
    # Affichage
    if unite_affichage == "Cols":
        df_momentum["Momentum_Aff"] = df_momentum["Momentum_HL"] * 100
        st.dataframe(
            df_momentum[["agence", "article", "Vente M-1 (HL)", "Coef M-1", "SARR M-1 (HL)", "Vente M-2 (HL)", "Coef M-2", "SARR M-2 (HL)", "Momentum_Aff"]],
            column_config={
                "Vente M-1 (HL)": st.column_config.NumberColumn("Vente M-1", format="%.2f"),
                "Coef M-1": st.column_config.NumberColumn("Coef M-1", format="%.4f"),
                "SARR M-1 (HL)": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                "Vente M-2 (HL)": st.column_config.NumberColumn("Vente M-2", format="%.2f"),
                "Coef M-2": st.column_config.NumberColumn("Coef M-2", format="%.4f"),
                "SARR M-2 (HL)": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                "Momentum_Aff": st.column_config.NumberColumn("Momentum (Cols)", format="%.2f"),
            },
            use_container_width=True
        )
    else:
        st.dataframe(
            df_momentum[["agence", "article", "Vente M-1 (HL)", "Coef M-1", "SARR M-1 (HL)", "Vente M-2 (HL)", "Coef M-2", "SARR M-2 (HL)", "Momentum_HL"]],
            column_config={
                "Vente M-1 (HL)": st.column_config.NumberColumn("Vente M-1", format="%.2f"),
                "Coef M-1": st.column_config.NumberColumn("Coef M-1", format="%.4f"),
                "SARR M-1 (HL)": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                "Vente M-2 (HL)": st.column_config.NumberColumn("Vente M-2", format="%.2f"),
                "Coef M-2": st.column_config.NumberColumn("Coef M-2", format="%.4f"),
                "SARR M-2 (HL)": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                "Momentum_HL": st.column_config.NumberColumn("Momentum (HL)", format="%.2f"),
            },
            use_container_width=True
        )

    # --- PANNEAU DE DEBUG POUR COMPRENDRE L'ÉCART ---
    st.markdown("---")
    with st.expander("🔍 Voir le détail du calcul des coefficients (Pourquoi l'écart avec Excel ?)"):
        st.write("Voici les ratios calculés pour chaque année historique. Streamlit fait la moyenne de ces ratios.")
        
        # On affiche le debug uniquement pour les articles filtrés
        if len(sel_articles) > 0 or len(sel_agences) > 0:
            # Mois M-2 (ex: Août)
            mois_m2 = mois_cutoff - 2 if mois_cutoff > 2 else mois_cutoff + 10
            mois_m1 = mois_cutoff - 1 if mois_cutoff > 1 else 12
            
            st.write(f"**Calcul du Coefficient pour M-1 ({MOIS_NOMS[mois_m1-1]}) et M-2 ({MOIS_NOMS[mois_m2-1]}) :**")
            
            debug_filtre = debug_ratios[debug_ratios['mois'].isin([mois_m1, mois_m2])].copy()
            debug_filtre['mois'] = debug_filtre['mois'].map(lambda x: MOIS_NOMS[x-1])
            
            # On affiche le détail
            st.dataframe(debug_filtre.sort_values(["agence", "article", "mois", "annee"]).style.format({"Ratio_Annuel": "{:.4f}"}))
            
            st.info("💡 **Explication :** Si ton Excel affiche 1.0 pour Août, mais que Streamlit trouve 0.93, c'est que la moyenne des ratios ci-dessus donne 0.93. Par exemple, si l'année 2024 avait un ratio de 0.8 et 2025 un ratio de 1.06, la moyenne est 0.93. Excel utilise peut-être une autre année ou une autre méthode pour trouver 1.0.")
        else:
            st.write("Filtre un article et une agence spécifique pour voir le détail des calculs.")

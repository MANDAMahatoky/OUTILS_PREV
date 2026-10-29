import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision S&OP (Étapes 1 à 5.1)")

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
# ÉTAPE 1 : CHARGEMENT ET ENRICHISSEMENT (CONVERSION COLS -> HL)
# ==============================================================================
@st.cache_data(show_spinner="Chargement des données et conversion (Cols -> HL)...")
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes) -> pd.DataFrame:
    flux_ref = io.BytesIO(ref_bytes)
    df_ref = pd.read_excel(flux_ref, sheet_name="Ref actif")
    
    df_ref = df_ref.rename(columns={
        "Article": "article_original", "Positionnement": "positionnement", 
        "Occasion": "occasion", "Contenance (hl)": "contenance_hl", "Contenance (Cl)": "contenance_cl"
    })
    
    for col in ["article_original", "positionnement", "occasion", "contenance_hl", "contenance_cl"]:
        if col not in df_ref.columns: df_ref[col] = 0.0 if "contenance" in col else "Non renseigné"
        
    df_ref = df_ref[["article_original", "positionnement", "occasion", "contenance_hl", "contenance_cl"]].copy()
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    df_ref["cle_article"] = df_ref["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    df_ref = df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)

    flux_ventes = io.BytesIO(ventes_bytes)
    df_raw = pd.read_excel(flux_ventes, sheet_name=0, header=None)
    
    if detecter_format_pivote(df_raw):
        # On lit la colonne volume sous le nom "volume_brut" (qui est en Cols)
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "volume_brut"])}
        df = df_raw.rename(columns=rename).copy()
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
        df["mois"] = df["mois"].apply(normaliser_mois)
        df["volume_brut"] = pd.to_numeric(df["volume_brut"], errors="coerce").fillna(0.0)
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
    df_enrichi["volume_brut"] = df_enrichi["volume_brut"].fillna(0.0)
    df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
    df_enrichi["article"] = df_enrichi["article_original_x"]
    df_enrichi["contenance_cl"] = pd.to_numeric(df_enrichi["contenance_cl"], errors="coerce").fillna(100.0)
    df_enrichi.loc[df_enrichi["contenance_cl"] <= 0, "contenance_cl"] = 100.0
    
    # --- FORMULE DE CONVERSION : HL = Cols * (Contenance_cl / 10000) ---
    df_enrichi["hl"] = df_enrichi["volume_brut"] * (df_enrichi["contenance_cl"] / 10000)
    
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
    
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "hl", "volume_brut", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# ÉTAPES 4 & 5.1 : CALCUL DES INDICES, SARR, MOMENTUM ET BASE
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices, SARR, Momentum et Base...")
def calculer_etapes_4_et_5_1(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, fenetre_histo: str, methode_coef: str):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- ÉTAPE 4 : CALCUL DES INDICES & SARR ---
    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    if df_hist.empty: df_hist = df_realise.copy()

    annee_max = annee_cloture - 1
    if fenetre_histo == "3 dernières années": annee_min = annee_max - 2
    elif fenetre_histo == "2 dernières années": annee_min = annee_max - 1
    else: annee_min = df_hist['annee'].min()
        
    df_hist = df_hist[df_hist['annee'] >= annee_min].copy()

    # Filtrage des années complètes (12 mois)
    mois_par_annee = df_hist.groupby(['agence', 'article', 'annee'])['mois'].nunique().reset_index()
    annees_completes = mois_par_annee[mois_par_annee['mois'] == 12][['agence', 'article', 'annee']]
    df_hist_complet = df_hist.merge(annees_completes, on=['agence', 'article', 'annee'], how='inner')
    
    if df_hist_complet.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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

    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    # --- ÉTAPE 5.1 : MOMENTUM & BASE ---
    df_sarr_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_sarr_sorted[df_sarr_sorted['rang'] < 4].copy()
    
    resultats_momentum_base = []
    
    for (ag, art), group in df_derniers.groupby(['agence', 'article']):
        row_m = group[group['rang'] == 0]
        row_m1 = group[group['rang'] == 1]
        row_m2 = group[group['rang'] == 2]
        row_m3 = group[group['rang'] == 3]

        sarr_m = row_m['SARR_HL'].values[0] if not row_m.empty else 0
        sarr_m1 = row_m1['SARR_HL'].values[0] if not row_m1.empty else 0
        sarr_m2 = row_m2['SARR_HL'].values[0] if not row_m2.empty else 0
        sarr_m3 = row_m3['SARR_HL'].values[0] if not row_m3.empty else 0
        
        date_m1 = f"{MOIS_NOMS[int(row_m1['mois'].values[0])-1]}-{str(int(row_m1['annee'].values[0]))[-2:]}" if not row_m1.empty else "-"
        date_m2 = f"{MOIS_NOMS[int(row_m2['mois'].values[0])-1]}-{str(int(row_m2['annee'].values[0]))[-2:]}" if not row_m2.empty else "-"
        
        # Calcul du Momentum (moyenne des variations des 3 derniers mois)
        var1 = sarr_m - sarr_m1
        var2 = sarr_m1 - sarr_m2
        var3 = sarr_m2 - sarr_m3
        momentum = np.mean([var1, var2, var3])
        
        # Calcul de la Base
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        
        resultats_momentum_base.append({
            "Agence": ag, 
            "Article": art,
            "Mois M (SARR)": sarr_m,
            "Mois M-1": date_m1, 
            "SARR M-1 (HL)": sarr_m1,
            "Mois M-2": date_m2, 
            "SARR M-2 (HL)": sarr_m2,
            "Momentum (HL)": momentum, 
            "Base (HL)": base
        })
                
    df_momentum_base = pd.DataFrame(resultats_momentum_base)
    return table_indices, df_sarr, df_momentum_base

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

    # --- FILTRES ---
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
    st.sidebar.header("⚙️ Cutoff")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cutoff = st.sidebar.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=9, format_func=lambda m: f"{m} - {MOIS_NOMS[m-1]}")

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Options de Calcul")
    fenetre_histo = st.sidebar.radio("Période pour les Coefs", options=["Tout l'historique", "3 dernières années", "2 dernières années"], index=0)
    methode_coef = st.sidebar.radio("Méthode de calcul", options=["Moyenne des Ratios", "Ratio des Sommes"], index=0)
    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["HL", "Cols"], index=0)

    # --- CALCULS ---
    table_indices, df_sarr, df_momentum_base = calculer_etapes_4_et_5_1(df_perimetre, annee_cloture, mois_cutoff, fenetre_histo, methode_coef)

    if df_sarr.empty or df_momentum_base.empty:
        st.warning("⚠️ Aucune année complète (12 mois) trouvée pour calculer les coefficients.")
        st.stop()

    st.success(f"✅ Étapes 4 et 5.1 validées. Les volumes sources (Cols) ont bien été convertis en HL.")
    
    tab_indices, tab_sarr, tab_momentum, tab_diag = st.tabs([
        "📊 Indices (Étape 4)", 
        "📈 Table du SARR", 
        "⚡ Momentum & Base (Étape 5.1)",
        "🩺 Diagnostic Données"
    ])

    # --- CONVERSION POUR L'AFFICHAGE ---
    if unite_affichage == "Cols":
        df_sarr["Vol_Aff"] = df_sarr["hl"] * (10000 / df_sarr["contenance_cl"].replace(0, 100))
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"] * (10000 / df_sarr["contenance_cl"].replace(0, 100))
        col_momentum = "Momentum_Cols"
        col_base = "Base_Cols"
        
        # Création des colonnes converties pour le tableau Momentum/Base
        df_momentum_base["Momentum_Cols"] = df_momentum_base["Momentum (HL)"] * (10000 / df_momentum_base["Article"].map(df_enrichi.drop_duplicates('article').set_index('article')['contenance_cl']).replace(0,100))
        df_momentum_base["Base_Cols"] = df_momentum_base["Base (HL)"] * (10000 / df_momentum_base["Article"].map(df_enrichi.drop_duplicates('article').set_index('article')['contenance_cl']).replace(0,100))
    else:
        df_sarr["Vol_Aff"] = df_sarr["hl"]
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"]
        col_momentum = "Momentum (HL)"
        col_base = "Base (HL)"

    with tab_indices:
        st.subheader("Table des Indices de Saisonnalité")
        pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
        pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
        st.dataframe(pivot_indices.style.format("{:.2f}"), use_container_width=True)

    with tab_sarr:
        st.subheader(f"Table du SARR (en {unite_affichage})")
        st.markdown(f"### 📅 Détail Mensuel du SARR")
        st.dataframe(
            df_sarr[["annee", "mois", "agence", "article", "Vol_Aff", "Indice", "SARR_Aff"]].sort_values(["annee", "mois", "agence", "article"]),
            column_config={
                "Vol_Aff": st.column_config.NumberColumn(f"Volume ({unite_affichage})", format="%.2f"),
                "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                "SARR_Aff": st.column_config.NumberColumn(f"SARR ({unite_affichage})", format="%.2f")
            },
            use_container_width=True, height=400
        )

    with tab_momentum:
        st.subheader("Calcul du Momentum et de la Base (Étape 5.1)")
        st.info("💡 Le Momentum est la moyenne des variations du SARR sur les 3 derniers mois. La Base est le maximum entre le SARR du dernier mois et la moyenne des 3 mois précédents.")
        
        st.dataframe(
            df_momentum_base,
            column_config={
                "Mois M (SARR)": st.column_config.NumberColumn("SARR M (HL)", format="%.2f"),
                "SARR M-1 (HL)": st.column_config.NumberColumn("SARR M-1 (HL)", format="%.2f"),
                "SARR M-2 (HL)": st.column_config.NumberColumn("SARR M-2 (HL)", format="%.2f"),
                "Momentum (HL)": st.column_config.NumberColumn("Momentum (HL)", format="%.2f"),
                "Base (HL)": st.column_config.NumberColumn("Base (HL)", format="%.2f"),
                "Momentum_Cols": st.column_config.NumberColumn("Momentum (Cols)", format="%.2f"),
                "Base_Cols": st.column_config.NumberColumn("Base (Cols)", format="%.2f"),
            },
            use_container_width=True, height=400
        )

    with tab_diag:
        st.subheader("🩺 Vérification de la conversion (Cols -> HL)")
        st.warning("Vérifiez que le 'Volume Converti (HL)' correspond bien aux volumes que vous utilisez dans vos calculs Excel.")
        
        df_diag = df_perimetre[df_perimetre["annee"] == annee_cloture].groupby(['mois', 'agence', 'article', 'contenance_cl'])[['volume_brut', 'hl']].sum().reset_index()
        df_diag = df_diag[(df_diag['volume_brut'] > 0) | (df_diag['hl'] > 0)].sort_values(['mois', 'agence', 'article'])
        
        if sel_articles: df_diag = df_diag[df_diag["article"].isin(sel_articles)]
        if sel_agences: df_diag = df_diag[df_diag["agence"].isin(sel_agences)]
        
        st.dataframe(
            df_diag.style.format({"volume_brut": "{:,.0f}", "hl": "{:,.2f}", "contenance_cl": "{:,.0f}"}),
            column_config={
                "contenance_cl": st.column_config.NumberColumn("Contenance (cl)"),
                "volume_brut": st.column_config.NumberColumn("Volume Brut Fichier (Cols)"),
                "hl": st.column_config.NumberColumn("Volume Converti (HL)")
            },
            use_container_width=True
        )

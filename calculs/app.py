import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision S&OP (Étapes 1 à 5.2)")

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
    
    # Conversion Cols -> HL
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
# ÉTAPES 4, 5.1 & 5.2 : CALCULS
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices, SARR, Momentum et Prévisions...")
def calculer_modele(df_perimetre: pd.DataFrame, annee_min_histo: int, annee_max_histo: int, annee_cloture: int, mois_cutoff: int, annee_cible: int, methode_coef: str):
    
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, None

    df_hist = df_realise[(df_realise["annee"] >= annee_min_histo) & (df_realise["annee"] <= annee_max_histo)].copy()
    if df_hist.empty: return None, None, None, None, None

    # Filtrage des années complètes (12 mois)
    mois_par_annee = df_hist.groupby(['agence', 'article', 'annee'])['mois'].nunique().reset_index()
    annees_completes = mois_par_annee[mois_par_annee['mois'] == 12][['agence', 'article', 'annee']]
    df_hist_complet = df_hist.merge(annees_completes, on=['agence', 'article', 'annee'], how='inner')
    
    if df_hist_complet.empty: return None, None, None, None, None

    # --- ÉTAPE 4 : INDICES & SARR ---
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
    df_sarr['SARR_Cols'] = df_sarr['volume_brut'] / df_sarr['Indice'].replace(0, 1.0)

    # --- ÉTAPE 5.1 : MOMENTUM & BASE ---
    df_sarr_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_sarr_sorted[df_sarr_sorted['rang'] < 4].copy()
    
    resultats_momentum = []
    
    for (ag, art), group in df_derniers.groupby(['agence', 'article']):
        def get_val(rang, col): return group[group['rang'] == rang][col].values[0] if len(group[group['rang'] == rang]) > 0 else 0
        def get_date(rang): 
            r = group[group['rang'] == rang]
            return f"{MOIS_NOMS[int(r['mois'].values[0])-1]}-{str(int(r['annee'].values[0]))[-2:]}" if not r.empty else "-"

        sarr_m = get_val(0, 'SARR_HL')
        sarr_m1 = get_val(1, 'SARR_HL')
        sarr_m2 = get_val(2, 'SARR_HL')
        sarr_m3 = get_val(3, 'SARR_HL')
        
        var1, var2, var3 = sarr_m - sarr_m1, sarr_m1 - sarr_m2, sarr_m2 - sarr_m3
        momentum = np.mean([var1, var2, var3])
        base = max(sarr_m, np.mean([sarr_m1, sarr_m2, sarr_m3]))
        
        info_art = df_realise[(df_realise['agence'] == ag) & (df_realise['article'] == art)].iloc[0]
        
        resultats_momentum.append({
            "Agence": ag, "Article": art,
            "M-1 (Date)": get_date(1), "SARR M-1 (Cols)": get_val(1, 'SARR_Cols'),
            "M-2 (Date)": get_date(2), "SARR M-2 (Cols)": get_val(2, 'SARR_Cols'),
            "M-3 (Date)": get_date(3), "SARR M-3 (Cols)": get_val(3, 'SARR_Cols'),
            "Base_HL": base, "Momentum_HL": momentum, "Contenance": info_art['contenance_cl']
        })
        
    df_momentum = pd.DataFrame(resultats_momentum)

    # --- ÉTAPE 5.2 : PRÉVISIONS AVEC CAGR ---
    resultats_previsions = []
    
    for _, row in df_momentum.iterrows():
        ag, art, base, momentum, contenance = row['Agence'], row['Article'], row['Base_HL'], row['Momentum_HL'], row['Contenance']
        
        art_hist = df_hist_complet[(df_hist_complet['article'] == art) & (df_hist_complet['agence'] == ag)]
        vol_debut = art_hist[art_hist['annee'] == annee_min_histo]['hl'].sum()
        vol_fin = art_hist[art_hist['annee'] == annee_max_histo]['hl'].sum()
        nb_ans = annee_max_histo - annee_min_histo
        cagr_val = ((vol_fin / vol_debut) ** (1 / nb_ans)) - 1 if nb_ans > 0 and vol_debut > 0 and vol_fin > 0 else 0.0

        for y in range(annee_cloture, annee_cible + 1):
            multiplicateur_cagr = (1 + cagr_val) ** (y - annee_cloture)
            for m in range(1, 13):
                if y == annee_cloture and m <= mois_cutoff: continue
                coef = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]['Indice'].values[0]
                prev_hl = max(0.0, ((coef * base) + momentum) * multiplicateur_cagr)
                
                resultats_previsions.append({
                    "annee": y, "mois": m, "agence": ag, "article": art, "Date": f"{MOIS_NOMS[m-1]}-{str(y)[-2:]}",
                    "Indice": coef, "Base_HL": base, "Momentum_HL": momentum,
                    "CAGR (%)": cagr_val * 100, "Prevision_HL": prev_hl, "Prevision_Cols": prev_hl * (10000 / contenance)
                })

    df_previsions = pd.DataFrame(resultats_previsions)
    return table_indices, df_sarr, df_momentum, df_hist, df_previsions

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
    st.sidebar.header("📅 Intervalle Historique")
    annee_min_reelle = int(df_perimetre["annee"].min()) if not df_perimetre.empty else 2020
    annee_max_reelle = int(df_perimetre["annee"].max()) if not df_perimetre.empty else 2026
    
    st.sidebar.success(f"Données détectées : **{annee_min_reelle}** à **{annee_max_reelle}**")
    annee_min_histo = st.sidebar.number_input("Année Min (Début)", min_value=2015, max_value=2030, value=2024)
    annee_max_histo = st.sidebar.number_input("Année Max (Fin)", min_value=annee_min_histo, max_value=2030, value=2025)
    
    st.sidebar.header("⚙️ Cutoff & Cible")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cutoff = st.sidebar.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=9, format_func=lambda m: f"{m} - {MOIS_NOMS[m-1]}")
    
    st.sidebar.markdown("---")
    annee_cible = st.sidebar.number_input("Année Cible (Prévisions)", min_value=annee_cloture, max_value=2035, value=2027)

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Options de Calcul")
    methode_coef = st.sidebar.radio("Méthode de calcul", options=["Moyenne des Ratios", "Ratio des Sommes"], index=0)
    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["Cols", "HL"], index=0) # Cols par défaut

    # --- CALCULS ---
    table_indices, df_sarr, df_momentum, df_hist, df_previsions = calculer_modele(
        df_perimetre, annee_min_histo, annee_max_histo, annee_cloture, mois_cutoff, annee_cible, methode_coef
    )

    if table_indices is None:
        st.warning("⚠️ Aucune année complète (12 mois) trouvée pour calculer les coefficients.")
        st.stop()

    st.success(f"✅ Modèle calculé sur l'intervalle {annee_min_histo} - {annee_max_histo}.")
    
    tab_indices, tab_sarr, tab_momentum, tab_prev, tab_diag = st.tabs([
        "📊 Indices", "📈 SARR", "⚡ Momentum & Base (Comparaison)", "🚀 5.2 Prévisions", "🩺 Diagnostic Données"
    ])

    # --- CONVERSION POUR L'AFFICHAGE ---
    if unite_affichage == "Cols":
        df_sarr["Vol_Aff"] = df_sarr["volume_brut"]
        df_sarr["SARR_Aff"] = df_sarr["SARR_Cols"]
        col_prev = "Prevision_Cols"
    else:
        df_sarr["Vol_Aff"] = df_sarr["hl"]
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"]
        col_prev = "Prevision_HL"

    with tab_indices:
        st.subheader("Table des Indices de Saisonnalité")
        pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
        pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
        st.dataframe(pivot_indices.style.format("{:.2f}"), use_container_width=True)

    with tab_sarr:
        st.subheader(f"Table du SARR (en {unite_affichage})")
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
        st.subheader("Comparaison du Momentum et de la Base")
        st.info("Ce tableau reproduit exactement la structure de votre fichier Excel (colonnes M-1, M-2, M-3) pour vous permettre de vérifier les valeurs.")
        
        # On force l'affichage en Cols pour ce tableau de comparaison
        st.dataframe(
            df_momentum[["Agence", "Article", "M-1 (Date)", "SARR M-1 (Cols)", "M-2 (Date)", "SARR M-2 (Cols)", "M-3 (Date)", "SARR M-3 (Cols)", "Momentum_HL", "Base_HL"]],
            column_config={
                "SARR M-1 (Cols)": st.column_config.NumberColumn("SARR M-1 (Cols)", format="%.2f"),
                "SARR M-2 (Cols)": st.column_config.NumberColumn("SARR M-2 (Cols)", format="%.2f"),
                "SARR M-3 (Cols)": st.column_config.NumberColumn("SARR M-3 (Cols)", format="%.2f"),
                "Base_HL": st.column_config.NumberColumn("Base (HL)", format="%.2f"),
                "Momentum_HL": st.column_config.NumberColumn("Momentum (HL)", format="%.2f"),
            },
            use_container_width=True
        )

    with tab_prev:
        st.subheader(f"Prévisions Finales jusqu'en {annee_cible} (en {unite_affichage})")
        
        pivot_mensuel = df_previsions.pivot_table(
            index=['annee', 'agence', 'article'], columns='mois', values=col_prev, aggfunc='sum'
        ).fillna(0)
        pivot_mensuel.columns = [MOIS_NOMS[c-1] for c in pivot_mensuel.columns]
        pivot_mensuel['Total Année'] = pivot_mensuel.sum(axis=1)
        st.dataframe(pivot_mensuel.style.format("{:,.2f}"), use_container_width=True)
        
        st.markdown("### 📅 Détail Mensuel")
        st.dataframe(
            df_previsions[["annee", "mois", "Date", "agence", "article", "Indice", "Base_HL", "Momentum_HL", "CAGR (%)", col_prev]].sort_values(["annee", "mois", "agence", "article"]),
            column_config={
                "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                "Base_HL": st.column_config.NumberColumn("Base (HL)", format="%.2f"),
                "Momentum_HL": st.column_config.NumberColumn("Momentum (HL)", format="%.2f"),
                "CAGR (%)": st.column_config.NumberColumn("CAGR (%)", format="%.2f"),
                col_prev: st.column_config.NumberColumn(f"Prévision ({unite_affichage})", format="%.2f"),
            },
            use_container_width=True, height=400
        )

    with tab_diag:
        st.subheader("🩺 Diagnostic : Volumes Bruts vs Convertis")
        
        df_diag = df_perimetre.groupby(['annee', 'mois', 'agence', 'article', 'contenance_cl'])[['volume_brut', 'hl']].sum().reset_index()
        df_diag = df_diag[(df_diag['volume_brut'] > 0) | (df_diag['hl'] > 0)].sort_values(['annee', 'mois', 'agence', 'article'])
        
        if sel_articles: df_diag = df_diag[df_diag["article"].isin(sel_articles)]
        if sel_agences: df_diag = df_diag[df_diag["agence"].isin(sel_agences)]
        
        st.dataframe(
            df_diag.style.format({"volume_brut": "{:,.0f}", "hl": "{:,.2f}", "contenance_cl": "{:,.0f}"}),
            column_config={
                "contenance_cl": st.column_config.NumberColumn("Contenance (cl)"),
                "volume_brut": st.column_config.NumberColumn("Volume Fichier (Cols)"),
                "hl": st.column_config.NumberColumn("Volume Converti (HL)")
            },
            use_container_width=True
        )

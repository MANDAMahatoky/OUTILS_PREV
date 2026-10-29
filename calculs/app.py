import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import base64

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision : Étapes 4 et 5.1")

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

def get_csv_download_link(df, filename):
    csv = df.to_csv(index=True).encode('utf-8')
    b64 = base64.b64encode(csv).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Télécharger en CSV</a>'

# ==============================================================================
# ÉTAPE 1 : CHARGEMENT ET ENRICHISSEMENT
# ==============================================================================
@st.cache_data(show_spinner="Chargement des données...")
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
# VÉRIFICATION DE L'INTÉGRALITÉ DE L'HISTORIQUE
# ==============================================================================
def verifier_integrite_historique(df_perimetre: pd.DataFrame, annee_min: int, annee_max: int):
    annees_presentes = df_perimetre[(df_perimetre["annee"] >= annee_min) & (df_perimetre["annee"] <= annee_max)]
    annees_uniques = sorted(annees_presentes["annee"].unique())
    
    annees_manquantes = [a for a in range(annee_min, annee_max + 1) if a not in annees_uniques]
    
    mois_par_annee = annees_presentes.groupby('annee')['mois'].nunique()
    annees_incompletes = mois_par_annee[mois_par_annee < 12].index.tolist()
    annees_completes = mois_par_annee[mois_par_annee == 12].index.tolist()
    
    return annees_manquantes, annees_incompletes, annees_completes

# ==============================================================================
# ÉTAPE 4 & 5.1 : CALCULS
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et du Momentum...")
def calculer_modele(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, annee_min_histo: int, annee_max_histo: int, 
                    methode_coef: str, niveau_agregation: str):
    
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None

    df_hist = df_realise[(df_realise["annee"] >= annee_min_histo) & (df_realise["annee"] <= annee_max_histo)].copy()
    if df_hist.empty: return None, None, None

    if niveau_agregation == "Par Agence & Article":
        group_cols = ['agence', 'article']
    else:
        group_cols = ['article']

    # --- CALCUL DES INDICES ---
    vols = df_hist.groupby(group_cols + ['annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols = vols.reindex(columns=range(1, 13), fill_value=0.0)
    vols_annuels = vols.sum(axis=1)
    
    vols_mois_cumules = vols.groupby(group_cols).sum()
    vols_annuels_cumules = vols_annuels.groupby(group_cols).sum()
    nb_annees = df_hist.groupby(group_cols)['annee'].nunique()
    
    moy_histo = vols_mois_cumules.div(nb_annees, axis=0)
    moy_globale = vols_annuels_cumules / (12.0 * nb_annees)

    if methode_coef == "Moyenne des Ratios":
        ratios = vols.div(vols_annuels / 12.0, axis=0).replace([np.inf, -np.inf], np.nan)
        indices = ratios.groupby(group_cols).mean().fillna(1.0)
    else:
        indices = moy_histo.div(moy_globale, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    table_indices = indices.reset_index().melt(id_vars=group_cols, var_name='mois', value_name='Indice')

    df_sarr = df_realise.merge(table_indices, on=group_cols + ['mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    # --- CALCUL DU MOMENTUM & BASE ---
    df_sarr_sorted = df_sarr.sort_values(group_cols + ['annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(group_cols).cumcount(ascending=False)
    
    resultats_momentum = []
    
    for _, group in df_sarr_sorted.groupby(group_cols):
        if len(group_cols) == 2:
            ag = group[group_cols[0]].iloc[0]
            art = group[group_cols[1]].iloc[0]
        else:
            ag = "Global"
            art = group[group_cols[0]].iloc[0]

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
        
        momentum = sarr_m1 - sarr_m2
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        
        resultats_momentum.append({
            "agence": ag, "article": art, 
            "Mois M-1": date_m1, "SARR M-1": sarr_m1,
            "Mois M-2": date_m2, "SARR M-2": sarr_m2,
            "Momentum_HL": momentum, 
            "Base_HL": base
        })
        
    df_momentum = pd.DataFrame(resultats_momentum)
    return table_indices, df_sarr, df_momentum

# ==============================================================================
# FONCTION DE COLORATION (ROUGE < 1, VERT > 1)
# ==============================================================================
def color_cells(val):
    try:
        val = float(val)
        if val < 0.999:
            return 'background-color: #f8d7da; color: #721c24;' # Rouge clair (Mois faible)
        elif val > 1.001:
            return 'background-color: #d4edda; color: #155724;' # Vert clair (Mois fort)
        else:
            return '' # 1.0 = Neutre
    except:
        return ''

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col_app, col_info = st.columns([3.5, 1])

with col_info:
    st.markdown("### 📖 Guide d'utilisation")
    st.info("Cet outil calcule les indices de saisonnalité et le momentum pour lisser les ventes (SARR).")
    
    st.markdown("**1. Indices (Coefs)**")
    st.markdown("Le ratio entre les ventes d'un mois et la moyenne globale.")
    st.markdown("🟩 > 1.0 : **Mois Fort**")
    st.markdown("🟥 < 1.0 : **Mois Faible**")
    
    st.markdown("**2. SARR & Momentum**")
    st.markdown("`SARR = Volume / Indice`. Le Momentum est la différence de SARR entre les deux derniers mois (`M-1 - M-2`).")

with col_app:
    col1, col2 = st.columns(2)
    with col1:
        fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
    with col2:
        fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"])

    if fichier_ventes is not None and fichier_ref is not None:
        df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue())

        # Initialisation pour récupérer les vraies bornes de l'historique
        annee_min_reelle = int(df_enrichi["annee"].min()) if not df_enrichi.empty else 2020
        annee_max_reelle = int(df_enrichi["annee"].max()) if not df_enrichi.empty else 2026

        # --- FILTRES PERIMETRE COMPLETS ---
        st.sidebar.header("🔍 1. Périmètre")
        segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
        sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
        
        df_temp = df_enrichi.copy()
        if sel_segments: df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
        
        positions_dispo = sorted([p for p in df_temp["positionnement"].unique() if pd.notna(p)])
        sel_positions = st.sidebar.multiselect("🎯 Positionnement", options=positions_dispo, placeholder="Tous")
        if sel_positions: df_temp = df_temp[df_temp["positionnement"].isin(sel_positions)]
        
        occasions_dispo = sorted([o for o in df_temp["occasion"].unique() if pd.notna(o)])
        sel_occasions = st.sidebar.multiselect("🥂 Occasion", options=occasions_dispo, placeholder="Toutes")
        if sel_occasions: df_temp = df_temp[df_temp["occasion"].isin(sel_occasions)]

        articles_dispo = sorted(df_temp["article"].unique())
        sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
        
        agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
        sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")

        df_perimetre = df_enrichi.copy()
        if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
        if sel_positions: df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_positions)]
        if sel_occasions: df_perimetre = df_perimetre[df_perimetre["occasion"].isin(sel_occasions)]
        if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
        if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ 2. Cutoff & Options")
        annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
        mois_cutoff = st.sidebar.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=7, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
        
        st.sidebar.markdown("---")
        st.sidebar.header("📅 3. Intervalle Historique")
        
        st.sidebar.success(f"📊 Années détectées : **{annee_min_reelle}** à **{annee_max_reelle}**")
        
        annee_min_histo = st.sidebar.number_input("Année Min (Début)", min_value=2015, max_value=annee_cloture-1, value=annee_min_reelle)
        annee_max_histo = st.sidebar.number_input("Année Max (Fin)", min_value=annee_min_histo, max_value=annee_cloture-1, value=min(annee_cloture - 1, annee_max_reelle))
        
        st.sidebar.markdown("---")
        niveau_agregation = st.sidebar.radio("Niveau d'agrégation", options=["Par Article (Global)", "Par Agence & Article"], index=0)
        methode_coef = st.sidebar.radio("Méthode de calcul", options=["Ratio des Sommes", "Moyenne des Ratios"], index=0)
        unite_affichage = st.sidebar.radio("Unité d'affichage", options=["HL", "Cols"], index=0)

        # Vérification
        annees_manquantes, annees_incompletes, annees_completes = verifier_integrite_historique(df_perimetre, annee_min_histo, annee_max_histo)

        if annees_manquantes or annees_incompletes:
            st.error("🚨 **Calcul interrompu : Données historiques incomplètes.**")
            if annees_manquantes:
                st.warning(f"Les années suivantes n'existent pas du tout : **{', '.join(map(str, annees_manquantes))}**.")
            if annees_incompletes:
                st.warning(f"Les années suivantes sont incomplètes (moins de 12 mois) : **{', '.join(map(str, annees_incompletes))}**.")
            
            if annees_completes:
                st.info(f"💡 **Proposition :** Modifiez l'intervalle. Les données complètes sont disponibles pour : **{', '.join(map(str, annees_completes))}**. Essayez l'année min **{annees_completes[0]}** et l'année max **{annees_completes[-1]}**.")
            st.stop()

        # Calculs
        table_indices, df_sarr, df_momentum = calculer_modele(
            df_perimetre, annee_cloture, mois_cutoff, annee_min_histo, annee_max_histo, methode_coef, niveau_agregation
        )
        
        if table_indices is None:
            st.error("⚠️ Impossible de calculer le modèle.")
        else:
            st.success(f"✅ Modèle calculé avec succès sur l'intervalle {annee_min_histo} - {annee_max_histo}.")
            
            tab_indices, tab_momentum = st.tabs(["📊 4. Indices de Saisonnalité", "📈 5.1 Momentum & Base"])

            with tab_indices:
                st.subheader("Table des Indices")
                if niveau_agregation == "Par Agence & Article":
                    pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
                else:
                    pivot_indices = table_indices.pivot_table(index=['article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
                    
                pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
                
                try:
                    styled_df = pivot_indices.style.map(color_cells).format("{:.2f}")
                except AttributeError:
                    styled_df = pivot_indices.style.applymap(color_cells).format("{:.2f}")
                    
                st.dataframe(styled_df, use_container_width=True)
                st.markdown(get_csv_download_link(pivot_indices, "indices.csv"), unsafe_allow_html=True)

            with tab_momentum:
                st.subheader("Calcul du Momentum et de la Base")
                st.write("Le Momentum est la différence entre le SARR du mois M-1 et du mois M-2.")
                
                if unite_affichage == "Cols":
                    df_momentum["Momentum_Aff"] = df_momentum["Momentum_HL"] * 100
                    df_momentum["Base_Aff"] = df_momentum["Base_HL"] * 100
                    
                    st.dataframe(
                        df_momentum[["agence", "article", "Mois M-1", "SARR M-1", "Mois M-2", "SARR M-2", "Momentum_Aff", "Base_Aff"]],
                        column_config={
                            "SARR M-1": st.column_config.NumberColumn("SARR M-1 (HL)", format="%.2f"),
                            "SARR M-2": st.column_config.NumberColumn("SARR M-2 (HL)", format="%.2f"),
                            "Momentum_Aff": st.column_config.NumberColumn("Momentum (Cols)", format="%.2f"),
                            "Base_Aff": st.column_config.NumberColumn("Base (Cols)", format="%.2f"),
                        },
                        use_container_width=True
                    )
                    st.markdown(get_csv_download_link(df_momentum, "momentum.csv"), unsafe_allow_html=True)
                else:
                    st.dataframe(
                        df_momentum[["agence", "article", "Mois M-1", "SARR M-1", "Mois M-2", "SARR M-2", "Momentum_HL", "Base_HL"]],
                        column_config={
                            "SARR M-1": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                            "SARR M-2": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                            "Momentum_HL": st.column_config.NumberColumn("Momentum", format="%.2f"),
                            "Base_HL": st.column_config.NumberColumn("Base", format="%.2f"),
                        },
                        use_container_width=True
                    )
                    st.markdown(get_csv_download_link(df_momentum, "momentum.csv"), unsafe_allow_html=True)

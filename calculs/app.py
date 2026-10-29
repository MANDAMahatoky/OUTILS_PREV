import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision : Étapes 4 et 5")

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
# VÉRIFICATION DE L'INTÉGRALITÉ DE L'HISTORIQUE
# ==============================================================================
def verifier_integrite_historique(df_perimetre: pd.DataFrame, annee_min: int, annee_max: int, niveau_agregation: str):
    if niveau_agregation == "Par Agence & Article":
        group_cols = ['agence', 'article']
    else:
        group_cols = ['article']

    annees_presentes = df_perimetre[(df_perimetre["annee"] >= annee_min) & (df_perimetre["annee"] <= annee_max)]
    annees_uniques = sorted(annees_presentes["annee"].unique())
    
    annees_manquantes = [a for a in range(annee_min, annee_max + 1) if a not in annees_uniques]
    
    annees_incompletes = []
    for a in annees_uniques:
        mois_par_art = annees_presentes[annees_presentes["annee"] == a].groupby(group_cols)["mois"].nunique()
        if (mois_par_art < 12).any():
            annees_incompletes.append(a)
            
    return annees_manquantes, annees_incompletes, annees_uniques

# ==============================================================================
# ÉTAPE 4 & 5 : CALCULS (INDICES, SARR, MOMENTUM, CAGR, PREVISIONS)
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices, du Momentum et des Prévisions...")
def calculer_modele(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, annee_min_histo: int, annee_max_histo: int, 
                    methode_coef: str, niveau_agregation: str, use_cagr: bool, annee_cible: int):
    
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None

    df_hist = df_realise[(df_realise["annee"] >= annee_min_histo) & (df_realise["annee"] <= annee_max_histo)].copy()
    if df_hist.empty: return None, None, None, None

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
    for keys, group in df_sarr_sorted.groupby(group_cols):
        ag, art = keys if isinstance(keys, tuple) else ("Global", keys)
        
        sarr_m1 = group[group['rang'] == 1]['SARR_HL'].values[0] if len(group[group['rang'] == 1]) > 0 else 0
        sarr_m2 = group[group['rang'] == 2]['SARR_HL'].values[0] if len(group[group['rang'] == 2]) > 0 else 0
        sarr_m3 = group[group['rang'] == 3]['SARR_HL'].values[0] if len(group[group['rang'] == 3]) > 0 else 0
        sarr_m = group[group['rang'] == 0]['SARR_HL'].values[0] if len(group[group['rang'] == 0]) > 0 else 0
        
        momentum = sarr_m1 - sarr_m2
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        
        resultats_momentum.append({
            "agence": ag, "article": art, 
            "SARR M-1": sarr_m1, "SARR M-2": sarr_m2, "SARR M-3": sarr_m3, "SARR M": sarr_m,
            "Momentum_HL": momentum, "Base_HL": base
        })
        
    df_momentum = pd.DataFrame(resultats_momentum)

    # --- CALCUL DU CAGR ET DES PRÉVISIONS ---
    resultats_previsions = []
    
    for _, row in df_momentum.iterrows():
        ag, art = row['agence'], row['article']
        base, momentum = row['Base_HL'], row['Momentum_HL']
        
        # Calcul du CAGR
        if use_cagr:
            # On récupère les volumes annuels de la période historique
            if niveau_agregation == "Par Agence & Article":
                hist_group = vols_annuels.loc[(ag, art)]
            else:
                hist_group = vols_annuels.loc[art]
                
            vol_debut = hist_group.get(annee_min_histo, 0)
            vol_fin = hist_group.get(annee_max_histo, 0)
            nb_ans = annee_max_histo - annee_min_histo
            
            if nb_ans > 0 and vol_debut > 0 and vol_fin > 0:
                cagr_val = ((vol_fin / vol_debut) ** (1 / nb_ans)) - 1
            else:
                cagr_val = 0.0
        else:
            cagr_val = 0.0
            
        # Prévisions jusqu'à l'année cible
        for y in range(annee_cloture, annee_cible + 1):
            multiplicateur = (1 + cagr_val) ** (y - annee_cloture)
            
            for m in range(1, 13):
                # On applique la même logique de Cutoff
                if y == annee_cloture and m <= mois_cutoff: continue
                
                coef_data = table_indices[(table_indices['mois'] == m)]
                if niveau_agregation == "Par Agence & Article":
                    coef_data = coef_data[(coef_data['agence'] == ag) & (coef_data['article'] == art)]
                else:
                    coef_data = coef_data[coef_data['article'] == art]
                
                coef = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
                
                prev_hl = ((coef * base) + momentum) * multiplicateur
                prev_hl = max(0.0, prev_hl)
                
                resultats_previsions.append({
                    "annee": y, "mois": m, "agence": ag, "article": art,
                    "Date": f"{MOIS_NOMS[m-1]}-{str(y)[-2:]}",
                    "Indice": coef, "Base": base, "Momentum": momentum,
                    "CAGR": cagr_val * 100,
                    "Prevision_HL": prev_hl
                })

    df_previsions = pd.DataFrame(resultats_previsions)
    return table_indices, df_sarr, df_momentum, df_previsions

# ==============================================================================
# INTERFACE STREAMLIT : MISE EN PAGE AVEC PANNEAU DROIT
# ==============================================================================
col_app, col_info = st.columns([3, 1])

with col_info:
    st.markdown("### 📖 Méthodes de calcul")
    st.info("Calculs dynamiques, sans modification manuelle.")
    
    st.markdown("**1. Indices**")
    st.markdown("`Ventes du mois / Moyenne globale` sur l'intervalle sélectionné.")
    
    st.markdown("**2. SARR & Momentum**")
    st.markdown("`SARR = Volume / Indice`. \n\n`Momentum = SARR M-1 - SARR M-2`.")
    
    st.markdown("**3. Prévisions (CAGR)**")
    st.markdown("`(Indice * Base + Momentum) * (1 + CAGR)^n`.")
    st.caption("Le CAGR lisse la croissance entre l'année min et max de ton historique.")

with col_app:
    col1, col2 = st.columns(2)
    with col1:
        fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
    with col2:
        fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"])

    if fichier_ventes is not None and fichier_ref is not None:
        df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue())

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

        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Cutoff & Options")
        annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
        mois_cutoff = st.sidebar.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=7, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
        annee_cible = st.sidebar.number_input("Année Cible (Prévisions)", min_value=annee_cloture, max_value=2035, value=annee_cloture+1)
        
        st.sidebar.markdown("---")
        st.sidebar.header("📅 Intervalle Historique")
        annee_min_histo = st.sidebar.number_input("Année Min (Début)", min_value=2015, max_value=annee_cloture-1, value=annee_cloture-2)
        annee_max_histo = st.sidebar.number_input("Année Max (Fin)", min_value=annee_min_histo, max_value=annee_cloture-1, value=annee_cloture-1)
        
        st.sidebar.markdown("---")
        niveau_agregation = st.sidebar.radio("Niveau de calcul", options=["Par Agence & Article", "Par Article (Global)"], index=0)
        methode_coef = st.sidebar.radio("Méthode de calcul", options=["Ratio des Sommes", "Moyenne des Ratios"], index=0)
        use_cagr = st.sidebar.checkbox("Activer le CAGR pour la projection", value=True)
        unite_affichage = st.sidebar.radio("Unité d'affichage", options=["HL", "Cols"], index=0)

        # --- VERIFICATION DE L'INTÉGRALITÉ ---
        annees_manquantes, annees_incompletes, annees_uniques = verifier_integrite_historique(
            df_perimetre, annee_min_histo, annee_max_histo, niveau_agregation
        )

        if annees_manquantes or annees_incompletes:
            st.error("🚨 **Calcul interrompu : Données historiques incomplètes.**")
            if annees_manquantes:
                st.warning(f"Les années suivantes n'existent pas du tout dans les données : **{', '.join(map(str, annees_manquantes))}**.")
            if annees_incompletes:
                st.warning(f"Les années suivantes sont incomplètes (moins de 12 mois) : **{', '.join(map(str, annees_incompletes))}**.")
            
            if annees_uniques:
                st.info(f"💡 **Proposition :** Modifiez l'intervalle historique. Les données complètes sont disponibles pour : **{', '.join(map(str, annees_uniques))}**. Essayez de sélectionner l'année min à **{annees_uniques[0]}** et l'année max à **{annees_uniques[-1]}**.")
            
            st.stop()

        # --- CALCULS ---
        table_indices, df_sarr, df_momentum, df_previsions = calculer_modele(
            df_perimetre, annee_cloture, mois_cutoff, annee_min_histo, annee_max_histo, 
            methode_coef, niveau_agregation, use_cagr, annee_cible
        )
        
        if df_previsions is None:
            st.error("⚠️ Impossible de calculer le modèle.")
        else:
            st.success(f"✅ Modèle calculé avec succès (CAGR {'Activé' if use_cagr else 'Désactivé'}).")
            
            tab_indices, tab_momentum, tab_prev = st.tabs(["📊 4. Indices", "📈 5.1 Momentum", "🚀 5.2 Prévisions"])

            with tab_indices:
                st.subheader("Table des Indices Saisonniers")
                pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
                pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
                st.dataframe(pivot_indices.style.format("{:.2f}"), use_container_width=True)

            with tab_momentum:
                st.subheader("Calcul du Momentum & Base")
                st.dataframe(df_momentum.style.format({"SARR M-1": "{:.2f}", "SARR M-2": "{:.2f}", "SARR M-3": "{:.2f}", "SARR M": "{:.2f}", "Momentum_HL": "{:.2f}", "Base_HL": "{:.2f}"}), use_container_width=True)

            with tab_prev:
                st.subheader("Prévisions Finales avec CAGR")
                
                # Conversion pour affichage
                if unite_affichage == "Cols":
                    df_previsions["Prevision_Aff"] = df_previsions["Prevision_HL"] * 100
                    col_aff = "Prevision_Aff"
                else:
                    col_aff = "Prevision_HL"

                # TCD Mensuel
                pivot_prev = df_previsions.pivot_table(
                    index=['annee', 'agence', 'article'], columns='mois', values=col_aff, aggfunc='sum'
                )
                pivot_prev.columns = [MOIS_NOMS[c-1] for c in pivot_prev.columns]
                pivot_prev['Total Année'] = pivot_prev.sum(axis=1)
                st.dataframe(pivot_prev.style.format("{:,.2f}", na_rep="-"), use_container_width=True)

                # Détail
                st.dataframe(
                    df_previsions[["annee", "mois", "Date", "agence", "article", "Indice", "Base", "Momentum", "CAGR", col_aff]].sort_values(["annee", "mois", "agence", "article"]),
                    column_config={
                        "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                        "Base": st.column_config.NumberColumn("Base (HL)", format="%.0f"),
                        "Momentum": st.column_config.NumberColumn("Momentum (HL)", format="%.0f"),
                        "CAGR": st.column_config.NumberColumn("CAGR (%)", format="%.2f"),
                        col_aff: st.column_config.NumberColumn(f"Prévision ({unite_affichage})", format="%.2f"),
                    },
                    use_container_width=True, height=400
                )

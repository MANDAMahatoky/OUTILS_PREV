import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import math

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision : Analyse Période Momentum")

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

# Arrondi "Excel" pour l'affichage
def excel_round(val, decimals=1):
    if pd.isna(val): return val
    factor = 10 ** decimals
    return math.floor(val * factor + 0.5) / factor

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
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, fenetre_histo: str, methode_coef: str, niveau_agregation: str):
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    if df_hist.empty: df_hist = df_realise.copy()

    annee_max = annee_cloture - 1
    if fenetre_histo == "3 dernières années": annee_min = annee_max - 2
    elif fenetre_histo == "2 dernières années": annee_min = annee_max - 1
    else: annee_min = df_hist['annee'].min()
    df_hist = df_hist[df_hist['annee'] >= annee_min].copy()

    if niveau_agregation == "Par Agence & Article":
        group_cols = ['agence', 'article']
    else:
        group_cols = ['article']

    mois_par_annee = df_hist.groupby(group_cols + ['annee'])['mois'].nunique().reset_index()
    annees_completes = mois_par_annee[mois_par_annee['mois'] == 12][group_cols + ['annee']]
    df_hist_complet = df_hist.merge(annees_completes, on=group_cols + ['annee'], how='inner')
    if df_hist_complet.empty: df_hist_complet = df_hist.copy()

    vols = df_hist_complet.groupby(group_cols + ['annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols = vols.reindex(columns=range(1, 13), fill_value=0.0)
    vols_annuels = vols.sum(axis=1)
    
    # CALCUL DE LA MOYENNE HISTO
    vols_mois_cumules = vols.groupby(group_cols).sum()
    vols_annuels_cumules = vols_annuels.groupby(group_cols).sum()
    nb_annees = df_hist_complet.groupby(group_cols)['annee'].nunique()
    moy_histo = vols_mois_cumules.div(nb_annees, axis=0)
    moy_globale = vols_annuels_cumules / (12.0 * nb_annees)

    if methode_coef == "Moyenne des Ratios":
        ratios = vols.div(vols_annuels / 12.0, axis=0).replace([np.inf, -np.inf], np.nan)
        indices = ratios.groupby(group_cols).mean().fillna(1.0)
    else:
        # Ratio des Sommes (Formule Excel)
        indices = moy_histo.div(moy_globale, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    debug_data = vols_mois_cumules.reset_index().melt(id_vars=group_cols, var_name='mois', value_name='Volume_Total')
    debug_data['Total_Annuel'] = debug_data.apply(lambda row: vols_annuels_cumules.loc[tuple(row[col] for col in group_cols)] if len(group_cols) > 1 else vols_annuels_cumules.loc[row['article']], axis=1)
    debug_data['Moyenne_Histo'] = debug_data.apply(lambda row: moy_histo.loc[tuple(row[col] for col in group_cols)][row['mois']] if len(group_cols) > 1 else moy_histo.loc[row['article']][row['mois']], axis=1)
    debug_data['Moyenne_Globale'] = debug_data.apply(lambda row: moy_globale.loc[tuple(row[col] for col in group_cols)] if len(group_cols) > 1 else moy_globale.loc[row['article']], axis=1)

    table_indices = indices.reset_index().melt(id_vars=group_cols, var_name='mois', value_name='Indice')
    
    # Ajout d'une colonne d'indice formaté comme Excel
    table_indices['Indice_Excel'] = table_indices['Indice'].apply(lambda x: excel_round(x, 1))

    df_sarr = df_realise.merge(table_indices, on=group_cols + ['mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)
    
    return table_indices, df_sarr, debug_data

# ==============================================================================
# FONCTION D'ANALYSE PÉRIODE MOMENTUM
# ==============================================================================
@st.cache_data(show_spinner="Génération du tableau...")
def generer_tableau_momentum(df_sarr: pd.DataFrame, periode_momentum: int, unite_affichage: str):
    df_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois'], ascending=[True, True, False, False]).copy()
    resultats = []
    
    for (ag, art), group in df_sorted.groupby(['agence', 'article']):
        group_n = group.head(periode_momentum).reset_index(drop=True)
        if len(group_n) == 0: continue
            
        row = {"Agence": ag, "Article": art}
        contenance = group_n.loc[0, 'contenance_cl'] if 'contenance_cl' in group_n.columns else 100.0
        multiplicateur = (10000 / contenance) if unite_affichage == "Cols" else 1.0
        
        for i in range(periode_momentum):
            if i < len(group_n):
                mois_val = int(group_n.loc[i, 'mois'])
                annee_val = int(group_n.loc[i, 'annee'])
                row[f"M-{i+1}"] = f"{MOIS_NOMS[mois_val-1].lower()}-{str(annee_val)[-2:]}"
            else:
                row[f"M-{i+1}"] = "-"
                
        for i in range(periode_momentum):
            if i < len(group_n): 
                # On utilise l'indice Excel arrondi pour l'affichage, mais le calcul du SARR garde la précision
                row[f"M{i+1}"] = group_n.loc[i, 'Indice']
            else: 
                row[f"M{i+1}"] = np.nan

        for i in range(periode_momentum):
            if i < len(group_n): 
                coef_val = group_n.loc[i, 'Indice'] # Précision maximale pour le calcul
                if pd.notna(coef_val) and coef_val > 0:
                    sarr_val = (group_n.loc[i, 'hl'] / coef_val) * multiplicateur
                else:
                    sarr_val = np.nan
                row[f"SARR M-{i+1}"] = sarr_val
            else: 
                row[f"SARR M-{i+1}"] = np.nan
                
        valides = [row[f"SARR M-{i+1}"] for i in range(periode_momentum) if pd.notna(row[f"SARR M-{i+1}"])]
        row["Moyenne SARR"] = np.mean(valides) if valides else np.nan
        
        resultats.append(row)
        
    df_final = pd.DataFrame(resultats)
    
    cols_ordered = ["Agence", "Article"]
    cols_ordered.extend([f"M-{i+1}" for i in range(periode_momentum)])
    cols_ordered.extend([f"M{i+1}" for i in range(periode_momentum)])
    cols_ordered.extend([f"SARR M-{i+1}" for i in range(periode_momentum)])
    cols_ordered.append("Moyenne SARR")
    
    return df_final[cols_ordered]

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
    
    periode_momentum = st.sidebar.slider("Période Momentum (Nombre de mois)", min_value=3, max_value=12, value=5, step=1)
    niveau_agregation = st.sidebar.radio("Niveau de calcul des indices", options=["Par Article (Global)", "Par Agence & Article"], index=0)

    fenetre_histo = st.sidebar.radio("Période pour les Coefs", options=["2 dernières années", "3 dernières années", "Tout l'historique"], index=0)
    methode_coef = st.sidebar.radio("Méthode de calcul", options=["Ratio des Sommes", "Moyenne des Ratios"], index=0)

    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["Cols", "HL"], index=0)

    table_indices, df_sarr, debug_data = calculer_indices_et_sarr(df_perimetre, annee_cloture, mois_cutoff, fenetre_histo, methode_coef, niveau_agregation)
    
    if df_sarr.empty:
        st.warning("⚠️ Impossible de calculer le SARR.")
        st.stop()

    df_analyse = generer_tableau_momentum(df_sarr, periode_momentum, unite_affichage)

    st.success(f"✅ Tableau généré avec succès.")
    
    tab_analyse, tab_verif, tab_indices = st.tabs([
        "📊 Tableau d'Analyse Période", 
        "🧮 Vérification Formule Excel",
        "📈 Table des Indices (Vue Globale)"
    ])

    with tab_analyse:
        st.subheader("Tableau Détaillé (Dates, Coefficients, SARR)")
        
        # Affichage calqué sur Excel (1 décimale)
        format_dict = {f"M{i+1}": "{:.1f}" for i in range(periode_momentum)}
        format_dict.update({f"SARR M-{i+1}": "{:,.1f}" for i in range(periode_momentum)})
        format_dict["Moyenne SARR"] = "{:,.2f}"
        
        st.dataframe(
            df_analyse.style.format(format_dict, na_rep="-"),
            use_container_width=True,
            height=400
        )

    with tab_verif:
        st.subheader("Vérification : Moyenne Histo / Moyenne Globale")
        st.write("Ce tableau reproduit exactement les colonnes D et E de ton fichier Excel : `Moyenne_Histo (Mois) / Moyenne_Globale`.")
        
        if len(sel_articles) > 0:
            if niveau_agregation == "Par Agence & Article" and len(sel_agences) > 0:
                dbg = debug_data[(debug_data['agence'] == sel_agences[0]) & (debug_data['article'] == sel_articles[0])].copy()
            else:
                dbg = debug_data[debug_data['article'] == sel_articles[0]].copy()

            if not dbg.empty:
                dbg['mois'] = dbg['mois'].map(lambda x: MOIS_NOMS[x-1])
                moy_globale = dbg['Moyenne_Globale'].values[0]
                
                st.info(f"**Moyenne Globale de l'article = {moy_globale:,.2f} HL**")
                
                dbg['Indice_Calculé'] = dbg['Moyenne_Histo'] / moy_globale
                
                st.dataframe(
                    dbg[['article'] + (['agence'] if niveau_agregation == "Par Agence & Article" else []) + ["mois", "Moyenne_Histo", "Indice_Calculé"]].style.format({
                        "Moyenne_Histo": "{:,.2f}",
                        "Indice_Calculé": "{:.6f}"
                    }),
                    use_container_width=True
                )
                st.warning("💡 **Analyse :** Si le mois de Mai affiche `0.8` dans le tableau final mais `0.8503` ici, c'est un problème d'arrondi standard (Python arrondit .5 à l'inférieur par défaut). Mais le SARR est calculé avec la vraie valeur.")
            else:
                st.write("Pas assez de données pour afficher le détail.")
        else:
            st.write("Sélectionne un article pour voir le détail.")

    with tab_indices:
        st.subheader("Table des Indices (Coefficients)")
        if niveau_agregation == "Par Agence & Article":
            pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice_Excel', aggfunc='first').fillna(1.0)
        else:
            pivot_indices = table_indices.pivot_table(index=['article'], columns='mois', values='Indice_Excel', aggfunc='first').fillna(1.0)
            
        pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
        st.dataframe(pivot_indices.style.format("{:.1f}"), use_container_width=True)

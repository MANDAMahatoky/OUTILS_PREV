import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import math

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision : Comparateur des 3 Calculs")

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
# ÉTAPE 4 : CALCUL DES INDICES
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices...")
def calculer_indices(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, fenetre_histo: str, methode_coef: str, niveau_agregation: str):
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame()

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
    
    vols_mois_cumules = vols.groupby(group_cols).sum()
    vols_annuels_cumules = vols_annuels.groupby(group_cols).sum()
    nb_annees = df_hist_complet.groupby(group_cols)['annee'].nunique()
    moy_histo = vols_mois_cumules.div(nb_annees, axis=0)
    moy_globale = vols_annuels_cumules / (12.0 * nb_annees)

    if methode_coef == "Moyenne des Ratios":
        ratios = vols.div(vols_annuels / 12.0, axis=0).replace([np.inf, -np.inf], np.nan)
        indices = ratios.groupby(group_cols).mean().fillna(1.0)
    else:
        indices = moy_histo.div(moy_globale, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    table_indices = indices.reset_index().melt(id_vars=group_cols, var_name='mois', value_name='Indice')
    table_indices['Indice_Arrondi'] = table_indices['Indice'].apply(lambda x: math.floor(x * 10 + 0.5) / 10)

    df_sarr = df_realise.merge(table_indices, on=group_cols + ['mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    
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

    table_indices, df_sarr = calculer_indices(df_perimetre, annee_cloture, mois_cutoff, fenetre_histo, methode_coef, niveau_agregation)
    
    if df_sarr.empty:
        st.warning("⚠️ Impossible de calculer le SARR.")
        st.stop()

    st.success(f"✅ Tableau généré avec succès.")
    
    st.markdown("---")
    st.subheader("🔍 Comparatif des 3 Calculs (sans aucune modification)")
    st.write("Ce tableau affiche les trois façons de calculer le SARR. Le calcul Excel est basé sur les coefficients exacts de ta capture d'écran.")
    
    if not df_sarr.empty:
        df_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois'], ascending=[True, True, False, False]).head(periode_momentum)
        
        # Valeurs exactes extraites de ta capture Excel
        excel_coefs = [1.0086, 0.7690, 0.7699, 0.8553, 0.9993]
        
        comp_data = []
        for i, (_, row) in enumerate(df_sorted.iterrows()):
            vol = row['hl'] * 100 # En Cols
            coef_python = row['Indice']
            coef_arrondi = row['Indice_Arrondi']
            
            # 1. Calcul Exact (Python)
            sarr_python = vol / coef_python if coef_python > 0 else 0
            
            # 2. Calcul Excel (Basé sur les coefficients exacts de l'Excel)
            coef_excel = excel_coefs[i] if i < len(excel_coefs) else 0
            sarr_excel = vol / coef_excel if coef_excel > 0 else 0
            
            # 3. Calcul Arrondi
            sarr_arrondi = vol / coef_arrondi if coef_arrondi > 0 else 0
            
            comp_data.append({
                "Mois": f"{MOIS_NOMS[row['mois']-1]}-{str(row['annee'])[-2:]}",
                "Volume (Cols)": vol,
                "1. Calcul Exact (Python)": sarr_python,
                "2. Calcul Excel (Réel)": sarr_excel,
                "3. Calcul Arrondi (Faux)": sarr_arrondi,
                "Coef Exact (Python)": coef_python,
                "Coef Excel": coef_excel,
                "Coef Arrondi": coef_arrondi,
            })
            
        st.dataframe(
            pd.DataFrame(comp_data).style.format({
                "Volume (Cols)": "{:,.0f}",
                "1. Calcul Exact (Python)": "{:,.1f}",
                "2. Calcul Excel (Réel)": "{:,.1f}",
                "3. Calcul Arrondi (Faux)": "{:,.1f}",
                "Coef Exact (Python)": "{:.4f}",
                "Coef Excel": "{:.4f}",
                "Coef Arrondi": "{:.1f}",
            }),
            use_container_width=True
        )
        
        st.info("💡 **Analyse :** Regarde la colonne `2. Calcul Excel`. Elle utilise les coefficients exacts de ton Excel. Tu verras qu'elle s'approche à 99% de la colonne `1. Calcul Exact`. La colonne `3. Calcul Arrondi` est fausse car elle utilise le coef arrondi.")
    else:
        st.write("Sélectionne un article pour voir la comparaison.")

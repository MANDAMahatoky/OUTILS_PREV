import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import altair as alt

st.set_page_config(page_title="Dashboard S&OP", layout="wide", page_icon="📊")
st.title("Dashboard S&OP : Focus Étape 6 (GAP)")

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
MOIS_ABB = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]

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
    df_enrichi["volume_unites"] = df_enrichi["hl"] * (10000 / df_enrichi["contenance_cl"].replace(0, 100.0))
    
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
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "volume_unites", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# ÉTAPES 4 & 5 : CALCUL DES INDICES, SARR ET PRÉVISIONS
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et projection...")
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cloture: int):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame()
    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    if df_hist.empty: df_hist = df_realise.copy()
        
    grille_hist = pd.MultiIndex.from_product([df_hist['agence'].unique(), df_hist['article'].unique(), df_hist['annee'].unique(), range(1, 13)], names=['agence', 'article', 'annee', 'mois']).to_frame(index=False)
    df_hist_grille = grille_hist.merge(df_hist, on=['agence', 'article', 'annee', 'mois'], how='left')
    df_hist_grille['volume_unites'] = df_hist_grille['volume_unites'].fillna(0.0)
    nb_annees = df_hist_grille.groupby(['agence', 'article'])['annee'].nunique().reset_index().rename(columns={'annee': 'nb_annees'})
    vol_mois = df_hist_grille.groupby(['agence', 'article', 'mois'])['volume_unites'].sum().reset_index()
    moy_mois = vol_mois.merge(nb_annees, on=['agence', 'article'])
    moy_mois['Moy_Mois'] = moy_mois['volume_unites'] / moy_mois['nb_annees']
    vol_total = df_hist_grille.groupby(['agence', 'article'])['volume_unites'].sum().reset_index().rename(columns={'volume_unites': 'vol_total'})
    moy_ann = vol_total.merge(nb_annees, on=['agence', 'article'])
    moy_ann['Moy_Ann'] = moy_ann['vol_total'] / (moy_ann['nb_annees'] * 12)
    indices = moy_mois.merge(moy_ann[['agence', 'article', 'Moy_Ann']], on=['agence', 'article'])
    indices['Indice'] = indices['Moy_Mois'] / indices['Moy_Ann'].replace(0, np.nan)
    indices['Indice'] = indices['Indice'].fillna(1.0)
    table_indices = indices[['agence', 'article', 'mois', 'Indice']]

    df_ytd = df_realise[df_realise["annee"] == annee_cloture].copy()
    df_projete = df_ytd.copy()
    ytd_totaux = df_ytd.groupby(['agence', 'article']).agg(vol_ytd=('volume_unites', 'sum'), contenance=('contenance_cl', 'first'), segment=('segment', 'first'), produit=('produit', 'first'), positionnement=('positionnement', 'first'), occasion=('occasion', 'first')).reset_index()
    for _, row in ytd_totaux.iterrows():
        ag, art = row['agence'], row['article']
        coefs_ecoules = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] <= mois_cloture)]['Indice'].sum()
        if coefs_ecoules == 0: coefs_ecoules = mois_cloture
        vol_annuel_proj = (row['vol_ytd'] / coefs_ecoules) * 12
        for m in range(mois_cloture + 1, 13):
            coef_data = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]
            coef_mois = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
            vol_projete = (vol_annuel_proj / 12) * coef_mois
            df_projete = pd.concat([df_projete, pd.DataFrame([{'annee': annee_cloture, 'mois': m, 'segment': row['segment'], 'produit': row['produit'], 'agence': ag, 'nature': 'Projeté', 'hl': vol_projete * (row['contenance'] / 10000), 'volume_unites': vol_projete, 'article': art, 'positionnement': row['positionnement'], 'occasion': row['occasion'], 'contenance_cl': row['contenance']}])], ignore_index=True)
    
    df_final = pd.concat([df_realise, df_projete], ignore_index=True).drop_duplicates(subset=['annee', 'mois', 'agence', 'article'])
    df_sarr = df_final.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR'] = df_sarr['volume_unites'] / df_sarr['Indice'].replace(0, 1.0)
    return table_indices, df_sarr

@st.cache_data(show_spinner="Calcul des prévisions...")
def calculer_previsions(df_sarr: pd.DataFrame, table_indices: pd.DataFrame, annee_cloture: int, mois_cloture: int, annee_cible: int, mois_cible: int):
    condition_realise = (df_sarr["annee"] < annee_cloture) | ((df_sarr["annee"] == annee_cloture) & (df_sarr["mois"] <= mois_cloture))
    df_hist = df_sarr[condition_realise].sort_values(['agence', 'article', 'annee', 'mois'])
    if df_hist.empty: return pd.DataFrame()
    df_hist['rang'] = df_hist.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_hist[df_hist['rang'] < 4].copy()
    
    nb_mois_a_projeter = (annee_cible - annee_cloture) * 12 + (mois_cible - mois_cloture)
    if nb_mois_a_projeter <= 0: return pd.DataFrame()

    previsions = []
    for (agence, article), group in df_derniers.groupby(['agence', 'article']):
        sarr_m = group[group['rang'] == 0]['SARR'].values[0] if len(group[group['rang'] == 0]) > 0 else 0
        sarr_m1 = group[group['rang'] == 1]['SARR'].values[0] if len(group[group['rang'] == 1]) > 0 else 0
        sarr_m2 = group[group['rang'] == 2]['SARR'].values[0] if len(group[group['rang'] == 2]) > 0 else 0
        sarr_m3 = group[group['rang'] == 3]['SARR'].values[0] if len(group[group['rang'] == 3]) > 0 else 0
        var1 = sarr_m - sarr_m1; var2 = sarr_m1 - sarr_m2; var3 = sarr_m2 - sarr_m3
        momentum = np.mean([var1, var2, var3])
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        contenance = group['contenance_cl'].values[0] if 'contenance_cl' in group else 100.0
        
        for i in range(1, nb_mois_a_projeter + 1):
            mois_futur = mois_cloture + i
            annee_futur = annee_cloture
            if mois_futur > 12:
                mois_futur -= 12
                annee_futur += 1
            indice_data = table_indices[(table_indices['agence'] == agence) & (table_indices['article'] == article) & (table_indices['mois'] == mois_futur)]
            indice = indice_data['Indice'].values[0] if not indice_data.empty else 1.0
            prev_unites = (indice * base) + momentum
            prev_unites = max(0.0, prev_unites)
            prev_hl = prev_unites * (contenance / 10000)
            previsions.append({"Agence": agence, "Article": article, "Annee": annee_futur, "Mois": mois_futur, "Date": f"{MOIS_ABB[mois_futur-1]}-{str(annee_futur)[-2:]}", "Indice": indice, "Base": base, "Momentum": momentum, "Prevision_HL": prev_hl, "Prevision_Unites": prev_unites})
    return pd.DataFrame(previsions)

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

    # --------------------------------------------------------------------------
    # FILTRES (Barre latérale)
    # --------------------------------------------------------------------------
    st.sidebar.header("🔍 Filtres")
    segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
    sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
    
    df_temp = df_enrichi.copy()
    if sel_segments:
        df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
    articles_dispo = sorted(df_temp["article"].unique())
    sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
    
    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")

    df_perimetre = df_enrichi.copy()
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Cutoff & Cible")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
    
    annee_cible = st.sidebar.number_input("Année Cible", min_value=2026, max_value=2035, value=2027)
    mois_cible = st.sidebar.selectbox("Mois Cible", options=list(range(1, 13)), index=0, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    objectif_global = st.sidebar.number_input("Objectif (Volume)", min_value=0.0, value=1000000.0, step=10000.0)
    unite = st.sidebar.radio("Unité d'affichage", options=["HL", "Unités"], index=1, horizontal=True)

    # Calculs
    table_indices, df_sarr = calculer_indices_et_sarr(df_perimetre, annee_cloture, mois_cloture)
    df_previsions = calculer_previsions(df_sarr, table_indices, annee_cloture, mois_cloture, annee_cible, mois_cible)

    if df_previsions.empty:
        st.warning("La date cible est antérieure ou égale à la date de clôture.")
        st.stop()

    col_val = "hl" if unite == "HL" else "volume_unites"
    col_prev = "Prevision_HL" if unite == "HL" else "Prevision_Unites"

    # ==============================================================================
    # FOCUS : ÉTAPE 6 (CALCUL DU GAP)
    # ==============================================================================
    st.header("🎯 Étape 6 : Analyse et Cohérence du GAP")
    
    # 1. Réalisé (Uniquement le réalisé jusqu'au cutoff)
    df_realise = df_sarr[df_sarr["nature"] == "Réalisé"]
    realise_art = df_realise.groupby("article")[col_val].sum().rename("Réalisé YTD")
    
    # 2. Prévisions (Fin d'année 2026 projetée + Prévisions 2027+)
    # On additionne le projeté de l'année en cours (si présent) et les prévisions futures
    df_projete_ytd = df_sarr[df_sarr["nature"] == "Projeté"]
    prev_ytd_art = df_projete_ytd.groupby("article")[col_val].sum().rename("Prévisions (Fin N)")
    prev_futures_art = df_previsions.groupby("Article")[col_prev].sum().rename("Prévisions (Futur)")
    
    # 3. Construction du tableau de cohérence
    df_gap = pd.concat([realise_art, prev_ytd_art, prev_futures_art], axis=1).fillna(0)
    df_gap["Total Prévisions"] = df_gap["Prévisions (Fin N)"] + df_gap["Prévisions (Futur)"]
    df_gap["Total Projeté"] = df_gap["Réalisé YTD"] + df_gap["Total Prévisions"]
    
    # 4. Application de la formule du diagramme
    df_gap["Objectif"] = objectif_global
    df_gap["GAP"] = df_gap["Objectif"] - df_gap["Total Projeté"]
    
    # 5. Alerte visuelle (Si GAP > 0, il manque du volume)
    df_gap["Alerte"] = np.where(df_gap["GAP"] > 0, "🔴 Manque", "🟢 Dépassé")
    
    # 6. Ajout d'une ligne "TOTAL"
    total_row = pd.DataFrame({
        "Réalisé YTD": [df_gap["Réalisé YTD"].sum()],
        "Prévisions (Fin N)": [df_gap["Prévisions (Fin N)"].sum()],
        "Prévisions (Futur)": [df_gap["Prévisions (Futur)"].sum()],
        "Total Prévisions": [df_gap["Total Prévisions"].sum()],
        "Total Projeté": [df_gap["Total Projeté"].sum()],
        "Objectif": [objectif_global],
        "GAP": [objectif_global - df_gap["Total Projeté"].sum()],
        "Alerte": ["🔴 Manque" if (objectif_global - df_gap["Total Projeté"].sum()) > 0 else "🟢 Dépassé"]
    }, index=["TOTAL"])
    
    df_gap_final = pd.concat([df_gap, total_row])
    
    # Affichage du tableau
    st.dataframe(
        df_gap_final,
        column_config={
            "Réalisé YTD": st.column_config.NumberColumn(format="%.0f"),
            "Prévisions (Fin N)": st.column_config.NumberColumn(format="%.0f"),
            "Prévisions (Futur)": st.column_config.NumberColumn(format="%.0f"),
            "Total Prévisions": st.column_config.NumberColumn(format="%.0f"),
            "Total Projeté": st.column_config.NumberColumn(format="%.0f"),
            "Objectif": st.column_config.NumberColumn(format="%.0f"),
            "GAP": st.column_config.NumberColumn(format="%.0f"),
        },
        use_container_width=True
    )

    # Affichage des KPI de la formule
    st.markdown("---")
    st.subheader("Formule appliquée")
    tot_real = df_gap["Réalisé YTD"].sum()
    tot_prev = df_gap["Total Prévisions"].sum()
    tot_proj = tot_real + tot_prev
    gap_global = objectif_global - tot_proj
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    col_f1.metric("1. Réalisé", f"{tot_real:,.0f}")
    col_f2.metric("2. Prévisions", f"{tot_prev:,.0f}")
    col_f3.metric("3. Total Projeté", f"{tot_proj:,.0f}", help="Réalisé + Prévisions")
    col_f4.metric("4. GAP", f"{gap_global:,.0f}", delta="- Manque" if gap_global > 0 else "+ Dépassement", delta_color="inverse" if gap_global > 0 else "normal", help="Objectif - Total Projeté")

import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import altair as alt

st.set_page_config(page_title="Dashboard S&OP", layout="wide", page_icon="📊")
st.title("Dashboard S&OP : Prévisions & GAP (100% HL)")

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
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "nature", "hl", "article", "positionnement", "occasion"]]

# ==============================================================================
# ÉTAPES 4 & 5 : CALCUL DES INDICES, SARR ET PRÉVISIONS (EN HL)
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et projection...")
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cloture: int):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame()
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
    indices['Indice'] = indices['Indice'].fillna(1.0)
    table_indices = indices[['agence', 'article', 'mois', 'Indice']]

    df_ytd = df_realise[df_realise["annee"] == annee_cloture].copy()
    df_projete = df_ytd.copy()
    ytd_totaux = df_ytd.groupby(['agence', 'article']).agg(vol_ytd=('hl', 'sum'), segment=('segment', 'first'), produit=('produit', 'first'), positionnement=('positionnement', 'first'), occasion=('occasion', 'first')).reset_index()
    for _, row in ytd_totaux.iterrows():
        ag, art = row['agence'], row['article']
        coefs_ecoules = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] <= mois_cloture)]['Indice'].sum()
        if coefs_ecoules == 0: coefs_ecoules = mois_cloture
        vol_annuel_proj = (row['vol_ytd'] / coefs_ecoules) * 12
        for m in range(mois_cloture + 1, 13):
            coef_data = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]
            coef_mois = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
            vol_projete = (vol_annuel_proj / 12) * coef_mois
            df_projete = pd.concat([df_projete, pd.DataFrame([{'annee': annee_cloture, 'mois': m, 'segment': row['segment'], 'produit': row['produit'], 'agence': ag, 'nature': 'Projeté', 'hl': vol_projete, 'article': art, 'positionnement': row['positionnement'], 'occasion': row['occasion']}])], ignore_index=True)
    
    df_final = pd.concat([df_realise, df_projete], ignore_index=True).drop_duplicates(subset=['annee', 'mois', 'agence', 'article'])
    df_sarr = df_final.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)
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
        
        for i in range(1, nb_mois_a_projeter + 1):
            mois_futur = mois_cloture + i
            annee_futur = annee_cloture
            if mois_futur > 12:
                mois_futur -= 12
                annee_futur += 1
            indice_data = table_indices[(table_indices['agence'] == agence) & (table_indices['article'] == article) & (table_indices['mois'] == mois_futur)]
            indice = indice_data['Indice'].values[0] if not indice_data.empty else 1.0
            prev_hl = (indice * base) + momentum
            prev_hl = max(0.0, prev_hl)
            previsions.append({"Agence": agence, "Article": article, "Annee": annee_futur, "Mois": mois_futur, "Date": f"{MOIS_ABB[mois_futur-1]}-{str(annee_futur)[-2:]}", "Indice": indice, "Base": base, "Momentum": momentum, "Prevision_HL": prev_hl})
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
    # ÉTAPE 2 : PÉRIMÈTRE (Filtres)
    # --------------------------------------------------------------------------
    st.sidebar.header("🔍 Étape 2 : Périmètre")
    
    segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
    if 'previous_segments' not in st.session_state:
        st.session_state.previous_segments = []
    sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
    
    if sel_segments != st.session_state.previous_segments:
        st.session_state.sel_articles = []
        st.session_state.previous_segments = sel_segments

    df_temp = df_enrichi.copy()
    if sel_segments:
        df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
    articles_dispo = sorted(df_temp["article"].unique())
    sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous", key="sel_articles")

    agences_dispo = sorted([a for a in df_enrichi["agence"].unique() if a != "Aucune vente"])
    sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")

    df_perimetre = df_enrichi.copy()
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    # --------------------------------------------------------------------------
    # PARAMÈTRES DE CALCUL & CIBLE
    # --------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Cutoff & Cible")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
    
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Cible de Prévision")
    annee_cible = st.sidebar.number_input("Année Cible", min_value=2026, max_value=2035, value=2027)
    mois_cible = st.sidebar.selectbox("Mois Cible", options=list(range(1, 13)), index=0, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    objectif_global = st.sidebar.number_input("Objectif (HL)", min_value=0.0, value=1000000.0, step=10000.0)

    # Calculs
    table_indices, df_sarr = calculer_indices_et_sarr(df_perimetre, annee_cloture, mois_cloture)
    df_previsions = calculer_previsions(df_sarr, table_indices, annee_cloture, mois_cloture, annee_cible, mois_cible)

    if df_previsions.empty:
        st.warning("La date cible est antérieure ou égale à la date de clôture.")
        st.stop()

    # ==============================================================================
    # ÉTAPE 6 & 7 : DASHBOARD & AFFICHAGE (TOUT EN HL)
    # ==============================================================================
    st.success(f"✅ Données prêtes pour la cible : {MOIS_ABB[mois_cible-1].capitalize()} {annee_cible} (100% HL).")
    
    df_realise = df_sarr[(df_sarr["annee"] == annee_cloture) & (df_sarr["mois"] <= mois_cloture)]
    df_prev_cible = df_previsions[(df_previsions["Annee"] == annee_cible) & (df_previsions["Mois"] == mois_cible)]
    
    tot_real = df_realise["hl"].sum()
    tot_prev = df_prev_cible["Prevision_HL"].sum()
    tot_proj = tot_real + tot_prev
    gap_global = objectif_global - tot_proj

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Réalisé YTD (HL)", f"{tot_real:,.2f} HL")
    kpi2.metric("Prévisions Cible (HL)", f"{tot_prev:,.2f} HL")
    kpi3.metric("Total Projeté (HL)", f"{tot_proj:,.2f} HL")
    
    if gap_global > 0:
        kpi4.metric("GAP vs Objectif", f"{gap_global:,.2f} HL", delta="- Manque", delta_color="inverse")
    else:
        kpi4.metric("GAP vs Objectif", f"{gap_global:,.2f} HL", delta="+ Dépassement", delta_color="normal")

    tab_tcd, tab_graph, tab_gap, tab_export = st.tabs(["🎯 Tableau Croisé (TCD)", "📈 Graphique", "🚨 Détail du GAP", "📥 Export"])

    with tab_tcd:
        st.subheader(f"Prévisions pour {MOIS_ABB[mois_cible-1].capitalize()} {annee_cible} (en HL)")
        if not df_prev_cible.empty:
            pivot = pd.pivot_table(df_prev_cible, values="Prevision_HL", index="Article", columns="Agence", aggfunc="sum", margins=True, margins_name="Total").fillna(0)
            st.dataframe(pivot.style.format("{:,.2f}"), use_container_width=True)
        else:
            st.info("Aucune prévision disponible pour ce mois.")

    with tab_graph:
        st.subheader("Évolution : Réalisé vs Prévisions (en HL)")
        df_reel = df_sarr.groupby(["annee", "mois"])["hl"].sum().reset_index()
        df_reel["Type"] = "Réalisé"
        df_reel["Date_Str"] = df_reel["annee"].astype(str) + "-" + df_reel["mois"].astype(str).str.zfill(2)
        
        df_prev = df_previsions.groupby(["Annee", "Mois"])["Prevision_HL"].sum().reset_index()
        df_prev["Type"] = "Prévision"
        df_prev["Date_Str"] = df_prev["Annee"].astype(str) + "-" + df_prev["Mois"].astype(str).str.zfill(2)
        
        df_chart = pd.concat([
            df_reel[["Date_Str", "hl", "Type"]].rename(columns={"hl": "Volume"}),
            df_prev[["Date_Str", "Prevision_HL", "Type"]].rename(columns={"Prevision_HL": "Volume"})
        ]).sort_values("Date_Str")

        chart = alt.Chart(df_chart).mark_line(point=True).encode(
            x=alt.X("Date_Str:N", sort=None, title="Période"),
            y=alt.Y("Volume:Q", title="Volume (HL)"),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Réalisé", "Prévision"], range=["#9E6315EF", "#9BD69E"])),
            tooltip=["Date_Str", "Type", alt.Tooltip("Volume:Q", format=",.2f")]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

    with tab_gap:
        st.subheader("Analyse du GAP par Article")
        
        realise_art = df_realise.groupby("article")["hl"].sum().rename("Réalisé YTD")
        prev_cible_art = df_prev_cible.groupby("Article")["Prevision_HL"].sum().rename("Prévisions Cible")
        
        df_gap = pd.concat([realise_art, prev_cible_art], axis=1).fillna(0)
        df_gap["Total Projeté"] = df_gap["Réalisé YTD"] + df_gap["Prévisions Cible"]
        
        df_gap["Objectif"] = objectif_global
        df_gap["GAP"] = df_gap["Objectif"] - df_gap["Total Projeté"]
        df_gap["Alerte"] = np.where(df_gap["GAP"] > 0, "🔴 Manque", "🟢 Dépassé")
        
        total_row = pd.DataFrame({
            "Réalisé YTD": [df_gap["Réalisé YTD"].sum()],
            "Prévisions Cible": [df_gap["Prévisions Cible"].sum()],
            "Total Projeté": [df_gap["Total Projeté"].sum()],
            "Objectif": [objectif_global],
            "GAP": [objectif_global - df_gap["Total Projeté"].sum()],
            "Alerte": ["🔴 Manque" if (objectif_global - df_gap["Total Projeté"].sum()) > 0 else "🟢 Dépassé"]
        }, index=["TOTAL"])
        
        df_gap_final = pd.concat([df_gap, total_row])
        
        st.dataframe(
            df_gap_final,
            column_config={
                "Réalisé YTD": st.column_config.NumberColumn(format="%.2f"),
                "Prévisions Cible": st.column_config.NumberColumn(format="%.2f"),
                "Total Projeté": st.column_config.NumberColumn(format="%.2f"),
                "Objectif": st.column_config.NumberColumn(format="%.2f"),
                "GAP": st.column_config.NumberColumn(format="%.2f"),
            },
            use_container_width=True
        )

    with tab_export:
        st.subheader("Exporter les données")
        tampon = io.BytesIO()
        with pd.ExcelWriter(tampon, engine="openpyxl") as xl:
            df_previsions.to_excel(xl, index=False, sheet_name="Previsions_Detail")
            if 'pivot' in locals():
                pivot.to_excel(xl, sheet_name="TCD_Previsions")
            df_gap.to_excel(xl, sheet_name="Analyse_GAP")
        
        st.download_button(
            "📥 Télécharger le fichier Excel complet",
            data=tampon.getvalue(),
            file_name=f"Export_SOP_{annee_cible}_{MOIS_ABB[mois_cible-1]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

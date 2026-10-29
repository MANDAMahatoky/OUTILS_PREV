import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import base64

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stMetric label { font-size: 1rem !important; color: #555; }
    .stMetric div[data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #111; font-weight: bold; }
    h1 { color: #1f77b4; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; border-radius: 5px 5px 0 0; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Moteur de Prévision S&OP")
st.markdown("**Étapes 4, 5.1 et 5.2 : Indices, Momentum, Base et Prévisions (CAGR)**")
st.divider()

# ==============================================================================
# DICTIONNAIRE DE CORRESPONDANCE AGENCE -> REGION
# ==============================================================================
MAPPING_REGIONS = {
    "11-Andranomahery": "Centre", "12-Antsirabe": "Centre",
    "01-Tanjombato": "Est", "09-Tamatave": "Est",
    "03-Usine-Diego": "Nord", "07-Majunga": "Nord", "18-Ambanja": "Nord",
    "19-Sambava": "Nord", "21-Nosy-Be": "Nord",
    "04-Tulear": "Sud", "05-Fianarantsoa": "Sud", "06-Ihosy": "Sud",
    "08-Manakara": "Sud", "23-Morondova": "Sud", "24-Fort-Dauphin": "Sud"
}

def get_region(agence):
    return MAPPING_REGIONS.get(str(agence).strip(), None)

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
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="text-decoration: none; color: white; background-color: #28a745; padding: 8px 15px; border-radius: 5px; font-size: 14px;">📥 Télécharger {filename}</a>'

# ==============================================================================
# ÉTAPE 1 : CHARGEMENT ET ENRICHISSEMENT
# ==============================================================================
@st.cache_data(show_spinner="Chargement et traitement des données...")
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
    
    df_ref = df_ref.drop_duplicates(subset=["article_original"]).reset_index(drop=True)

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
    
    df_enrichi["region"] = df_enrichi["agence"].apply(get_region)
    
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
    return df_enrichi[["annee", "mois", "segment", "produit", "region", "agence", "hl", "article", "positionnement", "occasion", "contenance_cl"]]

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
# ÉTAPES 4, 5.1 & 5.2 : CALCULS
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices, du Momentum et des Prévisions...")
def calculer_modele(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, annee_min_histo: int, annee_max_histo: int, 
                    methode_coef: str, niveau_agregation: str, annee_cible: int, 
                    use_rounded_coef: bool, forced_cagr: float, forced_base: float):
    
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, None, None, None

    df_hist = df_realise[(df_realise["annee"] >= annee_min_histo) & (df_realise["annee"] <= annee_max_histo)].copy()
    if df_hist.empty: return None, None, None, None, None, None, None

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
    
    # Option : Utiliser les coefficients arrondis pour le SARR
    if use_rounded_coef:
        table_indices['Indice'] = table_indices['Indice'].round(1)

    df_sarr = df_realise.merge(table_indices, on=group_cols + ['mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    # --- ÉTAPE 5.1 : MOMENTUM & BASE ---
    df_sarr_sorted = df_sarr.sort_values(group_cols + ['annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(group_cols).cumcount(ascending=False)
    
    resultats_momentum = []
    resultats_vue_excel = []
    resultats_audit_m1_m2 = []
    
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
        
        contenance = group['contenance_cl'].iloc[0] if 'contenance_cl' in group.columns else 100.0
        multiplicateur = 10000 / contenance
        
        date_m1 = f"{MOIS_NOMS[int(row_m1['mois'].values[0])-1]}-{str(int(row_m1['annee'].values[0]))[-2:]}" if not row_m1.empty else "-"
        date_m2 = f"{MOIS_NOMS[int(row_m2['mois'].values[0])-1]}-{str(int(row_m2['annee'].values[0]))[-2:]}" if not row_m2.empty else "-"
        
        momentum = sarr_m1 - sarr_m2
        
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base_calc = max(sarr_m, moy_3_mois)
        
        # Option : Forcer la Base
        base_final = forced_base if forced_base > 0 else base_calc
        
        resultats_momentum.append({
            "agence": ag, "article": art, 
            "Mois M-1": date_m1, "SARR M-1": sarr_m1,
            "Mois M-2": date_m2, "SARR M-2": sarr_m2,
            "SARR M": sarr_m,
            "Moyenne M1-M2-M3": moy_3_mois,
            "Momentum_HL": momentum, 
            "Base_HL": base_final,
            "Multiplicateur": multiplicateur
        })

        if not row_m1.empty and not row_m2.empty:
            resultats_audit_m1_m2.append({
                "Agence": ag, "Article": art,
                "Mois M-1": date_m1, "Volume M-1 (HL)": row_m1['hl'].values[0], "Indice M-1": row_m1['Indice'].values[0], "SARR M-1 (HL)": sarr_m1,
                "Mois M-2": date_m2, "Volume M-2 (HL)": row_m2['hl'].values[0], "Indice M-2": row_m2['Indice'].values[0], "SARR M-2 (HL)": sarr_m2
            })

        row_vue = {"agence": ag, "article": art}
        for i in range(1, 13):
            row_r = group[group['rang'] == i]
            if not row_r.empty:
                m_val = int(row_r['mois'].values[0])
                a_val = int(row_r['annee'].values[0])
                row_vue[f"M-{i} (Date)"] = f"{MOIS_NOMS[m_val-1].lower()}-{str(a_val)[-2:]}"
                row_vue[f"M-{i} (Vol)"] = row_r['hl'].values[0]
                row_vue[f"M-{i} (SARR)"] = row_r['SARR_HL'].values[0]
            else:
                row_vue[f"M-{i} (Date)"] = "-"
                row_vue[f"M-{i} (Vol)"] = 0
                row_vue[f"M-{i} (SARR)"] = 0
        resultats_vue_excel.append(row_vue)
        
    df_momentum = pd.DataFrame(resultats_momentum)
    df_vue_excel = pd.DataFrame(resultats_vue_excel)
    df_audit = pd.DataFrame(resultats_audit_m1_m2)

    # --- ÉTAPE 5.2 : PRÉVISIONS AVEC CAGR ---
    resultats_previsions = []
    
    for _, row in df_momentum.iterrows():
        ag, art = row['agence'], row['article']
        base, momentum = row['Base_HL'], row['Momentum_HL']
        multiplicateur = row['Multiplicateur']
        
        art_hist = df_hist[df_hist['article'] == art]
        if len(group_cols) == 2:
            art_hist = art_hist[art_hist['agence'] == ag]
            
        vol_debut = art_hist[art_hist['annee'] == annee_min_histo]['hl'].sum()
        vol_fin = art_hist[art_hist['annee'] == annee_max_histo]['hl'].sum()
        nb_ans = annee_max_histo - annee_min_histo
        
        if nb_ans > 0 and vol_debut > 0 and vol_fin > 0:
            cagr_val = ((vol_fin / vol_debut) ** (1 / nb_ans)) - 1
        else:
            cagr_val = 0.0
            
        # Option : Forcer le CAGR
        cagr_final = forced_cagr / 100.0 if forced_cagr != 0 else cagr_val

        for y in range(annee_cloture, annee_cible + 1):
            multiplicateur_cagr = (1 + cagr_final) ** (y - annee_cloture)
            
            for m in range(1, 13):
                if y == annee_cloture and m <= mois_cutoff: continue
                
                if len(group_cols) == 2:
                    coef_data = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]
                else:
                    coef_data = table_indices[(table_indices['article'] == art) & (table_indices['mois'] == m)]
                
                coef = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
                
                prev_hl = ((coef * base) + momentum) * multiplicateur_cagr
                prev_hl = max(0.0, prev_hl)
                prev_cols = prev_hl * multiplicateur
                
                resultats_previsions.append({
                    "annee": y, "mois": m, "agence": ag, "article": art,
                    "Date": f"{MOIS_NOMS[m-1]}-{str(y)[-2:]}",
                    "Indice": coef, "Base": base, "Momentum": momentum,
                    "CAGR (%)": cagr_final * 100,
                    "Prevision_HL": prev_hl,
                    "Prevision_Cols": prev_cols
                })

    df_previsions = pd.DataFrame(resultats_previsions)
    
    return table_indices, df_sarr, df_momentum, df_hist, df_previsions, df_vue_excel, df_audit

# ==============================================================================
# FONCTION DE COLORATION
# ==============================================================================
def color_cells(val):
    try:
        val = float(val)
        if val < 0.999:
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        elif val > 1.001:
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        else:
            return 'background-color: #e2e3e5; color: #383d41;'
    except:
        return ''

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col_info, col_app = st.columns([1, 3])

with col_info:
    st.markdown("### 📖 Guide Méthodologique")
    st.info("Calculs dynamiques et transparents.")
    with st.expander("1. Indices de Saisonnalité", expanded=True):
        st.markdown("🟩 **Vert (> 1.0)** : Mois Fort\n🟥 **Rouge (< 1.0)** : Mois Faible")
    with st.expander("2. SARR & Momentum", expanded=True):
        st.markdown("**SARR** : `Volume / Indice`.\n**Momentum** : Variation M-1 vs M-2.")
    with st.expander("3. Prévisions (CAGR)", expanded=True):
        st.markdown("**Formule** : `(Indice * Base + Momentum) * (1 + CAGR)^n`.")

with col_app:
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            fichier_ventes = st.file_uploader("📁 1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
        with col2:
            fichier_ref = st.file_uploader("📁 2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"])

    if fichier_ventes is not None and fichier_ref is not None:
        df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue())

        st.sidebar.header("🔍 1. Périmètre d'analyse")
        
        regions_dispo = sorted([r for r in df_enrichi["region"].unique() if pd.notna(r) and r != "Autre Région"])
        sel_regions = st.sidebar.multiselect("🌍 Région", options=regions_dispo, placeholder="Toutes")
        
        df_temp = df_enrichi.copy()
        if sel_regions: df_temp = df_temp[df_temp["region"].isin(sel_regions)]
        
        segments_dispo = sorted([s for s in df_temp["segment"].unique() if pd.notna(s)])
        sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
        if sel_segments: df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
        
        positions_dispo = sorted([p for p in df_temp["positionnement"].unique() if pd.notna(p)])
        sel_positions = st.sidebar.multiselect("🎯 Positionnement", options=positions_dispo, placeholder="Tous")
        if sel_positions: df_temp = df_temp[df_temp["positionnement"].isin(sel_positions)]
        
        occasions_dispo = sorted([o for o in df_temp["occasion"].unique() if pd.notna(o)])
        sel_occasions = st.sidebar.multiselect("🥂 Occasion", options=occasions_dispo, placeholder="Toutes")
        if sel_occasions: df_temp = df_temp[df_temp["occasion"].isin(sel_occasions)]

        contenances_dispo = sorted([c for c in df_temp["contenance_cl"].unique() if pd.notna(c)])
        sel_contenances = st.sidebar.multiselect("🧴 Contenance (cl)", options=contenances_dispo, placeholder="Toutes")
        if sel_contenances: df_temp = df_temp[df_temp["contenance_cl"].isin(sel_contenances)]

        articles_dispo = sorted(df_temp["article"].unique())
        sel_articles = st.sidebar.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
        
        agences_dispo = sorted([a for a in df_temp["agence"].unique() if a != "Aucune vente"])
        sel_agences = st.sidebar.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")

        df_perimetre = df_enrichi.copy()
        if sel_regions: df_perimetre = df_perimetre[df_perimetre["region"].isin(sel_regions)]
        if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
        if sel_positions: df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_positions)]
        if sel_occasions: df_perimetre = df_perimetre[df_perimetre["occasion"].isin(sel_occasions)]
        if sel_contenances: df_perimetre = df_perimetre[df_perimetre["contenance_cl"].isin(sel_contenances)]
        if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
        if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ 2. Paramètres du Modèle")
        
        annee_min_reelle = int(df_perimetre["annee"].min()) if not df_perimetre.empty else 2020
        annee_max_reelle = int(df_perimetre["annee"].max()) if not df_perimetre.empty else 2026
        
        with st.sidebar.expander("📅 Intervalle Historique", expanded=True):
            st.success(f"Données détectées : **{annee_min_reelle}** à **{annee_max_reelle}**")
            annee_min_histo = st.number_input("Année Min (Début)", min_value=2015, max_value=2030, value=2024)
            annee_max_histo = st.number_input("Année Max (Fin)", min_value=annee_min_histo, max_value=2030, value=2025)
            
        with st.sidebar.expander("🎯 Cutoff & Cible", expanded=True):
            annee_cloture = st.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
            mois_cutoff = st.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=9, format_func=lambda m: f"{m} - {MOIS_NOMS[m-1]}")
            
            st.markdown("---")
            annee_cible = st.number_input("Année Cible (Prévisions)", min_value=annee_cloture, max_value=2035, value=2027)
            
        with st.sidebar.expander("🛠️ Options de Calcul", expanded=False):
            niveau_agregation = st.radio("Niveau d'agrégation", options=["Par Agence & Article", "Par Article (Global)"], index=0)
            methode_coef = st.radio("Méthode de calcul", options=["Ratio des Sommes", "Moyenne des Ratios"], index=0)
            unite_affichage = st.radio("Unité d'affichage", options=["Cols", "HL"], index=0)

        with st.sidebar.expander("🔧 Réplique Excel (Optionnel)", expanded=False):
            st.write("Permet de forcer les paramètres si Excel utilise des chiffres figés.")
            use_rounded_coef = st.checkbox("Utiliser les coefficients arrondis (1 décimale)", value=False, help="Excel arrondit parfois l'affichage mais utilise la valeur exacte. Cochez ceci si vos SARR ne collent pas.")
            forced_cagr = st.number_input("Forcer le CAGR (%) (0 = auto)", min_value=-100.0, max_value=200.0, value=0.0, step=0.1)
            forced_base = st.number_input("Forcer la Base (HL) (0 = auto)", min_value=0.0, max_value=100000.0, value=0.0, step=10.0)

        # VÉRIFICATION
        annees_manquantes, annees_incompletes, annees_completes = verifier_integrite_historique(df_perimetre, annee_min_histo, annee_max_histo)

        if annees_manquantes or annees_incompletes:
            st.error("🚨 **Calcul interrompu : Données historiques incomplètes.**")
            if annees_manquantes:
                st.warning(f"Les années suivantes n'existent pas : **{', '.join(map(str, annees_manquantes))}**.")
            if annees_incompletes:
                st.warning(f"Les années suivantes sont incomplètes (moins de 12 mois) : **{', '.join(map(str, annees_incompletes))}**.")
            
            if annees_completes:
                st.info(f"💡 **Proposition :** Modifiez l'intervalle. Données complètes pour : **{', '.join(map(str, annees_completes))}**. Sélectionnez Min=**{annees_completes[0]}** et Max=**{annees_completes[-1]}**.")
            st.stop()

        # CALCULS
        table_indices, df_sarr, df_momentum, df_hist, df_previsions, df_vue_excel, df_audit = calculer_modele(
            df_perimetre, annee_cloture, mois_cutoff, annee_min_histo, annee_max_histo, methode_coef, niveau_agregation, annee_cible,
            use_rounded_coef, forced_cagr, forced_base
        )
        
        if table_indices is None:
            st.error("⚠️ Impossible de calculer le modèle.")
        else:
            # --- KPIs GLOBAUX ---
            with st.container(border=True):
                kpi1, kpi2, kpi3 = st.columns(3)
                vol_total = df_hist["hl"].sum()
                kpi1.metric(f"Volume Histo {annee_min_histo}-{annee_max_histo} (HL)", f"{vol_total:,.0f}")
                
                nb_articles_filtres = df_hist['article'].nunique()
                nb_articles_total = df_enrichi['article'].nunique()
                kpi2.metric("Nb Articles Histo", f"{nb_articles_filtres} / {nb_articles_total}")
                
                kpi3.metric("Nb Agences Histo", f"{df_hist[df_hist['agence'] != 'Aucune vente']['agence'].nunique()}")
            
            st.success(f"✅ Modèle calculé sur l'intervalle {annee_min_histo} - {annee_max_histo}.")
            
            # --- TABS DE RESULTATS ---
            tab_indices, tab_momentum, tab_prev, tab_audit, tab_vue = st.tabs([
                "📊 Indices", "📈 Momentum & Base", "🚀 5.2 Prévisions", "🔍 Audit M-1 / M-2", "🔍 Vue Excel"
            ])

            with tab_indices:
                with st.container(border=True):
                    st.subheader("Table des Indices")
                    if niveau_agregation == "Par Agence & Article":
                        pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
                    else:
                        pivot_indices = table_indices.pivot_table(index=['article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
                    pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
                    
                    try:
                        styled_df = pivot_indices.style.map(color_cells).format("{:.1f}")
                    except AttributeError:
                        styled_df = pivot_indices.style.applymap(color_cells).format("{:.1f}")
                    st.dataframe(styled_df, use_container_width=True, height=400)

            with tab_momentum:
                with st.container(border=True):
                    st.subheader("Calcul du Momentum et de la Base")
                    
                    if unite_affichage == "Cols":
                        df_momentum["Momentum_Aff"] = df_momentum["Momentum_HL"] * df_momentum["Multiplicateur"]
                        df_momentum["Base_Aff"] = df_momentum["Base_HL"] * df_momentum["Multiplicateur"]
                        
                        st.dataframe(
                            df_momentum[["agence", "article", "Mois M-1", "SARR M-1", "Mois M-2", "SARR M-2", "Momentum_Aff", "Base_Aff"]],
                            column_config={
                                "SARR M-1": st.column_config.NumberColumn("SARR M-1 (HL)", format="%.2f"),
                                "SARR M-2": st.column_config.NumberColumn("SARR M-2 (HL)", format="%.2f"),
                                "Momentum_Aff": st.column_config.NumberColumn("Momentum (Cols)", format="%.2f"),
                                "Base_Aff": st.column_config.NumberColumn("Base (Cols)", format="%.2f"),
                            },
                            use_container_width=True, height=400
                        )
                    else:
                        st.dataframe(
                            df_momentum[["agence", "article", "Mois M-1", "SARR M-1", "Mois M-2", "SARR M-2", "Momentum_HL", "Base_HL"]],
                            column_config={
                                "SARR M-1": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                                "SARR M-2": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                                "Momentum_HL": st.column_config.NumberColumn("Momentum", format="%.2f"),
                                "Base_HL": st.column_config.NumberColumn("Base", format="%.2f"),
                            },
                            use_container_width=True, height=400
                        )

            with tab_prev:
                with st.container(border=True):
                    st.subheader(f"Prévisions Finales avec CAGR jusqu'en {annee_cible}")
                    if unite_affichage == "Cols":
                        col_aff = "Prevision_Cols"
                    else:
                        col_aff = "Prevision_HL"

                    st.markdown("### 📊 TCD des Prévisions Mensuelles")
                    pivot_prev = df_previsions.pivot_table(
                        index=['annee', 'agence', 'article'], columns='mois', values=col_aff, aggfunc='sum'
                    )
                    pivot_prev.columns = [MOIS_NOMS[c-1] for c in pivot_prev.columns]
                    pivot_prev['Total Année'] = pivot_prev.sum(axis=1)
                    st.dataframe(pivot_prev.style.format("{:,.2f}", na_rep="-"), use_container_width=True)

            with tab_audit:
                st.subheader("🔍 Audit des Composants (M-1 et M-2)")
                st.write("Compare ces chiffres avec ton Excel !")
                st.dataframe(
                    df_audit.style.format({
                        "Volume M-1 (HL)": "{:,.2f}", "Indice M-1": "{:.4f}", "SARR M-1 (HL)": "{:,.2f}",
                        "Volume M-2 (HL)": "{:,.2f}", "Indice M-2": "{:.4f}", "SARR M-2 (HL)": "{:,.2f}"
                    }),
                    use_container_width=True
                )

            with tab_vue:
                st.subheader("Validation : Historique Décalé (M-1 à M-12)")
                if unite_affichage == "Cols":
                    df_vue_aff = df_vue_excel.copy()
                    contenance_map = df_enrichi.drop_duplicates(subset=['article']).set_index('article')['contenance_cl'].to_dict()
                    for i in range(1, 13):
                        df_vue_aff[f"M-{i} (Vol)"] = df_vue_aff.apply(lambda row: row[f"M-{i} (Vol)"] * (10000 / contenance_map.get(row['article'], 100)), axis=1)
                        df_vue_aff[f"M-{i} (SARR)"] = df_vue_aff.apply(lambda row: row[f"M-{i} (SARR)"] * (10000 / contenance_map.get(row['article'], 100)), axis=1)
                else:
                    df_vue_aff = df_vue_excel.copy()

                if len(sel_articles) > 0: df_vue_aff = df_vue_aff[df_vue_aff["article"].isin(sel_articles)]
                if len(sel_agences) > 0: df_vue_aff = df_vue_aff[df_vue_aff["agence"].isin(sel_agences)]

                st.dataframe(df_vue_aff, use_container_width=True, height=400)

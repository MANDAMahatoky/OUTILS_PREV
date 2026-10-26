import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étapes 1 à 5 : S&OP", layout="wide")
st.title("Moteur de Prévision S&OP : Étape 5 (Cohérence Excel)")

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
@st.cache_data(show_spinner="Chargement des fichiers...")
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
            df["segment"].astype(str).str.contains("total", case=False, na=False) | 
            df["produit"].astype(str).str.contains("total", case=False, na=False) |
            df["agence"].astype(str).str.contains("total", case=False, na=False) | 
            df["nature"].astype(str).str.contains("total", case=False, na=False) |
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
# ÉTAPE 4 : CALCUL DES INDICES ET DU SARR
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et du SARR...")
def calculer_indices_et_sarr(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cloture: int):
    condition_realise = (df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cloture))
    df_realise = df_perimetre[condition_realise].copy()

    if df_realise.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_hist_coef = df_realise[df_realise['annee'] < annee_cloture].copy()
    if df_hist_coef.empty:
        df_hist_coef = df_realise.copy()

    grille_complete = pd.MultiIndex.from_product(
        [df_hist_coef['agence'].unique(), df_hist_coef['article'].unique(), df_hist_coef['annee'].unique(), range(1, 13)],
        names=['agence', 'article', 'annee', 'mois']
    ).to_frame(index=False)

    df_hist_complet = grille_complete.merge(df_hist_coef, on=['agence', 'article', 'annee', 'mois'], how='left')
    df_hist_complet['volume_unites'] = df_hist_complet['volume_unites'].fillna(0.0)

    nb_annees = df_hist_complet.groupby(['agence', 'article'])['annee'].nunique().reset_index().rename(columns={'annee': 'nb_annees'})
    vol_mois = df_hist_complet.groupby(['agence', 'article', 'mois'])['volume_unites'].sum().reset_index()
    moy_mois = vol_mois.merge(nb_annees, on=['agence', 'article'])
    moy_mois['Moy_Mois'] = moy_mois['volume_unites'] / moy_mois['nb_annees']

    vol_total = df_hist_complet.groupby(['agence', 'article'])['volume_unites'].sum().reset_index().rename(columns={'volume_unites': 'vol_total'})
    moy_ann = vol_total.merge(nb_annees, on=['agence', 'article'])
    moy_ann['Moy_Ann'] = moy_ann['vol_total'] / (moy_ann['nb_annees'] * 12)

    indices = moy_mois.merge(moy_ann[['agence', 'article', 'Moy_Ann']], on=['agence', 'article'])
    indices['Indice'] = indices['Moy_Mois'] / indices['Moy_Ann'].replace(0, np.nan)
    indices['Indice'] = indices['Indice'].fillna(1.0)

    table_indices = indices[['agence', 'article', 'mois', 'Indice']]

    df_sarr = df_perimetre.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR'] = df_sarr['volume_unites'] / df_sarr['Indice'].replace(0, 1.0)

    return table_indices, df_sarr

# ==============================================================================
# ÉTAPE 5 : CALCUL DU MOMENTUM ET DES PRÉVISIONS
# ==============================================================================
def calculer_previsions(df_sarr: pd.DataFrame, table_indices: pd.DataFrame, annee_cloture: int, mois_cloture: int, arrondir_indice: bool):
    condition_realise = (df_sarr["annee"] < annee_cloture) | ((df_sarr["annee"] == annee_cloture) & (df_sarr["mois"] <= mois_cloture))
    df_hist = df_sarr[condition_realise].sort_values(['agence', 'article', 'annee', 'mois'])
    
    if df_hist.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_hist['rang'] = df_hist.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_hist[df_hist['rang'] < 4].copy()
    
    previsions = []
    verification = []
    
    for (agence, article), group in df_derniers.groupby(['agence', 'article']):
        sarr_m = group[group['rang'] == 0]['SARR'].values[0] if len(group[group['rang'] == 0]) > 0 else 0
        sarr_m1 = group[group['rang'] == 1]['SARR'].values[0] if len(group[group['rang'] == 1]) > 0 else 0
        sarr_m2 = group[group['rang'] == 2]['SARR'].values[0] if len(group[group['rang'] == 2]) > 0 else 0
        sarr_m3 = group[group['rang'] == 3]['SARR'].values[0] if len(group[group['rang'] == 3]) > 0 else 0
        
        var1 = sarr_m - sarr_m1
        var2 = sarr_m1 - sarr_m2
        var3 = sarr_m2 - sarr_m3
        momentum = np.mean([var1, var2, var3])
        
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        
        verification.append({
            "Agence": agence,
            "Article": article,
            "SARR M (Dernier)": round(sarr_m),
            "SARR M-1": round(sarr_m1),
            "SARR M-2": round(sarr_m2),
            "SARR M-3": round(sarr_m3),
            "Moyenne M-1,M-2,M-3": round(moy_3_mois),
            "Base retenue": round(base),
            "Momentum": round(momentum)
        })
        
        contenance = group['contenance_cl'].values[0] if 'contenance_cl' in group else 100.0
        
        for i in range(1, 13):
            mois_futur = mois_cloture + i
            annee_futur = annee_cloture
            if mois_futur > 12:
                mois_futur -= 12
                annee_futur += 1
            
            indice_data = table_indices[(table_indices['agence'] == agence) & (table_indices['article'] == article) & (table_indices['mois'] == mois_futur)]
            indice = indice_data['Indice'].values[0] if not indice_data.empty else 1.0
            
            # FIX : On arrondit l'indice à 1 décimale si demandé
            indice_calcul = round(indice, 1) if arrondir_indice else indice
            
            prev_unites = (indice_calcul * base) + momentum
            prev_unites = max(0.0, prev_unites)
            
            prev_hl = prev_unites * (contenance / 10000)
            
            previsions.append({
                "Agence": agence,
                "Article": article,
                "Annee": annee_futur,
                "Mois": mois_futur,
                "Date": f"{MOIS_ABB[mois_futur-1]}-{str(annee_futur)[-2:]}",
                "Indice": indice_calcul,
                "Base": base,
                "Momentum": momentum,
                "Prevision_Unites": prev_unites,
                "Prevision_HL": prev_hl
            })
            
    return pd.DataFrame(previsions), pd.DataFrame(verification)

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"], key="ventes")
with col2:
    fichier_ref = st.file_uploader("2. Fichier Référentiel (Classeur2.xlsx)", type=["xlsx"], key="ref")

if fichier_ventes is not None and fichier_ref is not None:
    
    df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue())

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

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Paramètres du Cutoff")
    annee_cloture = st.sidebar.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
    mois_cloture = st.sidebar.selectbox("Mois Pivot (M-1)", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    # FIX : Option pour arrondir comme Excel
    arrondir_indice = st.sidebar.checkbox("Arrondir les indices (comme Excel)", value=True)

    # Calculs
    table_indices, df_sarr = calculer_indices_et_sarr(df_perimetre, annee_cloture, mois_cloture)
    df_previsions, df_verification = calculer_previsions(df_sarr, table_indices, annee_cloture, mois_cloture, arrondir_indice)

    st.success("✅ Étapes 1 à 5 complétées !")
    
    tab_verif, tab_etape5 = st.tabs([
        "🔍 Vérification des calculs (Momentum & Base)",
        "🚀 Tableau des Prévisions (Oct-26 à Sept-27)"
    ])

    with tab_verif:
        st.markdown("#### Détail des calculs (SARR, Base, Momentum)")
        st.write("Ce tableau vous montre exactement les SARR utilisés. Si les chiffres correspondent à votre Excel, le reste suivra.")
        
        if not df_verification.empty:
            st.dataframe(
                df_verification,
                column_config={
                    "SARR M (Dernier)": st.column_config.NumberColumn(format="%.0f"),
                    "SARR M-1": st.column_config.NumberColumn(format="%.0f"),
                    "SARR M-2": st.column_config.NumberColumn(format="%.0f"),
                    "SARR M-3": st.column_config.NumberColumn(format="%.0f"),
                    "Moyenne M-1,M-2,M-3": st.column_config.NumberColumn(format="%.0f"),
                    "Base retenue": st.column_config.NumberColumn(format="%.0f"),
                    "Momentum": st.column_config.NumberColumn(format="%.0f")
                },
                use_container_width=True
            )

    with tab_etape5:
        st.markdown("#### Table des Prévisions (Étape 5)")
        st.info("Les indices sont arrondis à 1 décimale pour correspondre au calcul Excel. Exemple : 1.074 devient 1.1.")
        
        if not df_previsions.empty:
            st.dataframe(
                df_previsions[["Annee", "Mois", "Date", "Agence", "Article", "Indice", "Base", "Momentum", "Prevision_HL"]],
                column_config={
                    "Indice": st.column_config.NumberColumn("Indice", format="%.1f"),
                    "Base": st.column_config.NumberColumn("Base (SARR)", format="%.0f"),
                    "Momentum": st.column_config.NumberColumn("Momentum", format="%.0f"),
                    "Prevision_HL": st.column_config.NumberColumn("Prévision (HL)", format="%.2f")
                },
                use_container_width=True
            )
        else:
            st.warning("Aucune prévision calculée.")

import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ==============================================================================
# CONFIGURATION ET DESIGN AVANCÉ
# ==============================================================================
st.set_page_config(page_title="PREVISIONS STAR MADAGASCAR", layout="wide", page_icon="⭐", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #F4F6F8 !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E7EB; box-shadow: 2px 0 10px rgba(0,0,0,0.03); }
    [data-testid="stSidebar"] h2 { color: #E30613 !important; font-size: 1.4rem; font-weight: 800; }
    [data-testid="stSidebar"] h5 { color: #4B5563 !important; font-weight: 600; margin-top: 1.5rem; }
    h1 { color: #E30613 !important; font-weight: 900 !important; letter-spacing: -0.02em; margin-bottom: 0 !important; }
    h2, h3 { color: #009640 !important; font-weight: 800 !important; }
    p { color: #4B5563; }
    .kpi-card {
        background: #FFFFFF; border-radius: 12px; padding: 24px;
        border: 1px solid #E5E7EB; border-left: 6px solid #E30613; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        display: flex; flex-direction: column; justify-content: space-between; height: 140px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
    .kpi-header { display: flex; justify-content: space-between; align-items: center; color: #6B7280; font-size: 1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-icon { font-size: 1.5rem; opacity: 0.8; }
    .kpi-value { font-size: 2.6rem; font-weight: 800; color: #111827; margin-top: 8px; line-height: 1.1; }
    .kpi-footer { font-size: 0.9rem; color: #9CA3AF; font-weight: 500; margin-top: 4px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; padding-bottom: 8px; border-bottom: 2px solid #E5E7EB; }
    .stTabs [data-baseweb="tab"] { height: 40px; background-color: transparent; color: #6B7280; border-radius: 6px; padding: 8px 16px; font-weight: 600; border: none; transition: all 0.2s ease; }
    .stTabs [data-baseweb="tab"]:hover { background-color: #F3F4F6; color: #111827; }
    .stTabs [aria-selected="true"] { background-color: #E30613 !important; color: #FFFFFF !important; box-shadow: 0 4px 6px -1px rgba(227, 6, 19, 0.3); }
    div[data-testid="stDataFrame"] { background-color: #FFFFFF; padding: 12px; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    div[data-testid="stPlotlyChart"] { background-color: #FFFFFF; padding: 16px; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .streamlit-expanderHeader { font-weight: 600 !important; color: #111827 !important; }
    .streamlit-expanderContent { background-color: #FFFFFF; border-radius: 0 0 12px 12px; }
    .stMultiSelect, .stNumberInput, .stSelectbox { margin-bottom: 10px; }
    div[data-baseweb="select"] > div { border-radius: 8px; border-color: #D1D5DB; }
</style>
""", unsafe_allow_html=True)

# En-tête
LOGO_PATH = "LOGO_STAR.png"
col_logo, col_titre = st.columns([1.5, 5], gap="medium", vertical_alignment="center")
with col_logo:
    try:
        st.image(LOGO_PATH, width="stretch")
    except:
        st.info("Logo non trouvé")

with col_titre:
    st.markdown("""
        <div style='text-align: left; padding-bottom: 10px;'>
            <h1 style='font-size: 3rem; margin: 0;'>PREVISIONS STAR MADAGASCAR</h1>
            <p style='color: #6B7280; font-size: 1.2rem; font-weight: 500; margin-top: 4px; letter-spacing: 0.02em;'>
                Moteur de prévision S&OP complet (Étapes 1 à 5)
            </p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border: 1px solid #E5E7EB; margin: 10px 0 30px 0;'>", unsafe_allow_html=True)

# ==============================================================================
# RÉFÉRENTIEL ET MAPPING
# ==============================================================================
REF_DEFAUT = [
    {"Article": "Booster Appel-Mix 50CL VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"}, {"Article": "Booster Tornado 50CL VER VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "Caprice Ananas 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"}, {"Article": "Caprice Ananas 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Ananas 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"}, {"Article": "Caprice Bonbon Anglais 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"}, {"Article": "Caprice Bonbon Anglais 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 35 cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"}, {"Article": "Caprice Bonbon Anglais 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"}, {"Article": "Caprice Grenadine 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"}, {"Article": "Caprice Grenadine 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 35 cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"}, {"Article": "Caprice Grenadine 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"}, {"Article": "Caprice Orange 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"}, {"Article": "Caprice Orange 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 35 cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"}, {"Article": "Caprice Orange 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"}, {"Article": "Caprice Citron 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Citron 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"}, {"Article": "Caprice Citron 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Citron 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"}, {"Article": "Tonic 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Tonic 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"}, {"Article": "World Cola 100cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "World Cola 100cl WOCO VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"}, {"Article": "World Cola 150cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "World Cola 30cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"}, {"Article": "World Cola 30cl WOCO VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "World Cola 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"}, {"Article": "World Cola 35cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"},
    {"Article": "World Cola 50cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"}, {"Article": "Beaufort 33 CL CAN", "Contenance (Cl)": 33, "Positionnement": "Premium"},
    {"Article": "Beaufort 33CL VER", "Contenance (Cl)": 33, "Positionnement": "Premium"}, {"Article": "FRESH 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Entrée"},
    {"Article": "THB Fresh 33 cl VER", "Contenance (Cl)": 33, "Positionnement": "Entrée"}, {"Article": "THB Fresh 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Entrée"},
    {"Article": "Gold 8 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Premium"}, {"Article": "Gold 8 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blanche 33cl VER", "Contenance (Cl)": 33, "Positionnement": "Premium"}, {"Article": "Gold Blanche 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blanche 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Premium"}, {"Article": "Gold Blonde 33 cl VER", "Contenance (Cl)": 33, "Positionnement": "Premium"},
    {"Article": "Gold Blonde 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Premium"}, {"Article": "Gold Blonde 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blonde 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Premium"}, {"Article": "Queen s 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Premium"},
    {"Article": "THB Pilsener 33 cl VER", "Contenance (Cl)": 33, "Positionnement": "Milieu"}, {"Article": "THB Pilsener 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "THB Pilsener 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Milieu"}, {"Article": "Cristal 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Entrée"},
    {"Article": "Cristal 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Entrée"}, {"Article": "Cristal 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Entrée"},
    {"Article": "Cristal 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"}, {"Article": "Cristalline 100 cl PET", "Contenance (Cl)": 100, "Positionnement": "Entrée"},
    {"Article": "Cristalline 200 cl PET", "Contenance (Cl)": 200, "Positionnement": "Entrée"}, {"Article": "Eau vive 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Entrée"},
    {"Article": "Eau vive 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Entrée"}, {"Article": "Eau vive 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "FOSA 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Entrée"}, {"Article": "XXL 30cl BOB VER", "Contenance (Cl)": 30, "Positionnement": "Entrée"},
    {"Article": "XXL 30cl VER", "Contenance (Cl)": 30, "Positionnement": "Entrée"}, {"Article": "XXL 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Entrée"},
    {"Article": "XXL 35cl PET", "Contenance (Cl)": 35, "Positionnement": "Entrée"}
]

MAPPING_REGIONS = {
    "11-Andranomahery": "Centre", "12-Antsirabe": "Centre", "01-Tanjombato": "Est", "09-Tamatave": "Est",
    "03-Usine-Diego": "Nord", "07-Majunga": "Nord", "18-Ambanja": "Nord", "19-Sambava": "Nord", "21-Nosy-Be": "Nord",
    "04-Tulear": "Sud", "05-Fianarantsoa": "Sud", "06-Ihosy": "Sud", "08-Manakara": "Sud", "23-Morondava": "Sud", "24-Fort-Dauphin": "Sud"
}

MOIS_NOMS = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

def normaliser_mois(serie: pd.Series) -> pd.Series:
    series_clean = serie.astype(str).str.strip()
    try:
        numeric_series = pd.to_numeric(series_clean, errors='coerce')
        if numeric_series.notna().all():
            dates = pd.to_datetime(numeric_series, unit='D', origin='1899-12-30', errors='coerce')
            if dates.notna().all():
                return dates.dt.month
    except: pass
    mois_map = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
    texte_series = series_clean.apply(lambda x: unicodedata.normalize("NFD", str(x)).encode("ascii", "ignore").decode("utf-8").lower())
    return texte_series.map(mois_map).fillna(1).astype(int)

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    if annee0.between(1990, 2100).sum() < len(df) * 0.3 and df.shape[1] >= 8:
        annee1 = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        return annee1.between(1990, 2100).sum() > len(df) * 0.3
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

@st.cache_data(show_spinner="Chargement et enrichissement des données...")
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes = None) -> pd.DataFrame:
    if ref_bytes is not None:
        df_ref = pd.read_excel(io.BytesIO(ref_bytes), sheet_name="Ref actif")
        df_ref = df_ref.rename(columns={"Article": "article_original", "Positionnement": "positionnement", "Occasion": "occasion", "Contenance (Cl)": "contenance_cl"})
        df_ref = df_ref[["article_original", "positionnement", "occasion", "contenance_cl"]].copy()
    else:
        df_ref = pd.DataFrame(REF_DEFAUT).rename(columns={"Article": "article_original", "Contenance (Cl)": "contenance_cl", "Positionnement": "positionnement"})
        df_ref["occasion"] = "Non renseigné"
    
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    df_ref["cle_article"] = df_ref["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    df_ref = df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)

    df_raw = pd.read_excel(io.BytesIO(ventes_bytes), sheet_name=0, header=None)
    if not detecter_format_pivote(df_raw): return pd.DataFrame()

    annee0 = pd.to_numeric(df_raw.iloc[:, 0], errors="coerce")
    if annee0.between(1990, 2100).sum() < len(df_raw) * 0.3 and df_raw.shape[1] >= 8:
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "volume_brut"], start=1)}
    else:
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "volume_brut"])}
        
    df = df_raw.rename(columns=rename).copy()
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["mois"] = normaliser_mois(df["mois"])
    df["volume_brut"] = pd.to_numeric(df["volume_brut"], errors="coerce").fillna(0.0)
    
    masque_total = df["segment"].astype(str).str.contains("total", case=False, na=False) | df["produit"].astype(str).str.contains("total", case=False, na=False) | df["agence"].astype(str).str.contains("total", case=False, na=False) | df["nature"].astype(str).str.contains("total", case=False, na=False) | df["nature"].isna()
    df = df[~masque_total].copy()
    
    df["article_original"] = df["nature"].astype(str).str.replace(r'^[^-]+-', '', regex=True).str.strip()
    df["agence"] = df["agence"].astype(str).str.strip()
    df["annee"] = df["annee"].fillna(2026).astype(int)
    df["cle_article"] = df["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)

    df_enrichi = pd.merge(df_ref, df, on="cle_article", how="outer")
    df_enrichi["article"] = df_enrichi["article_original_x"].fillna(df_enrichi["article_original_y"]).fillna("Inconnu").astype(str)
    df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
    df_enrichi["volume_brut"] = df_enrichi["volume_brut"].fillna(0.0)
    df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
    
    df_enrichi["contenance_cl"] = pd.to_numeric(df_enrichi["contenance_cl"], errors="coerce").fillna(100.0)
    df_enrichi.loc[df_enrichi["contenance_cl"] <= 0, "contenance_cl"] = 100.0

    masque_fut20 = df_enrichi["article"].str.contains(r'20L|20 L|FUT 20', case=False, na=False, regex=True)
    df_enrichi.loc[masque_fut20, "contenance_cl"] = 2000.0
    
    df_enrichi["hl"] = df_enrichi["volume_brut"] * (df_enrichi["contenance_cl"] / 10000.0)
    df_enrichi["region"] = df_enrichi["agence"].map(MAPPING_REGIONS).fillna("Autre")
    
    conditions = [df_enrichi["article"].str.contains(x, case=False, na=False) for x in ["booster|alcoomix", "caprice|tonic|world cola|d jino|youzou|coca|fanta|sprite", "beaufort|fresh|thb|gold|queen|skol|castel|libertalia", "cristal|cristalline|eau vive|eau", "xxl|fosa", "judor|jus", "vin", "negoce"]]
    choices = ["5-ALCOMIX", "2-BG", "1-BIERES", "4-EAUX", "3-ENERGY", "4-JUS", "7-VIN", "6-NEGOCE"]
    df_enrichi["segment"] = np.select(conditions, choices, default="AUTRE / INCONNU")
    
    return df_enrichi[["annee", "mois", "segment", "region", "produit", "agence", "hl", "volume_brut", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# CALCULS (ÉTAPES 3 À 5) - LOGIQUE EXCEL (Cumul_Coef vrai, SIERREUR)
# ==============================================================================
@st.cache_data(show_spinner="Calcul ultra-rapide des prévisions...")
def calculer_etape_5(df_perimetre: pd.DataFrame, annee_min_is: int, annee_max_is: int, annee_min_cagr: int, annee_max_cagr: int, annee_cloture: int, mois_cutoff: int, annee_cible: int, _cache_bust="v30"):
    
    articles_avec_vente = df_perimetre.groupby('article')['hl'].sum()
    articles_avec_vente = articles_avec_vente[articles_avec_vente > 0].index
    df_perimetre_filtre = df_perimetre[df_perimetre['article'].isin(articles_avec_vente)].copy()
    
    if df_perimetre_filtre.empty:
        return None, None, None, None, df_perimetre

    df_limite = df_perimetre_filtre[(df_perimetre_filtre["annee"] < annee_cloture) | ((df_perimetre_filtre["annee"] == annee_cloture) & (df_perimetre_filtre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, df_perimetre_filtre

    # Indice de Saisonnalité
    df_hist_is = df_realise[(df_realise["annee"] >= annee_min_is) & (df_realise["annee"] <= annee_max_is)].copy()
    if df_hist_is.empty: return None, None, None, None, df_realise

    mois_par_annee = df_hist_is.groupby(['agence', 'article', 'annee'])['mois'].nunique().reset_index()
    df_hist_is_complet = df_hist_is.merge(mois_par_annee[mois_par_annee['mois'] == 12][['agence', 'article', 'annee']], on=['agence', 'article', 'annee'], how='inner')
    
    if df_hist_is_complet.empty:
        table_indices = pd.DataFrame(columns=['agence', 'article', 'mois', 'Indice'])
    else:
        vols = df_hist_is_complet.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0).reindex(columns=range(1, 13), fill_value=0.0) 
        vols_mois_cumules = vols.groupby(['agence', 'article']).sum()
        vols_annuels_cumules = vols.sum(axis=1).groupby(['agence', 'article']).sum()
        
        indices = vols_mois_cumules.div(vols_annuels_cumules / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0) 
        
        sum_indices = indices.sum(axis=1)
        indices = indices.div(sum_indices, axis=0) * 12.0

        table_indices = indices.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')
        table_indices['mois'] = table_indices['mois'].astype(int) 

    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    df_perim_unique = df_perimetre_filtre[['agence', 'article', 'contenance_cl']].drop_duplicates(subset=['agence', 'article'])
    
    df_ytd = df_realise[(df_realise['annee'] == annee_cloture) & (df_realise['mois'] <= mois_cutoff)].groupby(['agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'YTD_HL'})

    # LOGIQUE HYBRIDE POUR LA BASE DU CAGR
    df_ventes_positives = df_realise[df_realise['hl'] > 0]
    df_premiere_annee = df_ventes_positives.groupby(['agence', 'article'])['annee'].min().reset_index().rename(columns={'annee': 'Annee_Debut'})

    df_base = pd.merge(df_perim_unique, df_ytd, on=['agence', 'article'], how='left')
    df_base = pd.merge(df_base, df_premiere_annee, on=['agence', 'article'], how='left')

    df_base['YTD_HL'] = df_base['YTD_HL'].fillna(0.0)
    df_base['Annee_Debut'] = df_base['Annee_Debut'].fillna(annee_cloture)
    
    df_base['Annee_Base'] = np.maximum(annee_min_cagr, df_base['Annee_Debut'])

    df_base_vol = df_realise.groupby(['agence', 'article', 'annee'])['hl'].sum().reset_index()
    df_base = pd.merge(df_base, df_base_vol, left_on=['agence', 'article', 'Annee_Base'], right_on=['agence', 'article', 'annee'], how='left')
    df_base = df_base.rename(columns={'hl': 'Base_Hist'})
    df_base = df_base.drop(columns=['annee'])
    df_base['Base_Hist'] = df_base['Base_Hist'].fillna(0.0)

    # VRAI CALCUL DU CUMUL_COEF (Comme Excel le fait en interne)
    df_cumul_coef = table_indices[table_indices['mois'] <= mois_cutoff].groupby(['agence', 'article'])['Indice'].sum().reset_index().rename(columns={'Indice': 'Cumul_Coef'})
    df_base = pd.merge(df_base, df_cumul_coef, on=['agence', 'article'], how='left')
    df_base['Cumul_Coef'] = df_base['Cumul_Coef'].fillna(mois_cutoff * 1.0)
    df_base['Cumul_Coef'] = df_base['Cumul_Coef'].replace(0, 1.0)

    # Run-Rate
    df_base['Projection_CurrentYear'] = np.where(
        df_base['Cumul_Coef'] > 0,
        df_base['YTD_HL'] / (df_base['Cumul_Coef'] / 12.0),
        0.0
    )

    df_base['Nb_Annees'] = annee_cloture - df_base['Annee_Base']
    
    # Formule CAGR (SIERREUR)
    df_base['CAGR_val'] = np.where(
        (df_base['Base_Hist'] > 0) & (df_base['Projection_CurrentYear'] > 0) & (df_base['Nb_Annees'] > 0),
        ((df_base['Projection_CurrentYear'] / df_base['Base_Hist']) ** (1 / df_base['Nb_Annees'])) - 1,
        0.0
    )

    annees_cibles = list(range(annee_cloture, annee_cible + 1))
    mois_cibles = list(range(1, 13))
    
    df_cross = df_base.assign(key=1).merge(pd.DataFrame({'annee': annees_cibles, 'key': 1}), on='key').drop('key', axis=1)
    df_cross = df_cross.assign(key=1).merge(pd.DataFrame({'mois': mois_cibles, 'key': 1}), on='key').drop('key', axis=1)
    
    df_cross = pd.merge(df_cross, table_indices, on=['agence', 'article', 'mois'], how='left')
    df_cross['Indice'] = df_cross['Indice'].fillna(1.0)
    
    df_realise_grouped = df_realise.groupby(['annee', 'mois', 'agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'hl_reel'})
    df_cross = pd.merge(df_cross, df_realise_grouped, on=['annee', 'mois', 'agence', 'article'], how='left')
    
    df_cross['is_realise'] = (df_cross['annee'] == annee_cloture) & (df_cross['mois'] <= mois_cutoff)
    df_cross['Statut'] = np.where(df_cross['is_realise'], "Réalisé", "Prévision")
    
    df_cross['multiplicateur_cagr'] = (1 + df_cross['CAGR_val']) ** (df_cross['annee'] - annee_cloture)
    
    df_cross['Prevision_HL'] = np.maximum(0.0, (df_cross['Projection_CurrentYear'] * df_cross['multiplicateur_cagr']) * (df_cross['Indice'] / 12.0))
    
    df_cross['Volume_HL'] = np.where(df_cross['is_realise'], df_cross['hl_reel'].fillna(0.0), df_cross['Prevision_HL'])
    df_cross['Volume_HL'] = np.maximum(0.0, df_cross['Volume_HL'])
    df_cross['Volume_Cols'] = df_cross['Volume_HL'] * (10000 / df_cross['contenance_cl'].replace(0, 100))
    
    df_cross['CAGR (%)'] = df_cross['CAGR_val'] * 100
    df_cross['Date'] = df_cross['mois'].apply(lambda m: MOIS_NOMS[m-1]) + '-' + df_cross['annee'].astype(str).str[-2:]
    
    df_cross = df_cross.rename(columns={'Projection_CurrentYear': 'Projection_Annuelle'})
    
    cols_finales = ["annee", "mois", "agence", "article", "contenance_cl", "Date", "Statut", "Indice", "Projection_Annuelle", "CAGR (%)", "Volume_HL", "Volume_Cols"]
    
    return table_indices, df_sarr, None, df_cross[cols_finales].copy(), df_realise

# ==============================================================================
# INTERFACE UTILISATEUR
# ==============================================================================
with st.expander("📁 1. Importer vos fichiers (Données Brutes)", expanded=False):
    c1, c2 = st.columns(2)
    with c1: fichier_ventes = st.file_uploader("Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
    with c2: fichier_ref = st.file_uploader("Fichier Référentiel (Optionnel)", type=["xlsx"])

if fichier_ventes is not None:
    df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue() if fichier_ref is not None else None)

    with st.sidebar:
        st.markdown("<h2>⚙️ Paramètres</h2>", unsafe_allow_html=True)
        st.markdown("##### 2. Périmètre (Filtres)")
        
        regions_dispo = sorted([str(r) for r in df_enrichi["region"].unique() if pd.notna(r) and str(r) != "Aucune vente"])
        sel_regions = st.multiselect("Région", options=regions_dispo, placeholder="Toutes")
        df_temp = df_enrichi[df_enrichi["region"].isin(sel_regions)] if sel_regions else df_enrichi

        positionnements_dispo = sorted([str(p) for p in df_temp["positionnement"].unique() if pd.notna(p)])
        sel_positionnements = st.multiselect("Positionnement", options=positionnements_dispo, placeholder="Tous")
        df_temp = df_temp[df_temp["positionnement"].isin(sel_positionnements)] if sel_positionnements else df_temp

        contenances_dispo = sorted([int(c) for c in df_temp["contenance_cl"].unique() if pd.notna(c)])
        sel_contenances = st.multiselect("Contenance (cl)", options=contenances_dispo, placeholder="Toutes")
        df_temp = df_temp[df_temp["contenance_cl"].isin(sel_contenances)] if sel_contenances else df_temp

        segments_dispo = sorted([str(s) for s in df_temp["segment"].unique() if pd.notna(s)])
        sel_segments = st.multiselect("Segment", options=segments_dispo, placeholder="Tous")
        df_temp = df_temp[df_temp["segment"].isin(sel_segments)] if sel_segments else df_temp

        articles_dispo = sorted([str(a) for a in df_temp["article"].unique() if pd.notna(a)])
        sel_articles = st.multiselect("Article", options=articles_dispo, placeholder="Tous")
        df_temp = df_temp[df_temp["article"].isin(sel_articles)] if sel_articles else df_temp

        agences_dispo = sorted([str(a) for a in df_temp["agence"].unique() if pd.notna(a) and str(a) != "Aucune vente"])
        sel_agences = st.multiselect("Agence", options=agences_dispo, placeholder="Toutes")

        st.markdown("##### 📅 Période Indice Saisonnalité (IS)")
        annee_min_is = st.number_input("Année Min IS", min_value=2010, max_value=2030, value=2024)
        annee_max_is = st.number_input("Année Max IS", min_value=annee_min_is, max_value=2030, value=max(2025, annee_min_is))

        st.markdown("##### 📈 Période CAGR")
        annee_min_cagr = st.number_input("Année Min CAGR", min_value=2010, max_value=2030, value=2017)
        annee_max_cagr = st.number_input("Année Max CAGR", min_value=annee_min_cagr, max_value=2030, value=2025)

        st.markdown("##### 🎯 Cutoff & Cible")
        annee_cloture = st.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
        annee_cible = st.number_input("Année Cible", min_value=annee_cloture, max_value=2035, value=annee_cloture)
        mois_cutoff = st.selectbox("Mois de Cutoff", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {MOIS_NOMS[m-1]}")

        st.markdown("##### ⚙️ Affichage")
        unite_affichage = st.radio("Unité", options=["HL", "Cols"], index=1)

    df_perimetre = df_enrichi.copy()
    if sel_regions: df_perimetre = df_perimetre[df_perimetre["region"].isin(sel_regions)]
    if sel_positionnements: df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_positionnements)]
    if sel_contenances: df_perimetre = df_perimetre[df_perimetre["contenance_cl"].isin(sel_contenances)]
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    table_indices, df_sarr, _, df_previsions, df_realise = calculer_etape_5(
        df_perimetre, 
        annee_min_is, annee_max_is, 
        annee_min_cagr, annee_max_cagr, 
        annee_cloture, mois_cutoff, annee_cible
    )

    if table_indices is None:
        st.warning("⚠️ Impossible de calculer les prévisions. Vérifiez vos filtres.")
        st.stop()

    col_prev_aff = "Volume_Cols" if unite_affichage == "Cols" else "Volume_HL"

    df_cible = df_previsions[df_previsions['annee'] == annee_cible]
    atterrissage_cible = df_cible[col_prev_aff].sum()

    if annee_cible == annee_cloture:
        st.markdown(f"""<div class="kpi-card" style="width: 100%; border-left: 6px solid #009640;">
            <div class="kpi-header"><span>Atterrissage {annee_cible} (Réalisé + Prévisions)</span> <span class="kpi-icon">🎯</span></div>
            <div class="kpi-value">{atterrissage_cible:,.0f}</div>
            <div class="kpi-footer">{unite_affichage} (Projection finale)</div>
        </div>""", unsafe_allow_html=True)
    else:
        cagr_applique = df_previsions['CAGR (%)'].mean() if not df_previsions.empty else 0.0
        kpi1, kpi2 = st.columns(2)
        with kpi1:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><span>Atterrissage {annee_cible}</span> <span class="kpi-icon">🎯</span></div><div class="kpi-value">{atterrissage_cible:,.0f}</div><div class="kpi-footer">{unite_affichage} (Réalisé + Prévisions)</div></div>""", unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><span>CAGR Appliqué</span> <span class="kpi-icon">📈</span></div><div class="kpi-value">{cagr_applique:,.2f}%</div><div class="kpi-footer">Croissance annuelle moyenne</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📁 Données Brutes", "⚙️ Périmètre", "📊 Réalisé Cumulé", "📈 Indices & SARR", "🔮 Prévisions"
    ])

    with tab1:
        st.markdown("### Étape 1 : Données Brutes Enrichies (Ventes + Référentiel)")
        st.dataframe(df_enrichi, width="stretch", hide_index=True)

    with tab2:
        st.markdown("### Étape 2 : Périmètre Filtré")
        st.dataframe(df_perimetre, width="stretch", hide_index=True)

    with tab3:
        st.markdown("### Étape 3 : Réalisé Cumulé (Jusqu'au Cutoff)")
        if df_realise is not None and not df_realise.empty:
            st.dataframe(df_realise.groupby(['annee', 'mois', 'region', 'agence', 'article'])[['hl']].sum().reset_index(), width="stretch", hide_index=True)
        else:
            st.info("Aucune donnée réalisée pour le moment.")

    with tab4:
        st.markdown("### Étape 4 : Indices de Saisonnalité & SARR")
        c_idx, c_sarr = st.columns(2)
        with c_idx:
            st.markdown("**Indices de Saisonnalité (Basés sur la période IS)**")
            if not table_indices.empty:
                pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
                pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
                st.dataframe(pivot_indices, width="stretch")
            else:
                st.info("Pas d'historique complet (12 mois) pour calculer les indices.")
        with c_sarr:
            st.markdown("**Table SARR (5 derniers mois glissants)**")
            df_sarr["SARR_Aff"] = df_sarr["SARR_HL"] * (10000 / df_sarr["contenance_cl"].replace(0, 100)) if unite_affichage == "Cols" else df_sarr["SARR_HL"]
            df_sarr_derniers = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).groupby(['agence', 'article']).tail(5)
            st.dataframe(df_sarr_derniers[["annee", "mois", "agence", "article", "SARR_Aff"]].sort_values(["agence", "article", "annee", "mois"]), width="stretch", hide_index=True)

    with tab5:
        st.markdown("### Étape 5 : Dynamique (Projection Annuelle & CAGR)")
        
        mode_affichage = st.radio("Choisir le mode d'affichage :", ["📊 Tableau", "📈 Graphiques Data Analyst"], horizontal=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if mode_affichage == "📊 Tableau":
            st.markdown("#### 5.1 Résultat Final")
            
            pivot_mensuel = df_previsions.pivot_table(
                index=['annee', 'agence', 'article'], columns='mois', values=col_prev_aff, aggfunc='sum'
            ).fillna(0)
            pivot_mensuel.columns = [MOIS_NOMS[c-1] for c in pivot_mensuel.columns]
            pivot_mensuel['Total Année'] = pivot_mensuel.sum(axis=1)
            
            pivot_mensuel = pivot_mensuel[pivot_mensuel.sum(axis=1) > 0]
            
            st.dataframe(pivot_mensuel, width="stretch")
            
            with st.expander("Voir le détail des calculs (Projection Annuelle & CAGR)"):
                cols_to_show = ["annee", "mois", "Statut", "agence", "article", "Indice", col_prev_aff]
                
                if 'Projection_Annuelle' in df_previsions.columns:
                    df_previsions['Projection_Annuelle_Aff'] = df_previsions['Projection_Annuelle'] * (10000 / df_previsions['contenance_cl'].replace(0, 100)) if unite_affichage == "Cols" else df_previsions['Projection_Annuelle']
                    cols_to_show.insert(-1, "Projection_Annuelle_Aff")
                    
                if annee_cible > annee_cloture:
                    cols_to_show.insert(-1, "CAGR (%)")
                    
                st.dataframe(
                    df_previsions[cols_to_show].sort_values(["annee", "mois", "agence", "article"]),
                    column_config={
                        "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                        "CAGR (%)": st.column_config.NumberColumn("CAGR (%)", format="%.2f"),
                        "Projection_Annuelle_Aff": st.column_config.NumberColumn(f"Projection Annuelle ({unite_affichage})", format="%.2f"),
                        col_prev_aff: st.column_config.NumberColumn(f"Volume Mensuel ({unite_affichage})", format="%.2f"),
                    },
                    width="stretch", hide_index=True, height=400
                )

        else:
            st.markdown("#### 📊 Analyse Visuelle des Prévisions")
            
            st.markdown("##### 📈 Évolution Globale des Volumes (Réalisé vs Prévisions)")
            
            df_graph = df_previsions.copy()
            df_graph['Date_Str'] = df_graph['annee'].astype(str) + '-' + df_graph['mois'].astype(str).str.zfill(2) + '-01'
            df_graph['Date'] = pd.to_datetime(df_graph['Date_Str'])
            
            df_grouped = df_graph.groupby(['Date', 'Statut'])[col_prev_aff].sum().reset_index()

            df_real = df_grouped[df_grouped['Statut'] == 'Réalisé']
            df_prev = df_grouped[df_grouped['Statut'] == 'Prévision']

            df_real = df_real[df_real[col_prev_aff] > 0]
            df_prev = df_prev[df_prev[col_prev_aff] > 0]

            fig1 = go.Figure()
            
            if not df_real.empty:
                fig1.add_trace(go.Scatter(
                    x=df_real['Date'], y=df_real[col_prev_aff], 
                    mode='lines+markers', name='Réalisé', 
                    line=dict(color='#009640', width=3, shape='spline'),
                    fill='tozeroy', fillcolor='rgba(0, 150, 64, 0.1)'
                ))
            if not df_prev.empty:
                fig1.add_trace(go.Scatter(
                    x=df_prev['Date'], y=df_prev[col_prev_aff], 
                    mode='lines+markers', name='Prévision', 
                    line=dict(color='#E30613', width=3, dash='dash', shape='spline'),
                    fill='tozeroy', fillcolor='rgba(227, 6, 19, 0.05)'
                ))

            fig1.update_layout(
                title=dict(text=f"Évolution Globale (Cible: {annee_cible})", font=dict(size=18, color="#111827")),
                xaxis_title="Mois",
                yaxis_title=f"Volume ({unite_affichage})",
                hovermode="x unified",
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=40, r=40, t=60, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6', linecolor='#E5E7EB', dtick="M1", tickformat="%b-%y")
            fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6', linecolor='#E5E7EB')
            
            st.plotly_chart(fig1, width="stretch")

            st.markdown("---")
            st.markdown("#### 🔍 Analyse de la Saisonnalité et des Produits")

            col_g1, col_g2 = st.columns(2)

            with col_g1:
                if not table_indices.empty:
                    df_saison = table_indices.groupby('mois')['Indice'].mean().reset_index()
                    df_saison['Mois_Nom'] = df_saison['mois'].apply(lambda m: MOIS_NOMS[m-1])
                    
                    colors = ['#009640' if val < 1 else '#E30613' for val in df_saison['Indice']]
                    
                    fig2 = go.Figure(data=[go.Bar(
                        x=df_saison['Mois_Nom'], 
                        y=df_saison['Indice'], 
                        marker_color=colors,
                        text=df_saison['Indice'].round(2),
                        textposition='auto'
                    )])
                    
                    fig2.add_hline(y=1.0, line_dash="dash", line_color="#4B5563", annotation_text="Moyenne (1.0)", annotation_position="bottom right")

                    fig2.update_layout(
                        title=dict(text="Profil de Saisonnalité (Indice Moyen)", font=dict(size=16, color="#111827")),
                        xaxis_title="Mois",
                        yaxis_title="Indice (Base 1.0)",
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        margin=dict(l=20, r=20, t=50, b=20)
                    )
                    fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6', linecolor='#E5E7EB')
                    st.plotly_chart(fig2, width="stretch")

            with col_g2:
                df_top = df_previsions.groupby('article')[col_prev_aff].sum().sort_values(ascending=True).tail(10).reset_index()
                
                fig3 = go.Figure(data=[go.Bar(
                    x=df_top[col_prev_aff], 
                    y=df_top['article'], 
                    orientation='h', 
                    marker=dict(color=df_top[col_prev_aff], colorscale=['#FFC0C0', '#E30613'])
                )])
                
                fig3.update_layout(
                    title=dict(text="Top 10 Articles (Volume Total Projeté)", font=dict(size=16, color="#111827")),
                    xaxis_title=f"Volume ({unite_affichage})",
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                fig3.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6', linecolor='#E5E7EB')
                st.plotly_chart(fig3, width="stretch")

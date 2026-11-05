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
# CONFIGURATION ET DESIGN 
# ==============================================================================
st.set_page_config(page_title="PREVISIONS STAR MADAGASCAR", layout="wide", page_icon="⭐", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    /* Reset et Fond */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F4F6F8 !important; }
    [data-testid="stSidebar"] { display: none; }
    
    /* Header Blanc (Brand STAR) */
    .hero-header {
        background-color: #FFFFFF;
        color: #111827;
        padding: 30px 40px;
        border-radius: 0 0 20px 20px;
        margin-top: -60px;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
        border-bottom: 4px solid #E30613;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }
    .hero-header h1 { color: #E30613 !important; font-size: 2.8rem; font-weight: 900; margin-bottom: 10px; letter-spacing: -0.02em; }
    .hero-header p { color: #6B7280; font-size: 1.1rem; margin-bottom: 20px; font-weight: 500; }
    .badge-demo {
        background-color: #FEF2F2; color: #E30613; padding: 6px 14px;
        border-radius: 20px; font-size: 0.8rem; font-weight: 700;
        display: inline-block; border: 1px solid #FECACA;
    }
    
    /* Cartes Blanches */
    .white-card {
        background: white; border-radius: 12px; padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        border: 1px solid #E5E7EB; margin-bottom: 20px; height: 100%;
    }
    
    /* KPI Cards */
    .kpi-label { color: #6B7280; font-size: 0.95rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .kpi-value { color: #111827; font-size: 2.6rem; font-weight: 800; line-height: 1.1; }
    .kpi-value-green { color: #009640; }
    .kpi-value-red { color: #E30613; }
    .kpi-footer { color: #9CA3AF; font-size: 0.85rem; margin-top: 8px; font-weight: 500; }

    /* Titres de sections */
    .section-title { color: #111827; font-size: 1.2rem; font-weight: 800; margin-bottom: 5px; }
    .section-subtitle { color: #6B7280; font-size: 0.85rem; margin-bottom: 20px; font-weight: 500; }

    /* Inputs Streamlit */
    div[data-baseweb="select"] > div, div[data-testid="stNumberInput"] input, div[data-testid="stMultiSelect"] {
        background-color: #F9FAFB !important; border-radius: 8px !important; border: 1px solid #D1D5DB !important;
    }
    .stSelectbox label, .stNumberInput label, .stMultiSelect label { color: #4B5563 !important; font-size: 0.85rem !important; font-weight: 600 !important; }
    
    /* =========================================================
       NAVIGATION (RADIO STYLISÉ EN ONGLETS TRÈS ESPACÉS)
       ========================================================= */
    div[role="radiogroup"] {
        gap: 80px !important; /* Espacement massif */
        border-bottom: 2px solid #E5E7EB !important;
        padding-bottom: 0px !important;
        margin-bottom: 30px !important;
        display: flex !important;
        flex-wrap: wrap !important;
    }
    div[role="radiogroup"] label {
        background: transparent !important; border: none !important; border-bottom: 4px solid transparent !important;
        border-radius: 0 !important; padding: 10px 0px !important; margin: 0 !important;
    }
    div[role="radiogroup"] label div p {
        font-size: 1.6rem !important; font-weight: 800 !important; color: #6B7280 !important; transition: color 0.2s ease !important;
    }
    div[role="radiogroup"] label:hover div p { color: #111827 !important; }
    div[role="radiogroup"] label:has(input:checked) div p { color: #E30613 !important; font-weight: 900 !important; }
    div[role="radiogroup"] label:has(input:checked) { border-bottom: 4px solid #E30613 !important; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    
    /* Masquer les marges inutiles */
    .block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

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
    except Exception: pass
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
        df_ref = df_ref.rename(columns={"Article": "article_original", "Positionnement": "positionnement", "Occasion": "occasion", "Contenance (Cl)": "contenance_cl"}, errors="ignore")
        for col in ["positionnement", "occasion", "contenance_cl"]:
            if col not in df_ref.columns: df_ref[col] = "Non renseigné" if col != "contenance_cl" else 100.0
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
    
    masque_total = df[['segment', 'produit', 'agence', 'nature']].astype(str).apply(lambda s: s.str.contains("total", case=False, na=False)).any(axis=1) | df['nature'].isna()
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
    
    for col in ['region', 'segment', 'positionnement', 'occasion']:
        if col in df_enrichi.columns: df_enrichi[col] = df_enrichi[col].astype('category')

    return df_enrichi[["annee", "mois", "segment", "region", "produit", "agence", "hl", "volume_brut", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# LOGIQUE DE CALCUL
# ==============================================================================
def _calculer_indices_fallback(df_realise, annee_min_is, annee_max_is):
    df_h = df_realise[(df_realise['annee'] >= annee_min_is) & (df_realise['annee'] <= annee_max_is)].copy()
    if df_h.empty: return pd.DataFrame(columns=['agence', 'article', 'mois', 'Indice'])
    complet = (df_h.groupby(['agence', 'article', 'annee'], observed=True)['mois'].nunique().reset_index().query('mois == 12')[['agence', 'article', 'annee']])
    df_h = df_h.merge(complet, on=['agence', 'article', 'annee'], how='inner')
    if df_h.empty: return pd.DataFrame(columns=['agence', 'article', 'mois', 'Indice'])

    def _idx(group_cols):
        v = (df_h.groupby(group_cols + ['annee', 'mois'], observed=True)['hl'].sum().unstack('mois').fillna(0.0).reindex(columns=range(1, 13), fill_value=0.0))
        cum_m = v.groupby(group_cols).sum()
        cum_a = v.sum(axis=1).groupby(group_cols).sum()
        return (cum_m.div(cum_a / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0).reset_index().melt(id_vars=group_cols, var_name='mois', value_name='Indice'))

    idx1 = _idx(['agence', 'article'])
    idx2 = _idx(['article']).rename(columns={'Indice': 'Indice_art'})
    tot = df_h.groupby('mois', observed=True)['hl'].sum().reindex(range(1, 13), fill_value=0.0)
    glob = (tot / (tot.sum() / 12.0)).reset_index()
    glob.columns = ['mois', 'Indice_glob']

    result = (df_h[['agence', 'article', 'mois']].drop_duplicates().merge(idx1, on=['agence', 'article', 'mois'], how='left').merge(idx2, on=['article', 'mois'], how='left').merge(glob, on='mois', how='left'))
    result['Indice'] = result['Indice'].fillna(result['Indice_art']).fillna(result['Indice_glob']).fillna(1.0)
    result['mois'] = result['mois'].astype(int)
    return result[['agence', 'article', 'mois', 'Indice']]

@st.cache_data(show_spinner="Calcul ultra-rapide des prévisions...")
def calculer_etape_5(df_perimetre, annee_min_is, annee_max_is, annee_min_cagr, annee_max_cagr, annee_cloture, mois_cutoff, annee_cible, cache_bust="v52"):
    articles_avec_vente = df_perimetre.groupby('article', observed=True)['hl'].sum()
    articles_avec_vente = articles_avec_vente[articles_avec_vente > 0].index
    df_perimetre_filtre = df_perimetre[df_perimetre['article'].isin(articles_avec_vente)].copy()
    if df_perimetre_filtre.empty: return None, None, None, None, df_perimetre

    df_limite = df_perimetre_filtre[(df_perimetre_filtre["annee"] < annee_cloture) | ((df_perimetre_filtre["annee"] == annee_cloture) & (df_perimetre_filtre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, df_perimetre_filtre

    table_indices = _calculer_indices_fallback(df_realise, annee_min_is, annee_max_is)
    if table_indices.empty: return None, None, None, None, df_realise

    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    df_perim_unique = df_perimetre_filtre[['agence', 'article', 'contenance_cl']].drop_duplicates(subset=['agence', 'article'])
    df_realise['hl_positif'] = np.maximum(0.0, df_realise['hl'])
    df_ytd = (df_realise[(df_realise['annee'] == annee_cloture) & (df_realise['mois'] <= mois_cutoff)].groupby(['agence', 'article'], observed=True)['hl_positif'].sum().reset_index().rename(columns={'hl_positif': 'YTD_HL'}))
    df_premiere_annee = (df_realise[df_realise['hl'] > 0].groupby(['agence', 'article'], observed=True)['annee'].min().reset_index().rename(columns={'annee': 'Annee_Debut'}))

    df_base = (df_perim_unique.merge(df_ytd, on=['agence', 'article'], how='left').merge(df_premiere_annee, on=['agence', 'article'], how='left'))
    df_base['YTD_HL'] = df_base['YTD_HL'].fillna(0.0)
    df_base['Annee_Debut'] = df_base['Annee_Debut'].fillna(annee_cloture)
    df_base['Annee_Base'] = np.maximum(annee_min_cagr, df_base['Annee_Debut'])

    df_base_vol = (df_realise.groupby(['agence', 'article', 'annee'], observed=True)['hl'].sum().reset_index())
    df_base = df_base.merge(df_base_vol, left_on=['agence', 'article', 'Annee_Base'], right_on=['agence', 'article', 'annee'], how='left')
    df_base = df_base.rename(columns={'hl': 'Base_Hist'}).drop(columns=['annee'])
    df_base['Base_Hist'] = df_base['Base_Hist'].fillna(0.0)

    df_cumul = (table_indices[table_indices['mois'] <= mois_cutoff].groupby(['agence', 'article'], observed=True)['Indice'].sum().reset_index().rename(columns={'Indice': 'Cumul_Coef'}))
    df_base = df_base.merge(df_cumul, on=['agence', 'article'], how='left')
    df_base['Cumul_Coef'] = df_base['Cumul_Coef'].fillna(mois_cutoff * 1.0).replace(0, 1.0)
    df_base['Base_Mensuelle'] = df_base['YTD_HL'] / df_base['Cumul_Coef']
    df_base['Projection_CurrentYear'] = df_base['Base_Mensuelle'] * 12.0
    df_base['Nb_Annees'] = annee_cloture - df_base['Annee_Base']

    df_hist_cagr = df_realise[(df_realise['annee'] >= annee_min_cagr) & (df_realise['annee'] <= annee_max_cagr)].groupby(['agence', 'article', 'annee'], observed=True)['hl'].sum().reset_index()
    if not df_hist_cagr.empty:
        g = df_hist_cagr.groupby(['agence', 'article'], observed=True)
        df_vol_debut = (df_hist_cagr[df_hist_cagr['annee'] == g['annee'].transform('min')].groupby(['agence', 'article'], observed=True)['hl'].sum().rename('Vol_Debut').reset_index())
        df_vol_fin = (df_hist_cagr[df_hist_cagr['annee'] == g['annee'].transform('max')].groupby(['agence', 'article'], observed=True)['hl'].sum().rename('Vol_Fin').reset_index())
        df_annees_hist = (df_hist_cagr.groupby(['agence', 'article'], observed=True)['annee'].agg(['min', 'max']).rename(columns={'min': 'Annee_Debut_Hist', 'max': 'Annee_Fin_Hist'}).reset_index())
        df_base = (df_base.merge(df_vol_debut, on=['agence', 'article'], how='left').merge(df_vol_fin, on=['agence', 'article'], how='left').merge(df_annees_hist, on=['agence', 'article'], how='left'))
        df_base['Nb_Annees_Hist'] = (df_base['Annee_Fin_Hist'] - df_base['Annee_Debut_Hist']).clip(lower=0)
        df_base['CAGR_Hist'] = np.where((df_base['Vol_Debut'] > 0) & (df_base['Vol_Fin'] > 0) & (df_base['Nb_Annees_Hist'] > 0), (df_base['Vol_Fin'] / df_base['Vol_Debut']) ** (1 / df_base['Nb_Annees_Hist']) - 1, 0.0)
    else:
        df_base['CAGR_Hist'] = 0.0

    df_base['CAGR_val'] = np.where((df_base['Base_Hist'] > 0) & (df_base['Projection_CurrentYear'] > 0) & (df_base['Nb_Annees'] > 0), (df_base['Projection_CurrentYear'] / df_base['Base_Hist']) ** (1 / df_base['Nb_Annees']) - 1, df_base['CAGR_Hist'])

    annees_cibles = list(range(annee_cloture, annee_cible + 1))
    mois_cibles = list(range(1, 13))
    n_base = len(df_base)
    idx = pd.MultiIndex.from_product([range(n_base), annees_cibles, mois_cibles], names=['_i', 'annee', 'mois'])
    df_cross = df_base.reset_index(drop=True).iloc[idx.get_level_values('_i').to_numpy()].reset_index(drop=True)
    df_cross['annee'] = idx.get_level_values('annee').to_numpy()
    df_cross['mois'] = idx.get_level_values('mois').to_numpy()

    df_cross = df_cross.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_cross['Indice'] = df_cross['Indice'].fillna(1.0)
    df_realise_grouped = (df_realise.groupby(['annee', 'mois', 'agence', 'article'], observed=True)['hl'].sum().reset_index().rename(columns={'hl': 'hl_reel'}))
    df_cross = df_cross.merge(df_realise_grouped, on=['annee', 'mois', 'agence', 'article'], how='left')

    df_cross['is_realise'] = (df_cross['annee'] == annee_cloture) & (df_cross['mois'] <= mois_cutoff)
    df_cross['multiplicateur_cagr'] = (1 + df_cross['CAGR_val']) ** (df_cross['annee'] - annee_cloture)
    
    # Prévision PURE (pour superposition)
    df_cross['Prevision_HL'] = np.maximum(0.0, df_cross['Base_Mensuelle'] * df_cross['Indice'] * df_cross['multiplicateur_cagr'])
    
    # Volume mixte (Réalisé si dispo, sinon Prévision)
    df_cross['Volume_HL'] = np.where(df_cross['is_realise'], df_cross['hl_reel'].fillna(0.0), df_cross['Prevision_HL'])
    df_cross['Volume_HL'] = np.maximum(0.0, df_cross['Volume_HL'])
    
    contenance_safe = df_cross['contenance_cl'].replace(0, 100).fillna(100.0)
    df_cross['Volume_Cols'] = df_cross['Volume_HL'] * (10000.0 / contenance_safe)
    df_cross['Prevision_Cols'] = df_cross['Prevision_HL'] * (10000.0 / contenance_safe) # Ajout pour superposition en Cols
    
    df_cross['Statut'] = np.where(df_cross['is_realise'], "Réalisé", "Prévision")
    df_cross['CAGR (%)'] = df_cross['CAGR_val'] * 100

    _mois_arr = np.array(MOIS_NOMS, dtype=object)
    df_cross['Date'] = (_mois_arr[df_cross['mois'].to_numpy() - 1] + '-' + df_cross['annee'].astype(str).str[-2:].to_numpy())

    cols_finales = ["annee", "mois", "agence", "article", "contenance_cl", "Date", "Statut", "Indice", "Base_Mensuelle", "CAGR (%)", "Volume_HL", "Prevision_HL", "Volume_Cols", "Prevision_Cols"]
    df_realise_out = df_realise[df_realise['article'].isin(articles_avec_vente)].copy()

    return table_indices, df_sarr, None, df_cross[cols_finales].copy(), df_realise_out

@st.cache_data(show_spinner=False)
def _pivot_indices_cached(df_idx: pd.DataFrame) -> pd.DataFrame:
    p = df_idx.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
    p.columns = [MOIS_NOMS[c - 1] for c in p.columns]
    return p

@st.cache_data(show_spinner=False)
def _pivot_mensuel_cached(df: pd.DataFrame, col_val: str) -> pd.DataFrame:
    p = df.pivot_table(index=['annee', 'agence', 'article'], columns='mois', values=col_val, aggfunc='sum').fillna(0)
    p.columns = [MOIS_NOMS[c - 1] for c in p.columns]
    return p

# ==============================================================================
# INTERFACE UTILISATEUR
# ==============================================================================

# 1. HEADER BLANC 
st.markdown("""
<div class="hero-header">
    <p style="text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; color: #6B7280; font-weight: 700;">Perspectives • S&OP</p>
    <h1>PREVISIONS STAR MADAGASCAR</h1>
    <p>Moteur de prévision complet - Explorez les tendances à venir et comparez différents scénarios.</p>
    <div class="badge-demo">⭐ Données Officielles STAR</div>
</div>
""", unsafe_allow_html=True)

# 2. IMPORTATION DES DONNÉES
with st.expander("📁 Importer vos fichiers (Données Brutes)", expanded=False):
    c1, c2 = st.columns(2)
    with c1: fichier_ventes = st.file_uploader("Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
    with c2: fichier_ref = st.file_uploader("Fichier Référentiel (Optionnel)", type=["xlsx"])

if fichier_ventes is not None:
    df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue() if fichier_ref is not None else None)

    # 3. BARRE DE FILTRES HORIZONTALE
    with st.container():
        st.markdown('<div class="white-card" style="padding: 20px 24px;">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Affinez votre perspective</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Modifiez les filtres pour explorer les projections.</div>', unsafe_allow_html=True)
        
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            regions_dispo = sorted([str(r) for r in df_enrichi["region"].unique() if pd.notna(r) and str(r) != "Aucune vente"])
            sel_regions = st.multiselect("Région", options=regions_dispo, placeholder="Toutes")
            df_temp = df_enrichi[df_enrichi["region"].isin(sel_regions)] if sel_regions else df_enrichi
        with f2:
            segments_dispo = sorted([str(s) for s in df_temp["segment"].unique() if pd.notna(s)])
            sel_segments = st.multiselect("Segment", options=segments_dispo, placeholder="Tous")
            df_temp = df_temp[df_temp["segment"].isin(sel_segments)] if sel_segments else df_temp
        with f3:
            positionnements_dispo = sorted([str(p) for p in df_temp["positionnement"].unique() if pd.notna(p)])
            sel_positionnements = st.multiselect("Positionnement", options=positionnements_dispo, placeholder="Tous")
            df_temp = df_temp[df_temp["positionnement"].isin(sel_positionnements)] if sel_positionnements else df_temp
        with f4:
            articles_dispo = sorted([str(a) for a in df_temp["article"].unique() if pd.notna(a)])
            sel_articles = st.multiselect("Article", options=articles_dispo, placeholder="Tous")
            df_temp = df_temp[df_temp["article"].isin(sel_articles)] if sel_articles else df_temp

        f5, f6, f7, f8 = st.columns(4)
        with f5:
            agences_dispo = sorted([str(a) for a in df_temp["agence"].unique() if pd.notna(a) and str(a) != "Aucune vente"])
            sel_agences = st.multiselect("Agence", options=agences_dispo, placeholder="Toutes")
        with f6:
            contenances_dispo = sorted([int(c) for c in df_temp["contenance_cl"].unique() if pd.notna(c)])
            sel_contenances = st.multiselect("Contenance (cl)", options=contenances_dispo, placeholder="Toutes")
        with f7:
            annee_cible = st.number_input("Année Cible", min_value=2020, max_value=2035, value=2026)
        with f8:
            unite_affichage = st.radio("Unité", options=["HL", "Cols"], index=1, horizontal=True)
        
        with st.expander("⚙️ Paramètres avancés (IS, CAGR, Cutoff)"):
            p1, p2, p3, p4, p5 = st.columns(5)
            with p1: annee_min_is = st.number_input("Année Min IS", min_value=2010, max_value=2030, value=2024)
            with p2: annee_max_is = st.number_input("Année Max IS", min_value=annee_min_is, max_value=2030, value=max(2025, annee_min_is))
            with p3: annee_min_cagr = st.number_input("Année Min CAGR", min_value=2010, max_value=2030, value=2017)
            with p4: annee_max_cagr = st.number_input("Année Max CAGR", min_value=annee_min_cagr, max_value=2030, value=2025)
            with p5: 
                annee_cloture = st.number_input("Année Clôture", min_value=2020, max_value=2030, value=2026)
                mois_cutoff = st.selectbox("Mois Cutoff", options=list(range(1, 13)), index=8, format_func=lambda m: f"{MOIS_NOMS[m-1]}")
            
            mois_cibles_selection = st.multiselect("Mois cible (Filtre)", options=MOIS_NOMS, default=[])

        st.markdown('</div>', unsafe_allow_html=True)

    # APPLICATION DES FILTRES
    df_perimetre = df_enrichi.copy()
    if sel_regions: df_perimetre = df_perimetre[df_perimetre["region"].isin(sel_regions)]
    if sel_positionnements: df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_positionnements)]
    if sel_contenances: df_perimetre = df_perimetre[df_perimetre["contenance_cl"].isin(sel_contenances)]
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    # CALCULS
    table_indices, df_sarr, _, df_previsions, df_realise = calculer_etape_5(
        df_perimetre, annee_min_is, annee_max_is, annee_min_cagr, annee_max_cagr, annee_cloture, mois_cutoff, annee_cible
    )

    if table_indices is None:
        st.warning("⚠️ Impossible de calculer les prévisions. Vérifiez vos filtres.")
        st.stop()

    col_prev_aff = "Volume_Cols" if unite_affichage == "Cols" else "Volume_HL"
    col_prev_pure = "Prevision_Cols" if unite_affichage == "Cols" else "Prevision_HL"

    if not mois_cibles_selection:
        df_previsions_filtre = df_previsions
        label_mois_str = "Tous les mois"
    else:
        mois_cibles_nums = [MOIS_NOMS.index(m) + 1 for m in mois_cibles_selection]
        df_previsions_filtre = df_previsions[df_previsions['mois'].isin(mois_cibles_nums)].copy()
        label_mois_str = ", ".join(mois_cibles_selection)

    df_cible = df_previsions_filtre[df_previsions_filtre['annee'] == annee_cible]
    atterrissage_cible = df_cible[col_prev_aff].sum()
    cagr_applique = df_previsions_filtre['CAGR (%)'].mean() if not df_previsions_filtre.empty else 0.0

    # 4. CARTES KPI
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
        <div class="white-card">
            <div class="kpi-label">Atterrissage {annee_cible}</div>
            <div class="kpi-value">{atterrissage_cible:,.0f}</div>
            <div class="kpi-footer">{unite_affichage} (Réalisé + Prévisions)</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="white-card">
            <div class="kpi-label">CAGR Appliqué</div>
            <div class="kpi-value kpi-value-green">{cagr_applique:,.2f}%</div>
            <div class="kpi-footer">Croissance annuelle moyenne</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        ytd_val = 0
        if df_realise is not None and not df_realise.empty:
            ytd_df = df_realise[df_realise['annee'] == annee_cloture]
            if unite_affichage == "Cols":
                ytd_val = ytd_df.apply(lambda r: r['hl'] * (10000 / r['contenance_cl']) if r['contenance_cl'] > 0 else r['hl'], axis=1).sum()
            else:
                ytd_val = ytd_df['hl'].sum()
        st.markdown(f"""
        <div class="white-card">
            <div class="kpi-label">Volume Réalisé (YTD)</div>
            <div class="kpi-value kpi-value-red">{ytd_val:,.0f}</div>
            <div class="kpi-footer">{unite_affichage} jusqu'au cutoff</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. GRAPHIQUES (Filtré sur l'année cible)
    col_g1, col_g2 = st.columns([2, 1])
    
    with col_g1:
        st.markdown(f"""
        <div class="white-card">
            <div class="section-title">Superposition Réalisé vs Prévision ({annee_cible})</div>
            <div class="section-subtitle">La ligne pleine montre le réalisé, la ligne pointillée montre la prévision pure</div>
        """, unsafe_allow_html=True)
        
        # ICI : On filtre pour n'afficher QUE l'année cible
        df_graph = df_previsions_filtre[df_previsions_filtre['annee'] == annee_cible].copy()
        
        df_graph['Date_Str'] = df_graph['annee'].astype(str) + '-' + df_graph['mois'].astype(str).str.zfill(2) + '-01'
        df_graph['Date_Plot'] = pd.to_datetime(df_graph['Date_Str'])
        
        # 1. Prévision Pure (toute l'année cible)
        df_prev_pure = df_graph.groupby('Date_Plot', observed=True)[col_prev_pure].sum().reset_index()
        
        # 2. Réalisé (seulement jusqu'au cutoff)
        df_real = df_graph[df_graph['Statut'] == 'Réalisé'].groupby('Date_Plot', observed=True)[col_prev_aff].sum().reset_index()

        fig1 = go.Figure()

        # Trace Prévision (Rouge pointillé)
        if not df_prev_pure.empty:
            fig1.add_trace(go.Scatter(
                x=df_prev_pure['Date_Plot'], y=df_prev_pure[col_prev_pure],
                mode='lines+markers', name='Prévision (Pure)',
                line=dict(color='#E30613', width=3, dash='dot', shape='spline', smoothing=1.3),
                marker=dict(size=7, color='#E30613', line=dict(color='white', width=1.5))
            ))

        # Trace Réalisé (Noir plein par-dessus)
        if not df_real.empty:
            fig1.add_trace(go.Scatter(
                x=df_real['Date_Plot'], y=df_real[col_prev_aff],
                mode='lines+markers', name='Réalisé',
                line=dict(color='#111827', width=4, shape='spline', smoothing=1.3),
                marker=dict(size=8, color='#111827', line=dict(color='white', width=1.5))
            ))

        fig1.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, linecolor='#E5E7EB', tickformat="%b-%y"),
            yaxis=dict(showgrid=True, gridcolor='#F3F4F6', zeroline=False),
            height=320,
            hovermode="x unified"
        )
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_g2:
        st.markdown("""
        <div class="white-card">
            <div class="section-title">Par produit</div>
            <div class="section-subtitle">Top 10 Articles (Volumes prévus)</div>
        """, unsafe_allow_html=True)
        
        df_top = df_previsions_filtre.groupby('article', observed=True)[col_prev_aff].sum().sort_values(ascending=True).tail(10).reset_index()
        
        fig2 = go.Figure(go.Bar(
            x=df_top[col_prev_aff], y=df_top['article'], orientation='h',
            marker=dict(color=['#009640' if i % 2 == 0 else '#E30613' for i in range(len(df_top))]),
            text=df_top[col_prev_aff].apply(lambda x: f"{x:,.0f}"),
            textposition='auto', textfont=dict(color='white')
        ))
        fig2.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, tickfont=dict(color='#4B5563', size=11)),
            height=320
        )
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <p style="color: #9CA3AF; font-size: 0.75rem; margin-top: 10px;">
        Projection basée sur la logique SARR et CAGR. Les chiffres sont donnés à titre indicatif.
    </p>
    """, unsafe_allow_html=True)

    # 6. MENU DE NAVIGATION PERSONNALISÉ
    st.markdown("<hr style='border: 1px solid #E5E7EB; margin: 30px 0;'>", unsafe_allow_html=True)
    
    tab_names = ["Données Brutes", "Périmètre", "Réalisé Cumulé", "Indices & SARR", "Prévisions Détaillées"]
    active_tab = st.radio("Navigation", tab_names, horizontal=True, label_visibility="collapsed")

    N_MAX_DISPLAY = 5000

    if active_tab == "Données Brutes":
        st.markdown("### Étape 1 : Données Brutes Enrichies (Ventes + Référentiel)")
        if len(df_enrichi) > N_MAX_DISPLAY:
            st.caption(f"⚠️ Affichage limité à {N_MAX_DISPLAY:,} lignes sur {len(df_enrichi):,}.")
            st.dataframe(df_enrichi.head(N_MAX_DISPLAY), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_enrichi, use_container_width=True, hide_index=True)

    elif active_tab == "Périmètre":
        st.markdown("### Étape 2 : Périmètre Filtré")
        if len(df_perimetre) > N_MAX_DISPLAY:
            st.caption(f"⚠️ Affichage limité à {N_MAX_DISPLAY:,} lignes sur {len(df_perimetre):,}.")
            st.dataframe(df_perimetre.head(N_MAX_DISPLAY), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_perimetre, use_container_width=True, hide_index=True)

    elif active_tab == "Réalisé Cumulé":
        st.markdown("### Étape 3 : Réalisé Cumulé (Jusqu'au Cutoff)")
        if df_realise is not None and not df_realise.empty:
            df_real_agg = (df_realise.groupby(['annee', 'mois', 'region', 'agence', 'article'], observed=True)[['hl']].sum().reset_index())
            st.dataframe(df_real_agg.head(N_MAX_DISPLAY), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune donnée réalisée pour le moment.")

    elif active_tab == "Indices & SARR":
        st.markdown("### Étape 4 : Indices de Saisonnalité & SARR")
        c_idx, c_sarr = st.columns(2)
        with c_idx:
            st.markdown("**Indices de Saisonnalité**")
            if not table_indices.empty:
                pivot_indices = _pivot_indices_cached(table_indices)
                st.dataframe(pivot_indices, use_container_width=True)
            else:
                st.info("Pas d'historique complet.")
        with c_sarr:
            st.markdown("**Table SARR (5 derniers mois)**")
            df_sarr["SARR_Aff"] = (df_sarr["SARR_HL"] * (10000 / df_sarr["contenance_cl"].replace(0, 100)) if unite_affichage == "Cols" else df_sarr["SARR_HL"])
            df_sarr_derniers = (df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).groupby(['agence', 'article'], observed=True).tail(5))
            st.dataframe(df_sarr_derniers[["annee", "mois", "agence", "article", "SARR_Aff"]].sort_values(["agence", "article", "annee", "mois"]), use_container_width=True, hide_index=True)

    elif active_tab == "Prévisions Détaillées":
        st.markdown("### Résultat Final")
        st.markdown(f"Projections mensuelles pour : **<span style='color: #E30613;'>{label_mois_str}</span>**", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        col_search, col_export = st.columns([3, 1])
        
        with col_search:
            search_query = st.text_input("Rechercher", "", placeholder="Rechercher un article ou une agence...", label_visibility="collapsed")
            
        with col_export:
            pivot_mensuel = _pivot_mensuel_cached(df_previsions_filtre, col_prev_aff).copy()
            if len(mois_cibles_selection) > 1: pivot_mensuel['Total Période'] = pivot_mensuel.sum(axis=1)
            elif len(mois_cibles_selection) == 0: pivot_mensuel['Total Année'] = pivot_mensuel.sum(axis=1)
            pivot_mensuel = pivot_mensuel[pivot_mensuel.sum(axis=1) > 0]
            
            csv = pivot_mensuel.to_csv().encode('utf-8')
            st.download_button(
                label="Exporter en CSV",
                data=csv,
                file_name=f"previsions_star_{annee_cible}.csv",
                mime="text/csv",
                use_container_width=True
            )

        pivot_mensuel_reset = pivot_mensuel.reset_index()
        pivot_mensuel_reset.columns = [
            "Année" if str(c).lower() == "annee" else 
            "Agence" if str(c).lower() == "agence" else 
            "Article" if str(c).lower() == "article" else 
            "Total Période" if "période" in str(c).lower() else
            "Total Année" if "année" in str(c).lower() else str(c)
            for c in pivot_mensuel_reset.columns
        ]

        if search_query:
            mask = pivot_mensuel_reset.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
            pivot_mensuel_display = pivot_mensuel_reset[mask]
        else:
            pivot_mensuel_display = pivot_mensuel_reset

        col_config = {
            "Année": st.column_config.NumberColumn("Année", format="%d"),
            "Agence": st.column_config.TextColumn("Agence"),
            "Article": st.column_config.TextColumn("Article"),
        }
        for mois in MOIS_NOMS:
            if mois in pivot_mensuel_display.columns:
                col_config[mois] = st.column_config.NumberColumn(mois, format="localized")
        
        if "Total Période" in pivot_mensuel_display.columns:
             col_config["Total Période"] = st.column_config.NumberColumn("Total Période", format="localized")
        if "Total Année" in pivot_mensuel_display.columns:
             col_config["Total Année"] = st.column_config.NumberColumn("Total Année", format="localized")

        st.dataframe(
            pivot_mensuel_display,
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
            height=500
        )

        with st.expander("Voir le détail des calculs"):
            cols_to_show = ["annee", "mois", "Statut", "agence", "article", "Indice", "Base_Mensuelle", col_prev_aff]
            if annee_cible > annee_cloture: cols_to_show.insert(-1, "CAGR (%)")
            df_detail = (df_previsions_filtre[cols_to_show].sort_values(["annee", "mois", "agence", "article"]))
            st.dataframe(df_detail.head(N_MAX_DISPLAY), use_container_width=True, hide_index=True, height=400)

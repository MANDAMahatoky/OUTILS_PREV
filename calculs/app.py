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
st.set_page_config(page_title="PREVISIONS STAR MADAGASCAR", layout="wide", page_icon="⭐", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F4F6F8 !important; }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB; box-shadow: 2px 0 10px rgba(0,0,0,0.03);
    }
    [data-testid="stSidebar"] h2 { color: #111827 !important; font-size: 1.1rem; font-weight: 700; margin-top: 10px; margin-bottom: 15px; }
    [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stNumberInput label, [data-testid="stSidebar"] .stMultiSelect label { color: #4B5563 !important; font-size: 0.85rem !important; font-weight: 600 !important; }
    
    /* HEADER COMPACT */
    .hero-header {
        background: linear-gradient(135deg, #B91C1C 0%, #E30613 100%); color: white; padding: 24px 30px;
        border-radius: 12px; margin-top: 10px; margin-bottom: 25px; box-shadow: 0 4px 10px -5px rgba(227, 6, 19, 0.3);
        display: flex; flex-direction: row; justify-content: space-between; align-items: center;
    }
    .hero-header h1 { color: white !important; font-size: 1.6rem; font-weight: 700; margin: 0; letter-spacing: -0.02em; }
    .hero-header p { color: #FECACA; font-size: 0.9rem; margin: 0; margin-top: 6px; font-weight: 500; }
    .badge-demo { background-color: white; color: #E30613; padding: 8px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.1); white-space: nowrap; }
    
    /* CARDS & KPI */
    .white-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03); border: 1px solid #E5E7EB; margin-bottom: 20px; height: 100%; }
    .kpi-label { color: #6B7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .kpi-value { color: #E30613; font-size: 2.2rem; font-weight: 600; line-height: 1.1; }
    .kpi-value-dark { color: #111827; }
    .kpi-value-green { color: #059669; }
    .kpi-value-red { color: #E30613; }
    .kpi-footer { color: #9CA3AF; font-size: 0.8rem; margin-top: 8px; font-weight: 500; }
    
    /* SECTIONS */
    .section-title { color: #111827; font-size: 1.2rem; font-weight: 700; margin-bottom: 5px; }
    .section-subtitle { color: #6B7280; font-size: 0.85rem; margin-bottom: 20px; font-weight: 500; }
    
    /* FORMS & EXPANDERS */
    div[data-baseweb="select"] > div, div[data-testid="stNumberInput"] input, div[data-testid="stMultiSelect"] { background-color: #F9FAFB !important; border-radius: 8px !important; border: 1px solid #D1D5DB !important; }
    div[data-testid="stExpander"] { background-color: white !important; border-radius: 12px !important; border: 1px solid #E5E7EB !important; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02) !important; margin-bottom: 20px !important; }
    div[data-testid="stExpander"] > details > summary { background-color: #F9FAFB !important; border-radius: 12px !important; font-weight: 600 !important; color: #111827 !important; padding: 15px 20px !important; border-bottom: 1px solid transparent !important; }
    div[data-testid="stExpander"] > details[open] > summary { border-bottom: 1px solid #E5E7EB !important; border-bottom-left-radius: 0 !important; border-bottom-right-radius: 0 !important; }
    
    /* TABLES */
    div[data-testid="stDataFrame"] { border: 1px solid #E5E7EB !important; border-radius: 8px !important; padding: 10px !important; background-color: white !important; }
    
    /* NAVIGATION TABS */
    div[role="radiogroup"] { gap: 28px !important; border-bottom: 2px solid #E5E7EB !important; padding-bottom: 0px !important; margin-bottom: 25px !important; display: flex !important; flex-wrap: wrap !important; align-items: flex-end !important; }
    div[role="radiogroup"] label { background: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; border-radius: 0 !important; padding: 8px 4px 14px 4px !important; margin: 0 !important; cursor: pointer !important; transition: all 0.2s ease !important; }
    div[role="radiogroup"] label div p { font-size: 1.05rem !important; font-weight: 600 !important; color: #6B7280 !important; transition: color 0.2s ease !important; margin: 0 !important; letter-spacing: 0.01em !important; }
    div[role="radiogroup"] label:hover div p { color: #111827 !important; }
    div[role="radiogroup"] label:has(input:checked) { border-bottom: 3px solid #E30613 !important; }
    div[role="radiogroup"] label:has(input:checked) div p { color: #E30613 !important; font-weight: 700 !important; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] label:focus-within { outline: none !important; box-shadow: none !important; }
    div[role="radiogroup"] + div { margin-top: -10px !important; }
    
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def color_error(val, seuil_alerte=10, seuil_bon=5):
    try:
        val = float(val)
        if val > seuil_alerte: return 'background-color: #FEE2E2; color: #991B1B;'
        if val < seuil_bon: return 'background-color: #D1FAE5; color: #065F46;'
        return 'background-color: #FEF3C7; color: #92400E;'
    except: return ''

def color_ecart(val):
    try:
        val = float(val)
        if abs(val) > 30: return 'background-color: #FEE2E2; color: #991B1B;'
        if abs(val) > 15: return 'background-color: #FEF3C7; color: #92400E;'
        return 'background-color: #D1FAE5; color: #065F46;'
    except: return ''

def get_region(agence):
    if pd.isna(agence): return "Autre"
    a = str(agence).lower().replace("-", "").replace(" ", "").replace("_", "")
    if "andranomahery" in a or "antsirabe" in a: return "Centre"
    if "tanjombato" in a or "tamatave" in a: return "Est"
    if "diego" in a or "majunga" in a or "ambanja" in a or "sambava" in a or "nosybe" in a: return "Nord"
    if "tulear" in a or "fianarantsoa" in a or "ihosy" in a or "manakara" in a or "morondava" in a or "dauphin" in a: return "Sud"
    return "Autre"

def extraire_marque(article):
    if pd.isna(article): return "Inconnu"
    a = str(article).strip()
    a_low = a.lower()
    if "world cola" in a_low: return "World Cola"
    if "eau vive" in a_low: return "Eau Vive"
    return a.split()[0]

def extraire_emballage(article):
    if pd.isna(article): return "Inconnu"
    a = str(article).upper()
    if "PET" in a: return "PET"
    if "CAN" in a: return "CAN"
    if "VER" in a: return "VER"
    if "BOB" in a: return "BOB"
    return "AUTRE"

def clean_text_for_key(text):
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]', '', text)

def clean_text_for_budget_key(text):
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = text.replace('33 cl', '33').replace('33cl', '33')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]', '', text)

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

MOIS_NOMS = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

def normaliser_mois(serie: pd.Series) -> pd.Series:
    series_clean = serie.astype(str).str.strip()
    try:
        numeric_series = pd.to_numeric(series_clean, errors='coerce')
        if numeric_series.notna().all():
            if numeric_series.between(1, 12).all():
                return numeric_series.astype(int)
            dates = pd.to_datetime(numeric_series, unit='D', origin='1899-12-30', errors='coerce')
            if dates.notna().all():
                return dates.dt.month
    except Exception:
        pass
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

# ==============================================================================
# LOGIQUE DE CALCUL
# ==============================================================================
@st.cache_data(show_spinner=False)
def charger_ruptures(rupture_bytes):
    if rupture_bytes is None: return pd.DataFrame()
    try:
        df = pd.read_excel(io.BytesIO(rupture_bytes), sheet_name="Rupture", header=None)
        df = df.iloc[1:, [0, 1, 2, 3]].copy()
        df.columns = ['Mois_Str', 'agence', 'article', 'rupture_hl']
        
        df['Mois_Str'] = df['Mois_Str'].astype(str).str.strip()
        df['mois'] = pd.to_numeric(df['Mois_Str'].str.split(' ').str[0], errors='coerce')
        df['annee'] = pd.to_numeric(df['Mois_Str'].str.split(' ').str[1], errors='coerce')
        
        df = df.dropna(subset=['mois', 'annee', 'agence', 'article'])
        df['annee'] = df['annee'].astype(int)
        df['mois'] = df['mois'].astype(int)
        df['rupture_hl'] = pd.to_numeric(df['rupture_hl'], errors='coerce').fillna(0.0)
        
        df['agence'] = df['agence'].astype(str).str.strip()
        df['cle_article'] = df['article'].astype(str).apply(clean_text_for_key)
        
        return df[['annee', 'mois', 'agence', 'cle_article', 'rupture_hl']]
    except Exception as e:
        st.error(f"Erreur de lecture du fichier rupture : {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner="Chargement et enrichissement des données...")
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes, rupture_bytes: bytes) -> pd.DataFrame:
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
    df_ref["marque"] = df_ref["article_original"].apply(extraire_marque)
    df_ref["emballage"] = df_ref["article_original"].apply(extraire_emballage)
    df_ref["cle_article"] = df_ref["article_original"].apply(clean_text_for_key)
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
    df["cle_article"] = df["article_original"].apply(clean_text_for_key)

    if ref_bytes is not None:
        df_enrichi = pd.merge(df_ref, df, on="cle_article", how="inner")
    else:
        df_enrichi = pd.merge(df_ref, df, on="cle_article", how="outer")
        
    df_enrichi["article"] = df_enrichi["article_original_x"].fillna(df_enrichi["article_original_y"]).fillna("Inconnu").astype(str)
    df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
    df_enrichi["volume_brut"] = df_enrichi["volume_brut"].fillna(0.0)
    df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
    df_enrichi["marque"] = df_enrichi["marque"].fillna("Inconnu")
    df_enrichi["emballage"] = df_enrichi["emballage"].fillna("AUTRE")
    df_enrichi["contenance_cl"] = pd.to_numeric(df_enrichi["contenance_cl"], errors="coerce").fillna(100.0)
    df_enrichi.loc[df_enrichi["contenance_cl"] <= 0, "contenance_cl"] = 100.0

    masque_fut20 = df_enrichi["article"].str.contains(r'20L|20 L|FUT 20', case=False, na=False, regex=True)
    df_enrichi.loc[masque_fut20, "contenance_cl"] = 2000.0
    
    df_enrichi["hl"] = df_enrichi["volume_brut"].fillna(0.0)
    df_enrichi["region"] = df_enrichi["agence"].apply(get_region)
    df_enrichi["occasion"] = df_enrichi["occasion"].fillna("Non renseigné").astype(str)
    df_enrichi["positionnement"] = df_enrichi["positionnement"].fillna("Non renseigné").astype(str)
    
    conditions = [df_enrichi["article"].str.contains(x, case=False, na=False) for x in ["booster|alcoomix", "caprice|tonic|world cola|d jino|youzou|coca|fanta|sprite", "beaufort|fresh|thb|gold|queen|skol|castel|libertalia", "cristal|cristalline|eau vive|eau", "xxl|fosa", "judor|jus", "vin", "negoce"]]
    choices = ["5-ALCOMIX", "2-BG", "1-BIERES", "4-EAUX", "3-ENERGY", "4-JUS", "7-VIN", "6-NEGOCE"]
    df_enrichi["segment"] = np.select(conditions, choices, default="AUTRE / INCONNU")
    
    # --- INTEGRATION DES RUPTURES (POUR L'AFFICHAGE UNIQUEMENT) ---
    df_ruptures = charger_ruptures(rupture_bytes)
    if not df_ruptures.empty:
        df_enrichi = df_enrichi.merge(df_ruptures, on=['annee', 'mois', 'agence', 'cle_article'], how='left')
        df_enrichi['rupture_hl'] = df_enrichi['rupture_hl'].fillna(0.0)
    else:
        df_enrichi['rupture_hl'] = 0.0

    df_enrichi["hl_potentiel"] = df_enrichi["hl"] + df_enrichi["rupture_hl"]

    for col in ['region', 'segment', 'positionnement', 'occasion', 'marque', 'emballage']:
        if col in df_enrichi.columns: df_enrichi[col] = df_enrichi[col].astype('category')

    return df_enrichi[["annee", "mois", "segment", "region", "produit", "agence", "hl", "hl_potentiel", "rupture_hl", "volume_brut", "article", "positionnement", "occasion", "marque", "contenance_cl", "emballage"]]

def _calculer_indices_fallback(df_realise, annee_min_is, annee_max_is):
    df_h = df_realise[(df_realise['annee'] >= annee_min_is) & (df_realise['annee'] <= annee_max_is)].copy()
    if df_h.empty:
        max_annee = df_realise['annee'].max()
        df_h = df_realise[df_realise['annee'] == max_annee].copy()
    if df_h.empty: return pd.DataFrame(columns=['agence', 'article', 'mois', 'Indice'])

    def _idx(group_cols):
        # On utilise 'hl' (ventes réelles) pour les indices
        v = (df_h.groupby(group_cols + ['annee', 'mois'], observed=True)['hl'].sum().unstack('mois').fillna(0.0).reindex(columns=range(1, 13), fill_value=0.0))
        cum_m = v.groupby(group_cols).sum()
        cum_a = v.sum(axis=1).groupby(group_cols).sum()
        moy_mensuelle = cum_a / 12.0
        indices = cum_m.div(moy_mensuelle, axis=0)
        indices = indices.replace([np.inf, -np.inf], np.nan)
        return indices.reset_index().melt(id_vars=group_cols, var_name='mois', value_name='Indice')

    idx1 = _idx(['agence', 'article'])
    idx2 = _idx(['article']).rename(columns={'Indice': 'Indice_art'})
    idx3 = _idx(['marque']).rename(columns={'Indice': 'Indice_marque'})
    idx4 = _idx(['segment']).rename(columns={'Indice': 'Indice_seg'})
    tot = df_h.groupby('mois', observed=True)['hl'].sum().reindex(range(1, 13), fill_value=0.0)
    glob = (tot / (tot.sum() / 12.0)).reset_index()
    glob.columns = ['mois', 'Indice_glob']

    df_base = df_h[['agence', 'article', 'marque', 'segment', 'mois']].drop_duplicates()

    result = (df_base.merge(idx1, on=['agence', 'article', 'mois'], how='left')
                      .merge(idx2, on=['article', 'mois'], how='left')
                      .merge(idx3, on=['marque', 'mois'], how='left')
                      .merge(idx4, on=['segment', 'mois'], how='left')
                      .merge(glob, on='mois', how='left'))

    result['Indice'] = result['Indice'].fillna(result['Indice_art']).fillna(result['Indice_marque']).fillna(result['Indice_seg']).fillna(result['Indice_glob']).fillna(1.0)
    result['mois'] = result['mois'].astype(int)
    return result[['agence', 'article', 'mois', 'Indice']]

@st.cache_data(show_spinner="Calcul des prévisions...")
def calculer_etape_5(df_perimetre, annee_min_is, annee_max_is, annee_min_cagr, annee_max_cagr, annee_cloture, mois_cutoff, annee_cible, methode_croissance, budget_bytes, budget_all_agencies, cache_bust="v128"):
    budget_status = "skipped"

    annees_recentes = [annee_cloture, annee_cloture - 1]
    df_recent = df_perimetre[df_perimetre['annee'].isin(annees_recentes)]
    couples_actifs = df_recent[df_recent['hl'] > 0][['agence', 'article']].drop_duplicates()
    
    df_perimetre_filtre = pd.merge(df_perimetre, couples_actifs, on=['agence', 'article'], how='inner')
    if df_perimetre_filtre.empty: return None, None, None, None, df_perimetre, budget_status

    df_limite = df_perimetre_filtre[(df_perimetre_filtre["annee"] < annee_cloture) | ((df_perimetre_filtre["annee"] == annee_cloture) & (df_perimetre_filtre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, df_perimetre_filtre, budget_status

    table_indices = _calculer_indices_fallback(df_realise, annee_min_is, annee_max_is)
    if table_indices.empty:
        df_ag_art = df_perimetre_filtre[['agence', 'article']].drop_duplicates()
        df_ag_art['key'] = 1
        df_mois = pd.DataFrame({'mois': list(range(1, 13)), 'key': 1})
        table_indices = pd.merge(df_ag_art, df_mois, on='key').drop('key', axis=1)
        table_indices['Indice'] = 1.0

    df_realise_agg = df_realise.groupby(['annee', 'mois', 'agence', 'article'], observed=True)[['hl', 'hl_potentiel', 'rupture_hl']].sum().reset_index()
    min_annee = df_realise_agg['annee'].min()
    dates = pd.date_range(start=f'{min_annee}-01-01', end=f'{annee_cloture}-{mois_cutoff:02d}-01', freq='MS')
    df_dates = pd.DataFrame({'Date': dates})
    df_dates['annee'] = df_dates['Date'].dt.year
    df_dates['mois'] = df_dates['Date'].dt.month

    ag_art = df_realise_agg[['agence', 'article']].drop_duplicates()
    df_skeleton = pd.merge(ag_art, df_dates, how='cross')

    df_sarr_cont = pd.merge(df_skeleton, df_realise_agg, on=['annee', 'mois', 'agence', 'article'], how='left')
    df_sarr_cont = df_sarr_cont.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    
    df_sarr_cont['Indice'] = df_sarr_cont['Indice'].fillna(1.0).clip(lower=0.1) 
    # Retour au 'hl' pour le calcul du SARR
    df_sarr_cont['SARR_HL'] = df_sarr_cont['hl'] / df_sarr_cont['Indice']

    df_sarr_cont = df_sarr_cont.sort_values(['agence', 'article', 'annee', 'mois']).reset_index(drop=True)
    g = df_sarr_cont.groupby(['agence', 'article'], observed=True)

    df_sarr_cont['SARR_M1'] = g['SARR_HL'].shift(1)
    df_sarr_cont['SARR_M2'] = g['SARR_HL'].shift(2)
    df_sarr_cont['SARR_M3'] = g['SARR_HL'].shift(3)

    df_sarr_cont['SARR_MA3'] = df_sarr_cont[['SARR_M1', 'SARR_M2', 'SARR_M3']].mean(axis=1)
    
    df_sarr_cont['Base_EXCEL'] = df_sarr_cont['SARR_HL'].fillna(0.0)
    mask_ma3 = df_sarr_cont['SARR_MA3'].notna()
    df_sarr_cont.loc[mask_ma3, 'Base_EXCEL'] = np.maximum(df_sarr_cont.loc[mask_ma3, 'SARR_HL'].fillna(0.0), df_sarr_cont.loc[mask_ma3, 'SARR_MA3'])

    df_sarr_cont['Ecart_1'] = df_sarr_cont['SARR_HL'].fillna(0.0) - df_sarr_cont['SARR_M1'].fillna(0.0)
    df_sarr_cont['Ecart_2'] = df_sarr_cont['SARR_M1'].fillna(0.0) - df_sarr_cont['SARR_M2'].fillna(0.0)
    df_sarr_cont['Ecart_3'] = df_sarr_cont['SARR_M2'].fillna(0.0) - df_sarr_cont['SARR_M3'].fillna(0.0)
    df_sarr_cont['Momentum'] = df_sarr_cont[['Ecart_1', 'Ecart_2', 'Ecart_3']].mean(axis=1).fillna(0.0)

    df_base_momentum = df_sarr_cont[(df_sarr_cont['annee'] == annee_cloture) & (df_sarr_cont['mois'] == mois_cutoff)][['agence', 'article', 'Base_EXCEL', 'Momentum']].copy()

    df_perim_unique = df_perimetre_filtre[['agence', 'article', 'contenance_cl']].drop_duplicates(subset=['agence', 'article'])
    # Retour au 'hl' pour le YTD
    df_realise['hl_positif'] = np.maximum(0.0, df_realise['hl'])
    df_ytd = (df_realise[(df_realise['annee'] == annee_cloture) & (df_realise['mois'] <= mois_cutoff)].groupby(['agence', 'article'], observed=True)['hl_positif'].sum().reset_index().rename(columns={'hl_positif': 'YTD_HL'}))
    df_premiere_annee = (df_realise[df_realise['hl'] > 0].groupby(['agence', 'article'], observed=True)['annee'].min().reset_index().rename(columns={'annee': 'Annee_Debut'}))

    df_base = (df_perim_unique.merge(df_ytd, on=['agence', 'article'], how='left').merge(df_premiere_annee, on=['agence', 'article'], how='left'))
    df_base['YTD_HL'] = df_base['YTD_HL'].fillna(0.0)
    df_base['Annee_Debut'] = df_base['Annee_Debut'].fillna(annee_cloture)
    df_base['Annee_Base'] = np.maximum(annee_min_cagr, df_base['Annee_Debut'])

    # Retour au 'hl' pour la base historique
    df_base_vol = (df_realise.groupby(['agence', 'article', 'annee'], observed=True)['hl'].sum().reset_index())
    df_base = df_base.merge(df_base_vol, left_on=['agence', 'article', 'Annee_Base'], right_on=['agence', 'article', 'annee'], how='left')
    df_base = df_base.rename(columns={'hl': 'Base_Hist'}).drop(columns=['annee'])
    df_base['Base_Hist'] = df_base['Base_Hist'].fillna(0.0)

    df_mois_debut = (df_realise[(df_realise['annee'] == annee_cloture) & (df_realise['hl'] > 0)]
                     .groupby(['agence', 'article'], observed=True)['mois'].min()
                     .reset_index().rename(columns={'mois': 'Mois_Debut'}))
    
    df_base = df_base.merge(df_mois_debut, on=['agence', 'article'], how='left')
    df_base['Mois_Debut'] = df_base['Mois_Debut'].fillna(1).astype(int)

    df_indices_temp = df_base[['agence', 'article', 'Mois_Debut']].merge(table_indices, on=['agence', 'article'], how='left')
    df_cumul = (df_indices_temp[(df_indices_temp['mois'] >= df_indices_temp['Mois_Debut']) & (df_indices_temp['mois'] <= mois_cutoff)]
                .groupby(['agence', 'article'], observed=True)['Indice'].sum()
                .reset_index().rename(columns={'Indice': 'Cumul_Coef'}))

    df_base = df_base.drop(columns=['Mois_Debut']).merge(df_cumul, on=['agence', 'article'], how='left')
    df_base['Cumul_Coef'] = df_base['Cumul_Coef'].fillna(mois_cutoff * 1.0).replace(0, 1.0)
    df_base['Base_Mensuelle'] = df_base['YTD_HL'] / df_base['Cumul_Coef']
    df_base['Projection_CurrentYear'] = df_base['Base_Mensuelle'] * 12.0
    df_base['Nb_Annees'] = annee_cloture - df_base['Annee_Base']

    # Retour au 'hl' pour le CAGR historique
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

    df_base['CAGR_Hist'] = df_base['CAGR_Hist'].clip(lower=-0.20, upper=0.30)

    if methode_croissance == "CAGR Classique":
        df_base['CAGR_brut'] = np.where((df_base['Base_Hist'] > 0) & (df_base['Projection_CurrentYear'] > 0) & (df_base['Nb_Annees'] > 0), (df_base['Projection_CurrentYear'] / df_base['Base_Hist']) ** (1 / df_base['Nb_Annees']) - 1, df_base['CAGR_Hist'])
        df_base['CAGR_val'] = np.where(df_base['Base_Hist'] < 100.0, df_base['CAGR_Hist'], df_base['CAGR_brut'])
    
    elif methode_croissance == "Tendance Linéaire":
        slopes_data = []
        for (agence, article), group in df_hist_cagr.groupby(['agence', 'article'], observed=True):
            try:
                x = group['annee'].values.astype(float)
                y = group['hl'].values.astype(float) # Retour au 'hl'
                mask = ~np.isnan(x) & ~np.isnan(y)
                x = x[mask]
                y = y[mask]
                if len(x) >= 2 and np.sum(y) > 0:
                    slope, _ = np.polyfit(x, y, 1)
                    mean_y = np.mean(y)
                    slope_rel = float(slope / mean_y) if mean_y > 0 else 0.0
                else:
                    slope_rel = 0.0
            except Exception:
                slope_rel = 0.0
            slopes_data.append({'agence': agence, 'article': article, 'Slope_Rel': slope_rel})
            
        slopes = pd.DataFrame(slopes_data, columns=['agence', 'article', 'Slope_Rel'])
        if not slopes.empty:
            df_base = df_base.merge(slopes, on=['agence', 'article'], how='left')
            df_base['CAGR_val'] = df_base['Slope_Rel'].fillna(df_base['CAGR_Hist'])
        else:
            df_base['CAGR_val'] = df_base['CAGR_Hist']

    elif methode_croissance == "Moyenne 3 ans":
        try:
            df_pivot = df_hist_cagr.pivot_table(index=['agence', 'article'], columns='annee', values='hl', aggfunc='sum').fillna(0) # Retour au 'hl'
            growth_rates = df_pivot.pct_change(axis=1).iloc[:, -3:].mean(axis=1).reset_index(name='Avg_Growth')
            if not growth_rates.empty:
                df_base = df_base.merge(growth_rates, on=['agence', 'article'], how='left')
                df_base['CAGR_val'] = df_base['Avg_Growth'].fillna(df_base['CAGR_Hist'])
            else:
                df_base['CAGR_val'] = df_base['CAGR_Hist']
        except Exception:
            df_base['CAGR_val'] = df_base['CAGR_Hist']
    else:
        df_base['CAGR_val'] = df_base['CAGR_Hist']

    df_base['CAGR_val'] = df_base['CAGR_val'].clip(lower=-0.20, upper=0.30)
    df_base = df_base.merge(df_base_momentum, on=['agence', 'article'], how='left').fillna({'Base_EXCEL': 0.0, 'Momentum': 0.0})

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
    
    prev_2026 = df_cross['Base_Mensuelle'] * df_cross['Indice']
    prev_futur = df_cross['Base_Mensuelle'] * df_cross['Indice'] * df_cross['multiplicateur_cagr']

    df_cross['Prevision_HL'] = np.where(df_cross['annee'] == annee_cloture, prev_2026, prev_futur)
    df_cross['Prevision_HL'] = np.maximum(0.0, df_cross['Prevision_HL'])
    
    df_cross['key_article_budget'] = df_cross['article'].apply(clean_text_for_budget_key)
    
    if budget_bytes is not None:
        try:
            xls = pd.ExcelFile(io.BytesIO(budget_bytes))
            df_budget = None
            for sheet in xls.sheet_names:
                temp = pd.read_excel(xls, sheet_name=sheet)
                temp.columns = [str(c).strip().lower() for c in temp.columns]
                if any('article' in c for c in temp.columns) and any('valeur' in c for c in temp.columns) and any('mois' in c for c in temp.columns):
                    df_budget = temp.copy()
                    break
            
            if df_budget is None:
                budget_status = "warning"
            else:
                col_art = next((c for c in df_budget.columns if 'article' in c), None)
                col_val = next((c for c in df_budget.columns if 'valeur' in c), None)
                col_mois = next((c for c in df_budget.columns if 'mois' in c), None)
                col_ag = next((c for c in df_budget.columns if 'attribut' in c or 'agence' in c), None)
                
                if col_art and col_val and col_mois:
                    df_budget = df_budget.dropna(subset=[col_art])
                    mask_33can = df_budget[col_art].astype(str).str.contains('33', na=False) & df_budget[col_art].astype(str).str.contains('CAN', case=False, na=False)
                    df_budget = df_budget[mask_33can].copy()
                    
                    if df_budget.empty:
                        budget_status = "warning"
                    else:
                        df_budget['key_article_budget'] = df_budget[col_art].apply(clean_text_for_budget_key)
                        df_budget['mois'] = pd.to_numeric(df_budget[col_mois], errors='coerce')
                        df_budget['valeur_budget'] = pd.to_numeric(df_budget[col_val], errors='coerce').fillna(0.0)
                        df_budget = df_budget.dropna(subset=['mois'])
                        
                        df_temp_content = df_cross[['key_article_budget', 'contenance_cl']].drop_duplicates(subset=['key_article_budget'])
                        df_budget = df_budget.merge(df_temp_content, on='key_article_budget', how='left')
                        df_budget['contenance_cl'] = df_budget['contenance_cl'].fillna(33.0)
                        df_budget['valeur_budget'] = df_budget['valeur_budget'] * (df_budget['contenance_cl'] / 10000.0)
                        
                        mask_budget_target = (df_cross['annee'] == annee_cible) & (~df_cross['is_realise'])
                        
                        if budget_all_agencies or not col_ag:
                            df_budget_agg = df_budget.groupby(['key_article_budget', 'mois'])['valeur_budget'].sum().reset_index()
                            df_cross = df_cross.merge(df_budget_agg, on=['key_article_budget', 'mois'], how='left', suffixes=('', '_budget'))
                            
                            df_cross['Forecast_Total_Article_Mois'] = (
                                df_cross.loc[mask_budget_target]
                                .groupby(['key_article_budget', 'mois'])['Prevision_HL']
                                .transform('sum')
                                .reindex(df_cross.index)
                            )
                            
                            mask_apply = mask_budget_target & df_cross['valeur_budget'].notna()
                            mask_denom_pos = mask_apply & (df_cross['Forecast_Total_Article_Mois'] > 0)
                            mask_denom_zero = mask_apply & (df_cross['Forecast_Total_Article_Mois'] == 0)
                            
                            df_cross.loc[mask_denom_pos, 'Prevision_HL'] = (
                                df_cross.loc[mask_denom_pos, 'Prevision_HL']
                                * (df_cross.loc[mask_denom_pos, 'valeur_budget']
                                   / df_cross.loc[mask_denom_pos, 'Forecast_Total_Article_Mois'])
                            )
                            df_cross.loc[mask_denom_zero, 'Prevision_HL'] = df_cross.loc[mask_denom_zero, 'valeur_budget']
                            
                        else:
                            df_budget['agence_clean'] = df_budget[col_ag].astype(str).str.replace(r'^\d+-', '', regex=True)
                            df_budget['key_agence'] = df_budget['agence_clean'].apply(clean_text_for_key)
                            df_cross['key_agence'] = df_cross['agence'].apply(clean_text_for_key)
                            
                            df_budget_agg = df_budget.groupby(['key_article_budget', 'key_agence', 'mois'])['valeur_budget'].sum().reset_index()
                            df_cross = df_cross.merge(df_budget_agg, on=['key_article_budget', 'key_agence', 'mois'], how='left', suffixes=('', '_budget'))
                            
                            mask_apply = mask_budget_target & df_cross['valeur_budget'].notna()
                            df_cross.loc[mask_apply, 'Prevision_HL'] = df_cross.loc[mask_apply, 'valeur_budget']
                        
                        budget_status = "ok"
                else:
                    budget_status = "warning"
        except Exception as e:
            budget_status = "error"

    for c in ['key_article_budget', 'key_agence', 'valeur_budget', 'Forecast_Total_Article_Mois', 'contenance_cl_x', 'contenance_cl_y', 'agence_clean']:
        if c in df_cross.columns:
            df_cross = df_cross.drop(columns=[c])

    df_cross['Prevision_HL'] = np.maximum(0.0, df_cross['Prevision_HL'])
    df_cross['Volume_HL'] = np.where(df_cross['is_realise'], df_cross['hl_reel'].fillna(0.0), df_cross['Prevision_HL'])
    df_cross['Volume_HL'] = np.maximum(0.0, df_cross['Volume_HL'])
    
    contenance_safe = df_cross['contenance_cl'].replace(0, 100).fillna(100.0)
    df_cross['Volume_Cols'] = df_cross['Volume_HL'] * (10000.0 / contenance_safe)
    df_cross['Prevision_Cols'] = df_cross['Prevision_HL'] * (10000.0 / contenance_safe)
    
    df_cross['Statut'] = np.where(df_cross['is_realise'], "Réalisé", "Prévision")
    df_cross['CAGR (%)'] = df_cross['CAGR_val'] * 100

    _mois_arr = np.array(MOIS_NOMS, dtype=object)
    df_cross['Date'] = (_mois_arr[df_cross['mois'].to_numpy() - 1] + '-' + df_cross['annee'].astype(str).str[-2:].to_numpy())

    cols_finales = ["annee", "mois", "agence", "article", "contenance_cl", "Date", "Statut", "Indice", "Base_EXCEL", "Momentum", "Base_Mensuelle", "CAGR (%)", "Volume_HL", "Volume_Cols", "Prevision_HL", "Prevision_Cols", "hl_reel"]
    df_realise_out = df_realise.merge(
        df_perimetre_filtre[['agence', 'article']].drop_duplicates(),
        on=['agence', 'article'], how='inner'
    ).copy()

    df_sarr_out = df_sarr_cont.merge(df_perim_unique[['agence', 'article', 'contenance_cl']], on=['agence', 'article'], how='left')

    return table_indices, df_sarr_out, None, df_cross[cols_finales].copy(), df_realise_out, budget_status

@st.cache_data(show_spinner=False)
def _pivot_indices_cached(df_idx: pd.DataFrame) -> pd.DataFrame:
    p = df_idx.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
    p.columns = [MOIS_NOMS[c - 1] for c in p.columns]
    return p

# ==============================================================================
# INTERFACE UTILISATEUR
# ==============================================================================

with st.sidebar:
    BASE_DIR = Path(__file__).parent if "__file__" in locals() else Path.cwd()
    LOGO_PATH = BASE_DIR / "LOGO_STAR.png"
    
    if LOGO_PATH.exists(): st.image(str(LOGO_PATH), use_container_width=True)
    else: st.warning("⚠️ Logo non trouvé")
    
    st.markdown("<h2>🎯 Filtres & Paramètres</h2>", unsafe_allow_html=True)
    
    with st.expander("📁 Importer vos fichiers", expanded=True):
        fichier_ventes = st.file_uploader("Ventes (DATA_BRUT.xlsx)", type=["xlsx"], key="uploader_ventes")
        fichier_ref = st.file_uploader("Référentiel (Classeur2.xlsx)", type=["xlsx"], key="uploader_ref", help="Si fourni, l'application ne calculera que sur les articles de ce fichier.")
        fichier_budget = st.file_uploader("Budget Query (Optionnel)", type=["xlsx"], key="uploader_budget", help="Permet d'écraser les prévisions mathématiques par des valeurs manuelles (uniquement pour les 33 CAN).")
        fichier_rupture = st.file_uploader("Ruptures (rupture.xlsx)", type=["xlsx"], key="uploader_rupture", help="Fichier contenant l'historique des volumes perdus (Rup Hl) par mois/agence/article.")
        
        if fichier_budget is not None:
            budget_all_agencies = st.checkbox("Appliquer le Budget à toutes les agences", value=True, help="Si coché, les valeurs du 33 CAN s'appliqueront à toutes les agences.", key="chk_budget_all")
        else:
            budget_all_agencies = True

    if fichier_ventes is not None:
        df_enrichi = charger_et_enrichir(
            fichier_ventes.getvalue(), 
            fichier_ref.getvalue() if fichier_ref is not None else None,
            fichier_rupture.getvalue() if fichier_rupture is not None else None
        )

        st.markdown("#### 1. Périmètre")
        
        regions_dispo = sorted([str(r) for r in df_enrichi["region"].unique() if pd.notna(r) and str(r) not in ["Aucune vente", "Autre"]])
        sel_regions = st.multiselect("Région", options=regions_dispo, placeholder="Toutes", key="filter_region")
        df_temp = df_enrichi[df_enrichi["region"].isin(sel_regions)] if sel_regions else df_enrichi

        agences_dispo = sorted([str(a) for a in df_temp["agence"].unique() if pd.notna(a) and str(a) != "Aucune vente"])
        sel_agences = st.multiselect("Agence", options=agences_dispo, placeholder="Toutes", key="filter_agence")
        df_temp = df_temp[df_temp["agence"].isin(sel_agences)] if sel_agences else df_temp

        segments_dispo = sorted([str(s) for s in df_temp["segment"].unique() if pd.notna(s)])
        sel_segments = st.multiselect("Segment", options=segments_dispo, placeholder="Tous", key="filter_segment")
        df_temp = df_temp[df_temp["segment"].isin(sel_segments)] if sel_segments else df_temp

        marques_dispo = sorted([str(m) for m in df_temp["marque"].unique() if pd.notna(m) and str(m) != "Inconnu"])
        sel_marques = st.multiselect("Marque", options=marques_dispo, placeholder="Toutes", key="filter_marque")
        df_temp = df_temp[df_temp["marque"].isin(sel_marques)] if sel_marques else df_temp

        contenances_dispo = sorted([int(c) for c in df_temp["contenance_cl"].unique() if pd.notna(c)])
        sel_contenances = st.multiselect("Contenance (cl)", options=contenances_dispo, placeholder="Toutes", key="filter_contenance")
        df_temp = df_temp[df_temp["contenance_cl"].isin(sel_contenances)] if sel_contenances else df_temp

        emballages_dispo = sorted([str(e) for e in df_temp["emballage"].unique() if pd.notna(e) and str(e) != "AUTRE"])
        sel_emballages = st.multiselect("Emballage", options=emballages_dispo, placeholder="Tous", key="filter_emballage")
        df_temp = df_temp[df_temp["emballage"].isin(sel_emballages)] if sel_emballages else df_temp

        positionnements_dispo = sorted([str(p) for p in df_temp["positionnement"].unique() if pd.notna(p)])
        sel_positionnements = st.multiselect("Positionnement", options=positionnements_dispo, placeholder="Tous", key="filter_positionnement")
        df_temp = df_temp[df_temp["positionnement"].isin(sel_positionnements)] if sel_positionnements else df_temp

        occasions_dispo = sorted([str(o) for o in df_temp["occasion"].unique() if pd.notna(o) and str(o) != "Non renseigné"])
        sel_occasions = st.multiselect("Occasion", options=occasions_dispo, placeholder="Toutes", key="filter_occasion")
        df_temp = df_temp[df_temp["occasion"].isin(sel_occasions)] if sel_occasions else df_temp

        articles_dispo = sorted([str(a) for a in df_temp["article"].unique() if pd.notna(a)])
        sel_articles = st.multiselect("Article", options=articles_dispo, placeholder="Tous", key="filter_article")
        df_temp = df_temp[df_temp["article"].isin(sel_articles)] if sel_articles else df_temp

        st.markdown("#### 2. Paramètres de la cible")
        annee_cible = st.number_input("Année Cible", min_value=2020, max_value=2035, value=2026, key="param_annee_cible")
        
        unite_affichage = st.radio("Unité d'affichage", options=["HL", "Cols"], index=0, horizontal=True, key="param_unite")
        
        st.markdown("##### 🎯 Définition de l'Objectif")
        taux_ambition = st.number_input("Taux d'ambition vs N-1 (%)", value=5.0, step=1.0, help="Objectif calculé = Volume Réalisé N-1 * (1 + Taux)", key="param_taux")
        
        use_objectif_manuel = st.checkbox("Forcer un objectif manuel", key="param_use_objectif")
        if use_objectif_manuel:
            objectif_manuel = st.number_input(f"Objectif Annuel ({unite_affichage})", min_value=0.0, step=1000.0, value=4400743.0, key="param_objectif_manuel")
        
        methode_croissance = st.selectbox(
            "Méthode de prévision", 
            options=["Tendance Linéaire", "CAGR Classique", "Moyenne 3 ans"],
            index=0,
            key="param_methode"
        )
        
        with st.expander("⚙️ Paramètres avancés (IS, CAGR, Cutoff)"):
            p1, p2 = st.columns(2)
            with p1: annee_min_is = st.number_input("Année Min IS", min_value=2010, max_value=2030, value=2024, key="param_min_is")
            with p2: annee_max_is = st.number_input("Année Max IS", min_value=annee_min_is, max_value=2030, value=max(2025, annee_min_is), key="param_max_is")
            
            p3, p4 = st.columns(2)
            with p3: annee_min_cagr = st.number_input("Année Min CAGR", min_value=2010, max_value=2030, value=2017, key="param_min_cagr")
            with p4: annee_max_cagr = st.number_input("Année Max CAGR", min_value=annee_min_cagr, max_value=2030, value=2025, key="param_max_cagr")
            
            p5, p6 = st.columns(2)
            with p5: annee_cloture = st.number_input("Année Clôture", min_value=2020, max_value=2030, value=2026, key="param_annee_cloture")
            with p6: mois_cutoff = st.selectbox("Mois Cutoff", options=list(range(1, 13)), index=8, format_func=lambda m: f"{MOIS_NOMS[m-1]}", key="param_mois_cutoff")
            
            mois_cibles_selection = st.multiselect("Mois cible (Filtre tableau)", options=MOIS_NOMS, default=[], key="param_mois_cible", help="Filtre uniquement le tableau des prévisions, pas le KPI global.")

        st.markdown("---")
        st.markdown("#### 🛠️ Options d'affichage")
        show_raw_data = st.checkbox("Afficher l'onglet Données Brutes", value=False, help="Cochez cette case pour faire apparaître l'onglet des données brutes dans la navigation.", key="param_show_raw")

st.markdown("""
<div class="hero-header">
    <div>
        <h1>PREVISIONS STAR MADAGASCAR</h1>
        <p>Moteur de prévision hybride (Run-Rate, Heuristique & Indices)</p>
    </div>
    <div class="badge-demo">⭐ Données Officielles STAR</div>
</div>
""", unsafe_allow_html=True)

if fichier_ventes is None:
    st.info(
        "👋 **Bienvenue !** Pour démarrer :\n\n"
        "1. Importez votre fichier de **Ventes** (`DATA_BRUT.xlsx`) dans la barre latérale.\n"
        "2. (Optionnel) Importez un **Référentiel** pour restreindre le périmètre.\n"
        "3. (Optionnel) Importez un **Budget Query** pour écraser les prévisions (uniquement pour les 33 CAN).\n"
        "4. (Recommandé) Importez votre fichier de **Ruptures** pour fiabiliser les calculs.\n"
        "5. Ajustez les filtres et paramètres, puis explorez les onglets."
    )
    st.stop()

df_perimetre = df_enrichi.copy()
if sel_regions: df_perimetre = df_perimetre[df_perimetre["region"].isin(sel_regions)]
if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]
if sel_positionnements: df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_positionnements)]
if sel_contenances: df_perimetre = df_perimetre[df_perimetre["contenance_cl"].isin(sel_contenances)]
if sel_emballages: df_perimetre = df_perimetre[df_perimetre["emballage"].isin(sel_emballages)]
if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
if sel_marques: df_perimetre = df_perimetre[df_perimetre["marque"].isin(sel_marques)]
if sel_occasions: df_perimetre = df_perimetre[df_perimetre["occasion"].isin(sel_occasions)]

table_indices, df_sarr, _, df_previsions, df_realise, budget_status = calculer_etape_5(
    df_perimetre, annee_min_is, annee_max_is, annee_min_cagr, annee_max_cagr, annee_cloture, mois_cutoff, annee_cible, methode_croissance, fichier_budget.getvalue() if fichier_budget is not None else None, budget_all_agencies, cache_bust="v128"
)

if budget_status == "ok":
    st.sidebar.success("✅ Budget Query (33 CAN) appliqué à l'année cible.")
elif budget_status == "warning":
    st.sidebar.warning("⚠️ Aucune donnée valide (33 CAN) trouvée dans le fichier Budget.")
elif budget_status == "error":
    st.sidebar.error("⚠️ Erreur de lecture du Budget Query, ignoré.")

if table_indices is None:
    st.warning("⚠️ Impossible de calculer les prévisions. Vérifiez vos filtres (ex: pas de vente avant le cutoff).")
    st.stop()

col_prev_aff = "Volume_Cols" if unite_affichage == "Cols" else "Volume_HL"
col_prev_pure = "Prevision_Cols" if unite_affichage == "Cols" else "Prevision_HL"

df_cible_annuel = df_previsions[df_previsions['annee'] == annee_cible]
atterrissage_cible = df_cible_annuel[col_prev_aff].sum()

if not mois_cibles_selection:
    df_previsions_filtre = df_previsions
    label_mois_str = "Tous les mois"
else:
    mois_cibles_nums = [MOIS_NOMS.index(m) + 1 for m in mois_cibles_selection]
    df_previsions_filtre = df_previsions[df_previsions['mois'].isin(mois_cibles_nums)].copy()
    label_mois_str = ", ".join(mois_cibles_selection)

df_n1 = df_perimetre[df_perimetre['annee'] == (annee_cible - 1)].copy()
if not df_n1.empty:
    contenance_safe_n1 = df_n1['contenance_cl'].replace(0, 100).fillna(100.0)
    hist_n1_val = (df_n1['hl'] * (10000.0 / contenance_safe_n1)).sum() if unite_affichage == "Cols" else df_n1['hl'].sum()
else:
    hist_n1_val = 0.0
    
if hist_n1_val > 0:
    objectif_calcule = hist_n1_val * (1 + taux_ambition / 100.0)
else:
    objectif_calcule = atterrissage_cible * (1 + taux_ambition / 100.0)

objectif_final = objectif_manuel if use_objectif_manuel else objectif_calcule
gap = objectif_final - atterrissage_cible

df_eval = df_previsions_filtre[df_previsions_filtre['Statut'] == 'Réalisé'].copy()
df_eval_agg = df_eval.groupby(['annee', 'mois'], observed=True)[[col_prev_aff, col_prev_pure]].sum().reset_index()

if not df_eval_agg.empty and df_eval_agg[col_prev_aff].sum() > 0:
    y_true = df_eval_agg[col_prev_aff].values
    y_pred = df_eval_agg[col_prev_pure].values
    mae = np.mean(np.abs(y_true - y_pred))
    wmape = (np.sum(np.abs(y_true - y_pred)) / np.sum(y_true)) * 100
    denom_smape = np.abs(y_true) + np.abs(y_pred)
    valid_smape = denom_smape > 0
    if valid_smape.any():
        smape = np.mean(2 * np.abs(y_pred[valid_smape] - y_true[valid_smape]) / denom_smape[valid_smape]) * 100
    else:
        smape = 0.0
else:
    mae, wmape, smape = 0.0, 0.0, 0.0

k1, k2, k3 = st.columns(3, gap="large")
with k1:
    st.markdown(f"""
    <div class="white-card">
        <div class="kpi-label">Atterrissage {annee_cible}</div>
        <div class="kpi-value">{atterrissage_cible:,.0f}</div>
        <div class="kpi-footer">{unite_affichage} (Total Annuel Réalisé + Prévisions)</div>
    </div>""", unsafe_allow_html=True)

with k2:
    source_obj = "Manuel" if use_objectif_manuel else f"N-1 {taux_ambition:+.1f}%"
    st.markdown(f"""
    <div class="white-card">
        <div class="kpi-label">Objectif Annuel ({source_obj})</div>
        <div class="kpi-value kpi-value-dark">{objectif_final:,.0f}</div>
        <div class="kpi-footer">{unite_affichage} (Cible)</div>
    </div>""", unsafe_allow_html=True)

with k3:
    gap_color = "kpi-value-green" if gap <= 0 else "kpi-value-red"
    gap_label = "Objectif Atteint" if gap <= 0 else "Écart Restant"
    st.markdown(f"""
    <div class="white-card">
        <div class="kpi-label">GAP (Objectif - Atterrissage)</div>
        <div class="kpi-value {gap_color}">{gap:+,.0f}</div>
        <div class="kpi-footer">{gap_label} en {unite_affichage}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(f"""
<div class="white-card">
    <div class="section-title">Superposition Réalisé vs Prévision ({annee_cible})</div>
    <div class="section-subtitle">Comparaison mensuelle sur l'année complète</div>
""", unsafe_allow_html=True)

df_real_cible = df_perimetre[df_perimetre['annee'] == annee_cible].copy()
if annee_cible == annee_cloture: df_real_cible = df_real_cible[df_real_cible['mois'] <= mois_cutoff]

df_real_cible['Date_Str'] = df_real_cible['annee'].astype(str) + '-' + df_real_cible['mois'].astype(str).str.zfill(2) + '-01'
df_real_cible['Date_Plot'] = pd.to_datetime(df_real_cible['Date_Str'])
contenance_safe_real = df_real_cible['contenance_cl'].replace(0, 100).fillna(100.0)
df_real_cible['Volume_Aff'] = df_real_cible['hl'] * (10000.0 / contenance_safe_real) if unite_affichage == "Cols" else df_real_cible['hl']
df_real_plot = df_real_cible.groupby('Date_Plot', observed=True)['Volume_Aff'].sum().reset_index().rename(columns={'Volume_Aff': 'Volume'})

df_prev_cible = df_cible_annuel.copy()
df_prev_cible['Date_Str'] = df_prev_cible['annee'].astype(str) + '-' + df_prev_cible['mois'].astype(str).str.zfill(2) + '-01'
df_prev_cible['Date_Plot'] = pd.to_datetime(df_prev_cible['Date_Str'])
df_prev_plot = df_prev_cible.groupby('Date_Plot', observed=True)[col_prev_pure].sum().reset_index().rename(columns={col_prev_pure: 'Volume'})

fig1 = go.Figure()
if not df_prev_plot.empty:
    fig1.add_trace(go.Scatter(
        x=df_prev_plot['Date_Plot'], y=df_prev_plot['Volume'], 
        mode='lines+markers', name='Prévision (Pure)', 
        line=dict(color='#E30613', width=3, dash='dot', shape='spline', smoothing=1.3), 
        marker=dict(size=7, color='#E30613', line=dict(color='white', width=2)),
        hovertemplate="<b>Prévision</b>: %{y:,.0f}<extra></extra>"
    ))
if not df_real_plot.empty:
    fig1.add_trace(go.Scatter(
        x=df_real_plot['Date_Plot'], y=df_real_plot['Volume'], 
        mode='lines+markers', name='Réalisé', 
        line=dict(color='#B91C1C', width=4, shape='spline', smoothing=1.3), 
        marker=dict(size=9, color='#B91C1C', line=dict(color='white', width=2)),
        hovertemplate="<b>Réalisé</b>: %{y:,.0f}<extra></extra>"
    ))

fig1.update_layout(
    plot_bgcolor='#FFFFFF', 
    paper_bgcolor='#FFFFFF', 
    margin=dict(l=10, r=10, t=30, b=10), 
    legend=dict(
        orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, 
        font=dict(size=13, family="Inter", weight="bold")
    ),
    xaxis=dict(
        showgrid=True, gridcolor='#F3F4F6', linecolor='#E5E7EB', tickformat="%b-%y", dtick="M1", 
        tickfont=dict(family="Inter", size=12, weight="bold"),
        tickangle=-45
    ), 
    yaxis=dict(
        showgrid=True, gridcolor='#E5E7EB', zeroline=False, 
        tickfont=dict(family="Inter", size=12, weight="bold"),
        tickformat=",.0f"
    ), 
    height=500, 
    hovermode="x unified"
)
st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""<p style="color: #9CA3AF; font-size: 0.75rem; margin-top: 10px;">Les prévisions sont calculées sur les ventes réelles pour correspondre à la logique Excel.</p>""", unsafe_allow_html=True)

st.markdown("<hr style='border: 1px solid #E5E7EB; margin: 30px 0;'>", unsafe_allow_html=True)

tab_names = ["Réalisé Cumulé", "Indices & SARR", "Prévisions Détaillées", "Analyse Pareto (ABC)", "Fiabilité Prévisions", "Analyse Rupture"]
if show_raw_data: tab_names.insert(0, "Données Brutes")

active_tab = st.radio

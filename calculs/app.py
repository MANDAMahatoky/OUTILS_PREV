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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F4F6F8 !important; }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB; box-shadow: 2px 0 10px rgba(0,0,0,0.03);
    }
    [data-testid="stSidebar"] h2 { color: #E30613 !important; font-size: 1.4rem; font-weight: 900; margin-bottom: 20px; }
    [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stNumberInput label, [data-testid="stSidebar"] .stMultiSelect label { color: #4B5563 !important; font-size: 0.85rem !important; font-weight: 700 !important; }
    
    /* HEADER */
    .hero-header {
        background: linear-gradient(135deg, #B91C1C 0%, #E30613 100%); color: white; padding: 25px 20px;
        border-radius: 0 0 20px 20px; margin-top: -60px; margin-bottom: 30px; position: relative;
        overflow: hidden; box-shadow: 0 10px 20px -5px rgba(227, 6, 19, 0.4); text-align: center;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .hero-header h1 { color: white !important; font-size: 2.2rem; font-weight: 900; margin-bottom: 8px; letter-spacing: -0.02em; }
    .hero-header p { color: #FECACA; font-size: 1rem; margin-bottom: 15px; font-weight: 500; }
    .badge-demo { background-color: white; color: #E30613; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    
    /* CARDS & KPI */
    .white-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03); border-top: 4px solid #E30613; margin-bottom: 20px; height: 100%; }
    .kpi-label { color: #6B7280; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .kpi-value { color: #E30613; font-size: 2.6rem; font-weight: 900; line-height: 1.1; }
    .kpi-value-dark { color: #111827; }
    .kpi-value-green { color: #009640; }
    .kpi-value-red { color: #E30613; }
    .kpi-footer { color: #9CA3AF; font-size: 0.85rem; margin-top: 8px; font-weight: 500; }
    
    /* SECTIONS */
    .section-title { color: #111827; font-size: 1.2rem; font-weight: 800; margin-bottom: 5px; }
    .section-subtitle { color: #6B7280; font-size: 0.85rem; margin-bottom: 20px; font-weight: 500; }
    
    /* FORMS & EXPANDERS */
    div[data-baseweb="select"] > div, div[data-testid="stNumberInput"] input, div[data-testid="stMultiSelect"] { background-color: #F9FAFB !important; border-radius: 8px !important; border: 1px solid #D1D5DB !important; }
    div[data-testid="stExpander"] { background-color: white !important; border-radius: 12px !important; border: 1px solid #E5E7EB !important; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02) !important; margin-bottom: 20px !important; }
    div[data-testid="stExpander"] > details > summary { background-color: #F9FAFB !important; border-radius: 12px !important; font-weight: 700 !important; color: #111827 !important; padding: 15px 20px !important; border-bottom: 1px solid transparent !important; }
    div[data-testid="stExpander"] > details[open] > summary { border-bottom: 1px solid #E5E7EB !important; border-bottom-left-radius: 0 !important; border-bottom-right-radius: 0 !important; }
    
    /* TABLES */
    div[data-testid="stDataFrame"] { border: 1px solid #E5E7EB !important; border-radius: 8px !important; padding: 10px !important; background-color: white !important; }
    
    /* NAVIGATION TABS - DESIGN PRO */
    div[role="radiogroup"] { 
        gap: 28px !important; 
        border-bottom: 2px solid #E5E7EB !important; 
        padding-bottom: 0px !important; 
        margin-bottom: 25px !important; 
        display: flex !important; 
        flex-wrap: wrap !important; 
        align-items: flex-end !important;
    }
    
    div[role="radiogroup"] label { 
        background: transparent !important; 
        border: none !important; 
        border-bottom: 3px solid transparent !important; 
        border-radius: 0 !important; 
        padding: 8px 4px 14px 4px !important; 
        margin: 0 !important; 
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    
    /* Taille de police réduite pour un look pro */
    div[role="radiogroup"] label div p { 
        font-size: 1.05rem !important; 
        font-weight: 700 !important; 
        color: #6B7280 !important; 
        transition: color 0.2s ease !important; 
        margin: 0 !important;
        letter-spacing: 0.01em !important;
    }
    
    /* Effet au survol */
    div[role="radiogroup"] label:hover div p { 
        color: #111827 !important; 
    }
    
    /* Onglet actif : texte rouge et soulignement fin */
    div[role="radiogroup"] label:has(input:checked) { 
        border-bottom: 3px solid #E30613 !important; 
    }
    
    div[role="radiogroup"] label:has(input:checked) div p { 
        color: #E30613 !important; 
        font-weight: 800 !important; 
    }
    
    /* Masque le cercle du bouton radio */
    div[role="radiogroup"] label > div:first-child { 
        display: none !important; 
    }
    
    /* Enlève le cadre bleu moche au clic sur un onglet */
    div[role="radiogroup"] label:focus-within {
        outline: none !important;
        box-shadow: none !important;
    }

    /* Rapproche le titre de section de la barre d'onglets */
    div[role="radiogroup"] + div {
        margin-top: -10px !important;
    }
    
    .block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def make_bold(df):
    """Force les colonnes numériques à être en gras pour améliorer la visibilité."""
    if df is None or df.empty: return df
    for col in df.columns:
        if df[col].dtype.name == 'category':
            df[col] = df[col].astype(str)
    num_cols = df.select_dtypes(include=[np.number]).columns
    if len(num_cols) > 0:
        return df.style.set_properties(subset=num_cols, **{'font-weight': 'bold', 'color': '#111827'})
    return df

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
    """Extrait le type d'emballage depuis le nom de l'article."""
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

@st.cache_data(show_spinner="Chargement et enrichissement des données...")
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes) -> pd.DataFrame:
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
    
    for col in ['region', 'segment', 'positionnement', 'occasion', 'marque', 'emballage']:
        if col in df_enrichi.columns: df_enrichi[col] = df_enrichi[col].astype('category')

    return df_enrichi[["annee", "mois", "segment", "region", "produit", "agence", "hl", "volume_brut", "article", "positionnement", "occasion", "marque", "contenance_cl", "emballage"]]

# ==============================================================================
# LOGIQUE DE CALCUL
# ==============================================================================
def _calculer_indices_fallback(df_realise, annee_min_is, annee_max_is):
    df_h = df_realise[(df_realise['annee'] >= annee_min_is) & (df_realise['annee'] <= annee_max_is)].copy()
    
    if df_h.empty:
        max_annee = df_realise['annee'].max()
        df_h = df_realise[df_realise['annee'] == max_annee].copy()
        
    if df_h.empty: return pd.DataFrame(columns=['agence', 'article', 'mois', 'Indice'])

    def _idx(group_cols):
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
def calculer_etape_5(df_perimetre, annee_min_is, annee_max_is, annee_min_cagr, annee_max_cagr, annee_cloture, mois_cutoff, annee_cible, methode_croissance, budget_bytes, budget_all_agencies, cache_bust="v122"):
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

    df_realise_agg = df_realise.groupby(['annee', 'mois', 'agence', 'article'], observed=True)['hl'].sum().reset_index()
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
                y = group['hl'].values.astype(float)
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
            df_pivot = df_hist_cagr.pivot_table(index=['agence', 'article'], columns='annee', values='hl', aggfunc='sum').fillna(0)
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
    
    # =========================================================================
    # INTEGRATION DU BUDGET QUERY (UNIQUEMENT 33 CAN)
    # =========================================================================
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
                    
                    # FILTRE STRICT : 33 CAN UNIQUEMENT
                    mask_33can = df_budget[col_art].astype(str).str.contains('33', na=False) & df_budget[col_art].astype(str).str.contains('CAN', case=False, na=False)
                    df_budget = df_budget[mask_33can].copy()
                    
                    if df_budget.empty:
                        budget_status = "warning"
                    else:
                        df_budget['key_article_budget'] = df_budget[col_art].apply(clean_text_for_budget_key)
                        df_budget['mois'] = pd.to_numeric(df_budget[col_mois], errors='coerce')
                        df_budget['valeur_budget'] = pd.to_numeric(df_budget[col_val], errors='coerce').fillna(0.0)
                        df_budget = df_budget.dropna(subset=['mois'])
                        
                        df_temp_content = (
                            df_cross[['key_article_budget', 'contenance_cl']]
                            .drop_duplicates(subset=['key_article_budget'])
                        )
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
        
        if fichier_budget is not None:
            budget_all_agencies = st.checkbox("Appliquer à toutes les agences", value=True, help="Si coché, les valeurs du 33 CAN s'appliqueront à toutes les agences, quel que soit l'attribut 'Agence' dans le fichier.")
        else:
            budget_all_agencies = True

    if fichier_ventes is not None:
        df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue() if fichier_ref is not None else None)

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
    <p style="text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; color: rgba(255,255,255,0.8); font-weight: 700; margin-bottom: 5px;">Perspectives • S&OP</p>
    <h1>PREVISIONS STAR MADAGASCAR</h1>
    <p>Moteur de prévision hybride (Run-Rate, Heuristique & Indices) - Explorez les tendances à venir.</p>
    <div class="badge-demo">⭐ Données Officielles STAR</div>
</div>
""", unsafe_allow_html=True)

if fichier_ventes is None:
    st.info(
        "👋 **Bienvenue !** Pour démarrer :\n\n"
        "1. Importez votre fichier de **Ventes** (`DATA_BRUT.xlsx`) dans la barre latérale.\n"
        "2. (Optionnel) Importez un **Référentiel** pour restreindre le périmètre.\n"
        "3. (Optionnel) Importez un **Budget Query** pour écraser les prévisions (uniquement pour les 33 CAN).\n"
        "4. Ajustez les filtres et paramètres, puis explorez les onglets."
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
    df_perimetre, annee_min_is, annee_max_is, annee_min_cagr, annee_max_cagr, annee_cloture, mois_cutoff, annee_cible, methode_croissance, fichier_budget.getvalue() if fichier_budget is not None else None, budget_all_agencies, cache_bust="v122"
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

k1, k2, k3 = st.columns(3)
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

st.markdown("""<p style="color: #9CA3AF; font-size: 0.75rem; margin-top: 10px;">Projection basée sur la logique hybride : Run-Rate (Momentum) pour l'année en cours, CAGR ou Tendance pour les années futures.</p>""", unsafe_allow_html=True)

st.markdown("<hr style='border: 1px solid #E5E7EB; margin: 30px 0;'>", unsafe_allow_html=True)

tab_names = ["Périmètre", "Réalisé Cumulé", "Indices & SARR", "Prévisions Détaillées", "Analyse Pareto (ABC)", "Fiabilité Prévisions", "Analyse Rupture"]
if show_raw_data: tab_names.insert(0, "Données Brutes")

active_tab = st.radio("Navigation", tab_names, horizontal=True, label_visibility="collapsed", key="main_navigation_radio")
N_MAX_DISPLAY = 5000
tab_placeholder = st.empty()

with tab_placeholder.container():
    if active_tab == "Données Brutes":
        st.markdown("### Étape 1 : Données Brutes Enrichies")
        with st.expander("📊 Afficher le tableau des données brutes", expanded=True):
            if len(df_enrichi) > N_MAX_DISPLAY:
                st.caption(f"⚠️ Affichage limité à {N_MAX_DISPLAY:,} lignes sur {len(df_enrichi):,}.")
                st.dataframe(make_bold(df_enrichi.head(N_MAX_DISPLAY)), use_container_width=True, hide_index=True)
            else: st.dataframe(make_bold(df_enrichi), use_container_width=True, hide_index=True)

    elif active_tab == "Périmètre":
        st.markdown("### Étape 2 : Périmètre Filtré")
        with st.expander("📊 Afficher le tableau du périmètre", expanded=True):
            if len(df_perimetre) > N_MAX_DISPLAY:
                st.caption(f"⚠️ Affichage limité à {N_MAX_DISPLAY:,} lignes sur {len(df_perimetre):,}.")
                st.dataframe(make_bold(df_perimetre.head(N_MAX_DISPLAY)), use_container_width=True, hide_index=True)
            else: st.dataframe(make_bold(df_perimetre), use_container_width=True, hide_index=True)

    elif active_tab == "Réalisé Cumulé":
        st.markdown("### Étape 3 : Réalisé Cumulé (Jusqu'au Cutoff)")
        with st.expander("📊 Afficher le tableau du réalisé", expanded=True):
            if df_realise is not None and not df_realise.empty:
                df_real_agg = (df_realise.groupby(['annee', 'mois', 'region', 'agence', 'article'], observed=True)[['hl']].sum().reset_index())
                st.dataframe(make_bold(df_real_agg.head(N_MAX_DISPLAY)), use_container_width=True, hide_index=True)
            else: st.info("Aucune donnée réalisée pour le moment.")

    elif active_tab == "Indices & SARR":
        st.markdown("### Étape 4 : Indices de Saisonnalité & SARR")
        c_idx, c_sarr = st.columns(2)
        with c_idx:
            st.markdown("**Indices de Saisonnalité**")
            with st.expander("📊 Afficher les indices", expanded=True):
                if not table_indices.empty:
                    pivot_indices = _pivot_indices_cached(table_indices)
                    st.dataframe(make_bold(pivot_indices), use_container_width=True)
                else: st.info("Pas d'historique complet.")
        with c_sarr:
            st.markdown("**Table SARR (5 derniers mois) avec Momentum**")
            with st.expander("📊 Afficher le SARR & Momentum", expanded=True):
                df_sarr_calc = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
                
                df_sarr_calc["SARR_Aff"] = (df_sarr_calc["SARR_HL"] * (10000 / df_sarr_calc["contenance_cl"].replace(0, 100)) if unite_affichage == "Cols" else df_sarr_calc["SARR_HL"])
                df_sarr_calc["SARR_M1_Aff"] = (df_sarr_calc["SARR_M1"] * (10000 / df_sarr_calc["contenance_cl"].replace(0, 100)) if unite_affichage == "Cols" else df_sarr_calc["SARR_M1"])
                
                df_sarr_calc["Mois M"] = df_sarr_calc.apply(lambda r: f"{MOIS_NOMS[int(r['mois'])-1]}-{int(r['annee'])}", axis=1)
                df_sarr_calc["Mois M-1"] = df_sarr_calc.groupby(['agence', 'article'])["Mois M"].shift(1)
                
                df_sarr_calc["Momentum_M (%)"] = ((df_sarr_calc["SARR_Aff"] - df_sarr_calc["SARR_M1_Aff"]) / df_sarr_calc["SARR_M1_Aff"] * 100).replace([np.inf, -np.inf], np.nan)
                
                df_sarr_derniers = df_sarr_calc.groupby(['agence', 'article'], observed=True).tail(5)
                
                st.dataframe(
                    make_bold(df_sarr_derniers[["agence", "article", "Mois M-1", "SARR_M1_Aff", "Mois M", "SARR_Aff", "Momentum", "Momentum_M (%)"]]
                    .rename(columns={
                        "SARR_Aff": "Volume M", 
                        "SARR_M1_Aff": "Volume M-1", 
                        "Momentum": "Momentum (Vol Absolu)", 
                        "Momentum_M (%)": "Momentum M vs M-1 (%)"
                    })
                    .sort_values(["agence", "article", "Mois M"])),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Volume M": st.column_config.NumberColumn(format="%.0f"), 
                        "Volume M-1": st.column_config.NumberColumn(format="%.0f"), 
                        "Momentum (Vol Absolu)": st.column_config.NumberColumn(format="%.1f"),
                        "Momentum M vs M-1 (%)": st.column_config.NumberColumn(format="%.2f %%")
                    }
                )

    elif active_tab == "Prévisions Détaillées":
        st.markdown("### Résultat Final")
        st.markdown(f"Projections mensuelles pour : **<span style='color: #E30613;'>{label_mois_str}</span>**", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        col_search, col_export = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("Rechercher", "", placeholder="Rechercher un article ou une agence...", label_visibility="collapsed", key="search_previsions")
            
        with col_export:
            df_seg = df_perimetre[['article', 'segment']].drop_duplicates(subset=['article'])
            df_prev_seg = df_previsions_filtre.merge(df_seg, on='article', how='left')
            pivot_mensuel = df_prev_seg.pivot_table(index=['article', 'segment'], columns='mois', values=col_prev_aff, aggfunc='sum').fillna(0)
            pivot_mensuel.columns = [MOIS_NOMS[int(c) - 1] for c in pivot_mensuel.columns]
            
            if not mois_cibles_selection or len(mois_cibles_selection) == 12:
                nom_total = "Total Année"
            else:
                nom_total = "Total Période"
                
            pivot_mensuel[nom_total] = pivot_mensuel.sum(axis=1)
            pivot_mensuel = pivot_mensuel[pivot_mensuel[nom_total] > 0]
            
            pivot_mensuel_export = pivot_mensuel.reset_index().rename(columns={'article': 'Articles', 'segment': 'Segments'})
            for col in pivot_mensuel_export.columns:
                if pivot_mensuel_export[col].dtype.name in ['object', 'category', 'string']:
                    pivot_mensuel_export[col] = pivot_mensuel_export[col].apply(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode('utf-8') if pd.notna(x) else "")
            
            csv = pivot_mensuel_export.to_csv(sep=';', index=False).encode('utf-8-sig')
            st.download_button(label="Exporter en CSV", data=csv, file_name=f"previsions_star_{annee_cible}.csv", mime="text/csv", use_container_width=True, key="btn_export_csv")

        with st.expander("📊 Afficher le tableau des prévisions détaillées (Format Excel)", expanded=True):
            pivot_mensuel_reset = pivot_mensuel.reset_index().rename(columns={'article': 'Articles', 'segment': 'Segments'})
            if search_query:
                mask = pivot_mensuel_reset.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                pivot_mensuel_display = pivot_mensuel_reset[mask]
            else:
                pivot_mensuel_display = pivot_mensuel_reset

            col_config = {"Articles": st.column_config.TextColumn("Articles", width="medium"), "Segments": st.column_config.TextColumn("Segments", width="small")}
            for mois in MOIS_NOMS:
                if mois in pivot_mensuel_display.columns: col_config[mois] = st.column_config.NumberColumn(mois, format="%.2f")
            
            if nom_total in pivot_mensuel_display.columns:
                col_config[nom_total] = st.column_config.NumberColumn(nom_total, format="%.2f")

            st.dataframe(make_bold(pivot_mensuel_display), use_container_width=True, hide_index=True, column_config=col_config, height=600)

        with st.expander("🔍 Voir le détail des calculs (Hybride)"):
            st.markdown("**Note :** L'année de clôture utilise la projection du Run-Rate (Base Mensuelle) pour éviter l'explosion du Momentum absolu. Les années suivantes ajoutent le CAGR calculé.")
            cols_to_show = ["annee", "mois", "Statut", "agence", "article", "Indice", "Base_EXCEL", "Momentum", "Base_Mensuelle", "CAGR (%)", col_prev_aff]
            df_detail = (df_previsions_filtre[cols_to_show].sort_values(["annee", "mois", "agence", "article"]))
            st.dataframe(make_bold(df_detail.head(N_MAX_DISPLAY)), use_container_width=True, hide_index=True, height=400, column_config={"Base_EXCEL": st.column_config.NumberColumn(format="%.1f"), "Momentum": st.column_config.NumberColumn(format="%.1f"), "Base_Mensuelle": st.column_config.NumberColumn(format="%.1f"), "CAGR (%)": st.column_config.NumberColumn(format="%.2f %%")})

    elif active_tab == "Analyse Pareto (ABC)":
        st.markdown("### Analyse Pareto & Classification ABC")
        st.markdown("La classification ABC est une méthode de gestion des stocks qui consiste à diviser les articles en trois classes en fonction de leur contribution au volume total :")
        st.markdown("- **Classe A (0-80%)** : Les articles vitaux (généralement 20% des articles qui font 80% des ventes).\n- **Classe B (80-95%)** : Les articles intermédiaires.\n- **Classe C (95-100%)** : Les articles à faible rotation (la longue traîne).")
        st.markdown("<br>", unsafe_allow_html=True)
        
        df_pareto = df_previsions_filtre.groupby('article', observed=True)[col_prev_aff].sum().sort_values(ascending=False).reset_index()
        df_pareto = df_pareto[df_pareto[col_prev_aff] > 0]
        
        if not df_pareto.empty:
            total_vol = df_pareto[col_prev_aff].sum()
            df_pareto['Cumul_Pct'] = (df_pareto[col_prev_aff].cumsum() / total_vol) * 100
            df_pareto['Classe'] = np.select([df_pareto['Cumul_Pct'] <= 80, df_pareto['Cumul_Pct'] <= 95], ['A', 'B'], default='C')
            
            df_pareto_graph = df_pareto.head(15).copy()
            df_pareto_graph['Index'] = range(len(df_pareto_graph))
            df_pareto_graph['Article_Court'] = df_pareto_graph['article'].apply(lambda x: x if len(str(x)) <= 22 else str(x)[:19] + '...')
            
            fig2 = go.Figure()
            couleurs = {'A': '#E30613', 'B': '#F59E0B', 'C': '#9CA3AF'}
            for classe in ['A', 'B', 'C']:
                df_class = df_pareto_graph[df_pareto_graph['Classe'] == classe]
                if not df_class.empty:
                    fig2.add_trace(go.Bar(x=df_class['Index'], y=df_class[col_prev_aff], name=f'Classe {classe}', marker_color=couleurs[classe], customdata=df_class['article'], hovertemplate="<b>%{customdata}</b><br>Volume: %{y:,.0f}<extra></extra>"))
            fig2.add_trace(go.Scatter(x=df_pareto_graph['Index'], y=df_pareto_graph['Cumul_Pct'], name='% Cumulé', mode='lines+markers', line=dict(color='#111827', width=2), marker=dict(size=6, color='#111827'), yaxis='y2', customdata=df_pareto_graph['article'], hovertemplate="<b>%{customdata}</b><br>% Cumulé: %{y:.1f}%<extra></extra>"))
            
            for seuil, color in [(80, '#E30613'), (95, '#F59E0B')]:
                fig2.add_shape(type="line", x0=-0.5, x1=len(df_pareto_graph)-0.5, y0=seuil, y1=seuil, line=dict(color=color, width=1.5, dash="dot"), xref='x', yref='y2')

            fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=0, r=0, t=20, b=60), yaxis=dict(title=f"Volume ({unite_affichage})", showgrid=True, gridcolor='#F3F4F6', tickfont=dict(family="Inter", size=12, weight="bold")), yaxis2=dict(title="% Cumulé", overlaying='y', side='right', range=[0, 110], tickvals=[0, 20, 40, 60, 80, 100], showgrid=False, ticksuffix="%", tickfont=dict(family="Inter", size=12, weight="bold")), xaxis=dict(tickmode='array', tickvals=df_pareto_graph['Index'], ticktext=df_pareto_graph['Article_Court'], tickangle=-45, showgrid=False, tickfont=dict(size=11, family="Inter", weight="bold")), legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5), height=450, bargap=0.3, hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
            
            with st.expander("📋 Voir le détail par article", expanded=True):
                df_table = df_pareto[['article', 'Classe', col_prev_aff, 'Cumul_Pct']].copy()
                df_table.columns = ['Article', 'Classe', f'Volume ({unite_affichage})', '% Cumulé']
                st.dataframe(make_bold(df_table), use_container_width=True, hide_index=True, column_config={f'Volume ({unite_affichage})': st.column_config.NumberColumn(format="localized"), '% Cumulé': st.column_config.NumberColumn(format="%.1f %%"), 'Classe': st.column_config.TextColumn(width="small")}, height=400)
        else:
            st.info("Pas assez de données pour l'analyse.")

    elif active_tab == "Fiabilité Prévisions":
        st.markdown("### Qualité et Fiabilité du Modèle")
        st.markdown("Cette section évalue la précision de l'algorithme sur les mois déjà réalisés (période de cutoff). Elle permet de savoir si l'on peut faire confiance aux prévisions futures.")
        st.markdown("<br>", unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""<div class="white-card" style="border-top: 4px solid #4B5563;"><div class="kpi-label">MAE (Erreur Absolue Moyenne)</div><div class="kpi-value kpi-value-dark" style="font-size: 2rem;">{mae:,.0f}</div><div class="kpi-footer">Marge d'erreur moyenne en {unite_affichage}</div></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="white-card" style="border-top: 4px solid #4B5563;"><div class="kpi-label">WMAPE (Erreur % Pondérée)</div><div class="kpi-value kpi-value-dark" style="font-size: 2rem;">{wmape:,.2f}%</div><div class="kpi-footer">Précision sur le volume total (Standard industrie)</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="white-card" style="border-top: 4px solid #4B5563;"><div class="kpi-label">SMAPE (Erreur % Symétrique)</div><div class="kpi-value kpi-value-dark" style="font-size: 2rem;">{smape:,.2f}%</div><div class="kpi-footer">Précision sur les articles à faibles volumes</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("📊 Afficher le détail mensuel (Prévision vs Réalisé)", expanded=True):
            st.markdown("Ce tableau compare ce que le modèle prévoyait pour chaque mois écoulé par rapport à ce qui a réellement été vendu.")
            
            if not df_eval_agg.empty:
                df_error_monthly = df_eval_agg.copy()
                df_error_monthly['Ecart'] = df_error_monthly[col_prev_aff] - df_error_monthly[col_prev_pure]
                df_error_monthly['Erreur_Absolue'] = df_error_monthly['Ecart'].abs()
                df_error_monthly['Erreur_Pct (%)'] = np.where(df_error_monthly[col_prev_aff] > 0, (df_error_monthly['Erreur_Absolue'] / df_error_monthly[col_prev_aff]) * 100, 0)
                df_error_monthly['Mois_Label'] = df_error_monthly['mois'].apply(lambda m: MOIS_NOMS[int(m)-1])
                df_error_monthly = df_error_monthly[['annee', 'Mois_Label', col_prev_aff, col_prev_pure, 'Ecart', 'Erreur_Pct (%)']]
                df_error_monthly.columns = ['Année', 'Mois', f'Réalisé ({unite_affichage})', f'Prévision ({unite_affichage})', 'Écart', 'Erreur (%)']
                st.dataframe(make_bold(df_error_monthly), use_container_width=True, hide_index=True, column_config={f'Réalisé ({unite_affichage})': st.column_config.NumberColumn(format="localized"), f'Prévision ({unite_affichage})': st.column_config.NumberColumn(format="localized"), 'Écart': st.column_config.NumberColumn(format="localized"), 'Erreur (%)': st.column_config.NumberColumn(format="%.2f %%")})
            else:
                st.info("Aucune donnée réalisée à évaluer pour le moment (le mois de cutoff n'est peut-être pas encore passé).")

    elif active_tab == "Analyse Rupture":
        st.markdown("### Analyse de Rupture de Tendance (Change Point Detection)")
        st.markdown("Cette section détecte automatiquement les périodes où la tendance de vente a brusquement changé (chute ou explosion), par rapport à la dynamique historique.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        df_tendance = df_realise.groupby(['annee', 'mois'])['hl'].sum().reset_index()
        df_tendance['Date'] = pd.to_datetime(df_tendance['annee'].astype(str) + '-' + df_tendance['mois'].astype(str) + '-01')
        df_tendance = df_tendance.sort_values('Date').reset_index(drop=True)
        
        if len(df_tendance) > 3:
            df_tendance['Moyenne_3M'] = df_tendance['hl'].rolling(window=3, min_periods=1).mean()
            df_tendance['Moyenne_12M'] = df_tendance['hl'].rolling(window=12, min_periods=1).mean()
            
            seuil = 0.20
            df_tendance['Ecart_Pct'] = (df_tendance['Moyenne_3M'] - df_tendance['Moyenne_12M']) / df_tendance['Moyenne_12M']
            df_tendance['Rupture'] = df_tendance['Ecart_Pct'].abs() > seuil
            
            fig_rupture = go.Figure()
            
            fig_rupture.add_trace(go.Scatter(
                x=df_tendance['Date'], y=df_tendance['hl'], 
                mode='lines', name='Ventes Mensuelles',
                line=dict(color='#9CA3AF', width=1.5)
            ))
            
            fig_rupture.add_trace(go.Scatter(
                x=df_tendance['Date'], y=df_tendance['Moyenne_3M'], 
                mode='lines', name='Tendance Court Terme (3M)',
                line=dict(color='#E30613', width=3)
            ))
            
            fig_rupture.add_trace(go.Scatter(
                x=df_tendance['Date'], y=df_tendance['Moyenne_12M'], 
                mode='lines', name='Tendance Long Terme (12M)',
                line=dict(color='#111827', width=2, dash='dash')
            ))
            
            df_ruptures = df_tendance[df_tendance['Rupture']]
            if not df_ruptures.empty:
                fig_rupture.add_trace(go.Scatter(
                    x=df_ruptures['Date'], y=df_ruptures['Moyenne_3M'],
                    mode='markers', name='Rupture Détectée',
                    marker=dict(color='#F59E0B', size=12, symbol='star', line=dict(color='black', width=1)),
                    hovertemplate="<b>Rupture détectée</b><br>Écart: %{customdata:.1%}<extra></extra>",
                    customdata=df_ruptures['Ecart_Pct']
                ))
            
            fig_rupture.update_layout(
                plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', 
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                xaxis=dict(showgrid=True, gridcolor='#F3F4F6', linecolor='#E5E7EB', tickformat="%b-%y", dtick="M3"),
                yaxis=dict(showgrid=True, gridcolor='#E5E7EB', zeroline=False),
                height=450, hovermode="x unified"
            )
            st.plotly_chart(fig_rupture, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("#### Articles impactés par une rupture")
            st.markdown("Voici les articles qui ont un écart significatif entre leur moyenne récente et leur moyenne historique, avec des propositions d'initiatives concrètes :")
            
            df_art_rupture = df_realise.groupby(['annee', 'mois', 'article'])['hl'].sum().reset_index()
            df_art_rupture['Date'] = pd.to_datetime(df_art_rupture['annee'].astype(str) + '-' + df_art_rupture['mois'].astype(str) + '-01')
            df_art_rupture = df_art_rupture.sort_values('Date')
            
            g_art = df_art_rupture.groupby('article')
            df_last_3m = g_art.tail(3).groupby('article')['hl'].mean().rename('Moyenne_3M_Actuelle')
            df_last_12m = g_art.tail(12).groupby('article')['hl'].mean().rename('Moyenne_12M_Historique')
            
            df_impact = pd.concat([df_last_3m, df_last_12m], axis=1).dropna()
            df_impact['Ecart (%)'] = ((df_impact['Moyenne_3M_Actuelle'] - df_impact['Moyenne_12M_Historique']) / df_impact['Moyenne_12M_Historique']) * 100
            
            df_impact = df_impact[df_impact['Ecart (%)'].abs() > 20].sort_values('Ecart (%)')
            
            if not df_impact.empty:
                conditions = [
                    df_impact['Ecart (%)'] < -30,
                    (df_impact['Ecart (%)'] >= -30) & (df_impact['Ecart (%)'] < 0),
                    (df_impact['Ecart (%)'] > 0) & (df_impact['Ecart (%)'] <= 30),
                    df_impact['Ecart (%)'] > 30
                ]
                choices = [
                    "🛑 Chute critique : Vérifier rupture de stock ou fin de vie produit. Forcer une prévision basse via le Budget Query.",
                    "⚠️ Déclin modéré : Surveiller la cannibalisation (nouveau format ?) et ajuster l'année Min CAGR.",
                    "📈 Croissance forte : Vérifier les promos ou nouveaux référencements. Augmenter la prévision.",
                    "🚀 Explosion : Risque de rupture de stock. Ajuster la production et forcer une prévision haute via le Budget Query."
                ]
                df_impact['Proposition_Initiatives'] = np.select(conditions, choices, default="✅ Stable")
                
                st.dataframe(
                    make_bold(df_impact.reset_index().rename(columns={'article': 'Article', 'Proposition_Initiatives': '💡 Proposition d\'Initiative'})),
                    use_container_width=True, hide_index=True,
                    column_config={
                        'Moyenne_3M_Actuelle': st.column_config.NumberColumn("Moyenne 3M Actuelle", format="%.0f"),
                        'Moyenne_12M_Historique': st.column_config.NumberColumn("Moyenne 12M Historique", format="%.0f"),
                        'Ecart (%)': st.column_config.NumberColumn("Écart (%)", format="%.1f %%"),
                        '💡 Proposition d\'Initiative': st.column_config.TextColumn(width="large")
                    }
                )
            else:
                st.info("Aucune rupture majeure détectée sur les articles avec suffisamment d'historique.")
        else:
            st.info("Pas assez de données historiques pour réaliser une analyse de rupture.")

from __future__ import annotations

import io
import hashlib
import os
import sys
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

try:
    from .filter_dimensions import assurer_dimensions_filtres, options_filtre_cascade
    from .monthly_import import (
        normaliser_lignes_data_brut,
        normaliser_mois,
        remplacer_periodes_importees,
    )
    from .seasonality_index import (
        annees_completes_saisonnalite,
        calculer_indices_saisonnalite,
        calculer_matrice_indices_saisonnalite,
    )
except ImportError:
    try:
        from filter_dimensions import assurer_dimensions_filtres, options_filtre_cascade
        from monthly_import import (
            normaliser_lignes_data_brut,
            normaliser_mois,
            remplacer_periodes_importees,
        )
        from seasonality_index import (
            annees_completes_saisonnalite,
            calculer_indices_saisonnalite,
            calculer_matrice_indices_saisonnalite,
        )
    except ImportError as erreur_import:
        import importlib.util

        dossier_app = Path(__file__).resolve().parent
        manquants = [
            f"{nom}.py"
            for nom in ("filter_dimensions", "monthly_import", "seasonality_index")
            if importlib.util.find_spec(nom) is None
        ]
        st.error("Démarrage impossible : un fichier Python est introuvable ou obsolète.")
        st.write(f"**Détail :** {erreur_import}")
        if manquants:
            st.write("**Fichiers manquants à côté de app.py :** " + ", ".join(manquants))
        st.write(f"**Dossier de app.py :** {dossier_app}")
        st.write(
            "**Fichiers .py présents dans ce dossier :** "
            + (", ".join(sorted(p.name for p in dossier_app.glob("*.py"))) or "aucun")
        )
        st.info(
            "Ajoutez (ou remplacez) ces fichiers dans le dépôt GitHub, dans le même dossier "
            "que app.py, puis redéployez l'application."
        )
        st.stop()


def _lire_csv_robuste(flux: io.BytesIO | str):
    kwargs = {"encoding": "utf-8-sig", "engine": "python"}
    if isinstance(flux, (str, os.PathLike)):
        return pd.read_csv(flux, sep=None, **kwargs)
    return pd.read_csv(flux, sep=None, **kwargs)

st.set_page_config(
    page_title="Suivi & Prévision SAAR (S&OP)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

RACINE = Path(__file__).resolve().parent
DOSSIERS = [
    RACINE / "metier" / "data",
    RACINE.parent / "metier" / "data",
    RACINE / "data" / "input",
    RACINE / "data",
    RACINE,
    RACINE.parent,
    Path.cwd() / "metier" / "data",
    Path.cwd()
]

FICHIERS_CANDIDATS = [
    "DATA_BRUT.xlsx",
]

# ✚ "region" ajouté à la liste des colonnes conservées
COLONNES = [
    "annee", "mois", "periode", "agence", "region", "segment", "produit", "parfum", "format",
    "type_format", "article", "nature", "origine", "colis", "hl",
    "coeff_janvier", "coeff_fevrier", "coeff_mars", "coeff_avril", "coeff_mai",
    "coeff_juin", "coeff_juillet", "coeff_aout", "coeff_septembre",
    "coeff_octobre", "coeff_novembre", "coeff_decembre"
]

MOIS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]
MOIS_COMPLETS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]
COULEUR_REALISE = "#9E6315EF"
COULEUR_PREVISION = "#9BD69E"
COEFFICIENTS_SAISONNIERS = [
    f"coeff_{mois}"
    for mois in [
        "janvier", "fevrier", "mars", "avril", "mai", "juin",
        "juillet", "aout", "septembre", "octobre", "novembre", "decembre"
    ]
]
HAUSSE_SAISONNIERE_PREVISION = {6: 1.20, 12: 1.20}

FILTRES = [
    ("article", "🛒 Article"),
    ("positionnement", "📍 Positionnement"),
    ("occasion", "🎯 Occasion"),
    ("conditionnement", "📦 Format"),
    ("contenance_ci", "📏 Contenance (CI)"),
    ("contenance_hl", "🧪 Contenance (hl)"),
    ("agence", "🏢 Agence"),
    ("region", "🗺️ Région"),
]

AXES = {
    "Segment": "segment", "Produit": "produit", "Parfum": "parfum",
    "Format": "format", "Type de format": "type_format", "Agence": "agence", "Article": "article"
}

AGENCES_REFERENCE = [
    "01-Tanjombato",
    "03-Usine-Diego",
    "04-Tulear",
    "05-Fianarantsoa",
    "06-Ihosy",
    "07-Majunga",
    "08-Manakara",
    "09-Tamatave",
    "11-Andranomahery",
    "12-Antsirabe",
    "18-Ambanja",
    "19-Sambava",
    "21-Nosy-be",
    "23-Morondova",
    "24-Fort-Dauphin",
]

# ✚ Région par agence (filtre 🗺️ Région)
REGION_PAR_AGENCE = {
    "01-Tanjombato": "Centre",
    "03-Usine-Diego": "Nord",
    "04-Tulear": "Sud",
    "05-Fianarantsoa": "Sud",
    "06-Ihosy": "Sud",
    "07-Majunga": "Nord",
    "08-Manakara": "Sud",
    "09-Tamatave": "Est",
    "11-Andranomahery": "Centre",
    "12-Antsirabe": "Centre",
    "18-Ambanja": "Nord",
    "19-Sambava": "Nord",
    "21-Nosy-be": "Nord",
    "23-Morondova": "Nord",
    "24-Fort-Dauphin": "Sud",
}

TYPES = {
    "SS": "SS (Single serve)", "CU": "CU (Convivial Units)",
    "IC": "IC (Individual/Immediat Consumption)", "FC": "FC (Family/Future Consumption)"
}

@st.cache_data
def charger_referentiel():
    chemins_ref = [RACINE / "Classeur2.xlsx", Path.cwd() / "Classeur2.xlsx"]
    f_ref = next((p for p in chemins_ref if p.exists()), None)
    if f_ref:
        df_ref = pd.read_excel(f_ref, sheet_name="Ref actif")
        catalogue_lignes = []
        for _, r in df_ref.iterrows():
            art = str(r['Article']).strip()
            pos = str(r['Positionnement']).strip()
            occ = str(r['Occasion']).strip()
            fmt = str(r['Format']).strip()
            c_cl = r['Contenance (Cl)']
            c_hl = r['Contenance (hl)']
            segment = "BIERES" if any(b in art.lower() for b in ["beer", "thb", "gold", "queen", "beaufort"]) else ("EAUX" if "cristal" in art.lower() or "eau" in art.lower() else "BOISSONS")
            catalogue_lignes.append({
                "segment": segment,
                "produit": art.split()[0],
                "parfum": art,
                "format": f"{c_cl} cl {fmt}",
                "type_format": occ,
                "article": art,
                "positionnement": pos,
                "occasion": occ,
                "conditionnement": fmt,
                "contenance_ci": c_cl,
                "contenance_hl": c_hl,
                "type_format_lib": occ
            })
        return pd.DataFrame(catalogue_lignes)
    return pd.DataFrame(columns=["segment", "produit", "parfum", "format", "type_format", "article", "positionnement", "occasion", "conditionnement", "contenance_ci", "contenance_hl", "type_format_lib"])

CATALOGUE = charger_referentiel()
CATALOGUE_PAR_ARTICLE = {
    meta["article"].lower().strip(): meta
    for meta in CATALOGUE.to_dict(orient="records")
}

ARTICLES_REFERENTIEL = (
    CATALOGUE["article"].dropna().astype(str).str.strip().tolist()
    if not CATALOGUE.empty
    else []
)

DIMENSIONS_REFERENTIEL = {
    "article": "article",
    "positionnement": "positionnement",
    "occasion": "occasion",
    "conditionnement": "conditionnement",
    "contenance_ci": "contenance_ci",
    "contenance_hl": "contenance_hl",
    # ⚠️ PAS "region" ici : fourni par REGION_PAR_AGENCE, pas par Classeur2.xlsx
}


def _options_referentiel(col: str) -> list:
    """Valeurs disponibles dans Classeur2.xlsx pour une dimension donnée."""
    champ = DIMENSIONS_REFERENTIEL.get(col)
    if champ is None or CATALOGUE.empty or champ not in CATALOGUE.columns:
        return []
    valeurs = CATALOGUE[champ].dropna().astype(str).str.strip()
    valeurs = valeurs.loc[valeurs.ne("") & valeurs.str.lower().ne("nan")]
    return valeurs.drop_duplicates().tolist()


def _normaliser_option(v, col: str):
    """Convertit une option en valeur homogène (str ou float) pour set()/sorted()."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
        if col in {"contenance_ci", "contenance_hl"}:
            return float(v)
        return str(v)
    s = str(v).strip()
    return s if s and s.lower() not in {"nan", "none"} else None

ALIAS_COLONNES = {
    "annee": "annee", "annees": "annee", "year": "annee", "years": "annee",
    "mois": "mois", "month": "mois", "months": "mois",
    "periode": "periode", "period": "periode", "période": "periode",
    "date": "date",
    "agence": "agence", "agences": "agence", "agency": "agence",
    "region": "region", "région": "region", "regions": "region", "régions": "region",
    "segment": "segment", "segments": "segment",
    "produit": "produit", "produits": "produit", "product": "produit", "marque": "produit",
    "parfum": "parfum", "parfums": "parfum", "flavour": "parfum", "flavor": "parfum",
    "format": "format", "formats": "format",
    "type_format": "type_format", "type format": "type_format", "typeformat": "type_format", "type": "type_format",
    "article": "article", "articles": "article", "sku": "article", "code_article": "article", "designation": "article",
    "nature": "nature", "natures": "nature", "type_donnee": "nature",
    "origine": "origine",
    "colis": "colis", "coli": "colis", "cs": "colis",
    "cases": "colis", "quantite_vendue": "colis",
    "quantite": "colis", "qte": "colis",
    "hl": "hl", "hectolitre": "hl", "hectolitres": "hl", "volume_hl": "hl",
    "volume": "hl", "volumes": "hl",
}

st.markdown("""
<style>
:root {
  --red: #d7193f;
  --red-dark: #b0102f;
  --red-soft: #fff1f4;
  --red-glow: rgba(215, 25, 63, .18);
  --green: #0e8a4a;
  --green-dark: #0a6b39;
  --green-soft: #eaf7f0;
  --green-glow: rgba(14, 138, 74, .18);
  --white: #ffffff;
  --surface: #ffffff;
  --ink: #121017;
  --muted: #5c5665;
  --line: #e2e0e6;
  --radius: 16px;
  --font: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
  --shadow-sm: 0 1px 3px rgba(18, 16, 23, .04);
  --shadow: 0 4px 6px -1px rgba(18, 16, 23, .03), 0 12px 32px -10px rgba(18, 16, 23, .08);
  --shadow-hover: 0 10px 25px -5px rgba(18, 16, 23, .12);
  --brand-bar: linear-gradient(90deg, var(--red) 0 50%, var(--green) 50% 100%);
}

.stApp {
  background:
    radial-gradient(1000px 400px at 100% -10%, var(--red-soft) 0%, transparent 60%),
    radial-gradient(1000px 400px at 0% 110%, var(--green-soft) 0%, transparent 60%),
    var(--white);
  color: var(--ink);
  font-family: var(--font);
  -webkit-font-smoothing: antialiased;
}
.block-container { max-width: 1440px; padding: 2.5rem 4vw 4rem; }

header[data-testid="stHeader"] { 
  background: rgba(255, 255, 255, 0.82); 
  backdrop-filter: blur(14px); 
  -webkit-backdrop-filter: blur(14px);
  border: none; 
}
header[data-testid="stHeader"]::after { 
  content: ""; 
  position: absolute; 
  inset: auto 0 0 0; 
  height: 3px; 
  background: var(--brand-bar); 
}

h1, h2, h3 { font-family: var(--font); color: var(--ink); font-weight: 800 !important; letter-spacing: -.03em; }
.titre { font-size: clamp(2rem, 3.4vw, 2.75rem); font-weight: 800; letter-spacing: -.045em; line-height: 1.1; margin-bottom: .5rem; }
.titre span, .titre em { color: var(--red); font-style: normal; }
.titre::after { content: ""; display: block; width: 72px; height: 4px; margin-top: .8rem; border-radius: 99px; background: var(--brand-bar); }
.sous-titre { color: var(--muted); font-size: 1.05rem; line-height: 1.7; margin-bottom: 2rem; max-width: 75ch; }

hr { border: 0; height: 2px; margin: 2rem 0; opacity: .6; background: linear-gradient(90deg, transparent, var(--red) 25%, var(--white) 50%, var(--green) 75%, transparent); }

a { color: var(--green); font-weight: 600; text-decoration: none; transition: color .2s ease; }
a:hover { color: var(--green-dark); text-decoration: underline; }

section[data-testid="stSidebar"] { 
  background: #faf9fc; 
  border-right: 1px solid var(--line); 
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label { color: var(--muted); font-weight: 500; }
[data-testid="stSidebarNavLink"] { border-radius: 10px; margin: 3px .5rem; transition: background .2s ease; }
[data-testid="stSidebarNavLink"]:hover { background: var(--green-soft) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] { background: var(--green-soft) !important; box-shadow: inset 3px 0 0 var(--green); }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: var(--green-dark) !important; font-weight: 700; }

div[data-testid="stMetric"] {
  position: relative; 
  overflow: hidden;
  background: var(--surface); 
  border: 1px solid var(--line); 
  border-radius: var(--radius);
  padding: 1.35rem 1.4rem 1.25rem; 
  box-shadow: var(--shadow);
  transition: transform .25s cubic-bezier(.2,.8,.2,1), box-shadow .25s ease, border-color .25s ease;
}
div[data-testid="stMetric"]::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--red); }
div[data-testid="stColumn"]:nth-child(even) div[data-testid="stMetric"]::before { background: var(--green); }
div[data-testid="stMetric"]:hover { 
  transform: translateY(-3px); 
  border-color: rgba(215,25,63,.3); 
  box-shadow: var(--shadow-hover), 0 12px 30px -10px var(--red-glow); 
}
div[data-testid="stColumn"]:nth-child(even) div[data-testid="stMetric"]:hover { 
  border-color: rgba(14,138,74,.35); 
  box-shadow: var(--shadow-hover), 0 12px 30px -10px var(--green-glow); 
}
div[data-testid="stMetric"] label { color: var(--muted) !important; font-size: .78rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: .07em; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--ink) !important; font-size: clamp(1.6rem, 2.4vw, 2.1rem); font-weight: 800 !important; letter-spacing: -.04em; }
div[data-testid="stMetric"] [data-testid="stMetricDelta"] { display: inline-flex; padding: .15rem .6rem; border-radius: 99px; font-size: .78rem; font-weight: 700; background: var(--green-soft); color: var(--green-dark); }
div[data-testid="stMetric"] [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) { background: var(--red-soft); color: var(--red-dark); }

.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border: none !important; 
  border-radius: 12px !important; 
  color: #fff !important;
  padding: .65rem 1.25rem !important; 
  min-height: 2.75rem;
  font-family: var(--font); 
  font-size: .9rem; 
  font-weight: 700;
  transition: all .2s cubic-bezier(.2,0,0,1);
}
.stButton > button, [data-testid="stFormSubmitButton"] > button { 
  background: var(--red) !important; 
  box-shadow: 0 4px 14px -4px var(--red-glow) !important; 
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { 
  background: var(--red-dark) !important; 
  transform: translateY(-2px); 
  box-shadow: 0 6px 20px -4px var(--red-glow) !important; 
}
.stDownloadButton > button { 
  background: var(--green) !important; 
  box-shadow: 0 4px 14px -4px var(--green-glow) !important; 
}
.stDownloadButton > button:hover { 
  background: var(--green-dark) !important; 
  transform: translateY(-2px); 
  box-shadow: 0 6px 20px -4px var(--green-glow) !important; 
}
.stButton > button[kind="secondary"] { 
  background: var(--white) !important; 
  color: var(--green) !important; 
  border: 1.5px solid var(--green) !important; 
  box-shadow: none !important; 
}
.stButton > button[kind="secondary"]:hover { 
  background: var(--green-soft) !important; 
  color: var(--green-dark) !important; 
}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible { 
  outline: 3px solid rgba(14,138,74,.35); 
  outline-offset: 2px; 
}

div[data-baseweb="tab-list"] { 
  gap: .4rem; 
  background: #f1f0f5; 
  border-radius: 14px; 
  padding: .4rem; 
  width: fit-content; 
  box-shadow: inset 0 1px 2px rgba(18,16,23,.05); 
}
button[data-baseweb="tab"] { 
  color: var(--muted) !important; 
  font-family: var(--font); 
  font-size: .88rem; 
  font-weight: 600; 
  padding: .55rem 1.1rem !important; 
  border-radius: 10px !important; 
  transition: color .2s ease, background .2s ease; 
}
button[data-baseweb="tab"]:hover { 
  color: var(--green-dark) !important; 
  background: rgba(255,255,255,.6); 
}
button[data-baseweb="tab"][aria-selected="true"] { 
  background: var(--white) !important; 
  color: var(--red) !important; 
  font-weight: 700; 
  box-shadow: var(--shadow-sm); 
}
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] { display: none; }

.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, div[data-baseweb="select"] > div {
  background: var(--surface) !important; 
  color: var(--ink) !important;
  border: 1.5px solid var(--line) !important; 
  border-radius: 12px !important; 
  font-family: var(--font);
  transition: all .2s ease;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus,
.stDateInput input:focus, div[data-baseweb="select"] > div:focus-within {
  border-color: var(--green) !important; 
  box-shadow: 0 0 0 4px rgba(14,138,74,.12) !important; 
}
.stTextInput label, .stNumberInput label, .stTextArea label, .stSelectbox label, .stDateInput label, .stMultiSelect label {
  color: var(--ink) !important; 
  font-weight: 600 !important; 
  font-size: .85rem !important;
}
span[data-baseweb="tag"] { background: var(--green-soft) !important; color: var(--green-dark) !important; border-radius: 8px !important; font-weight: 600; }
[data-testid="stCheckbox"] [aria-checked="true"] { background: var(--green) !important; border-color: var(--green) !important; }
.stSlider [role="slider"] { background: var(--red) !important; box-shadow: 0 0 0 6px var(--red-glow) !important; }

div[data-testid="stDataFrame"], div[data-testid="stTable"], div[data-testid="stExpander"],
[data-testid="stForm"], [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {
  background: var(--surface); 
  border: 1px solid var(--line) !important; 
  border-radius: var(--radius); 
  overflow: hidden; 
  box-shadow: var(--shadow-sm);
}
[data-testid="stForm"], [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"] { padding: 1rem; }
div[data-testid="stExpander"] summary { font-weight: 600; color: var(--ink); }
div[data-testid="stExpander"] summary:hover { color: var(--green); }
div[data-testid="stExpander"] details[open] { box-shadow: inset 3px 0 0 var(--green); background: rgba(14,138,74,.01); }

div[data-testid="stAlert"] { border: none; border-radius: 12px; box-shadow: var(--shadow-sm); }
.stSuccess { background: var(--green-soft) !important; color: var(--green-dark) !important; }
.stError { background: var(--red-soft) !important; color: var(--red-dark) !important; }
[data-testid="stProgress"] [role="progressbar"] > div { background: var(--line) !important; border-radius: 99px; height: 8px; }
[data-testid="stProgress"] [role="progressbar"] > div > div { background: linear-gradient(90deg, var(--red), var(--green)) !important; border-radius: 99px; }

[data-testid="stFileUploaderDropzone"] { 
  background: var(--surface) !important; 
  border: 2px dashed rgba(14,138,74,.3) !important; 
  border-radius: var(--radius) !important; 
  transition: all .2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { 
  border-color: var(--green) !important; 
  background: var(--green-soft) !important; 
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d0ccd6; border-radius: 9px; border: 2px solid var(--white); }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

@media (max-width: 768px) {
  .block-container { padding: 1.25rem 1rem 2.5rem; }
  .titre { font-size: 1.85rem; }
  .sous-titre { font-size: .92rem; }
  div[data-testid="stMetric"] { padding: 1rem; }
  div[data-baseweb="tab-list"] { width: 100%; overflow-x: auto; }
  .stButton > button, .stDownloadButton > button { width: 100%; }
}
</style>
""", unsafe_allow_html=True)

def normaliser_nom(nom: str) -> str:
    s = str(nom).strip().lower()
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8')
    s = re.sub(r'[^a-z0-9_]+', '_', s).strip('_')
    return ALIAS_COLONNES.get(s, s)

AGENCES_PAR_CLE = {
    normaliser_nom(agence): agence
    for agence in AGENCES_REFERENCE
}
AGENCES_PAR_CLE.update(
    {
        normaliser_nom(agence.split("-", 1)[1]): agence
        for agence in AGENCES_REFERENCE
    }
)
AGENCES_PAR_CLE.update(
    {
        normaliser_nom(ancien_nom): agence
        for ancien_nom, agence in {
            "Andranomahe": "11-Andranomahery",
            "Anjombato": "01-Tanjombato",
            "Diego": "03-Usine-Diego",
            "Toliara": "04-Tulear",
            "Mahajanga": "07-Majunga",
            "Toamasina": "09-Tamatave",
            "Nosy-Be": "21-Nosy-be",
            "Nosy Be": "21-Nosy-be",
        }.items()
    }
)

def normaliser_agence(valeur: object) -> str:
    nom = str(valeur).strip()
    cle = normaliser_nom(nom)
    agence = AGENCES_PAR_CLE.get(cle)
    if agence is not None:
        return agence

    if re.fullmatch(r"\d+(?:_0)?", cle):
        code = f"{int(cle.split('_', 1)[0]):02d}"
        return next(
            (
                agence for agence in AGENCES_REFERENCE
                if agence.startswith(f"{code}-")
            ),
            nom,
        )
    return nom


def region_depuis_agence(valeur: object) -> str:
    """Retourne la région (Nord/Sud/Est/Centre) d'une agence."""
    agence_normalisee = normaliser_agence(valeur)
    return REGION_PAR_AGENCE.get(agence_normalisee, "Non renseigné")


def extraire_decalage_reel(col_name: str) -> int | None:
    s = normaliser_nom(col_name)
    m = re.search(r'real?\s*[-_]?\s*(\d+)', s)
    if m:
        return int(m.group(1))
    return None

def extraire_annee_mois(valeur) -> tuple[int | None, int | None]:
    val_str = str(valeur).strip()
    m = re.search(r'\b(20\d\d)[-_/]?0?([1-9]|1[0-2])\b', val_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    
    m2 = re.search(r'\b0?([1-9]|1[0-2])[-_/](20\d\d)\b', val_str)
    if m2:
        return int(m2.group(2)), int(m2.group(1))

    mois_abbr = ["janv", "fevr", "févr", "mars", "avr", "mai", "juin", "juil", "aout", "août", "sept", "oct", "nov", "dec", "déc"]
    val_lower = val_str.lower()
    for idx, m_name in enumerate(mois_abbr):
        m_num = [1, 2, 2, 3, 4, 5, 6, 7, 8, 8, 9, 10, 11, 12, 12][idx]
        if m_name in val_lower:
            m_an = re.search(r'(20\d\d|\d\d)', val_lower)
            if m_an:
                an = int(m_an.group(1))
                if an < 100:
                    an += 2000
                return an, m_num

    m_an_seul = re.search(r'\b(20\d\d)\b', val_str)
    if m_an_seul:
        return int(m_an_seul.group(1)), 1

    return None, None

def nettoyer_annees_mois(df: pd.DataFrame) -> pd.DataFrame:
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").fillna(2026).astype(int)
    df["mois"] = normaliser_mois(df["mois"]).fillna(1).astype(int)

    mask_inv = (df["annee"] >= 1) & (df["annee"] <= 12) & (df["mois"] >= 2020) & (df["mois"] <= 2035)
    if mask_inv.any():
        df.loc[mask_inv, ["annee", "mois"]] = df.loc[mask_inv, ["mois", "annee"]].values

    mask_2d = (df["annee"] >= 20) & (df["annee"] <= 50)
    df.loc[mask_2d, "annee"] = 2000 + df.loc[mask_2d, "annee"]

    if "periode" in df.columns:
        for idx in df[df["annee"].isna() | (df["annee"] < 2000) | (df["annee"] > 2050)].index:
            p = str(df.loc[idx, "periode"])
            a, m = extraire_annee_mois(p)
            if a and 2000 <= a <= 2050:
                df.loc[idx, "annee"] = a
            if m and 1 <= m <= 12:
                df.loc[idx, "mois"] = m

    df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
    return df

def lire_et_normaliser(contenu: bytes | None, nom: str, chemin: str | None, annee_cloture: int = 2026, mois_cloture: int = 9) -> pd.DataFrame:
    nom_fichier = Path(nom if contenu is not None else chemin or "").name.lower()
    est_data_brut = nom_fichier == "data_brut.xlsx"
    if contenu is not None:
        flux = io.BytesIO(contenu)
        if nom.lower().endswith(".csv"):
            df_raw = _lire_csv_robuste(flux)
        else:
            feuilles = pd.ExcelFile(flux).sheet_names
            if est_data_brut:
                feuille = next(
                    (f for f in feuilles if normaliser_nom(f) == "export"),
                    feuilles[0],
                )
                df_raw = pd.read_excel(flux, sheet_name=feuille, header=None)
            else:
                feuille = next((f for f in feuilles if normaliser_nom(f) == "ventes_long"), 0)
                df_preview = pd.read_excel(flux, sheet_name=feuille, nrows=5, header=None)
                header_idx = 0
                max_matches = 0
                for i, row in df_preview.iterrows():
                    matches = sum(1 for cell in row if normaliser_nom(cell) in ALIAS_COLONNES.values() or extraire_decalage_reel(cell) is not None)
                    if matches > max_matches:
                        max_matches = matches
                        header_idx = i
                flux.seek(0)
                df_raw = pd.read_excel(flux, sheet_name=feuille, header=header_idx)
    else:
        chemin_str = str(chemin)
        if chemin_str.lower().endswith(".csv"):
            df_raw = _lire_csv_robuste(chemin_str)
        else:
            feuilles = pd.ExcelFile(chemin_str).sheet_names
            if est_data_brut:
                feuille = next(
                    (f for f in feuilles if normaliser_nom(f) == "export"),
                    feuilles[0],
                )
                df_raw = pd.read_excel(chemin_str, sheet_name=feuille, header=None)
            else:
                feuille = next((f for f in feuilles if normaliser_nom(f) == "ventes_long"), 0)
                df_preview = pd.read_excel(chemin_str, sheet_name=feuille, nrows=5, header=None)
                header_idx = 0
                max_matches = 0
                for i, row in df_preview.iterrows():
                    matches = sum(1 for cell in row if normaliser_nom(cell) in ALIAS_COLONNES.values() or extraire_decalage_reel(cell) is not None)
                    if matches > max_matches:
                        max_matches = matches
                        header_idx = i
                df_raw = pd.read_excel(chemin_str, sheet_name=feuille, header=header_idx)

    df = (
        normaliser_lignes_data_brut(
            df_raw,
            articles_referentiel=ARTICLES_REFERENTIEL,
        )
        if est_data_brut
        else df_raw.copy()
    )
    df.columns = [str(c).strip() for c in df.columns]
    colonnes_source = list(df.columns)

    col_map = {}
    real_cols = []
    for c in df.columns:
        norm = normaliser_nom(c)
        if norm in ALIAS_COLONNES.values():
            col_map[c] = norm
        elif norm in COEFFICIENTS_SAISONNIERS:
            col_map[c] = norm
        elif extraire_decalage_reel(c) is not None:
            real_cols.append(c)
    df = df.rename(columns=col_map)

    if "date" in df.columns and ("annee" not in df.columns or "mois" not in df.columns):
        dates = pd.to_datetime(df["date"], errors="coerce")
        df["annee"] = dates.dt.year
        df["mois"] = dates.dt.month
        df["periode"] = dates.dt.strftime("%Y-%m")

    colonnes_reelles_decalees = {}
    colonnes_dates_decalees = {}
    for col in df.columns:
        nom_normalise = normaliser_nom(col)
        match_reel = re.fullmatch(r"real_(\d+)", nom_normalise)
        match_date = re.fullmatch(r"m_(\d+)", nom_normalise)
        if match_reel:
            colonnes_reelles_decalees[int(match_reel.group(1))] = col
        elif match_date:
            colonnes_dates_decalees[int(match_date.group(1))] = col

    lignes_reelles = []
    for decalage, col_reel in colonnes_reelles_decalees.items():
        col_date = colonnes_dates_decalees.get(decalage)
        if col_date is None:
            continue
        dates_reelles = pd.to_datetime(df[col_date], errors="coerce")
        volumes_reels = pd.to_numeric(df[col_reel], errors="coerce")
        valides = dates_reelles.notna() & volumes_reels.notna()
        if not valides.any():
            continue

        lignes = df.loc[valides].copy()
        dates_valides = dates_reelles.loc[valides]
        lignes["annee"] = dates_valides.dt.year
        lignes["mois"] = dates_valides.dt.month
        lignes["periode"] = dates_valides.dt.strftime("%Y-%m")
        lignes["nature"] = "Réalisé"
        lignes["hl"] = volumes_reels.loc[valides]
        lignes["colis"] = 0.0
        lignes_reelles.append(lignes)

    if real_cols and ("annee" not in df.columns or "mois" not in df.columns):
        id_vars = [c for c in df.columns if c not in real_cols]
        df = df.melt(id_vars=id_vars, value_vars=real_cols, var_name="col_real", value_name="hl")
        
        annees_m, mois_m, periodes_m, natures_m = [], [], [], []
        for val in df["col_real"]:
            lag = extraire_decalage_reel(val) or 1
            tot_mois = (annee_cloture * 12 + mois_cloture - 1) - (lag - 1)
            a = tot_mois // 12
            m = (tot_mois % 12) + 1
            
            annees_m.append(a)
            mois_m.append(m)
            periodes_m.append(f"{a}-{str(m).zfill(2)}")
            natures_m.append("Réalisé")
            
        df["annee"] = annees_m
        df["mois"] = mois_m
        df["periode"] = periodes_m
        df["nature"] = natures_m
        df = df.drop(columns=["col_real"])
    else:
        date_cols = []
        for c in df.columns:
            if normaliser_nom(c).startswith("realise_"):
                continue
            a, m = extraire_annee_mois(c)
            if a is not None and c not in ["annee", "mois", "periode"]:
                date_cols.append(c)

        if date_cols and ("annee" not in df.columns or "mois" not in df.columns):
            id_vars = [c for c in df.columns if c not in date_cols]
            df = df.melt(id_vars=id_vars, value_vars=date_cols, var_name="periode_brute", value_name="hl")
            
            annees_m, mois_m, periodes_m = [], [], []
            for val in df["periode_brute"]:
                a, m = extraire_annee_mois(val)
                annees_m.append(a if a else 2026)
                mois_m.append(m if m else 1)
                periodes_m.append(f"{a}-{str(m).zfill(2)}" if a and m else "2026-01")
                
            df["annee"] = annees_m
            df["mois"] = mois_m
            df["periode"] = periodes_m
            df = df.drop(columns=["periode_brute"])

    if lignes_reelles:
        df = pd.concat([df, *lignes_reelles], ignore_index=True, sort=False)

    defaut_valeurs = {
        "annee": 2026, "mois": 1, "periode": "2026-01",
        "agence": "Non renseigné", "region": "Non renseigné",
        "segment": "Non renseigné", "produit": "Non renseigné",
        "parfum": "Non renseigné", "format": "Non renseigné", "type_format": "Non renseigné",
        "article": "Non renseigné", "nature": "Prévision", "colis": 0.0, "hl": 0.0,
        "origine": "Donnée source",
        **dict.fromkeys(COEFFICIENTS_SAISONNIERS, 1.0)
    }

    colonnes_manquantes = {
        col: defaut_valeurs[col] for col in COLONNES if col not in df.columns
    }
    if colonnes_manquantes:
        df = pd.concat(
            [df, pd.DataFrame(colonnes_manquantes, index=df.index)],
            axis=1,
        )

    articles = df["article"].map(str).str.strip().str.lower()
    dimensions_catalogue = [
        "segment", "produit", "parfum", "format", "type_format",
        "positionnement", "occasion", "conditionnement",
        "contenance_ci", "contenance_hl"
    ]
    for c_dim in dimensions_catalogue:
        if c_dim not in df.columns:
            df[c_dim] = "Non renseigné"
        champ_catalogue = "type_format_lib" if c_dim == "type_format" else c_dim
        correspondances = {
            article: meta.get(champ_catalogue, "Non renseigné")
            for article, meta in CATALOGUE_PAR_ARTICLE.items()
        }
        valeurs = df[c_dim].map(str).str.strip()
        a_enrichir = valeurs.isin(["", "Non renseigné", "nan", "None"])
        valeurs_catalogue = articles.map(correspondances).fillna("Non renseigné")
        df[c_dim] = valeurs.mask(a_enrichir, valeurs_catalogue)

    df = df[COLONNES].copy()
    df = nettoyer_annees_mois(df)

    for c in ["colis", "hl"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    for c in COEFFICIENTS_SAISONNIERS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(1.0)

    for c in ["agence", "region", "segment", "produit", "parfum", "format", "type_format", "article", "nature", "origine", "periode"]:
        df[c] = df[c].fillna("Non renseigné").astype(str)

    df["agence"] = df["agence"].map(normaliser_agence)
    # ✚ Remplit region à partir de l'agence (filtre 🗺️ Région)
    df["region"] = df["agence"].map(region_depuis_agence)
    df["nature"] = df["nature"].replace("", "Prévision")
    df = assurer_dimensions_filtres(df, CATALOGUE_PAR_ARTICLE, TYPES)
    # ✚ Sécurité : réinjecte region au cas où assurer_dimensions_filtres l'aurait perdue
    df["region"] = df["agence"].map(region_depuis_agence)

    articles_nettoyes = df["article"].astype(str).str.strip().str.lower()
    articles_exclus = ["eaux (gaz)", "eaux (plate)", "bieres", "energy", "alcomix", "bg"]
    masque_article_valide = (
        ~articles_nettoyes.isin(["non renseigné", "nan", "none", ""])
        & ~articles_nettoyes.str.contains(
            r"total|général|general|sous-total", regex=True, na=False
        )
        & ~articles_nettoyes.isin(articles_exclus)
    )
    lignes_avant_filtre_article = len(df)
    exemples_articles = (
        df["article"].astype(str).str.strip().drop_duplicates().head(8).tolist()
    )
    df = df[masque_article_valide].copy()

    df.attrs["diagnostic_chargement"] = {
        "nom_fichier": nom_fichier,
        "est_data_brut": est_data_brut,
        "colonnes_source": colonnes_source,
        "colonnes_reconnues": sorted(set(col_map.values())),
        "colonnes_reel": sorted(colonnes_reelles_decalees),
        "colonnes_date": sorted(colonnes_dates_decalees),
        "lignes_avant_filtre_article": lignes_avant_filtre_article,
        "lignes_conservees": len(df),
        "exemples_articles": exemples_articles,
        "articles_referentiel": len(ARTICLES_REFERENTIEL),
    }
    return df


@st.cache_data(show_spinner="Chargement et préparation des données...")
def charger_et_normaliser(
    contenu: bytes | None,
    nom: str,
    chemin: str | None,
    annee_cloture: int,
    mois_cloture: int,
    revision_fichier: tuple[int, int] | None = None,
) -> pd.DataFrame:
    if chemin is not None and revision_fichier is not None:
        stat_fichier = Path(chemin).stat()
        if (stat_fichier.st_mtime_ns, stat_fichier.st_size) != revision_fichier:
            raise RuntimeError("Le fichier source a changé pendant son chargement. Relancez le calcul.")
    return lire_et_normaliser(contenu, nom, chemin, annee_cloture, mois_cloture)



@st.cache_data(show_spinner="Calcul de la projection SAAR (Atterrissage avec coefficients 2024-2025)...")
def appliquer_projection_saar(
    df: pd.DataFrame,
    annee_cloture: int,
    mois_cloture: int,
    annee_cible: int,
    taux_croissance: float,
) -> tuple[pd.DataFrame, int, int]:
    if annee_cible < annee_cloture:
        return df, 0, 0

    df = assurer_dimensions_filtres(df, CATALOGUE_PAR_ARTICLE, TYPES)
    # ✚ Sécurité : conserve region dans les dimensions
    if "region" not in df.columns:
        df["region"] = df["agence"].map(region_depuis_agence)

    cles = ["agence", "article"]
    dimensions = [
        "agence", "region", "segment", "produit", "parfum", "format",
        "type_format", "article", "origine", "positionnement", "occasion",
        "conditionnement", "contenance_ci", "contenance_hl"
    ]

    realise_ytd = df.loc[
        (df["nature"] == "Réalisé")
        & (df["annee"] == annee_cloture)
        & (df["mois"] <= mois_cloture)
    ]
    if realise_ytd.empty:
        return df, 0, 0

    cumul_ytd = realise_ytd.groupby(cles)[["hl", "colis"]].sum()
    derniere_ligne = (
        realise_ytd.sort_values(["annee", "mois"])
        .drop_duplicates(cles, keep="last")
        .set_index(cles)
    )

    annees_ref = [2024, 2025]
    df_ref = df.loc[df["annee"].isin(annees_ref) & (df["nature"] == "Réalisé")]
    
    def calculer_profils_reference(donnees: pd.DataFrame) -> dict[tuple, np.ndarray]:
        if donnees.empty:
            return {}
        volumes_mensuels = (
            donnees.groupby([*cles, "mois"])["hl"]
            .sum()
            .unstack("mois")
            .fillna(0.0)
            .reindex(columns=range(1, 13), fill_value=0.0)
            .clip(lower=0.0)
        )
        totaux = volumes_mensuels.sum(axis=1)
        profils = volumes_mensuels.div(totaux.where(totaux > 0), axis=0) * 12.0
        return {
            cle if isinstance(cle, tuple) else (cle,): profil.to_numpy(dtype=float)
            for cle, profil in profils.iterrows()
            if totaux.loc[cle] > 0
        }

    profils_ref = calculer_profils_reference(df_ref)
    
    colonnes_coefficients = [col for col in COEFFICIENTS_SAISONNIERS if col in df.columns]
    coefficients_agence_article = (
        df.groupby(cles)[colonnes_coefficients].first()
        if colonnes_coefficients
        else pd.DataFrame()
    )

    volumes_annee_precedente = (
        df.loc[df["annee"] == annee_cible - 1]
        .groupby([*cles, "mois"])[["hl", "colis"]]
        .sum()
    )
    
    taux_annuel = 1.0 + max(taux_croissance, 1.0) / 100.0
    facteur_croissance = taux_annuel ** (annee_cible - annee_cloture)
    
    projections = []
    profils_neutres = 0
    couples_projetes = set()

    for cle, volumes in cumul_ytd.iterrows():
        cle = cle if isinstance(cle, tuple) else (cle,)
        
        profil = profils_ref.get(cle)
        if profil is None or profil[:mois_cloture].sum() <= 0:
            profil = profils_ref.get((cle[1],))
            
        if (profil is None or profil[:mois_cloture].sum() <= 0) and cle in coefficients_agence_article.index:
            profil = coefficients_agence_article.loc[cle].reindex(
                COEFFICIENTS_SAISONNIERS, fill_value=1.0
            ).to_numpy(dtype=float)
            profil = np.nan_to_num(profil, nan=1.0, posinf=1.0, neginf=0.0)
            profil = np.clip(profil, 0.0, None)
            if profil.sum() > 0:
                profil = profil / profil.sum() * 12.0
            else:
                profil = None
                
        if profil is None or profil[:mois_cloture].sum() <= 0:
            profil = np.ones(12, dtype=float)
            profils_neutres += 1

        poids_ecoule = profil[:mois_cloture].sum()
        
        base_annuelle_hl = max(0.0, float(volumes["hl"]) / poids_ecoule * 12.0)
        base_annuelle_colis = max(0.0, float(volumes["colis"]) / poids_ecoule * 12.0)
        
        ligne_ref = derniere_ligne.loc[cle]
        
        for mois in range(1, 13):
            if annee_cible == annee_cloture and mois <= mois_cloture:
                continue

            facteur_mois = HAUSSE_SAISONNIERE_PREVISION.get(mois, 1.0)
            ligne = {
                col: cle[cles.index(col)] if col in cles else ligne_ref[col]
                for col in dimensions
            }
            
            cle_mois_precedent = (*cle, mois)
            if cle_mois_precedent in volumes_annee_precedente.index:
                plancher = volumes_annee_precedente.loc[cle_mois_precedent]
                volume_hl_min = max(0.0, float(plancher["hl"]))
                volume_colis_min = max(0.0, float(plancher["colis"]))
            else:
                annees_croissance_precedente = max(0, annee_cible - 1 - annee_cloture)
                volume_hl_min = (
                    base_annuelle_hl
                    * taux_annuel ** annees_croissance_precedente
                    * profil[mois - 1] / 12.0
                )
                volume_colis_min = (
                    base_annuelle_colis
                    * taux_annuel ** annees_croissance_precedente
                    * profil[mois - 1] / 12.0
                )

            ligne.update({
                "annee": annee_cible,
                "mois": mois,
                "periode": f"{annee_cible}-{mois:02d}",
                "nature": "Prévision",
                "hl": max(
                    volume_hl_min,
                    base_annuelle_hl * facteur_croissance
                    * profil[mois - 1] / 12.0,
                ) * facteur_mois,
                "colis": max(
                    volume_colis_min,
                    base_annuelle_colis * facteur_croissance
                    * profil[mois - 1] / 12.0,
                ) * facteur_mois,
            })
            projections.append(ligne)
            couples_projetes.add(cle)

    if not projections:
        return df, 0, profils_neutres

    nouvelles_previsions = pd.DataFrame(projections).reindex(columns=df.columns)
    
    masque_existant = (df["annee"] == annee_cible) & (df["nature"] == "Prévision")
    if annee_cible == annee_cloture:
        masque_existant &= df["mois"].gt(mois_cloture)
        
    df_nettoye = df.loc[~masque_existant]
    resultat = pd.concat([df_nettoye, nouvelles_previsions], ignore_index=True)
    
    return resultat, len(couples_projetes), profils_neutres

@st.cache_data(show_spinner="Reconstitution des prévisions historiques...")
def reconstituer_previsions_historiques(
    df: pd.DataFrame,
    annee_cloture: int,
    taux_croissance: float,
) -> pd.DataFrame:
    annees_presentes = set(df["annee"].unique())
    mois_par_annee = df.groupby("annee")["mois"].agg(["min", "max"])
    annees_completes = {
        int(annee)
        for annee, plage in mois_par_annee.iterrows()
        if plage["min"] == 1 and plage["max"] == 12
    }

    previsions_historiques = []
    previsions_par_annee: dict[int, pd.DataFrame] = {}
    facteur_croissance_minimal = 1.0 + max(taux_croissance, 1.0) / 100.0
    for annee_cible in sorted(annees_presentes):
        annee_precedente = int(annee_cible) - 1
        if (
            annee_cible >= annee_cloture
            or annee_precedente not in annees_completes
        ):
            continue

        historique = df.loc[df["annee"] < annee_cible].copy()
        historique["nature"] = "Réalisé"
        projection, _, _ = appliquer_projection_saar(
            historique,
            annee_precedente,
            12,
            int(annee_cible),
            taux_croissance,
        )
        prevision = projection.loc[
            projection["annee"].eq(annee_cible)
            & projection["nature"].eq("Prévision")
        ].copy()
        references_prevision = (
            previsions_par_annee[annee_precedente].groupby(
                ["agence", "article"]
            )[["hl", "colis"]].sum()
            if annee_precedente in previsions_par_annee
            else df.loc[df["annee"].eq(annee_precedente)]
            .groupby(["agence", "article"])[["hl", "colis"]]
            .sum()
        )
        for cle, indices in prevision.groupby(["agence", "article"]).groups.items():
            if cle not in references_prevision.index:
                continue
            reference = references_prevision.loc[cle]
            for colonne in ("hl", "colis"):
                volume_prevu = prevision.loc[indices, colonne].sum()
                volume_minimum = (
                    max(0.0, float(reference[colonne]))
                    * facteur_croissance_minimal
                )
                if volume_prevu > 0 and volume_prevu < volume_minimum:
                    prevision.loc[indices, colonne] *= volume_minimum / volume_prevu
        prevision["nature"] = "Prévision reconstituée"
        previsions_par_annee[int(annee_cible)] = prevision
        previsions_historiques.append(prevision)

    if not previsions_historiques:
        return df.iloc[0:0].assign(nature=pd.Series(dtype=str))
    return pd.concat(previsions_historiques, ignore_index=True)


def nombre(x: float, dec: int) -> str:
    return f"{x:,.{dec}f}".replace(",", " ")

def etiquette(periode: str) -> str:
    p = str(periode).split("-")
    if len(p) == 2:
        a, m = p
        if m.isdigit() and 1 <= int(m) <= 12:
            return f"{MOIS[int(m) - 1]}-{a[-2:]}"
    return str(periode)

def variation(avant, apres):
    avant = np.asarray(avant, dtype=float)
    apres = np.asarray(apres, dtype=float)
    return np.where(avant != 0, (apres - avant) / np.where(avant != 0, avant, 1) * 100, np.nan)

def tableau(df: pd.DataFrame, **kw):
    try:
        st.dataframe(df, width="stretch", **kw)
    except Exception:
        st.dataframe(df, width='stretch', **kw)

def afficher_vue(
    df: pd.DataFrame,
    mode: str,
    dec: int = 0,
    couleur: str | list[str] | None = None,
    hauteur: int | None = None,
    largeur: int | None = None,
    horizontal: bool = False,
) -> None:
    if mode == "Tableau":
        tableau(df.round(dec))
        return

    df_graphique = df.apply(pd.to_numeric, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    df_graphique = df_graphique.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df_graphique.empty:
        st.info("Aucune valeur numérique disponible pour afficher ce graphique.")
        return

    if couleur is None:
        couleurs_series = []
        for serie in df_graphique.columns:
            nom_serie = normaliser_nom(str(serie))
            if "realis" in nom_serie:
                couleurs_series.append(COULEUR_REALISE)
            elif any(
                terme in nom_serie
                for terme in ("prevision", "atterrissage", "cible")
            ):
                couleurs_series.append(COULEUR_PREVISION)
            else:
                couleurs_series.append(None)
        couleur_graphique = (
            [couleur_serie or "#6B7280" for couleur_serie in couleurs_series]
            if any(couleurs_series)
            else None
        )
    elif isinstance(couleur, str) and len(df_graphique.columns) > 1:
        couleur_graphique = [couleur] * len(df_graphique.columns)
    elif isinstance(couleur, list):
        couleurs_par_serie = dict(zip(df.columns, couleur))
        couleur_graphique = [
            couleurs_par_serie[serie]
            for serie in df_graphique.columns
            if serie in couleurs_par_serie
        ]
    else:
        couleur_graphique = couleur

    if mode == "Courbes":
        nom_axe = df_graphique.index.name or "Période"
        donnees_courbe = (
            df_graphique.rename_axis(nom_axe)
            .reset_index()
            .melt(
                id_vars=nom_axe,
                var_name="Série",
                value_name="Valeur",
            )
        )
        donnees_courbe[nom_axe] = donnees_courbe[nom_axe].astype(str)
        graphique = (
            alt.Chart(donnees_courbe)
            .mark_line(
                interpolate="monotone",
                point=alt.OverlayMarkDef(filled=True, size=35),
            )
            .encode(
                x=alt.X(
                    f"{nom_axe}:N",
                    sort=df_graphique.index.astype(str).tolist(),
                    title=nom_axe,
                ),
                y=alt.Y("Valeur:Q", title="Volume"),
                tooltip=[
                    alt.Tooltip(f"{nom_axe}:N", title=nom_axe),
                    alt.Tooltip("Série:N"),
                    alt.Tooltip("Valeur:Q", format=",.2f"),
                ],
            )
        )
        couleurs = (
            [couleur_graphique] * len(df_graphique.columns)
            if isinstance(couleur_graphique, str)
            else couleur_graphique
        )
        if couleurs is not None:
            graphique = graphique.encode(
                color=alt.Color(
                    "Série:N",
                    scale=alt.Scale(
                        domain=df_graphique.columns.tolist(),
                        range=couleurs,
                    ),
                    legend=alt.Legend(title=None),
                )
            )
        graphique = graphique.properties(height=hauteur or 350)
        if largeur is not None:
            graphique = graphique.properties(width=largeur)
        st.altair_chart(graphique, width="stretch")
    else:
        options = {"color": couleur_graphique, "stack": False}
        if hauteur is not None:
            options["height"] = hauteur
        if largeur is not None:
            options["width"] = largeur
        if horizontal:
            options["horizontal"] = True
        st.bar_chart(df_graphique, **options)

def trier(valeurs, col):
    valeurs = [v for v in valeurs if pd.notna(v)]
    if col in {"contenance_ci", "contenance_hl"}:
        return sorted(valeurs, key=float)
    if col == "conditionnement":
        ordre = {"CAN": 0, "PET": 1, "VER": 2}
        return sorted(valeurs, key=lambda valeur: (ordre.get(str(valeur), 99), str(valeur)))
    return sorted(valeurs)

FICHIERS_EXISTANTS = []
for d in DOSSIERS:
    for f_nom in FICHIERS_CANDIDATS:
        p = d / f_nom
        if p.exists() and p not in FICHIERS_EXISTANTS:
            FICHIERS_EXISTANTS.append(p)

st.markdown('<div class="titre"> Moteur S&OP : Prévision SAAR & Rolling Forecast</div>', unsafe_allow_html=True)
st.markdown('<div class="sous-titre">Prévision automatique par méthode SAAR (Seasonally Adjusted Run Rate) et mise à jour dynamique des cumuls.</div>', unsafe_allow_html=True)

st.sidebar.header("📁 Source & Import Mensuel")
st.sidebar.caption(
    "Chaque import remplace les périodes qu’il contient et conserve le reste "
    "de l’historique. Les cumuls et prévisions sont recalculés automatiquement."
)
version_import = st.session_state.get("version_widget_import_mensuel", 0)
if st.sidebar.button("Réinitialiser les imports de cette session"):
    st.session_state.pop("historique_cumule_mensuel", None)
    st.session_state.pop("empreinte_dernier_import_mensuel", None)
    st.session_state.pop("resume_dernier_import_mensuel", None)
    st.session_state["version_widget_import_mensuel"] = version_import + 1
    st.rerun()

version_import = st.session_state.get("version_widget_import_mensuel", 0)
importe = st.sidebar.file_uploader(
    "Importer un export mensuel ou un historique complet (.csv / .xlsx)",
    type=["csv", "xlsx"],
    key=f"import_mensuel_{version_import}",
)
chemin = FICHIERS_EXISTANTS[0] if FICHIERS_EXISTANTS else None

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cutoff S&OP (Mois Pivot Réalisé)")
col_c1, col_c2 = st.sidebar.columns(2)
annee_cloture = col_c1.number_input("Année Clôture", min_value=2000, max_value=2036, value=2023)
mois_cloture = col_c2.selectbox("Mois Pivot", options=list(range(1, 13)), index=8, format_func=lambda m: f"{m} - {MOIS[m-1]}")

st.sidebar.markdown("---")
st.sidebar.header("🎯 Année & Mois Cible")
annee_cible = st.sidebar.number_input(
    "Année Cible", min_value=2000, max_value=2040, value=int(annee_cloture) + 1
)
choix_mois = ["Tous les mois"] + MOIS_COMPLETS
mois_cible_str = st.sidebar.selectbox("Mois Cible", options=choix_mois, index=0)
mois_cible_num = (
    None
    if mois_cible_str == "Tous les mois"
    else MOIS_COMPLETS.index(mois_cible_str) + 1
)

st.sidebar.markdown("---")
st.sidebar.header("📊 Unité de Mesure")
val_choix = st.sidebar.radio(
    "Métrique",
    options=["hl", "colis"],
    format_func=lambda x: "Hectolitres (hl)" if x == "hl" else "Colis (cs)",
    horizontal=True,
)
val = val_choix
lib = "hl" if val == "hl" else "colis"

st.sidebar.markdown("---")
st.sidebar.header("🔢 Format d'Affichage")
dec = st.sidebar.number_input(
    "Nombre de décimales", min_value=0, max_value=4, value=0, step=1
)

st.sidebar.markdown("---")
st.sidebar.header("👁️ Mode d'Affichage")
mode_affichage = st.sidebar.selectbox(
    "Type de vue",
    options=["Tableau", "Courbes", "Histogramme"],
    index=0
)

df_brut = None
erreur_chargement = None
diagnostic_import_vide = None
historique = None
try:
    historique = st.session_state.get("historique_cumule_mensuel")
    if historique is None and chemin:
        stat_fichier = chemin.stat()
        historique = charger_et_normaliser(
            None, "", str(chemin),
            int(annee_cloture), int(mois_cloture),
            (stat_fichier.st_mtime_ns, stat_fichier.st_size)
        )
        if not historique.empty:
            st.session_state["historique_cumule_mensuel"] = historique

    if importe is not None:
        import_ignore = False
        contenu_import = importe.getvalue()
        empreinte = hashlib.sha256(contenu_import).hexdigest()
        if empreinte != st.session_state.get("empreinte_dernier_import_mensuel"):
            nouvel_import = charger_et_normaliser(
                contenu_import, importe.name, None,
                int(annee_cloture), int(mois_cloture)
            )
            if nouvel_import.empty:
                import_ignore = True
                diagnostic_import_vide = nouvel_import.attrs.get("diagnostic_chargement")
                erreur_chargement = (
                    f"« {importe.name} » a été lu mais aucune ligne exploitable "
                    "n'en est ressortie : import ignoré."
                )
                st.sidebar.error(erreur_chargement)
            else:
                if historique is None:
                    historique = nouvel_import
                    nb_periodes = nouvel_import[["annee", "mois"]].drop_duplicates().shape[0]
                else:
                    historique, nb_periodes = remplacer_periodes_importees(
                        historique,
                        nouvel_import,
                    )
                st.session_state["historique_cumule_mensuel"] = historique
                st.session_state["empreinte_dernier_import_mensuel"] = empreinte
                periodes = nouvel_import[["annee", "mois"]].drop_duplicates()
                periodes_triees = sorted(
                    (int(annee), int(mois))
                    for annee, mois in periodes.itertuples(index=False, name=None)
                )
                premiere_periode = f"{periodes_triees[0][0]}-{periodes_triees[0][1]:02d}"
                derniere_periode = f"{periodes_triees[-1][0]}-{periodes_triees[-1][1]:02d}"
                st.session_state["resume_dernier_import_mensuel"] = (
                    f"{importe.name} : {len(nouvel_import):,} lignes intégrées, "
                    f"{nb_periodes} période(s) remplacée(s) ou ajoutée(s) "
                    f"({premiere_periode} à {derniere_periode})."
                )
                historique = st.session_state["historique_cumule_mensuel"]

        if import_ignore:
            if historique is not None and not historique.empty:
                df_brut = historique.copy()
        else:
            df_brut = historique.copy()
            st.sidebar.success(
                st.session_state.get(
                    "resume_dernier_import_mensuel",
                    f"Fichier déjà intégré : {importe.name}",
                )
            )
    elif historique is not None:
        df_brut = historique.copy()
except Exception as e:
    erreur_chargement = f"{type(e).__name__} : {e}"
    st.sidebar.error(f"Erreur lors du chargement : {e}")

if df_brut is None or df_brut.empty:
    st.warning("⚠️ Aucun fichier source trouvé. Veuillez importer un fichier CSV ou Excel via la barre latérale pour lancer le tableau de bord.")
    _hist_diag = historique if isinstance(historique, pd.DataFrame) else st.session_state.get("historique_cumule_mensuel")
    _diag = diagnostic_import_vide or (
        _hist_diag.attrs.get("diagnostic_chargement")
        if isinstance(_hist_diag, pd.DataFrame)
        else None
    )
    if erreur_chargement or _diag or importe is not None or chemin is not None:
        with st.expander("🔎 Pourquoi ? Diagnostic du chargement", expanded=True):
            if erreur_chargement:
                st.error(f"Erreur pendant la lecture du fichier : {erreur_chargement}")
            if _diag:
                st.write(f"**Fichier lu :** {_diag['nom_fichier'] or '(sans nom)'}")
                st.write(
                    f"**Référentiel Classeur2.xlsx :** "
                    f"{_diag.get('articles_referentiel', 0)} articles chargés"
                )
                st.write(
                    "**Reconnu comme DATA_BRUT.xlsx :** "
                    + ("oui" if _diag["est_data_brut"] else
                       "non (le nom doit être exactement DATA_BRUT.xlsx pour la lecture de la feuille « Export »)")
                )
                st.write(f"**Colonnes du fichier :** {', '.join(map(str, _diag['colonnes_source'][:30]))}"
                         + (" …" if len(_diag["colonnes_source"]) > 30 else ""))
                st.write(f"**Colonnes reconnues :** {', '.join(_diag['colonnes_reconnues']) or 'aucune'}")
                st.write(
                    f"**Colonnes « Real -k » détectées :** {len(_diag['colonnes_reel'])} · "
                    f"**colonnes dates « M -k » :** {len(_diag['colonnes_date'])}"
                )
                st.write(
                    f"**Lignes lues :** {_diag['lignes_avant_filtre_article']} → "
                    f"**conservées après filtre article :** {_diag['lignes_conservees']}"
                )
                if _diag["exemples_articles"]:
                    st.write("**Exemples de valeurs d'article :** " + ", ".join(_diag["exemples_articles"]))
                if _diag["lignes_avant_filtre_article"] == 0:
                    st.info("Aucune ligne n'a été lue : vérifiez la feuille (« Export » pour DATA_BRUT.xlsx) et la ligne d'en-tête.")
                elif _diag["lignes_conservees"] == 0 and "article" not in _diag["colonnes_reconnues"]:
                    st.info("La colonne article n'est pas reconnue, donc toutes les lignes sont écartées. "
                            "En-têtes acceptés : Article, Articles, SKU, Code article, Désignation.")
                elif _diag["lignes_conservees"] == 0:
                    st.info("Toutes les lignes ont été écartées : articles vides, « Non renseigné », totaux ou catégories génériques.")
            st.caption(
                "Après correction du fichier ou d'un module : cliquez sur « Réinitialiser les imports de cette session » "
                "(barre latérale), puis menu ⋮ → « Clear cache », et réimportez."
            )
    st.stop()

df_brut = assurer_dimensions_filtres(df_brut, CATALOGUE_PAR_ARTICLE, TYPES)
# ✚ Sécurité finale : region toujours présente dans df_brut
df_brut["region"] = df_brut["agence"].map(region_depuis_agence)

csv_cumule = df_brut.to_csv(index=False).encode("utf-8-sig")
st.sidebar.download_button(
    "Télécharger l’historique cumulé (.csv)",
    data=csv_cumule,
    file_name="historique_cumule.csv",
    mime="text/csv",
    help="Réimportez ce fichier lors de votre prochaine session pour conserver l’historique mis à jour.",
)
st.sidebar.caption(
    f"Historique chargé : {len(df_brut):,} lignes · "
    f"{df_brut['annee'].nunique()} années · {df_brut['agence'].nunique()} agences."
)

df_brut["annee"] = pd.to_numeric(df_brut["annee"], errors="coerce").astype(int)
df_brut["mois"] = pd.to_numeric(df_brut["mois"], errors="coerce").astype(int)

cond_realise = (df_brut["annee"] < annee_cloture) | ((df_brut["annee"] == annee_cloture) & (df_brut["mois"] <= mois_cloture))
df_brut["nature"] = np.where(cond_realise, "Réalisé", "Prévision")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Moteur de Calcul SAAR")
activer_saar = st.sidebar.checkbox(
    "Activer la re-projection automatique SAAR",
    value=True,
    key="activer_saar_saisonnier",
)
afficher_previsions_historiques = st.sidebar.checkbox(
    "Afficher les prévisions historiques reconstituées",
    value=True,
    help=(
        "Prévisions simulées à partir des réalisés connus jusqu'à décembre de l'année précédente. "
        "Elles ne correspondent pas à des archives de prévisions réellement établies à l'époque."
    ),
)
taux_croissance_saar = st.sidebar.number_input(
    "Hausse minimale annuelle de la prévision (%)",
    min_value=1.0,
    value=1.0,
    step=0.5,
)
st.sidebar.caption(
    "Le réalisé à date est annualisé selon l'historique et les coefficients saisonniers du fichier, "
    "puis une hausse additionnelle de 20 % est appliquée aux prévisions de juin et décembre. "
    "Le volume annuel prévisionnel est au minimum en hausse de 1 % par rapport à l'année précédente "
    "(ou davantage selon le taux choisi)."
)

df_previsions_historiques = df_brut.iloc[0:0].copy()
df_previsions_toutes_annees = df_brut.iloc[0:0].copy()
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres Produits / Agences")

if st.sidebar.button("🔄 Réinitialiser les filtres"):
    for col, _ in FILTRES:
        if f"f_{col}" in st.session_state:
            del st.session_state[f"f_{col}"]
    st.rerun()

selections_filtres = {
    col: st.session_state.get(f"f_{col}", [])
    for col, _ in FILTRES
}

for col, label in FILTRES:
    if col not in df_brut.columns:
        continue

    options = options_filtre_cascade(
        df_brut,
        col,
        FILTRES,
        selections_filtres,
    )

    options = [
        o for o in (_normaliser_option(v, col) for v in options) if o is not None
    ]
    options_ref = _options_referentiel(col)
    options_ref = [
        o for o in (_normaliser_option(v, col) for v in options_ref) if o is not None
    ]

    if options_ref:
        options = list(set(options) | set(options_ref))

    if col == "agence":
        agences_presentes = set(options)
        options = [
            agence for agence in AGENCES_REFERENCE
            if agence in agences_presentes
        ]
    else:
        options = trier(options, col)

    if not options:
        continue

    cle = f"f_{col}"
    if cle in st.session_state:
        st.session_state[cle] = [v for v in st.session_state[cle] if v in options]
    
    choix = st.sidebar.multiselect(label, options, key=cle, placeholder="Tous")
    selections_filtres[col] = choix

d = df_brut.copy()
for col, _ in FILTRES:
    choix = selections_filtres[col]
    if choix:
        d = d[d[col].isin(choix)]

recherche = st.sidebar.text_input("🔎 Recherche article", "")
if recherche:
    d = d[d["article"].str.contains(recherche, case=False, na=False, regex=False)]

df_previsions_historiques = df_brut.iloc[0:0].copy()
df_previsions_toutes_annees = df_brut.iloc[0:0].copy()

if activer_saar:
    df_previsions_toutes_annees = reconstituer_previsions_historiques(
        df_brut,
        int(annee_cloture) + 1,
        float(taux_croissance_saar),
    )
    if afficher_previsions_historiques:
        df_previsions_historiques = df_previsions_toutes_annees.loc[
            df_previsions_toutes_annees["annee"].lt(annee_cloture)
        ].copy()
    
    nb_couples_saar = 0
    nb_profils_neutres = 0
    if annee_cible >= annee_cloture:
        for annee_projection in range(int(annee_cloture) + 1, int(annee_cible) + 1):
            df_brut, nb_couples_saar, nb_profils_neutres = appliquer_projection_saar(
                df_brut,
                int(annee_cloture),
                int(mois_cloture),
                annee_projection,
                float(taux_croissance_saar),
            )
            # ✚ Réinjecte region après projection
            df_brut["region"] = df_brut["agence"].map(region_depuis_agence)
    if annee_cible < annee_cloture:
        st.sidebar.warning("La projection SAAR s'applique à l'année de clôture ou aux années futures.")
    elif annee_cible == annee_cloture and mois_cloture == 12:
        st.sidebar.info("Aucun mois futur à projeter pour cette année de clôture.")
    elif nb_couples_saar == 0:
        st.sidebar.warning("Aucun réalisé à date ne permet de calculer une projection SAAR.")
    else:
        st.sidebar.success(f"Projection SAAR calculée pour {nb_couples_saar} couples agence/article.")
        if nb_profils_neutres:
            st.sidebar.info(
                f"Profil saisonnier neutre appliqué à {nb_profils_neutres} couples sans saisonnalité historique exploitable."
            )

for col, _ in FILTRES:
    choix = st.session_state.get(f"f_{col}", [])
    if choix and not df_previsions_historiques.empty and col in df_previsions_historiques.columns:
        df_previsions_historiques = df_previsions_historiques[
            df_previsions_historiques[col].isin(choix)
        ]
if recherche and not df_previsions_historiques.empty and "article" in df_previsions_historiques.columns:
    df_previsions_historiques = df_previsions_historiques[
        df_previsions_historiques["article"].str.contains(
            recherche, case=False, na=False, regex=False
        )
    ]

d_previsions_courbes = df_previsions_toutes_annees

d_tendance = pd.concat([d, df_previsions_historiques], ignore_index=True)
d_tendance["nature"] = d_tendance["nature"].replace(
    "Prévision reconstituée", "Prévision"
)

annees_reelles = sorted(
    int(annee)
    for annee in df_brut.loc[df_brut["nature"].eq("Réalisé"), "annee"].unique()
)
annees_debut_possibles = annees_reelles[:-1]
if annees_debut_possibles:
    st.markdown("### Indice de saisonnalité — période d’analyse")
    col_debut_annee, col_fin_annee = st.columns(2)
    annee_debut = col_debut_annee.selectbox(
        "Année début",
        options=annees_debut_possibles,
        index=0,
        key="saisonnalite_annee_debut",
    )
    annees_fin_possibles = [annee for annee in annees_reelles if annee > annee_debut]
    annee_fin_defaut = annees_fin_possibles[-1]
    if st.session_state.get("saisonnalite_annee_fin") not in annees_fin_possibles:
        st.session_state["saisonnalite_annee_fin"] = annee_fin_defaut
    annee_fin = col_fin_annee.selectbox(
        "Année fin",
        options=annees_fin_possibles,
        key="saisonnalite_annee_fin",
    )
    st.caption(
        f"Période inclusive : années {annee_debut} à {annee_fin}. "
        "L’indice est calculé sur les volumes réalisés : "
        "1,00 correspond à un mois moyen (moyenne des 12 mois)."
    )
    annees_indice = annees_completes_saisonnalite(
        d, int(annee_debut), int(annee_fin), int(annee_cloture), int(mois_cloture)
    )
    annees_exclues_indice = sorted(
        int(a)
        for a in d.loc[
            d["nature"].eq("Réalisé") & d["annee"].between(annee_debut, annee_fin),
            "annee",
        ].unique()
        if int(a) not in annees_indice
    )
    indices_saisonnalite = calculer_indices_saisonnalite(
        d,
        val,
        int(annee_debut),
        int(annee_fin),
        annee_cloture=int(annee_cloture),
        mois_cloture=int(mois_cloture),
    )
    if annees_indice:
        st.caption(
            "Années complètes retenues : "
            + ", ".join(map(str, annees_indice))
            + (
                " · Exclue(s) car incomplète(s) : "
                + ", ".join(
                    f"{a} (janv–{MOIS[int(mois_cloture) - 1]})"
                    for a in annees_exclues_indice
                )
                if annees_exclues_indice
                else ""
            )
            + "."
        )
    else:
        st.warning(
            "Aucune année complète (12 mois réalisés) dans la période choisie : "
            "l'indice saisonnier ne peut pas être calculé."
        )
else:
    indices_saisonnalite = pd.DataFrame()
    st.info(
        "Il faut des données réalisées sur au moins deux années pour afficher "
        "les indices de saisonnalité (année fin > année début)."
    )

d_cible = d[d["annee"] == annee_cible].copy()
if mois_cible_num:
    d_cible = d_cible[d_cible["mois"] == mois_cible_num]

vol_prev_cible = d_cible[val].sum()
vol_cumul_realise = d[(d["annee"] == annee_cloture) & (d["mois"] <= mois_cloture) & (d["nature"] == "Réalisé")][val].sum()

lib_p = f"Année entière {annee_cible}" if mois_cible_str == "Tous les mois" else f"{mois_cible_str} {annee_cible}"
lib_cumul = f"Cumul Réalisé YTD (Janv - {MOIS[mois_cloture-1].upper()} {annee_cloture})"

ANNEE_DEBUT_CUMUL = 2024

masque_realise_cumul = (
    d["nature"].eq("Réalisé")
    & d["annee"].ge(ANNEE_DEBUT_CUMUL)
    & (
        d["annee"].lt(annee_cloture)
        | (d["annee"].eq(annee_cloture) & d["mois"].le(mois_cloture))
    )
)
masque_prevision_cumul = (
    d["nature"].eq("Prévision")
    & d["annee"].eq(annee_cloture)
    & d["mois"].gt(mois_cloture)
)

vol_realise_a_date = float(d.loc[masque_realise_cumul, val].sum())
vol_prevision_cumul = float(d.loc[masque_prevision_cumul, val].sum())
vol_total_cumul = vol_realise_a_date + vol_prevision_cumul

mois_fin_realise = MOIS[mois_cloture - 1]
lib_periode_realise = f"{ANNEE_DEBUT_CUMUL} → {mois_fin_realise} {annee_cloture}"
lib_periode_prevision = (
    f"{MOIS[mois_cloture]} → déc {annee_cloture}"
    if mois_cloture < 12
    else "aucun mois restant"
)

k_realise, k_prevision, k_total = st.columns(3)
k_realise.metric(
    "Cumul réalisé à date",
    f"{nombre(vol_realise_a_date, dec)} {lib}",
    help=f"Réalisé du {lib_periode_realise}.",
)
k_prevision.metric(
    f"Cumul prévision ({lib_periode_prevision})",
    f"{nombre(vol_prevision_cumul, dec)} {lib}",
    help="Prévision des mois restants de l'année de clôture.",
)
k_total.metric(
    "Cumul total (réalisé + prévision)",
    f"{nombre(vol_total_cumul, dec)} {lib}",
    help="Somme du cumul réalisé à date et du cumul prévision.",
)
st.caption(
    f"Réalisé : {lib_periode_realise} · Prévision : {lib_periode_prevision} · "
    "Total = réalisé à date + prévision."
)

def libelle_realise_annee(annee: int) -> str:
    if annee < annee_cloture:
        return f"Réalisé {annee}"
    return f"Réalisé {annee} (janv–{mois_fin_realise})"

col_realise_cumul = "Cumul réalisé à date"
col_prevision_cumul = f"Prévision ({lib_periode_prevision})"
col_total_cumul = "Cumul total"
dim_detail = ["article", "agence", "segment", "produit", "parfum", "format"]

base_detail = d.loc[masque_realise_cumul | masque_prevision_cumul].copy()
if base_detail.empty:
    detail_cumuls = pd.DataFrame()
else:
    base_detail["colonne_cumul"] = np.where(
        base_detail["nature"].eq("Réalisé"),
        base_detail["annee"].map(libelle_realise_annee),
        col_prevision_cumul,
    )
    colonnes_annees = [
        libelle_realise_annee(a)
        for a in range(ANNEE_DEBUT_CUMUL, int(annee_cloture) + 1)
    ]
    detail_cumuls = (
        base_detail.pivot_table(
            index=dim_detail, columns="colonne_cumul", values=val, aggfunc="sum"
        )
        .fillna(0.0)
        .reindex(columns=[*colonnes_annees, col_prevision_cumul], fill_value=0.0)
    )
    detail_cumuls[col_realise_cumul] = detail_cumuls[colonnes_annees].sum(axis=1)
    detail_cumuls[col_total_cumul] = (
        detail_cumuls[col_realise_cumul] + detail_cumuls[col_prevision_cumul]
    )
    detail_cumuls = (
        detail_cumuls[
            [*colonnes_annees, col_realise_cumul, col_prevision_cumul, col_total_cumul]
        ]
        .sort_values(col_total_cumul, ascending=False)
        .reset_index()
    )


st.markdown("---")

tab_saisonnalite, tab_d = st.tabs([
    " Indice saisonnier",
    " Détail des cumuls & prévisions",
])

piv_comp = pd.DataFrame()
if not d_tendance.empty:
    piv_comp = d_tendance.pivot_table(
        index=["segment", "produit", "article"],
        columns=["annee", "nature"],
        values=val,
        aggfunc="sum"
    ).fillna(0.0)
    
    piv_comp.columns = [f"Volume {an} ({nat})" for an, nat in piv_comp.columns]
    
    col_prev = f"Volume {annee_cible} (Prévision)"
    annee_reference = (
        annee_cible
        if df_previsions_historiques["annee"].eq(annee_cible).any()
        else annee_cloture
    )
    col_ref = f"Volume {annee_reference} (Réalisé)"
    
    if col_prev in piv_comp.columns and col_ref in piv_comp.columns:
        piv_comp[f"Écart vs {annee_reference}"] = piv_comp[col_prev] - piv_comp[col_ref]
        piv_comp["Évolution (%)"] = variation(piv_comp[col_ref], piv_comp[col_prev])

with tab_d:
    st.subheader("Détail des cumuls et prévisions par article et agence")
    if detail_cumuls.empty:
        st.info(
            "Aucun réalisé à date ni prévision ne correspond aux filtres actifs. "
            "Vérifiez l'année de clôture, le mois pivot et les filtres."
        )
    else:
        st.caption(
            f"Réalisé {lib_periode_realise} · Prévision {lib_periode_prevision} · "
            f"Unité : {lib}. Triés par cumul total décroissant."
        )
        tableau(detail_cumuls.round(dec), height=520, hide_index=True)

    if not d_cible.empty:
        dim = ["agence", "segment", "produit", "parfum", "format", "article"]
        large = d_cible.pivot_table(index=dim, columns="periode", values=val, aggfunc="sum").fillna(0.0)
        periodes_ordonnees = [f"{annee_cible}-{mois:02d}" for mois in range(1, 13)]
        large = large.reindex(columns=periodes_ordonnees, fill_value=0.0)
        large.columns = [etiquette(p) for p in large.columns]
        large = large.reset_index()

with tab_saisonnalite:
    st.subheader("Indice de saisonnalité par mois")
    st.caption(
        "Coefficient = volume moyen du mois (années complètes retenues) ÷ volume "
        "mensuel moyen de ces années (12 mois). La moyenne des 12 coefficients vaut 1 ; "
        "1,40 signifie un mois 40 % au-dessus de la moyenne."
    )
    if indices_saisonnalite.empty:
        st.info(
            "Aucune période disponible : il faut au moins deux années avec des "
            "données réalisées."
        )
    elif indices_saisonnalite["Indice saisonnier"].notna().any():
        donnees_graphique_indice = indices_saisonnalite.set_index("Mois")[
            ["Indice saisonnier"]
        ]
        donnees_graphique_indice.index = pd.CategoricalIndex(
            donnees_graphique_indice.index,
            categories=donnees_graphique_indice.index.tolist(),
            ordered=True,
            name="Mois",
        )
        st.bar_chart(donnees_graphique_indice, height=400)
        
        st.markdown("#### Tableau détaillé des indices saisonniers")
        
        df_affiche = indices_saisonnalite.round(
            {"Volume moyen": dec, "Indice saisonnier": 2}
        )
        
        def mettre_en_gras(val):
            return 'font-weight: 700;'
            
        styled_df = df_affiche.style.map(mettre_en_gras)
        
        st.dataframe(styled_df, width="stretch", hide_index=True, height=450)
    else:
        st.info(
            "Aucun volume réalisé positif n'est disponible dans la période "
            "choisie avec les filtres actifs."
        )

st.markdown("---")
tampon = io.BytesIO()
with pd.ExcelWriter(tampon, engine="openpyxl") as xl:
    if not piv_comp.empty:
        df_export = piv_comp.copy()
        for col in df_export.select_dtypes(include=['object', 'string']).columns:
            df_export[col] = df_export[col].astype(str).str.slice(0, 32000)
            
        if df_export.shape[1] <= 16384:
            df_export.to_excel(xl, sheet_name="Projection")
        else:
            df_export.T.to_excel(xl, sheet_name="Projection")
            
    if not d_cible.empty:
        large.to_excel(xl, index=False, sheet_name="Détail Volumes")
    if not d.empty:
        d.to_excel(xl, index=False, sheet_name="Données Filtrées")
    if not xl.sheets:
        pd.DataFrame(
            {"Information": ["Aucune donnée disponible pour cette sélection."]}
        ).to_excel(xl, index=False, sheet_name="Informations")

st.download_button(
    f"📥 Télécharger la prévision ({lib})",
    data=tampon.getvalue(),
    file_name=f"Previsions_{annee_cible}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary"
)

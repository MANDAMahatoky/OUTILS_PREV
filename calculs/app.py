import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

# ==============================================================================
# CONFIGURATION DE LA PAGE ET DESIGN (DOMINANTE ROUGE)
# ==============================================================================
st.set_page_config(page_title="S&OP Prévisions", layout="wide", page_icon="🔴")

# Injection de CSS pour appliquer la charte graphique
st.markdown("""
<style>
    /* Fond principal très clair */
    .stApp {
        background-color: #FAFAFA;
    }
    
    /* Barre latérale : fond blanc avec bordure rouge épaisse */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 5px solid #D32F2F;
    }
    
    /* Titres en Rouge (dominante) */
    h1, h2, h3, h4 {
        color: #D32F2F !important;
    }
    
    /* Style des cartes Métriques (KPI) - Bordure et Ombre Rouges */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 2px solid #D32F2F;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 3px 3px 12px rgba(211, 47, 47, 0.2);
        text-align: center;
    }
    
    /* Chiffres des métriques en Rouge */
    [data-testid="stMetricValue"] {
        color: #D32F2F !important;
        font-size: 2rem !important;
        font-weight: 900;
    }
    
    /* Libellés des métriques en Vert */
    [data-testid="stMetricLabel"] {
        color: #2E7D32 !important;
        font-weight: bold;
    }
    
    /* Style des onglets : Actif = Rouge avec texte blanc */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #F0F2F6;
        color: #D32F2F;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        border: 1px solid #E0E0E0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
        border-bottom: 3px solid #2E7D32; /* Touche de vert */
        font-weight: bold;
    }
    
    /* Boutons rouges */
    .stButton>button {
        background-color: #D32F2F !important;
        color: white !important;
        border-radius: 5px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #D32F2F;'>📊 Moteur de Prévision S&OP</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #2E7D32; font-weight: bold;'>Planifiez vos volumes en toute sérénité (Indices, Momentum & CAGR)</p>", unsafe_allow_html=True)

# ==============================================================================
# RÉFÉRENTIEL INTÉGRÉ PAR DÉFAUT (Classeur2)
# ==============================================================================
REF_DEFAUT = [
    {"Article": "Booster Appel-Mix 50CL VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "Booster Tornado 50CL VER VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "Caprice Ananas 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Ananas 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Ananas 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 35 cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 35 cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"},
    {"Article": "Caprice Grenadine 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 35 cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"},
    {"Article": "Caprice Orange 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Caprice Bonbon Anglais 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "Caprice Citron 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Caprice Citron 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "Caprice Citron 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "Caprice Citron 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Tonic 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "Tonic 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "World Cola 100cl VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "World Cola 100cl WOCO VER", "Contenance (Cl)": 100, "Positionnement": "Milieu"},
    {"Article": "World Cola 150cl PET", "Contenance (Cl)": 150, "Positionnement": "Milieu"},
    {"Article": "World Cola 30cl VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "World Cola 30cl WOCO VER", "Contenance (Cl)": 30, "Positionnement": "Milieu"},
    {"Article": "World Cola 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "World Cola 35cl PET", "Contenance (Cl)": 35, "Positionnement": "Milieu"},
    {"Article": "World Cola 50cl PET", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "Beaufort 33 CL CAN", "Contenance (Cl)": 33, "Positionnement": "Premium"},
    {"Article": "Beaufort 33CL VER", "Contenance (Cl)": 33, "Positionnement": "Premium"},
    {"Article": "FRESH 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Entrée"},
    {"Article": "THB Fresh 33 cl VER", "Contenance (Cl)": 33, "Positionnement": "Entrée"},
    {"Article": "THB Fresh 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Entrée"},
    {"Article": "Gold 8 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold 8 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blanche 33cl VER", "Contenance (Cl)": 33, "Positionnement": "Premium"},
    {"Article": "Gold Blanche 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blanche 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blonde 33 cl VER", "Contenance (Cl)": 33, "Positionnement": "Premium"},
    {"Article": "Gold Blonde 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blonde 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Premium"},
    {"Article": "Gold Blonde 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Premium"},
    {"Article": "Queen s 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Premium"},
    {"Article": "THB Pilsener 33 cl VER", "Contenance (Cl)": 33, "Positionnement": "Milieu"},
    {"Article": "THB Pilsener 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Milieu"},
    {"Article": "THB Pilsener 65 cl VER", "Contenance (Cl)": 65, "Positionnement": "Milieu"},
    {"Article": "Cristal 100 cl VER", "Contenance (Cl)": 100, "Positionnement": "Entrée"},
    {"Article": "Cristal 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Entrée"},
    {"Article": "Cristal 30 cl VER", "Contenance (Cl)": 30, "Positionnement": "Entrée"},
    {"Article": "Cristal 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "Cristalline 100 cl PET", "Contenance (Cl)": 100, "Positionnement": "Entrée"},
    {"Article": "Cristalline 200 cl PET", "Contenance (Cl)": 200, "Positionnement": "Entrée"},
    {"Article": "Eau vive 150 cl PET", "Contenance (Cl)": 150, "Positionnement": "Entrée"},
    {"Article": "Eau vive 50 cl PET", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "Eau vive 50 cl VER", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "FOSA 50 cl CAN", "Contenance (Cl)": 50, "Positionnement": "Entrée"},
    {"Article": "XXL 30cl BOB VER", "Contenance (Cl)": 30, "Positionnement": "Entrée"},
    {"Article": "XXL 30cl VER", "Contenance (Cl)": 30, "Positionnement": "Entrée"},
    {"Article": "XXL 33 cl CAN", "Contenance (Cl)": 33, "Positionnement": "Entrée"},
    {"Article": "XXL 35cl PET", "Contenance (Cl)": 35, "Positionnement": "Entrée"}
]

# ==============================================================================
# MAPPING RÉGIONS
# ==============================================================================
MAPPING_REGIONS = {
    "11-Andranomahery": "Centre", "12-Antsirabe": "Centre",
    "01-Tanjombato": "Est", "09-Tamatave": "Est",
    "03-Usine-Diego": "Nord", "07-Majunga": "Nord", "18-Ambanja": "Nord", "19-Sambava": "Nord", "21-Nosy-Be": "Nord",
    "04-Tulear": "Sud", "05-Fianarantsoa": "Sud", "06-Ihosy": "Sud", "08-Manakara": "Sud", "23-Morondava": "Sud", "24-Fort-Dauphin": "Sud"
}

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
def charger_et_enrichir(ventes_bytes: bytes, ref_bytes: bytes = None) -> pd.DataFrame:
    if ref_bytes is not None:
        flux_ref = io.BytesIO(ref_bytes)
        df_ref = pd.read_excel(flux_ref, sheet_name="Ref actif")
        df_ref = df_ref.rename(columns={"Article": "article_original", "Positionnement": "positionnement", "Occasion": "occasion", "Contenance (Cl)": "contenance_cl"})
        df_ref = df_ref[["article_original", "positionnement", "occasion", "contenance_cl"]].copy()
    else:
        df_ref = pd.DataFrame(REF_DEFAUT)
        df_ref = df_ref.rename(columns={"Article": "article_original", "Contenance (Cl)": "contenance_cl", "Positionnement": "positionnement"})
        df_ref["occasion"] = "Non renseigné"
    
    df_ref["article_original"] = df_ref["article_original"].astype(str).str.strip()
    df_ref["cle_article"] = df_ref["article_original"].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    df_ref = df_ref.drop_duplicates(subset=["cle_article"]).reset_index(drop=True)

    flux_ventes = io.BytesIO(ventes_bytes)
    df_raw = pd.read_excel(flux_ventes, sheet_name=0, header=None)
    
    if detecter_format_pivote(df_raw):
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "volume_brut"])}
        df = df_raw.rename(columns=rename).copy()
        
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
        df["mois"] = df["mois"].apply(normaliser_mois)
        df["volume_brut"] = pd.to_numeric(df["volume_brut"], errors="coerce").fillna(0.0)
        
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

    df_enrichi = pd.merge(df_ref, df, on="cle_article", how="outer")
    
    df_enrichi["article"] = df_enrichi["article_original_x"].fillna(df_enrichi["article_original_y"])
    df_enrichi["annee"] = df_enrichi["annee"].fillna(2026).astype(int)
    df_enrichi["mois"] = df_enrichi["mois"].fillna(1).astype(int)
    df_enrichi["volume_brut"] = df_enrichi["volume_brut"].fillna(0.0)
    df_enrichi["agence"] = df_enrichi["agence"].fillna("Aucune vente")
    
    df_enrichi["contenance_cl"] = pd.to_numeric(df_enrichi["contenance_cl"], errors="coerce").fillna(100.0)
    df_enrichi.loc[df_enrichi["contenance_cl"] <= 0, "contenance_cl"] = 100.0
    
    df_enrichi["hl"] = df_enrichi["volume_brut"]
    df_enrichi["region"] = df_enrichi["agence"].map(MAPPING_REGIONS).fillna("Autre")
    
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
    
    return df_enrichi[["annee", "mois", "segment", "region", "produit", "agence", "hl", "volume_brut", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# ÉTAPES 4, 5.1 & 5.2 : CALCULS
# ==============================================================================
@st.cache_data(show_spinner="Calcul des prévisions...")
def calculer_modele(df_perimetre: pd.DataFrame, annee_min_histo: int, annee_max_histo: int, annee_cloture: int, mois_cutoff: int, annee_cible: int):
    
    df_limite = df_perimetre[(df_perimetre["annee"] < annee_cloture) | ((df_perimetre["annee"] == annee_cloture) & (df_perimetre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, None

    df_hist = df_realise[(df_realise["annee"] >= annee_min_histo) & (df_realise["annee"] <= annee_max_histo)].copy()
    if df_hist.empty: return None, None, None, None, None

    mois_par_annee = df_hist.groupby(['agence', 'article', 'annee'])['mois'].nunique().reset_index()
    annees_completes = mois_par_annee[mois_par_annee['mois'] == 12][['agence', 'article', 'annee']]
    df_hist_complet = df_hist.merge(annees_completes, on=['agence', 'article', 'annee'], how='inner')
    
    if df_hist_complet.empty: return None, None, None, None, None

    # INDICES
    vols = df_hist_complet.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols = vols.reindex(columns=range(1, 13), fill_value=0.0) 
    vols_mois_cumules = vols.groupby(['agence', 'article']).sum()
    vols_annuels_cumules = vols.sum(axis=1).groupby(['agence', 'article']).sum()
    indices = vols_mois_cumules.div(vols_annuels_cumules / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    table_indices = indices.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')
    table_indices['mois'] = table_indices['mois'].astype(int) 

    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    # MOMENTUM & BASE
    df_sarr_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_sarr_sorted[df_sarr_sorted['rang'] < 4].copy()
    
    resultats_momentum = []
    for (ag, art), group in df_derniers.groupby(['agence', 'article']):
        def get_val(rang, col): 
            return group[group['rang'] == rang][col].values[0] if len(group[group['rang'] == rang]) > 0 else 0

        sarr_m, sarr_m1, sarr_m2, sarr_m3 = get_val(0, 'SARR_HL'), get_val(1, 'SARR_HL'), get_val(2, 'SARR_HL'), get_val(3, 'SARR_HL')
        momentum = np.mean([sarr_m - sarr_m1, sarr_m1 - sarr_m2, sarr_m2 - sarr_m3])
        
        group_realise = df_realise[(df_realise['agence'] == ag) & (df_realise['article'] == art)]
        vol_annee_cloture = group_realise[group_realise['annee'] == annee_cloture]['hl'].sum()
        mois_ecoules = group_realise[group_realise['annee'] == annee_cloture]['mois'].nunique()
        base = vol_annee_cloture / mois_ecoules if mois_ecoules > 0 else 0.0
        
        info_art = group_realise.iloc[0]
        resultats_momentum.append({"Agence": ag, "Article": art, "Base_HL": base, "Momentum_HL": momentum, "Contenance": info_art['contenance_cl']})
        
    df_momentum = pd.DataFrame(resultats_momentum)

    # PRÉVISIONS
    resultats_previsions = []
    dict_realises = df_realise.groupby(['annee', 'mois', 'agence', 'article'])['hl'].sum().to_dict()

    for _, row in df_momentum.iterrows():
        ag, art, base, momentum, contenance = row['Agence'], row['Article'], row['Base_HL'], row['Momentum_HL'], row['Contenance']
        
        art_hist_complet = df_hist_complet[(df_hist_complet['article'] == art) & (df_hist_complet['agence'] == ag)]
        if not art_hist_complet.empty:
            a_deb, a_fin = art_hist_complet['annee'].min(), art_hist_complet['annee'].max()
            v_deb = art_hist_complet[art_hist_complet['annee'] == a_deb]['hl'].sum()
            v_fin = art_hist_complet[art_hist_complet['annee'] == a_fin]['hl'].sum()
            nb_ans = a_fin - a_deb
            cagr_val = ((v_fin / v_deb) ** (1 / nb_ans)) - 1 if nb_ans > 0 and v_deb > 0 and v_fin > 0 else 0.0
        else:
            cagr_val = 0.0

        for y in range(annee_cloture, annee_cible + 1):
            multiplicateur_cagr = (1 + cagr_val) ** (y - annee_cloture)
            for m in range(1, 13):
                coef_data = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]
                coef = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
                
                if y == annee_cloture and m <= mois_cutoff:
                    statut = "Réalisé"
                    val_hl = dict_realises.get((y, m, ag, art), 0.0)
                else:
                    statut = "Prévision"
                    val_hl = max(0.0, ((coef * base) + momentum) * multiplicateur_cagr)
                    
                val_cols = val_hl * (10000 / contenance)
                
                resultats_previsions.append({
                    "annee": y, "mois": m, "agence": ag, "article": art, "Date": f"{MOIS_NOMS[m-1]}-{str(y)[-2:]}",
                    "Statut": statut, "Indice": coef, "Base_HL": base, "Momentum_HL": momentum, "CAGR (%)": cagr_val * 100, 
                    "Volume_HL": val_hl, "Volume_Cols": val_cols
                })

    df_previsions = pd.DataFrame(resultats_previsions)
    return table_indices, df_sarr, df_momentum, df_hist, df_previsions

# ==============================================================================
# INTERFACE STREAMLIT (ZONE DE TELECHARGEMENT)
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    fichier_ventes = st.file_uploader("1. Fichier des ventes (DATA_BRUT.xlsx)", type=["xlsx"])
with col2:
    fichier_ref = st.file_uploader("2. Fichier Référentiel (Optionnel)", type=["xlsx"], help="Laissez vide pour utiliser le référentiel intégré.")

if fichier_ventes is not None:
    
    df_enrichi = charger_et_enrichir(fichier_ventes.getvalue(), fichier_ref.getvalue() if fichier_ref is not None else None)

    # =========================================================================
    # FILTRES (DANS DES EXPANDERS POUR UN DESIGN PROPRE)
    # =========================================================================
    with st.sidebar.expander("🔍 Filtres Données", expanded=True):
        regions_dispo = sorted([r for r in df_enrichi["region"].unique() if pd.notna(r) and r != "Aucune vente"])
        sel_regions = st.multiselect("🗺️ Région", options=regions_dispo, placeholder="Toutes")
        
        positionnements_dispo = sorted([p for p in df_enrichi["positionnement"].unique() if pd.notna(p)])
        sel_positionnements = st.multiselect("🏷️ Positionnement", options=positionnements_dispo, placeholder="Tous")
        
        contenances_dispo = sorted([int(c) for c in df_enrichi["contenance_cl"].unique() if pd.notna(c)])
        sel_contenances = st.multiselect("📏 Contenance (cl)", options=contenances_dispo, placeholder="Toutes")
        
        segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
        sel_segments = st.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
        
        # Mise à jour dynamique
        df_temp = df_enrichi.copy()
        if sel_regions: df_temp = df_temp[df_temp["region"].isin(sel_regions)]
        if sel_positionnements: df_temp = df_temp[df_temp["positionnement"].isin(sel_positionnements)]
        if sel_contenances: df_temp = df_temp[df_temp["contenance_cl"].isin(sel_contenances)]
        if sel_segments: df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
        
        articles_dispo = sorted(df_temp["article"].unique())
        sel_articles = st.multiselect("🛒 Article", options=articles_dispo, placeholder="Tous")
        
        agences_dispo = sorted([a for a in df_temp["agence"].unique() if a != "Aucune vente"])
        sel_agences = st.multiselect("🏢 Agence", options=agences_dispo, placeholder="Toutes")

    with st.sidebar.expander("📅 Paramètres Temporels", expanded=True):
        annee_min_reelle = int(df_enrichi["annee"].min()) if not df_enrichi.empty else 2020
        annee_max_reelle = int(df_enrichi["annee"].max()) if not df_enrichi.empty else 2026
        
        annee_min_histo = st.number_input("Année Min Historique", min_value=2015, max_value=2030, value=2022)
        annee_max_histo = st.number_input("Année Max Historique", min_value=annee_min_histo, max_value=2030, value=2025)
        annee_cloture = st.number_input("Année de Clôture", min_value=2020, max_value=2030, value=2026)
        mois_cutoff = st.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=9, format_func=lambda m: f"{m} - {MOIS_NOMS[m-1]}")
        annee_cible = st.number_input("Année Cible (Fin Prévisions)", min_value=annee_cloture, max_value=2035, value=2027)

    with st.sidebar.expander("⚙️ Affichage", expanded=True):
        unite_affichage = st.radio("Unité d'affichage", options=["HL", "Cols"], index=0)

    # Application finale
    df_perimetre = df_enrichi.copy()
    if sel_regions: df_perimetre = df_perimetre[df_perimetre["region"].isin(sel_regions)]
    if sel_positionnements: df_perimetre = df_perimetre[df_perimetre["positionnement"].isin(sel_positionnements)]
    if sel_contenances: df_perimetre = df_perimetre[df_perimetre["contenance_cl"].isin(sel_contenances)]
    if sel_segments: df_perimetre = df_perimetre[df_perimetre["segment"].isin(sel_segments)]
    if sel_articles: df_perimetre = df_perimetre[df_perimetre["article"].isin(sel_articles)]
    if sel_agences: df_perimetre = df_perimetre[df_perimetre["agence"].isin(sel_agences)]

    # --- CALCULS ---
    table_indices, df_sarr, df_momentum, df_hist, df_previsions = calculer_modele(
        df_perimetre, annee_min_histo, annee_max_histo, annee_cloture, mois_cutoff, annee_cible
    )

    if table_indices is None:
        st.warning("⚠️ Aucune année complète (12 mois) trouvée dans l'intervalle historique.")
        st.stop()

    # ONGLETS
    tab_prev, tab_indices, tab_sarr, tab_diag = st.tabs([
        "🚀 Prévisions & Atterrissage", "📊 Indices", "📈 SARR Global", "🩺 Diagnostic Données"
    ])

    if unite_affichage == "Cols":
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"] * (10000 / df_sarr["contenance_cl"].replace(0, 100))
        df_sarr["Vol_Aff"] = df_sarr["hl"] * (10000 / df_sarr["contenance_cl"].replace(0, 100))
        col_prev_aff = "Volume_Cols"
    else:
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"]
        df_sarr["Vol_Aff"] = df_sarr["hl"]
        col_prev_aff = "Volume_HL"

    with tab_prev:
        st.markdown(f"### 🛬 Atterrissage {annee_cloture} (Réalisé + Prévisions)")
        
        df_atterrissage = df_previsions[df_previsions['annee'] == annee_cloture]
        
        # KPI Cards stylisées avec CSS
        col_at1, col_at2, col_at3 = st.columns(3)
        with col_at1:
            total_at = df_atterrissage[col_prev_aff].sum()
            st.metric(label=f"Total Global {annee_cloture}", value=f"{total_at:,.2f} {unite_affichage}")
        with col_at2:
            total_realise = df_atterrissage[df_atterrissage['Statut'] == 'Réalisé'][col_prev_aff].sum()
            st.metric(label="Déjà Réalisé (Janv - Cutoff)", value=f"{total_realise:,.2f} {unite_affichage}")
        with col_at3:
            total_prevision = df_atterrissage[df_atterrissage['Statut'] == 'Prévision'][col_prev_aff].sum()
            st.metric(label="Reste à Prévoir (Post-Cutoff)", value=f"{total_prevision:,.2f} {unite_affichage}")

        st.markdown("---")
        
        st.markdown("#### 📦 Détail de l'atterrissage par Article")
        df_atterrissage_sku = df_atterrissage.pivot_table(
            index='article', columns='Statut', values=col_prev_aff, aggfunc='sum'
        ).fillna(0)
        
        if 'Réalisé' not in df_atterrissage_sku.columns: df_atterrissage_sku['Réalisé'] = 0
        if 'Prévision' not in df_atterrissage_sku.columns: df_atterrissage_sku['Prévision'] = 0
            
        df_atterrissage_sku['Total'] = df_atterrissage_sku['Réalisé'] + df_atterrissage_sku['Prévision']
        df_atterrissage_sku = df_atterrissage_sku.sort_values('Total', ascending=False)
        
        st.dataframe(
            df_atterrissage_sku,
            column_config={
                "article": "Article",
                "Réalisé": st.column_config.NumberColumn(f"Réalisé ({unite_affichage})", format="%.2f"),
                "Prévision": st.column_config.NumberColumn(f"Prévision ({unite_affichage})", format="%.2f"),
                "Total": st.column_config.NumberColumn(f"Total ({unite_affichage})", format="%.2f")
            },
            use_container_width=True
        )

        st.markdown("---")
        
        st.subheader(f"📅 Prévisions Mensuelles jusqu'en {annee_cible}")
        
        pivot_mensuel = df_previsions.pivot_table(
            index=['annee', 'agence', 'article'], columns='mois', values=col_prev_aff, aggfunc='sum'
        ).fillna(0)
        pivot_mensuel.columns = [MOIS_NOMS[c-1] for c in pivot_mensuel.columns]
        pivot_mensuel['Total Année'] = pivot_mensuel.sum(axis=1)
        
        st.dataframe(pivot_mensuel, use_container_width=True)
        
        with st.expander("Voir le détail mensuel complet"):
            st.dataframe(
                df_previsions[["annee", "mois", "Date", "Statut", "agence", "article", "Indice", "Base_HL", "Momentum_HL", "CAGR (%)", col_prev_aff]].sort_values(["annee", "mois", "agence", "article"]),
                column_config={
                    "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                    "Base_HL": st.column_config.NumberColumn("Base (HL)", format="%.2f"),
                    "Momentum_HL": st.column_config.NumberColumn("Momentum (HL)", format="%.2f"),
                    "CAGR (%)": st.column_config.NumberColumn("CAGR (%)", format="%.2f"),
                    col_prev_aff: st.column_config.NumberColumn(f"Volume ({unite_affichage})", format="%.2f"),
                },
                use_container_width=True, height=400
            )

    with tab_indices:
        st.subheader("Table des Indices de Saisonnalité")
        pivot_indices = table_indices.pivot_table(index=['agence', 'article'], columns='mois', values='Indice', aggfunc='first').fillna(1.0)
        pivot_indices.columns = [MOIS_NOMS[c-1] for c in pivot_indices.columns]
        st.dataframe(pivot_indices, use_container_width=True)

    with tab_sarr:
        st.subheader(f"Table du SARR Global (en {unite_affichage})")
        st.dataframe(
            df_sarr[["annee", "mois", "agence", "article", "Vol_Aff", "Indice", "SARR_Aff"]].sort_values(["annee", "mois", "agence", "article"]),
            column_config={
                "Vol_Aff": st.column_config.NumberColumn(f"Volume ({unite_affichage})", format="%.2f"),
                "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                "SARR_Aff": st.column_config.NumberColumn(f"SARR ({unite_affichage})", format="%.2f")
            },
            use_container_width=True, height=500
        )

    with tab_diag:
        st.subheader("🩺 Diagnostic : Volumes Historiques")
        df_diag = df_perimetre.groupby(['annee', 'mois', 'region', 'agence', 'article', 'contenance_cl', 'positionnement'])[['hl']].sum().reset_index()
        df_diag = df_diag[df_diag['hl'] > 0].sort_values(['annee', 'mois', 'region', 'agence', 'article'])
        st.dataframe(df_diag, use_container_width=True)

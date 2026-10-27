import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Moteur de Prévision S&OP", layout="wide")
st.title("Moteur de Prévision S&OP (Étapes 1 à 5)")

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
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "hl", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# ÉTAPES 4 & 5 : CALCULS (INDICES VERROUILLÉS, SARR, MOMENTUM, PREVISIONS)
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices et prévisions...")
def calculer_previsions_excel(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, annee_cible: int, mois_cible: int, fenetre_histo: str, methode_coef: str):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 1. Historique strict (on n'inclut JAMAIS l'année de clôture ici)
    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    df_ytd = df_realise[df_realise["annee"] == annee_cloture].copy()
    
    if df_hist.empty: df_hist = df_ytd.copy()

    # Filtrage de la fenêtre historique
    annee_max = annee_cloture - 1
    if fenetre_histo == "3 dernières années":
        annee_min = annee_max - 2
    elif fenetre_histo == "2 dernières années":
        annee_min = annee_max - 1
    else:
        annee_min = df_hist['annee'].min()
        
    df_hist = df_hist[df_hist['annee'] >= annee_min].copy()

    # 2. Calcul des INDICES FINAUX (une seule fois, sur l'historique)
    vols = df_hist.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols_annuels = vols.sum(axis=1)
    
    if methode_coef == "Moyenne des Ratios":
        ratios = vols.div(vols_annuels / 12.0, axis=0).replace([np.inf, -np.inf], np.nan)
        indices = ratios.groupby(['agence', 'article']).mean().fillna(1.0)
    else:
        vols_mois_cumules = vols.groupby(['agence', 'article']).sum()
        vols_annuels_cumules = vols_annuels.groupby(['agence', 'article']).sum()
        indices = vols_mois_cumules.div(vols_annuels_cumules / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    table_indices = indices.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')

    # 3. Calcul du SARR Historique
    df_sarr_hist = df_hist.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr_hist['Indice'] = df_sarr_hist['Indice'].fillna(1.0)
    df_sarr_hist['SARR_HL'] = df_sarr_hist['hl'] / df_sarr_hist['Indice'].replace(0, 1.0)

    # 4. Calcul du Momentum et Base (uniquement sur l'historique réel)
    df_sarr_sorted = df_sarr_hist.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_sarr_sorted[df_sarr_sorted['rang'] < 4].copy()
    
    resultats_previsions = []
    
    for (ag, art), group in df_derniers.groupby(['agence', 'article']):
        sarr_m = group[group['rang'] == 0]['SARR_HL'].values[0] if len(group[group['rang'] == 0]) > 0 else 0
        sarr_m1 = group[group['rang'] == 1]['SARR_HL'].values[0] if len(group[group['rang'] == 1]) > 0 else 0
        sarr_m2 = group[group['rang'] == 2]['SARR_HL'].values[0] if len(group[group['rang'] == 2]) > 0 else 0
        sarr_m3 = group[group['rang'] == 3]['SARR_HL'].values[0] if len(group[group['rang'] == 3]) > 0 else 0
        
        var1 = sarr_m - sarr_m1
        var2 = sarr_m1 - sarr_m2
        var3 = sarr_m2 - sarr_m3
        momentum = np.mean([var1, var2, var3])
        
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        
        info_art = df_ytd[(df_ytd['agence'] == ag) & (df_ytd['article'] == art)].iloc[0] if len(df_ytd[(df_ytd['agence'] == ag) & (df_ytd['article'] == art)]) > 0 else None
        if info_art is None: continue
        
        for y in range(annee_cloture, annee_cible + 1):
            for m in range(1, 13):
                if y == annee_cloture and m <= mois_cutoff: continue
                if y == annee_cible and m > mois_cible: break
                
                coef_data = table_indices[(table_indices['agence'] == ag) & (table_indices['article'] == art) & (table_indices['mois'] == m)]
                coef = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
                
                prev_hl = (coef * base) + momentum
                prev_hl = max(0.0, prev_hl)
                
                resultats_previsions.append({
                    "agence": ag, "article": art, "annee": y, "mois": m,
                    "Date": f"{MOIS_NOMS[m-1]}-{str(y)[-2:]}",
                    "Indice": coef, "Base_HL": base, "Momentum_HL": momentum,
                    "Prevision_HL": prev_hl
                })
                
    df_previsions = pd.DataFrame(resultats_previsions)
    
    # On renvoie aussi la table des indices avec les vraies valeurs pour l'audit
    # et on renvoie le sarr pour la vue glissante
    df_sarr_full = pd.concat([df_sarr_hist, df_ytd.merge(table_indices, on=['agence', 'article', 'mois'], how='left')], ignore_index=True)
    df_sarr_full['Indice'] = df_sarr_full['Indice'].fillna(1.0)
    df_sarr_full['SARR_HL'] = df_sarr_full['hl'] / df_sarr_full['Indice'].replace(0, 1.0)
    
    return table_indices, df_sarr_full, df_previsions

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

    st.sidebar.header("🔍 Filtres")
    segments_dispo = sorted([s for s in df_enrichi["segment"].unique() if pd.notna(s)])
    sel_segments = st.sidebar.multiselect("📦 Segment", options=segments_dispo, placeholder="Tous")
    
    df_temp = df_enrichi.copy()
    if sel_segments: df_temp = df_temp[df_temp["segment"].isin(sel_segments)]
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
    mois_cutoff = st.sidebar.selectbox("Mois de Cutoff (M)", options=list(range(1, 13)), index=9, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")
    
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Cible des Prévisions")
    annee_cible = st.sidebar.number_input("Année Cible", min_value=2026, max_value=2035, value=2027)
    mois_cible = st.sidebar.selectbox("Mois Cible", options=list(range(1, 13)), index=11, format_func=lambda m: f"{m} - {['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'][m-1]}")

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Options de Calcul")
    fenetre_histo = st.sidebar.radio("Période pour les Coefs", options=["Tout l'historique", "3 dernières années", "2 dernières années"], index=0)
    methode_coef = st.sidebar.radio("Méthode de calcul", options=["Ratio des Sommes", "Moyenne des Ratios"], index=0)
    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["HL", "Unités"], index=0)

    # --- CALCULS ---
    table_indices, df_sarr, df_previsions = calculer_previsions_excel(df_perimetre, annee_cloture, mois_cutoff, annee_cible, mois_cible, fenetre_histo, methode_coef)

    if df_previsions.empty or df_sarr.empty:
        st.warning("⚠️ Aucune donnée calculée. Veuillez vérifier vos filtres et vos dates de Cutoff.")
        st.stop()

    st.success(f"✅ Coefficients verrouillés (Étape 4). Prévisions calculées.")
    
    tab_verif, tab_detail, tab_bilan = st.tabs([
        "🔍 Vérification (Vol / Coef / SARR)",
        "🚀 Détail des Prévisions", 
        "📊 Bilan Annuel (TCD)"
    ])

    # --- CONVERSION POUR L'AFFICHAGE ---
    if unite_affichage == "Unités":
        df_sarr["Vol_Aff"] = df_sarr["hl"] * (10000 / df_sarr["contenance_cl"].replace(0, 100))
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"] * (10000 / df_sarr["contenance_cl"].replace(0, 100))
        
        conte_map = df_perimetre.drop_duplicates('article').set_index('article')['contenance_cl']
        df_previsions["Prev_Aff"] = df_previsions.apply(lambda r: r["Prevision_HL"] * (10000 / conte_map.get(r["article"], 100)), axis=1)
        df_previsions["Base_Aff"] = df_previsions.apply(lambda r: r["Base_HL"] * (10000 / conte_map.get(r["article"], 100)), axis=1)
        df_previsions["Momentum_Aff"] = df_previsions.apply(lambda r: r["Momentum_HL"] * (10000 / conte_map.get(r["article"], 100)), axis=1)
        label = "Unités"
    else:
        df_sarr["Vol_Aff"] = df_sarr["hl"]
        df_sarr["SARR_Aff"] = df_sarr["SARR_HL"]
        df_previsions["Prev_Aff"] = df_previsions["Prevision_HL"]
        df_previsions["Base_Aff"] = df_previsions["Base_HL"]
        df_previsions["Momentum_Aff"] = df_previsions["Momentum_HL"]
        label = "HL"

    with tab_verif:
        st.subheader(f"Vérification des SARR (en {label})")
        st.write("Les coefficients sont ceux de l'Étape 4. Comparez la ligne M-1, M-2... avec votre Excel.")
        
        df_filtre = df_sarr.copy()
        if sel_agences: df_filtre = df_filtre[df_filtre["agence"].isin(sel_agences)]
        if sel_articles: df_filtre = df_filtre[df_filtre["article"].isin(sel_articles)]
        
        articles_uniques = df_filtre[['agence', 'article']].drop_duplicates()
        df_agg = df_filtre.groupby(['agence', 'article', 'annee', 'mois']).agg(
            vol=('Vol_Aff', 'sum'), sarr=('SARR_Aff', 'sum'), coef=('Indice', 'mean')
        ).reset_index()
        
        resultats = []
        for _, row in articles_uniques.iterrows():
            ag, art = row['agence'], row['article']
            ligne = {"Agence": ag, "Article": art}
            
            for i in range(1, 5): 
                m = mois_cutoff - i
                y = annee_cloture
                if m <= 0:
                    m += 12
                    y -= 1
                
                nom_mois = MOIS_NOMS[m-1].capitalize()
                ligne[f"Date M-{i}"] = f"{nom_mois[:3]}-{str(y)[-2:]}"
                
                data = df_agg[(df_agg['agence'] == ag) & (df_agg['article'] == art) & (df_agg['annee'] == y) & (df_agg['mois'] == m)]
                
                if not data.empty:
                    vol, coef, sarr = data['vol'].values[0], data['coef'].values[0], data['sarr'].values[0]
                else:
                    vol, coef, sarr = 0.0, 1.0, 0.0
                    
                ligne[f"Vol M-{i}"] = vol
                ligne[f"Coef M-{i}"] = coef
                ligne[f"SARR M-{i}"] = sarr
            
            resultats.append(ligne)
            
        df_verif = pd.DataFrame(resultats)
        
        if not df_verif.empty:
            cols_to_show = ["Agence", "Article"]
            for i in range(1, 5): 
                cols_to_show.extend([f"Vol M-{i}", f"Coef M-{i}", f"SARR M-{i}"])
            
            cols_to_show = [c for c in cols_to_show if c in df_verif.columns]
            
            format_dict = {}
            for col in cols_to_show:
                if "SARR" in col or "Vol" in col:
                    format_dict[col] = "{:,.1f}"
                elif "Coef" in col:
                    format_dict[col] = "{:.2f}"
            
            st.dataframe(df_verif[cols_to_show].style.format(format_dict), use_container_width=True, height=400)

    with tab_detail:
        st.subheader(f"Détail mensuel des Prévisions (en {label})")
        st.dataframe(
            df_previsions[["annee", "mois", "Date", "agence", "article", "Indice", "Base_Aff", "Momentum_Aff", "Prev_Aff"]].sort_values(["annee", "mois", "agence", "article"]),
            column_config={
                "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                "Base_Aff": st.column_config.NumberColumn("Base", format="%.0f"),
                "Momentum_Aff": st.column_config.NumberColumn("Momentum", format="%.0f"),
                "Prev_Aff": st.column_config.NumberColumn("Prévision", format="%.0f"),
            },
            use_container_width=True
        )

    with tab_bilan:
        st.subheader(f"Bilan Annuel {annee_cible} (en {label})")
        df_annee = df_previsions[df_previsions["annee"] == annee_cible]
        if not df_annee.empty:
            pivot_annuel = pd.pivot_table(df_annee, values="Prev_Aff", index="article", columns="agence", aggfunc="sum", margins=True, margins_name="Total general").fillna(0)
            st.dataframe(pivot_annuel.style.format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("Aucune prévision pour cette année.")

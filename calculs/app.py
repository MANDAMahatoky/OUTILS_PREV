import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata
import altair as alt

st.set_page_config(page_title="Étapes 1 à 5 : S&OP", layout="wide")
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
    return df_enrichi[["annee", "mois", "segment", "produit", "agence", "hl", "volume_unites", "article", "positionnement", "occasion", "contenance_cl"]]

# ==============================================================================
# ÉTAPES 4 & 5 : INDICES, SARR & PRÉVISIONS
# ==============================================================================
@st.cache_data(show_spinner="Calcul des indices, SARR et prévisions...")
def calculer_previsions_globales(df_perimetre: pd.DataFrame, annee_cloture: int, mois_cutoff: int, annee_cible: int, mois_cible: int):
    df_realise = df_perimetre[df_perimetre["annee"] <= annee_cloture].copy()
    if df_realise.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_hist = df_realise[df_realise["annee"] < annee_cloture].copy()
    df_ytd = df_realise[df_realise["annee"] == annee_cloture].copy()
    if df_hist.empty: df_hist = df_ytd.copy()

    # 1. Calcul des indices initiaux
    vols_init = df_hist.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols_annuels_init = vols_init.sum(axis=1)
    vols_mois_cumules_init = vols_init.groupby(['agence', 'article']).sum()
    vols_annuels_cumules_init = vols_annuels_init.groupby(['agence', 'article']).sum()
    indices_initiaux = vols_mois_cumules_init.div(vols_annuels_cumules_init / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    table_indices_initiaux = indices_initiaux.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')
    
    # 2. Projection fin d'année N
    df_projete_fin_n = df_ytd.copy()
    ytd_totaux = df_ytd.groupby(['agence', 'article']).agg(vol_ytd=('hl', 'sum')).reset_index()
    for _, row in ytd_totaux.iterrows():
        ag, art = row['agence'], row['article']
        coefs_ecoules = table_indices_initiaux[(table_indices_initiaux['agence'] == ag) & (table_indices_initiaux['article'] == art) & (table_indices_initiaux['mois'] <= mois_cutoff)]['Indice'].sum()
        if coefs_ecoules == 0: coefs_ecoules = mois_cutoff
        vol_annuel_proj = (row['vol_ytd'] / coefs_ecoules) * 12
        
        for m in range(mois_cutoff + 1, 13):
            # FIX : Sécurité si la valeur n'existe pas
            coef_data = table_indices_initiaux[(table_indices_initiaux['agence'] == ag) & (table_indices_initiaux['article'] == art) & (table_indices_initiaux['mois'] == m)]
            coef_mois = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
            
            vol_projete = (vol_annuel_proj / 12) * coef_mois
            info_art = df_ytd[(df_ytd['agence'] == ag) & (df_ytd['article'] == art)].iloc[0]
            df_projete_fin_n = pd.concat([df_projete_fin_n, pd.DataFrame([{
                'annee': annee_cloture, 'mois': m, 'segment': info_art['segment'], 'produit': info_art['produit'], 
                'agence': ag, 'hl': vol_projete, 'volume_unites': vol_projete * (10000 / info_art['contenance_cl']), 
                'article': art, 'positionnement': info_art['positionnement'], 'occasion': info_art['occasion'], 'contenance_cl': info_art['contenance_cl']
            }])], ignore_index=True)
            
    df_ytd_complet = pd.concat([df_ytd, df_projete_fin_n], ignore_index=True).drop_duplicates(subset=['annee', 'mois', 'agence', 'article'])
    
    # 3. Calcul des indices FINAUX
    df_global_hist = pd.concat([df_hist, df_ytd_complet], ignore_index=True)
    vols_final = df_global_hist.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0)
    vols_annuels_final = vols_final.sum(axis=1)
    vols_mois_cumules_final = vols_final.groupby(['agence', 'article']).sum()
    vols_annuels_cumules_final = vols_annuels_final.groupby(['agence', 'article']).sum()
    indices_finaux = vols_mois_cumules_final.div(vols_annuels_cumules_final / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    table_indices_finaux = indices_finaux.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')

    # 4. Calcul du SARR
    df_sarr = df_global_hist.merge(table_indices_finaux, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)
    df_sarr['SARR_Unites'] = df_sarr['volume_unites'] / df_sarr['Indice'].replace(0, 1.0)
    
    # 5. Calcul du Momentum, Base et Prévisions
    df_sarr_sorted = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
    df_sarr_sorted['rang'] = df_sarr_sorted.groupby(['agence', 'article']).cumcount(ascending=False)
    df_derniers = df_sarr_sorted[df_sarr_sorted['rang'] < 4].copy()
    
    resultats_previsions = []
    resultats_audit = []
    
    for (ag, art), group in df_derniers.groupby(['agence', 'article']):
        sarr_m = group[group['rang'] == 0]['SARR_Unites'].values[0] if len(group[group['rang'] == 0]) > 0 else 0
        sarr_m1 = group[group['rang'] == 1]['SARR_Unites'].values[0] if len(group[group['rang'] == 1]) > 0 else 0
        sarr_m2 = group[group['rang'] == 2]['SARR_Unites'].values[0] if len(group[group['rang'] == 2]) > 0 else 0
        sarr_m3 = group[group['rang'] == 3]['SARR_Unites'].values[0] if len(group[group['rang'] == 3]) > 0 else 0
        
        var1 = sarr_m - sarr_m1
        var2 = sarr_m1 - sarr_m2
        var3 = sarr_m2 - sarr_m3
        momentum = np.mean([var1, var2, var3])
        
        moy_3_mois = np.mean([sarr_m1, sarr_m2, sarr_m3])
        base = max(sarr_m, moy_3_mois)
        
        resultats_audit.append({
            "Agence": ag, "Article": art, 
            "SARR M": sarr_m, "SARR M-1": sarr_m1, "SARR M-2": sarr_m2, "SARR M-3": sarr_m3,
            "Moyenne M-1,M-2,M-3": moy_3_mois, "Base Retenue": base, "Momentum": momentum
        })
        
        info_art = df_ytd[(df_ytd['agence'] == ag) & (df_ytd['article'] == art)].iloc[0] if len(df_ytd[(df_ytd['agence'] == ag) & (df_ytd['article'] == art)]) > 0 else None
        if info_art is None: continue
        contenance = info_art['contenance_cl']
        
        for y in range(annee_cloture, annee_cible + 1):
            for m in range(1, 13):
                if y == annee_cloture and m <= mois_cutoff: continue
                if y == annee_cible and m > mois_cible: break
                
                # FIX : Sécurité pour les indices
                coef_data = table_indices_finaux[(table_indices_finaux['agence'] == ag) & (table_indices_finaux['article'] == art) & (table_indices_finaux['mois'] == m)]
                coef = coef_data['Indice'].values[0] if not coef_data.empty else 1.0
                
                prev_unites = (coef * base) + momentum
                prev_unites = max(0.0, prev_unites)
                prev_hl = prev_unites * (contenance / 10000)
                
                resultats_previsions.append({
                    "agence": ag, "article": art, "annee": y, "mois": m,
                    "Date": f"{MOIS_NOMS[m-1]}-{str(y)[-2:]}",
                    "Indice": coef, "Base": base, "Momentum": momentum,
                    "Prevision_HL": prev_hl, "Prevision_Unites": prev_unites
                })
                
    df_previsions = pd.DataFrame(resultats_previsions)
    df_audit = pd.DataFrame(resultats_audit)
    
    return table_indices_finaux, df_sarr, df_previsions, df_audit

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

    unite_affichage = st.sidebar.radio("Unité d'affichage", options=["Unités (Excel)", "HL (Fichier)"], index=0)

    table_indices, df_sarr, df_previsions, df_audit = calculer_previsions_globales(df_perimetre, annee_cloture, mois_cutoff, annee_cible, mois_cible)

    st.success(f"✅ Étapes 1 à 5 complétées. Prévisions calculées jusqu'à {MOIS_NOMS[mois_cible-1]} {annee_cible}.")
    
    tab_verif, tab_bilan, tab_detail, tab_sarr = st.tabs([
        "🔍 Vérification vs Excel (Base & Momentum)",
        "📅 Bilan Annuel (Total general)",
        "🚀 Détail des Prévisions (Étape 5)", 
        "🧮 Table du SARR (Étape 4)"
    ])

    col_val = "Prevision_Unites" if unite_affichage == "Unités (Excel)" else "Prevision_HL"

    with tab_verif:
        st.subheader("🔍 Audit des formules (Base & Momentum)")
        st.write("Voici les 4 derniers SARR utilisés par le moteur. Comparez ces chiffres avec les colonnes `SARR M-1` à `M-4` de votre Excel. S'ils sont identiques, alors la prévision finale sera identique.")
        
        if not df_audit.empty:
            st.dataframe(
                df_audit,
                column_config={
                    "SARR M": st.column_config.NumberColumn("SARR M (Dernier)", format="%.2f"),
                    "SARR M-1": st.column_config.NumberColumn("SARR M-1", format="%.2f"),
                    "SARR M-2": st.column_config.NumberColumn("SARR M-2", format="%.2f"),
                    "SARR M-3": st.column_config.NumberColumn("SARR M-3", format="%.2f"),
                    "Moyenne M-1,M-2,M-3": st.column_config.NumberColumn("Moyenne (M-1,M-2,M-3)", format="%.2f"),
                    "Base Retenue": st.column_config.NumberColumn("Base = MAX(M, Moyenne)", format="%.2f"),
                    "Momentum": st.column_config.NumberColumn("Momentum", format="%.2f"),
                },
                use_container_width=True
            )

    with tab_bilan:
        st.subheader(f"Bilan Annuel {annee_cible} (en {unite_affichage})")
        st.write("Ce tableau est la somme des 12 mois de l'année cible. Il correspond exactement à la colonne 'Total general' de votre Excel.")
        
        df_annee = df_previsions[df_previsions["annee"] == annee_cible]
        if not df_annee.empty:
            pivot_annuel = pd.pivot_table(df_annee, values=col_val, index="article", columns="agence", aggfunc="sum", margins=True, margins_name="Total general").fillna(0)
            st.dataframe(pivot_annuel.style.format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("Aucune prévision pour cette année.")

    with tab_detail:
        st.subheader("Détail mensuel des Prévisions")
        if not df_previsions.empty:
            st.dataframe(
                df_previsions[["annee", "mois", "Date", "agence", "article", "Indice", "Base", "Momentum", "Prevision_HL", "Prevision_Unites"]].sort_values(["annee", "mois", "agence", "article"]),
                column_config={
                    "Indice": st.column_config.NumberColumn("Coef", format="%.2f"),
                    "Base": st.column_config.NumberColumn("Base", format="%.0f"),
                    "Momentum": st.column_config.NumberColumn("Momentum", format="%.0f"),
                    "Prevision_HL": st.column_config.NumberColumn("Prévision (HL)", format="%.2f"),
                    "Prevision_Unites": st.column_config.NumberColumn("Prévision (Unités)", format="%.0f"),
                },
                use_container_width=True
            )

    with tab_sarr:
        st.subheader("Table du SARR (Historique)")
        if not df_sarr.empty:
            st.dataframe(
                df_sarr[["annee", "mois", "agence", "article", "hl", "volume_unites", "Indice", "SARR_Unites"]].sort_values(["annee", "mois", "agence", "article"]),
                column_config={
                    "hl": st.column_config.NumberColumn("Vol (HL)", format="%.2f"),
                    "volume_unites": st.column_config.NumberColumn("Vol (Unités)", format="%.0f"),
                    "Indice": st.column_config.NumberColumn("Coef", format="%.4f"),
                    "SARR_Unites": st.column_config.NumberColumn("SARR (Unités)", format="%.0f")
                },
                use_container_width=True
            )

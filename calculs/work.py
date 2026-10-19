# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# Version FINALE : Filtres en cascade (Région -> Agence, Segment -> Article)
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

st.set_page_config(page_title="Moteur Ventes", page_icon="📊", layout="wide")

# --- PARAMÈTRES ---
DEFAUT_MOIS_CLOTURES = 8
ANNEES_HISTO = 2

# ============================================================
# RÉFÉRENTIEL INTÉGRÉ (69 SKU + SEGMENT/MARQUE)
# ============================================================
# Format : (Article, Positionnement, Occasion, Segment)
REFERENTIEL_DATA = [
    # --- CAPRICE ---
    ("Caprice Ananas 100 cl VER", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Ananas 150 cl PET", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Ananas 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Bonbon Anglais 100 cl VER", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Bonbon Anglais 150 cl PET", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Bonbon Anglais 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Bonbon Anglais 35 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Bonbon Anglais 50cl PET",   "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Grenadine 100 cl VER", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Grenadine 150 cl PET", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Grenadine 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Grenadine 33 cl CAN",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Grenadine 35 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Grenadine 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Orange 100 cl VER", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Orange 150 cl PET", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Orange 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Orange 33 cl CAN",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Orange 35 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Orange 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Bonbon Anglais 33 cl CAN", "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Citron 100 cl VER", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Citron 150 cl PET", "MILIEU", "FC (Family/Future Consumption)", "CAPRICE"),
    ("Caprice Citron 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    ("Caprice Citron 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)", "CAPRICE"),
    # --- WORLD COLA / TONIC ---
    ("World Cola 100cl VER", "MILIEU", "FC (Family/Future Consumption)", "WORLD COLA"),
    ("World Cola 100cl WOCOVER", "MILIEU", "FC (Family/Future Consumption)", "WORLD COLA"),
    ("World Cola 150cl PET", "MILIEU", "FC (Family/Future Consumption)", "WORLD COLA"),
    ("World Cola 30cl VER", "MILIEU", "IC (Individual/Immediate Consumption)", "WORLD COLA"),
    ("World Cola 30cl WOCOVER", "MILIEU", "IC (Individual/Immediate Consumption)", "WORLD COLA"),
    ("World Cola 33 cl CAN", "MILIEU", "IC (Individual/Immediate Consumption)", "WORLD COLA"),
    ("World Cola 35cl PET", "MILIEU", "IC (Individual/Immediate Consumption)", "WORLD COLA"),
    ("World Cola 50cl PET", "MILIEU", "IC (Individual/Immediate Consumption)", "WORLD COLA"),
    ("Tonic 100 cl VER", "MILIEU", "FC (Family/Future Consumption)", "WORLD COLA"),
    ("Tonic 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)", "WORLD COLA"),
    # --- EAUX (CRISTALLINE / EAU VIVE / FOSA) ---
    ("Cristalline 100 cl PET", "MILIEU", "IC (Individual/Immediate Consumption)", "EAUX"),
    ("Cristalline 200 cl PET", "MILIEU", "FC (Family/Future Consumption)", "EAUX"),
    ("Eau vive 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)", "EAUX"),
    ("Eau vive 50 cl PET", "PREMIUM", "IC (Individual/Immediate Consumption)", "EAUX"),
    ("Eau vive 50 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)", "EAUX"),
    ("FOSA 50 cl CAN", "PREMIUM", "IC (Individual/Immediate Consumption)", "EAUX"),
    # --- BOOSTER ---
    ("Booster Appel-Mix 50CL VER", "PREMIUM", "CU (Convivial Units)", "BOOSTER"),
    ("Booster Tornado 50CL VER",   "PREMIUM", "CU (Convivial Units)", "BOOSTER"),
    # --- BIERES (THB / GOLD / QUEEN / BEAUFORT / FRESH) ---
    ("THB Pilsener 33 cl VER", "MILIEU", "SS (Single serve)", "THB"),
    ("THB Pilsener 50 cl CAN", "MILIEU", "SS (Single serve)", "THB"),
    ("THB Pilsener 65 cl VER", "MILIEU", "CU (Convivial Units)", "THB"),
    ("THB Fresh 33 cl VER", "ENTREE", "SS (Single serve)", "THB"),
    ("THB Fresh 65 cl VER", "ENTREE", "CU (Convivial Units)", "THB"),
    ("FRESH 33 cl CAN", "ENTREE", "IC (Individual/Immediate Consumption)", "THB"),
    ("Gold 8 50 cl CAN", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold 8 50 cl VER", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blanche 33cl VER", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blanche 50 cl CAN", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blanche 50 cl VER", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blonde 33 cl VER", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blonde 50 cl CAN", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blonde 50 cl VER", "PREMIUM", "SS (Single serve)", "GOLD"),
    ("Gold Blonde 65 cl VER", "PREMIUM", "CU (Convivial Units)", "GOLD"),
    ("Beaufort 33 CL CAN", "PREMIUM", "SS (Single serve)", "BEAUFORT"),
    ("Beaufort 33CL VER", "PREMIUM", "SS (Single serve)", "BEAUFORT"),
    ("Queen s 65 cl VER", "ENTREE", "CU (Convivial Units)", "QUEEN"),
    # --- CRISTAL / XXL ---
    ("Cristal 100 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)", "CRISTAL"),
    ("Cristal 150 cl PET", "PREMIUM", "IC (Individual/Immediate Consumption)", "CRISTAL"),
    ("Cristal 30 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)", "CRISTAL"),
    ("Cristal 50 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)", "CRISTAL"),
    ("XXL 30cl BOB VER", "PREMIUM", "IC (Individual/Immediate Consumption)", "XXL"),
    ("XXL 30cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)", "XXL"),
    ("XXL 33 cl CAN", "PREMIUM", "IC (Individual/Immediate Consumption)", "XXL"),
    ("XXL 35cl PET", "PREMIUM", "IC (Individual/Immediate Consumption)", "XXL"),
]

# ============================================================
# MAPPING AGENCES (15 Agences réparties par Région)
# ============================================================
AGENCES_DATA = [
    ("01-Tanjombato", "Centre"),
    ("11-Andranomahery", "Centre"),
    ("12-Antsirabe", "Centre"),
    ("09-Tamatave", "Est"),
    ("18-Ambanja", "Est"),
    ("19-Sambava", "Est"),
    ("07-Majunga", "Ouest"),
    ("23-Morondava", "Ouest"),
    ("24-Fort Dauphin", "Sud"),
    ("21-NosyBe", "Nord"),
    ("03-Diego", "Nord"),
    ("04-Tulear", "Sud"),
    ("05-Fianarantsoa", "Sud"),
    ("06-Ihosy", "Sud"),
    ("08-Manakara", "Est"),
]

MOIS_FR_INV = {
    "JANVIER": 1, "FÉVRIER": 2, "FEVRIER": 2, "MARS": 3, "AVRIL": 4,
    "MAI": 5, "JUIN": 6, "JUILLET": 7, "AOÛT": 8, "AOUT": 8,
    "SEPTEMBRE": 9, "OCTOBRE": 10, "NOVEMBRE": 11, "DÉCEMBRE": 12, "DECEMBRE": 12
}

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def construire_referentiel():
    # On ajoute le Segment à la fin
    return pd.DataFrame(REFERENTIEL_DATA, columns=["Article", "Positionnement", "Occasion", "Segment"])

def construire_mapping_auto():
    return pd.DataFrame(AGENCES_DATA, columns=["Agence", "Région"])

# ============================================================
# LECTEUR SUR-MESURE
# ============================================================
def extraire_ventes_sur_mesure(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i in range(len(raw)):
        try:
            annee_val   = raw.iloc[i, 0]
            mois_val    = raw.iloc[i, 1]
            agence_val  = raw.iloc[i, 4]
            article_val = raw.iloc[i, 5]
            volume_val  = raw.iloc[i, 6]

            if pd.isna(annee_val) or pd.isna(mois_val) or pd.isna(article_val) or pd.isna(volume_val):
                continue

            if str(article_val).strip().upper() == "TOTAL" or str(agence_val).strip().upper() == "TOTAL":
                continue

            vol_str = str(volume_val).replace(" ", "").replace(",", ".").replace("\xa0", "")
            try:
                volume = float(vol_str)
            except ValueError:
                continue

            try:
                annee = int(annee_val)
            except ValueError:
                continue

            mois_str = str(mois_val).strip().upper()
            mois = MOIS_FR_INV.get(mois_str)
            if not mois:
                continue

            date_val = pd.Timestamp(year=annee, month=mois, day=15)
            
            # Nettoyer le préfixe de l'article (ex: "190-Cristalline..." -> "Cristalline...")
            art_propre = re.sub(r"^\d+-", "", str(article_val).strip())

            rows.append({
                "Date": date_val, "Article": art_propre, "Agence": str(agence_val).strip(), "Volume": volume
            })
        except Exception:
            continue

    return pd.DataFrame(rows)

# ============================================================
# ENRICHISSEMENT
# ============================================================
def enrichir_ventes(ventes: pd.DataFrame) -> pd.DataFrame:
    ventes["Date"] = pd.to_datetime(ventes["Date"], errors="coerce")
    ventes = ventes.dropna(subset=["Date"])
    ventes["Mois"]  = ventes["Date"].dt.month
    ventes["Annee"] = ventes["Date"].dt.year

    ref = construire_referentiel()
    df = ventes.merge(ref, on="Article", how="left")

    df = df.merge(construire_mapping_auto(), on="Agence", how="left")

    np.random.seed(7)
    df["Objectif_Annuel"] = df.groupby(["Article", "Agence"])["Volume"].transform("sum") * 1.1
    df["Objectif_Annuel"] = df["Objectif_Annuel"].fillna(0)
    return df

# ============================================================
# CALCULS
# ============================================================
def get_perimetre(df, filtres):
    if all(len(f) == 0 for f in filtres.values()):
        return df, "GLOBAL"
    masque = pd.Series(True, index=df.index)
    for col, vals in filtres.items():
        if len(vals) > 0 and col in df.columns:
            masque &= df[col].isin(vals)
    return df[masque], "FILTRÉ"

def calcul_realise_cumule(df_per, mois_clotures):
    df_clot = df_per[df_per["Mois"] <= mois_clotures - 1]
    if df_clot.empty: return pd.DataFrame(columns=["Article", "Agence", "Réalisé"])
    return df_clot.groupby(["Article", "Agence"], as_index=False).agg(Réalisé=("Volume", "sum"))

def calcul_indices(df_per):
    nb_annees = df_per["Annee"].nunique()
    if nb_annees < ANNEES_HISTO:
        return pd.DataFrame({"Mois": range(1, 13), "Indice": [1.0] * 12})
    par_mois = df_per.groupby("Mois")["Volume"].sum()
    moy_mois = par_mois / nb_annees
    moy_ann  = df_per["Volume"].sum() / 12
    indices = pd.Series(1.0, index=moy_mois.index) if moy_ann == 0 else moy_mois / moy_ann
    return indices.rename("Indice").reset_index()

def calcul_sarr(df_per, indices):
    ind = indices.set_index("Mois")["Indice"]
    df = df_per.copy()
    df["Indice"] = df["Mois"].map(ind).fillna(1.0)
    df["SARR"] = np.where(df["Indice"] == 0, 0.0, df["Volume"] / df["Indice"])
    return df

def calcul_tendance(df_sarr):
    grp = (df_sarr.groupby(["Article", "Agence", "Mois"], as_index=False)
                  .agg(SARR=("SARR", "sum"))
                  .sort_values(["Article", "Agence", "Mois"]))
    if grp.empty: return pd.DataFrame(columns=["Article", "Agence", "Tendance"])
    def _tend(s):
        if len(s) < 4: return 0.0
        ec = s.diff().dropna()
        return float(ec.mean()) if len(ec) >= 3 else 0.0
    return grp.groupby(["Article", "Agence"])["SARR"].apply(_tend).reset_index(name="Tendance")

def calcul_prevision(df_sarr, tendance, indices, mois_clotures):
    if df_sarr.empty: return pd.DataFrame()
    ind = indices.set_index("Mois")["Indice"].to_dict()
    rows = []
    for (art, ag), grp in df_sarr.groupby(["Article", "Agence"]):
        s = grp.sort_values("Mois")["SARR"].values
        base = max(s[-1], s[-3:].mean()) if len(s) >= 3 else (s.mean() if len(s) else 0)
        t = tendance.loc[(tendance["Article"] == art) & (tendance["Agence"] == ag), "Tendance"]
        tv = float(t.iloc[0]) if len(t) else 0.0
        for h in range(1, 13):
            mois = ((mois_clotures - 1 + h) % 12) + 1
            prev = max(0.0, ind.get(mois, 1.0) * base + tv)
            rows.append({"Article": art, "Agence": ag, "Mois_Futur": mois, "Prévision": prev})
    return pd.DataFrame(rows)

def calcul_gap(df_per, realise, prevision):
    obj = df_per.groupby(["Article", "Agence"], as_index=False).agg(Objectif_Annuel=("Objectif_Annuel", "max"))
    r = realise.rename(columns={"Réalisé": "Realise"}) if not realise.empty else pd.DataFrame(columns=["Article","Agence","Realise"])
    p = prevision.groupby(["Article", "Agence"], as_index=False).agg(Prevision=("Prévision", "sum")) if not prevision.empty else pd.DataFrame(columns=["Article","Agence","Prevision"])
    
    res = (obj.merge(r, on=["Article", "Agence"], how="left")
              .merge(p, on=["Article", "Agence"], how="left"))
    res = res.fillna({"Realise": 0, "Prevision": 0, "Objectif_Annuel": 0})
    res["Total_Projeté"] = res["Realise"] + res["Prevision"]
    res["GAP"] = res["Objectif_Annuel"] - res["Total_Projeté"]
    res["Alerte"] = np.where(res["GAP"] < 0, "🔴 DÉFICIT", np.where(res["GAP"] > 0, "🟠 SURPLUS", "✅ ATTEINT"))
    return res

# ============================================================
# MAIN (INTERFACE AVEC FILTRES EN CASCADE)
# ============================================================
def main():
    st.sidebar.header("📤 1. Charger le fichier")
    uploaded_file = st.sidebar.file_uploader("Format Excel / CSV", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            raw = pd.read_excel(BytesIO(uploaded_file.getvalue()), header=None)
        except Exception:
            raw = pd.read_csv(BytesIO(uploaded_file.getvalue()), header=None)
        
        with st.spinner("Extraction des données en cours..."):
            ventes = extraire_ventes_sur_mesure(raw)
            
        if ventes.empty:
            st.sidebar.error("❌ Erreur de lecture du fichier.")
            st.stop()
            
        df_brut = enrichir_ventes(ventes)
        st.sidebar.success(f"✅ Fichier chargé : {len(df_brut):,} lignes valides")
    else:
        df_brut = enrichir_ventes(pd.DataFrame({
            "Date": [pd.Timestamp(2024,1,15)], "Article": ["Cristalline 100 cl PET"], 
            "Agence": ["01-Tanjombato"], "Volume": [0]
        }))
        st.sidebar.warning("⚠️ Mode Démo (Uploadez un fichier pour voir vos données)")

    # ==========================================
    # LOGIQUE DES FILTRES EN CASCADE
    # ==========================================
    st.sidebar.header("🎛️ 2. Filtres (Cascade)")
    
    # 1. Filtre Région
    toutes_les_regions = sorted(list(set([x[1] for x in AGENCES_DATA])))
    sel_regions = st.sidebar.multiselect("Région", toutes_les_regions, default=[])
    
    # 2. Filtre Agence (dépend de la Région)
    if len(sel_regions) > 0:
        agences_dispo = [ag for ag, reg in AGENCES_DATA if reg in sel_regions]
    else:
        agences_dispo = [ag for ag, reg in AGENCES_DATA]
    sel_agences = st.sidebar.multiselect("Agence", sorted(agences_dispo), default=[])
    
    # 3. Filtre Segment (Marque)
    tous_les_segments = sorted(list(set([x[3] for x in REFERENTIEL_DATA])))
    sel_segments = st.sidebar.multiselect("Segment (Marque)", tous_les_segments, default=[])
    
    # 4. Filtre Article (dépend du Segment)
    if len(sel_segments) > 0:
        articles_dispo = [art for art, pos, occ, seg in REFERENTIEL_DATA if seg in sel_segments]
    else:
        articles_dispo = [art for art, pos, occ, seg in REFERENTIEL_DATA]
    sel_articles = st.sidebar.multiselect("Article (SKU)", sorted(articles_dispo), default=[])

    # 5. Filtres restants
    sel_positionnements = st.sidebar.multiselect("Positionnement", ["ENTREE", "MILIEU", "PREMIUM"], default=[])
    sel_occasions = st.sidebar.multiselect("Occasion", ["CU (Convivial Units)", "FC (Family/Future Consumption)", "IC (Individual/Immediate Consumption)", "SS (Single serve)"], default=[])

    mois_clotures = st.sidebar.slider("Mois clôturés (M-1)", 1, 12, DEFAUT_MOIS_CLOTURES)

    # Création du dictionnaire de filtres
    filtres = {
        "Région": sel_regions,
        "Agence": sel_agences,
        "Segment": sel_segments,
        "Article": sel_articles,
        "Positionnement": sel_positionnements,
        "Occasion": sel_occasions
    }

    # --- Application du périmètre ---
    df_per, mode = get_perimetre(df_brut, filtres)
    if df_per.empty:
        st.error("❌ Aucune donnée pour ce périmètre. Modifiez vos filtres.")
        st.stop()

    # --- Calculs ---
    realise   = calcul_realise_cumule(df_per, mois_clotures)
    indices   = calcul_indices(df_per)
    sarr      = calcul_sarr(df_per, indices)
    tendance  = calcul_tendance(sarr)
    prevision = calcul_prevision(sarr, tendance, indices, mois_clotures)
    gap       = calcul_gap(df_per, realise, prevision)

    # --- Dashboard ---
    st.title("📊 Moteur de pilotage des ventes")
    badge = "🟢 MODE GLOBAL" if mode == "GLOBAL" else "🟣 MODE FILTRÉ"
    st.subheader(f"{badge} — périmètre : {len(df_per):,} lignes")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volume réalisé", f"{realise['Réalisé'].sum():,.0f}")
    c2.metric("Volume prévu (M+12)", f"{prevision['Prévision'].sum():,.0f}")
    c3.metric("Objectif annuel", f"{gap['Objectif_Annuel'].sum():,.0f}")
    c4.metric("GAP total", f"{gap['GAP'].sum():,.0f}", delta="🔴 déficit" if gap['GAP'].sum() < 0 else "🟠 surplus")
    
    st.divider()

    st.markdown("### 📈 Indices saisonniers (recalculés sur le périmètre)")
    st.bar_chart(indices.set_index("Mois")["Indice"])

    st.markdown("### 🔮 Prévisions mensuelles (M → M+12)")
    if not prevision.empty:
        pm = prevision.groupby("Mois_Futur", as_index=False).agg(Prévision=("Prévision", "sum"))
        st.line_chart(pm.set_index("Mois_Futur")["Prévision"])

    st.markdown("### 🎯 GAP & Alertes par Article × Agence")
    st.dataframe(
        gap.sort_values("GAP").style.format("{:,.0f}", subset=["GAP", "Realise", "Prevision", "Objectif_Annuel"]), 
        use_container_width=True
    )

if __name__ == "__main__":
    main()

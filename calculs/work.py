# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# Référentiel complet : 69 SKU × 15 Agences
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

st.set_page_config(
    page_title="Moteur Ventes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# PARAMÈTRES GLOBAUX
# ============================================================
DEFAUT_MOIS_CLOTURES = 8
ANNEES_HISTO = 2

# ============================================================
# RÉFÉRENTIEL INTÉGRÉ (Les 69 SKU du PDF Classeur2)
# ============================================================
REFERENTIEL_DATA = [
    ("Booster Appel-Mix 50CL VER", "PREMIUM", "CU (Convivial Units)"),
    ("Booster Tornado 50CL VER",   "PREMIUM", "CU (Convivial Units)"),
    ("Caprice Ananas 100 cl VER",  "MILIEU",  "FC (Family/Future Consumption)"),
    ("Caprice Ananas 150 cl PET",  "MILIEU",  "FC (Family/Future Consumption)"),
    ("Caprice Ananas 30 cl VER",   "MILIEU",  "IC (Individual/Immediate Consumption)"),
    ("Caprice Bonbon Anglais 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Bonbon Anglais 150 cl PET", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Bonbon Anglais 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Bonbon Anglais 35 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Bonbon Anglais 50cl PET",   "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Grenadine 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Grenadine 150 cl PET", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Grenadine 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Grenadine 33 cl CAN",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Grenadine 35 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Grenadine 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Orange 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Orange 150 cl PET", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Orange 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Orange 33 cl CAN",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Orange 35 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Orange 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Bonbon Anglais 33 cl CAN", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Citron 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Citron 150 cl PET", "MILIEU", "FC (Family/Future Consumption)"),
    ("Caprice Citron 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Caprice Citron 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Tonic 100 cl VER", "MILIEU", "FC (Family/Future Consumption)"),
    ("Tonic 30 cl VER",  "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("World Cola 100cl VER", "MILIEU", "FC (Family/Future Consumption)"),
    ("World Cola 100cl WOCOVER", "MILIEU", "FC (Family/Future Consumption)"),
    ("World Cola 150cl PET", "MILIEU", "FC (Family/Future Consumption)"),
    ("World Cola 30cl VER", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("World Cola 30cl WOCOVER", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("World Cola 33 cl CAN", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("World Cola 35cl PET", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("World Cola 50cl PET", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Beaufort 33 CL CAN", "PREMIUM", "SS (Single serve)"),
    ("Beaufort 33CL VER", "PREMIUM", "SS (Single serve)"),
    ("FRESH 33 cl CAN", "ENTREE", "IC (Individual/Immediate Consumption)"),
    ("THB Fresh 33 cl VER", "ENTREE", "SS (Single serve)"),
    ("THB Fresh 65 cl VER", "ENTREE", "CU (Convivial Units)"),
    ("Gold 8 50 cl CAN", "PREMIUM", "SS (Single serve)"),
    ("Gold 8 50 cl VER", "PREMIUM", "SS (Single serve)"),
    ("Gold Blanche 33cl VER", "PREMIUM", "SS (Single serve)"),
    ("Gold Blanche 50 cl CAN", "PREMIUM", "SS (Single serve)"),
    ("Gold Blanche 50 cl VER", "PREMIUM", "SS (Single serve)"),
    ("Gold Blonde 33 cl VER", "PREMIUM", "SS (Single serve)"),
    ("Gold Blonde 50 cl CAN", "PREMIUM", "SS (Single serve)"),
    ("Gold Blonde 50 cl VER", "PREMIUM", "SS (Single serve)"),
    ("Gold Blonde 65 cl VER", "PREMIUM", "CU (Convivial Units)"),
    ("Queen s 65 cl VER", "ENTREE", "CU (Convivial Units)"),
    ("THB Pilsener 33 cl VER", "MILIEU", "SS (Single serve)"),
    ("THB Pilsener 50 cl CAN", "MILIEU", "SS (Single serve)"),
    ("THB Pilsener 65 cl VER", "MILIEU", "CU (Convivial Units)"),
    ("Cristal 100 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("Cristal 150 cl PET", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("Cristal 30 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("Cristal 50 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("Cristalline 100 cl PET", "MILIEU", "IC (Individual/Immediate Consumption)"),
    ("Cristalline 200 cl PET", "MILIEU", "FC (Family/Future Consumption)"),
    ("Eau vive 150 cl PET", "PREMIUM", "FC (Family/Future Consumption)"),
    ("Eau vive 50 cl PET", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("Eau vive 50 cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("FOSA 50 cl CAN", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("XXL 30cl BOB VER", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("XXL 30cl VER", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("XXL 33 cl CAN", "PREMIUM", "IC (Individual/Immediate Consumption)"),
    ("XXL 35cl PET", "PREMIUM", "IC (Individual/Immediate Consumption)"),
]

# ============================================================
# MAPPING AGENCES (Les 15 agences du PDF)
# ============================================================
AGENCES_MADAGASCAR = [
    "01-Tanjombato", "03-Diego", "04-Tulear", "05-Fianarantsoa", 
    "06-Ihosy", "07-Majunga", "08-Manakara", "09-Tamatave", 
    "11-Andranomahery", "12-Antsirabe", "18-Ambanja", "19-Sambava", 
    "21-NosyBe", "23-Morondava", "24-Fort Dauphin"
]
REGIONS = ["Nord", "Ouest", "Est", "Centre", "Sud"]

MOIS_FR_INV = {
    "JANVIER": 1, "FÉVRIER": 2, "FEVRIER": 2, "MARS": 3, "AVRIL": 4,
    "MAI": 5, "JUIN": 6, "JUILLET": 7, "AOÛT": 8, "AOUT": 8,
    "SEPTEMBRE": 9, "OCTOBRE": 10, "NOVEMBRE": 11, "DÉCEMBRE": 12, "DECEMBRE": 12
}

# ============================================================
# GÉNÉRATION DE DONNÉES DÉMO (Si aucun fichier)
# ============================================================
def generer_donnees_demo():
    """Génère des fausses données pour peupler l'interface et les filtres."""
    np.random.seed(42)
    ref = pd.DataFrame(REFERENTIEL_DATA, columns=["Article", "Positionnement", "Occasion"])
    
    rows = []
    # On prend 5 articles au hasard parmi les 69 pour la démo
    articles_demo = ref["Article"].sample(5, random_state=1).tolist()
    
    for art in articles_demo:
        for ag in AGENCES_MADAGASCAR:
            for annee in [2023, 2024, 2025]:
                for mois in range(1, 13):
                    saison = 1 + 0.3 * np.sin((mois - 3) / 12 * 2 * np.pi)
                    vol = max(0, int(np.random.randint(500, 2000) * saison))
                    date_val = pd.Timestamp(year=annee, month=mois, day=15)
                    rows.append({
                        "Date": date_val, "Article": art, "Agence": ag, "Volume": vol
                    })
    df = pd.DataFrame(rows)
    
    # Mapping et Objectifs
    df = df.merge(ref, on="Article", how="left")
    df = df.merge(construire_mapping_auto(), on="Agence", how="left")
    df["Mois"] = df["Date"].dt.month
    df["Annee"] = df["Date"].dt.year
    
    # Objectif fictif = somme annuelle * 1.1
    df["Objectif_Annuel"] = df.groupby(["Article", "Agence"])["Volume"].transform("sum") * 1.1
    return df

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
def construire_referentiel():
    return pd.DataFrame(REFERENTIEL_DATA, columns=["Article", "Positionnement", "Occasion"])

def construire_mapping_auto():
    return pd.DataFrame({
        "Agence": AGENCES_MADAGASCAR,
        "Région": [REGIONS[i % len(REGIONS)] for i in range(len(AGENCES_MADAGASCAR))],
    })

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
# MAIN
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
        st.sidebar.success("✅ Fichier chargé avec succès !")
    else:
        # Mode démo pour afficher les filtres
        df_brut = generer_donnees_demo()
        st.sidebar.warning("⚠️ Mode Démo (Uploadez un fichier pour voir vos vraies données)")

    # --- FILTRES (Affichés dans tous les cas) ---
    st.sidebar.header("🎛️ 2. Filtres")
    st.sidebar.caption("Laisser vide = Mode GLOBAL")
    filtres = {}
    
    for col in ["Région", "Agence", "Positionnement", "Occasion"]:
        if col in df_brut.columns:
            # On récupère TOUTES les valeurs uniques, même si la démo/le fichier n'en a qu'une partie
            if col == "Agence":
                vals = sorted(AGENCES_MADAGASCAR)
            elif col == "Région":
                vals = sorted(REGIONS)
            elif col == "Positionnement":
                vals = ["ENTREE", "MILIEU", "PREMIUM"]
            elif col == "Occasion":
                vals = ["CU (Convivial Units)", "FC (Family/Future Consumption)", "IC (Individual/Immediate Consumption)", "SS (Single serve)"]
            else:
                vals = sorted(df_brut[col].dropna().unique().tolist())
                
            filtres[col] = st.sidebar.multiselect(col, vals, default=[])
            
    mois_clotures = st.sidebar.slider("Mois clôturés (M-1)", 1, 12, DEFAUT_MOIS_CLOTURES)

    # --- CALCULS ---
    df_per, mode = get_perimetre(df_brut, filtres)
    if df_per.empty:
        st.error("❌ Aucune donnée pour ce périmètre. Modifiez vos filtres.")
        st.stop()

    realise   = calcul_realise_cumule(df_per, mois_clotures)
    indices   = calcul_indices(df_per)
    sarr      = calcul_sarr(df_per, indices)
    tendance  = calcul_tendance(sarr)
    prevision = calcul_prevision(sarr, tendance, indices, mois_clotures)
    gap       = calcul_gap(df_per, realise, prevision)

    # --- DASHBOARD ---
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

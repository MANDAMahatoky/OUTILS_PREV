# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# UN SEUL UPLOAD — LECTEUR SUR-MESURE
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

st.set_page_config(
    page_title="Moteur Ventes — Historique",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAUT_MOIS_CLOTURES = 8
ANNEES_HISTO = 2

# ============================================================
# RÉFÉRENTIEL INTÉGRÉ (69 SKU)
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

CONV_CL_HL = {30: 0.003, 33: 0.0033, 35: 0.0035, 50: 0.005,
              65: 0.0065, 100: 0.01, 150: 0.015, 200: 0.02}

REGIONS = ["Nord", "Ouest", "Est", "Centre", "Sud"]
MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre",
    11: "novembre", 12: "décembre"
}
MOIS_FR_INV = {v.upper(): k for k, v in MOIS_FR.items()}
MOIS_EN_INV = {"JANUARY":1,"FEBRUARY":2,"MARCH":3,"APRIL":4,"MAY":5,"JUNE":6,
               "JULY":7,"AUGUST":8,"SEPTEMBER":9,"OCTOBER":10,"NOVEMBER":11,"DECEMBER":12}

# ============================================================
# UTILITAIRES
# ============================================================
def extraire_format(a):
    u = str(a).upper()
    if "CAN" in u:     return "CAN"
    if "PET" in u:     return "PET"
    if "WOCOVER" in u: return "WOCOVER"
    if "VER" in u:     return "VER"
    return "INCONNU"

def extraire_contenance(a):
    m = re.search(r"(\d+)\s*C?L", str(a).upper())
    return int(m.group(1)) if m else None

def construire_referentiel_integre():
    df = pd.DataFrame(REFERENTIEL_DATA,
                      columns=["Article", "Positionnement", "Occasion"])
    df["Format"]        = df["Article"].apply(extraire_format)
    df["Contenance_cl"] = df["Article"].apply(extraire_contenance)
    df["Contenance_hl"] = df["Contenance_cl"].map(CONV_CL_HL)
    return df

def construire_mapping_auto(agences):
    return pd.DataFrame({
        "Agence": agences,
        "Région": [REGIONS[i % len(REGIONS)] for i in range(len(agences))],
    })

def generer_objectifs_auto(ref, mapr):
    np.random.seed(7)
    obj = (ref[["Article"]].assign(key=1)
              .merge(mapr[["Agence"]].assign(key=1), on="key")
              .drop("key", axis=1))
    obj["Objectif_Annuel"] = np.random.randint(5000, 20000, size=len(obj))
    return obj

def normaliser_mois(val):
    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    if s in MOIS_FR_INV:
        return MOIS_FR_INV[s]
    if s in MOIS_EN_INV:
        return MOIS_EN_INV[s]
    s3 = s[:3]
    for k, v in MOIS_FR_INV.items():
        if k.startswith(s3):
            return v
    return None

# ============================================================
# LECTEUR SUR-MESURE POUR VOTRE FICHIER
# Format : Année | Mois | Catégorie | Sous-catégorie | Agence | Article | Volume
# ============================================================
def extraire_ventes_sur_mesure(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    
    for i in range(len(raw)):
        try:
            # Récupération par position (index de colonne)
            annee_val   = raw.iloc[i, 0]
            mois_val    = raw.iloc[i, 1]
            agence_val  = raw.iloc[i, 4]
            article_val = raw.iloc[i, 5]
            volume_val  = raw.iloc[i, 6]
            
            # 1. Ignorer les lignes vides ou d'en-tête
            if pd.isna(annee_val) or pd.isna(mois_val) or pd.isna(article_val):
                continue
                
            # 2. Ignorer les lignes "Total" (pour éviter le double comptage)
            if str(article_val).strip().upper() == "TOTAL":
                continue
                
            # 3. Nettoyer et convertir le volume (ex: "3 776" -> 3776.0)
            vol_str = str(volume_val).replace(" ", "").replace(",", ".").replace("\xa0", "")
            try:
                volume = float(vol_str)
            except ValueError:
                continue
                
            # 4. Convertir l'année
            try:
                annee = int(annee_val)
            except ValueError:
                continue
                
            # 5. Convertir le mois
            mois = normaliser_mois(mois_val)
            if not mois:
                continue
                
            # 6. Construire la date
            date_val = pd.Timestamp(year=annee, month=mois, day=15)
            
            # 7. Nettoyer le nom de l'article (enlever "190-", "189-", etc.)
            art_propre = re.sub(r"^\d+-", "", str(article_val).strip())
            
            rows.append({
                "Date": date_val,
                "Article": art_propre,
                "Agence": str(agence_val).strip(),
                "Volume": volume
            })
            
        except Exception:
            continue
            
    return pd.DataFrame(rows)

# ============================================================
# CHARGEMENT ET ENRICHISSEMENT
# ============================================================
@st.cache_data(show_spinner="⏳ Chargement du fichier...")
def charger_brut(file_bytes):
    try:
        return pd.read_excel(BytesIO(file_bytes), header=None)
    except Exception:
        return pd.read_csv(BytesIO(file_bytes), header=None)

def enrichir_ventes(ventes: pd.DataFrame) -> pd.DataFrame:
    # Normalisation
    ventes["Date"] = pd.to_datetime(ventes["Date"], errors="coerce")
    ventes = ventes.dropna(subset=["Date"])
    ventes["Volume"] = pd.to_numeric(ventes["Volume"], errors="coerce").fillna(0)
    ventes["Mois"]  = ventes["Date"].dt.month
    ventes["Annee"] = ventes["Date"].dt.year

    # Référentiel
    ref = construire_referentiel_integre()
    ref_merge = ref[["Article","Positionnement","Occasion","Format",
                     "Contenance_cl","Contenance_hl"]]
    df = ventes.merge(ref_merge, on="Article", how="left")

    # Mapping région
    agences = sorted(df["Agence"].dropna().unique().tolist())
    if "Région" not in df.columns:
        df = df.merge(construire_mapping_auto(agences), on="Agence", how="left")

    # Objectifs
    if "Objectif_Annuel" not in df.columns:
        mapr_used = df[["Agence","Région"]].drop_duplicates()
        df = df.merge(generer_objectifs_auto(ref, mapr_used),
                      on=["Article","Agence"], how="left")
    df["Objectif_Annuel"] = df["Objectif_Annuel"].fillna(0)

    return df

# ============================================================
# ÉTAPE 4 — PÉRIMÈTRE
# ============================================================
def get_perimetre(df, filtres):
    if all(len(f) == 0 for f in filtres.values()):
        return df, "GLOBAL"
    masque = pd.Series(True, index=df.index)
    for col, vals in filtres.items():
        if len(vals) > 0 and col in df.columns:
            masque &= df[col].isin(vals)
    return df[masque], "FILTRÉ"

# ============================================================
# CALCULS (étapes 5 → 10)
# ============================================================
def calcul_realise_cumule(df_per, mois_clotures):
    df_clot = df_per[df_per["Mois"] <= mois_clotures - 1]
    if df_clot.empty:
        return pd.DataFrame(columns=["Article", "Agence", "Réalisé"])
    return df_clot.groupby(["Article", "Agence"], as_index=False).agg(
        Réalisé=("Volume", "sum"))

def calcul_indices(df_per):
    nb_annees = df_per["Annee"].nunique() if "Annee" in df_per.columns else 1
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
    if grp.empty:
        return pd.DataFrame(columns=["Article", "Agence", "Tendance"])
    def _tend(s):
        if len(s) < 4: return 0.0
        ec = s.diff().dropna()
        if len(ec) < 3: return 0.0
        return float(ec.mean())
    return (grp.groupby(["Article", "Agence"])["SARR"]
               .apply(_tend).reset_index(name="Tendance"))

def calcul_prevision(df_sarr, tendance, indices, mois_clotures, horizon=12):
    if df_sarr.empty or "SARR" not in df_sarr.columns:
        return pd.DataFrame(columns=["Article", "Agence", "Mois_Futur", "Prévision"])
    ind = indices.set_index("Mois")["Indice"].to_dict()
    rows = []
    for (art, ag), grp in df_sarr.groupby(["Article", "Agence"]):
        s = grp.sort_values("Mois")["SARR"].values
        base = max(s[-1], s[-3:].mean()) if len(s) >= 3 else (s.mean() if len(s) else 0)
        t = tendance.loc[(tendance["Article"] == art) &
                         (tendance["Agence"] == ag), "Tendance"]
        tv = float(t.iloc[0]) if len(t) else 0.0
        for h in range(1, horizon + 1):
            mois = ((mois_clotures - 1 + h) % 12) + 1
            prev = max(0.0, ind.get(mois, 1.0) * base + tv)
            rows.append({"Article": art, "Agence": ag,
                         "Mois_Futur": mois, "Prévision": prev})
    return pd.DataFrame(rows)

def calcul_gap(df_per, realise, prevision):
    obj = df_per.groupby(["Article", "Agence"], as_index=False).agg(
        Objectif_Annuel=("Objectif_Annuel", "max"))
    r = (realise.rename(columns={"Réalisé": "Realise"})
         if not realise.empty and "Réalisé" in realise.columns
         else pd.DataFrame(columns=["Article","Agence","Realise"]))
    p = (prevision.groupby(["Article", "Agence"], as_index=False).agg(
            Prevision=("Prévision", "sum"))
         if not prevision.empty and "Article" in prevision.columns
         else pd.DataFrame(columns=["Article","Agence","Prevision"]))
    res = (obj.merge(r, on=["Article", "Agence"], how="left")
              .merge(p, on=["Article", "Agence"], how="left"))
    res = res.fillna({"Realise": 0, "Prevision": 0, "Objectif_Annuel": 0})
    res["Total_Projeté"] = res["Realise"] + res["Prevision"]
    res["GAP"] = res["Objectif_Annuel"] - res["Total_Projeté"]
    res["Alerte"] = np.where(res["GAP"] < 0, "🔴 DÉFICIT",
                     np.where(res["GAP"] > 0, "🟠 SURPLUS", "✅ ATTEINT"))
    return res

# ============================================================
# SIDEBAR
# ============================================================
def zone_upload():
    st.sidebar.header("📤 1. Charger l'historique des ventes")
    f = st.sidebar.file_uploader(
        "📄 Fichier Excel/CSV",
        type=["xlsx", "csv"], key="up_hist")
    return f

def construire_sidebar(df, mois_clotures):
    st.sidebar.header("🎛️ 2. Filtres")
    st.sidebar.caption("Laisser vide = Mode GLOBAL")
    axes = ["Région", "Agence", "Positionnement", "Occasion",
            "Format", "Contenance_cl"]
    filtres = {}
    for col in axes:
        if col in df.columns:
            vals = sorted(df[col].dropna().unique().tolist())
            filtres[col] = st.sidebar.multiselect(col, vals, default=[])
        else:
            filtres[col] = []
    st.sidebar.divider()
    st.sidebar.header("⚙️ 3. Paramètres")
    new_mc = st.sidebar.slider("Mois clôturés (M-1)", 1, 12, mois_clotures)
    return filtres, new_mc

# ============================================================
# DASHBOARD
# ============================================================
def afficher_dashboard(mode, df_per, realise, indices, sarr,
                       tendance, prevision, gap):
    st.title("📊 Moteur de pilotage des ventes")
    badge = "🟢 MODE GLOBAL" if mode == "GLOBAL" else "🟣 MODE FILTRÉ"
    st.subheader(f"{badge} — périmètre : {len(df_per):,} lignes")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volume réalisé", f"{realise['Réalisé'].sum():,.0f}")
    c2.metric("Volume prévu (M→M+12)", f"{prevision['Prévision'].sum():,.0f}")
    c3.metric("Objectif annuel", f"{gap['Objectif_Annuel'].sum():,.0f}")
    c4.metric("GAP total", f"{gap['GAP'].sum():,.0f}",
              delta="🔴 déficit" if gap['GAP'].sum() < 0 else "🟠 surplus")
    st.divider()

    st.markdown("### 📈 Indices saisonniers (recalculés sur le périmètre)")
    if not indices.empty:
        st.bar_chart(indices.set_index("Mois")["Indice"])

    st.markdown("### 🔮 Prévisions mensuelles (M → M+12)")
    if not prevision.empty and "Mois_Futur" in prevision.columns:
        pm = prevision.groupby("Mois_Futur", as_index=False).agg(
            Prévision=("Prévision", "sum"))
        st.line_chart(pm.set_index("Mois_Futur")["Prévision"])

    st.markdown("### 🎯 GAP & alertes par SKU × Agence")
    st.dataframe(
        gap.sort_values("GAP").style.format({
            "Objectif_Annuel": "{:,.0f}", "Realise": "{:,.0f}",
            "Prevision": "{:,.0f}", "Total_Projeté": "{:,.0f}",
            "GAP": "{:,.0f}",
        }),
        use_container_width=True, height=400,
    )

    st.markdown("### 🚨 Répartition des alertes")
    if not gap.empty and "Alerte" in gap.columns:
        a = gap["Alerte"].value_counts().reset_index()
        a.columns = ["Alerte", "Nombre"]
        st.bar_chart(a.set_index("Alerte")["Nombre"])

# ============================================================
# MAIN
# ============================================================
def main():
    if "mois_clotures" not in st.session_state:
        st.session_state.mois_clotures = DEFAUT_MOIS_CLOTURES

    fichier = zone_upload()

    if fichier is None:
        st.title("📊 Moteur de pilotage des ventes")
        st.info("👈 Uploadez votre historique des ventes dans la sidebar pour démarrer.")
        st.markdown("""
        ### 📋 Format attendu
        Le fichier doit contenir les colonnes dans cet ordre :
        `Année | Mois | Catégorie | Sous-catégorie | Agence | Article | Volume`
        
        L'application ignore automatiquement les lignes de type `Total` 
        pour éviter les doubles comptages.
        """)
        st.stop()

    # --- Lecture brute ---
    file_bytes = fichier.getvalue()
    raw = charger_brut(file_bytes)

    # --- Extraction sur-mesure ---
    st.markdown("### ⚙️ Extraction des ventes")
    ventes = extraire_ventes_sur_mesure(raw)

    if ventes.empty:
        st.error("❌ Impossible d'extraire les ventes. Vérifiez que votre fichier a bien 7 colonnes.")
        with st.expander("👁️ Aperçu des 10 premières lignes brutes"):
            st.dataframe(raw.head(10), use_container_width=True)
        st.stop()

    st.success(f"✅ {len(ventes):,} lignes extraites avec succès.")
    
    with st.expander("👁️ Aperçu des ventes extraites"):
        st.dataframe(ventes.head(20), use_container_width=True)

    # --- Enrichissement ---
    df_brut = enrichir_ventes(ventes)

    # --- Sidebar filtres ---
    filtres, mois_clotures = construire_sidebar(
        df_brut, st.session_state.mois_clotures)
    st.session_state.mois_clotures = mois_clotures

    # --- Périmètre ---
    df_per, mode = get_perimetre(df_brut, filtres)
    if df_per.empty:
        st.error("❌ Aucune donnée pour ce périmètre.")
        st.stop()

    # --- Calculs ---
    realise   = calcul_realise_cumule(df_per, mois_clotures)
    indices   = calcul_indices(df_per)
    sarr      = calcul_sarr(df_per, indices)
    tendance  = calcul_tendance(sarr)
    prevision = calcul_prevision(sarr, tendance, indices, mois_clotures)
    gap       = calcul_gap(df_per, realise, prevision)

    # --- Dashboard ---
    afficher_dashboard(mode, df_per, realise, indices, sarr,
                       tendance, prevision, gap)

if __name__ == "__main__":
    main()

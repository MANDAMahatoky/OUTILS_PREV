# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# Mode Global vs Mode Filtré — Workflow 11 étapes
# Version corrigée (gestion des cas vides)
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import date
from io import BytesIO

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Moteur Ventes — Global vs Filtré",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAUT_MOIS_CLOTURES = 8
ANNEES_HISTO = 2

# ============================================================
# RÉFÉRENTIEL PRODUIT
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


def enrichir_referentiel(df_ref):
    df = df_ref.copy()
    if "Format" not in df.columns:
        df["Format"] = df["Article"].apply(extraire_format)
    if "Contenance_cl" not in df.columns:
        df["Contenance_cl"] = df["Article"].apply(extraire_contenance)
        df["Contenance_hl"] = df["Contenance_cl"].map(CONV_CL_HL)
    return df


def lire_fichier(uploaded_file):
    if uploaded_file is None:
        return None
    b = uploaded_file.getvalue()
    try:
        return pd.read_excel(BytesIO(b))
    except Exception:
        try:
            return pd.read_csv(BytesIO(b))
        except Exception:
            return None


# ============================================================
# GÉNÉRATION DE DONNÉES DÉMO
# ============================================================
def generer_ventes_demo():
    np.random.seed(42)
    ref = construire_referentiel_integre()
    agences = ["Alger Centre", "Oran", "Constantine", "Annaba", "Blida",
               "Sétif", "Tlemcen", "Béjaïa", "Batna", "Tizi Ouzou",
               "Djelfa", "Biskra", "Tiaret", "Skikda", "Chlef"]
    rows = []
    for art in ref["Article"].unique():
        base = np.random.randint(200, 1500)
        for ag in agences:
            for annee in [2023, 2024, 2025]:
                for mois in range(1, 13):
                    saison = 1 + 0.35 * np.sin((mois - 3) / 12 * 2 * np.pi)
                    vol = max(0, int(base * saison * np.random.uniform(0.8, 1.2)))
                    rows.append([date(annee, mois, 15), art, ag, vol])
    return pd.DataFrame(rows, columns=["Date", "Article", "Agence", "Volume"])


def generer_mapping_demo():
    agences = ["Alger Centre", "Oran", "Constantine", "Annaba", "Blida",
               "Sétif", "Tlemcen", "Béjaïa", "Batna", "Tizi Ouzou",
               "Djelfa", "Biskra", "Tiaret", "Skikda", "Chlef"]
    regions = ["Nord", "Ouest", "Est", "Centre", "Sud"]
    return pd.DataFrame({
        "Agence": agences,
        "Région": [regions[i % len(regions)] for i in range(len(agences))],
    })


def generer_objectifs_demo():
    np.random.seed(7)
    ref = construire_referentiel_integre()
    mapr = generer_mapping_demo()
    obj = (ref[["Article"]].assign(key=1)
              .merge(mapr[["Agence"]].assign(key=1), on="key")
              .drop("key", axis=1))
    obj["Objectif_Annuel"] = np.random.randint(5000, 20000, size=len(obj))
    return obj


# ============================================================
# ÉTAPE 1 — CHARGEMENT ET FUSION
# ============================================================
@st.cache_data(show_spinner="⏳ Chargement et fusion des données...")
def charger_donnees(ventes_bytes, ref_bytes, mapr_bytes, obj_bytes):
    if ref_bytes:
        try:
            ref = pd.read_excel(BytesIO(ref_bytes))
        except Exception:
            ref = pd.read_csv(BytesIO(ref_bytes))
        ref = enrichir_referentiel(ref)
    else:
        ref = construire_referentiel_integre()

    if ventes_bytes:
        try:
            ventes = pd.read_excel(BytesIO(ventes_bytes))
        except Exception:
            ventes = pd.read_csv(BytesIO(ventes_bytes))
    else:
        ventes = generer_ventes_demo()

    if mapr_bytes:
        try:
            mapr = pd.read_excel(BytesIO(mapr_bytes))
        except Exception:
            mapr = pd.read_csv(BytesIO(mapr_bytes))
    else:
        mapr = generer_mapping_demo()

    if obj_bytes:
        try:
            obj = pd.read_excel(BytesIO(obj_bytes))
        except Exception:
            obj = pd.read_csv(BytesIO(obj_bytes))
    else:
        obj = generer_objectifs_demo()

    ventes["Date"] = pd.to_datetime(ventes["Date"])
    ventes["Mois"] = ventes["Date"].dt.month
    ventes["Annee"] = ventes["Date"].dt.year

    df = (ventes.merge(ref, on="Article", how="left")
                .merge(mapr, on="Agence", how="left")
                .merge(obj, on=["Article", "Agence"], how="left"))
    df["Objectif_Annuel"] = df["Objectif_Annuel"].fillna(0)
    return df


# ============================================================
# ÉTAPE 2 — MATRICE DE BASE
# ============================================================
@st.cache_data
def construire_matrice(df):
    axes = ["Article", "Agence", "Région", "Positionnement", "Occasion",
            "Format", "Contenance_cl", "Mois"]
    axes = [c for c in axes if c in df.columns]
    return df.groupby(axes, as_index=False, dropna=False)["Volume"].sum()


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
# ÉTAPE 5 — RÉALISÉ CUMULÉ
# ============================================================
def calcul_realise_cumule(df_per, mois_clotures):
    df_clot = df_per[df_per["Mois"] <= mois_clotures - 1]
    if df_clot.empty:
        return pd.DataFrame(columns=["Article", "Agence", "Réalisé"])
    return df_clot.groupby(["Article", "Agence"], as_index=False).agg(
        Réalisé=("Volume", "sum"))


# ============================================================
# ÉTAPE 6 — INDICES SAISONNIERS
# ============================================================
def calcul_indices(df_per):
    nb_annees = df_per["Annee"].nunique() if "Annee" in df_per.columns else 1
    if nb_annees < ANNEES_HISTO:
        return pd.DataFrame({"Mois": range(1, 13), "Indice": [1.0] * 12})
    par_mois = df_per.groupby("Mois")["Volume"].sum()
    moy_mois = par_mois / nb_annees
    moy_ann  = df_per["Volume"].sum() / 12
    if moy_ann == 0:
        indices = pd.Series(1.0, index=moy_mois.index)
    else:
        indices = moy_mois / moy_ann
    return indices.rename("Indice").reset_index()


# ============================================================
# ÉTAPE 7 — SARR
# ============================================================
def calcul_sarr(df_per, indices):
    ind = indices.set_index("Mois")["Indice"]
    df = df_per.copy()
    df["Indice"] = df["Mois"].map(ind).fillna(1.0)
    df["SARR"] = np.where(df["Indice"] == 0, 0.0, df["Volume"] / df["Indice"])
    return df


# ============================================================
# ÉTAPE 8 — TENDANCE  (corrigée : cas vide)
# ============================================================
def calcul_tendance(df_sarr):
    grp = (df_sarr.groupby(["Article", "Agence", "Mois"], as_index=False)
                  .agg(SARR=("SARR", "sum"))
                  .sort_values(["Article", "Agence", "Mois"]))
    if grp.empty:
        return pd.DataFrame(columns=["Article", "Agence", "Tendance"])
    def _tend(s):
        if len(s) < 4:
            return 0.0
        ec = s.diff().dropna()
        if len(ec) < 3:
            return 0.0
        return float(ec.mean())
    return (grp.groupby(["Article", "Agence"])["SARR"]
               .apply(_tend).reset_index(name="Tendance"))


# ============================================================
# ÉTAPE 9 — PRÉVISION  (corrigée : cas vide)
# ============================================================
def calcul_prevision(df_sarr, tendance, indices, mois_clotures, horizon=12):
    if df_sarr.empty or "SARR" not in df_sarr.columns:
        return pd.DataFrame(columns=["Article", "Agence", "Mois_Futur", "Prévision"])
    ind = indices.set_index("Mois")["Indice"].to_dict()
    rows = []
    for (art, ag), grp in df_sarr.groupby(["Article", "Agence"]):
        s = grp.sort_values("Mois")["SARR"].values
        if len(s) >= 3:
            base = max(s[-1], s[-3:].mean())
        elif len(s) > 0:
            base = s.mean()
        else:
            base = 0.0
        t = tendance.loc[(tendance["Article"] == art) &
                         (tendance["Agence"] == ag), "Tendance"]
        tv = float(t.iloc[0]) if len(t) else 0.0
        for h in range(1, horizon + 1):
            mois = ((mois_clotures - 1 + h) % 12) + 1
            prev = max(0.0, ind.get(mois, 1.0) * base + tv)
            rows.append({"Article": art, "Agence": ag,
                         "Mois_Futur": mois, "Prévision": prev})
    return pd.DataFrame(rows)


# ============================================================
# ÉTAPE 10 — GAP  (corrigée : cas vides)
# ============================================================
def calcul_gap(df_per, realise, prevision):
    obj = df_per.groupby(["Article", "Agence"], as_index=False).agg(
        Objectif_Annuel=("Objectif_Annuel", "max"))

    if realise.empty or "Réalisé" not in realise.columns:
        r = pd.DataFrame(columns=["Article", "Agence", "Realise"])
    else:
        r = realise.rename(columns={"Réalisé": "Realise"})

    if prevision.empty or "Article" not in prevision.columns:
        p = pd.DataFrame(columns=["Article", "Agence", "Prevision"])
    else:
        p = prevision.groupby(["Article", "Agence"], as_index=False).agg(
            Prevision=("Prévision", "sum"))

    res = (obj.merge(r, on=["Article", "Agence"], how="left")
              .merge(p, on=["Article", "Agence"], how="left"))
    res = res.fillna({"Realise": 0, "Prevision": 0, "Objectif_Annuel": 0})
    res["Total_Projeté"] = res["Realise"] + res["Prevision"]
    res["GAP"] = res["Objectif_Annuel"] - res["Total_Projeté"]
    res["Alerte"] = np.where(res["GAP"] < 0, "🔴 DÉFICIT",
                     np.where(res["GAP"] > 0, "🟠 SURPLUS", "✅ ATTEINT"))
    return res


# ============================================================
# UPLOAD
# ============================================================
def zone_upload():
    st.sidebar.header("📤 1. Charger les fichiers")
    st.sidebar.caption("Vide = référentiel intégré + démo")

    ventes_f = st.sidebar.file_uploader(
        "📄 Ventes (Date, Article, Agence, Volume)",
        type=["xlsx", "csv"], key="up_ventes")
    mapr_f = st.sidebar.file_uploader(
        "📄 Mapping Région (Agence, Région)",
        type=["xlsx", "csv"], key="up_mapr")
    obj_f = st.sidebar.file_uploader(
        "📄 Objectifs (Article, Agence, Objectif_Annuel)",
        type=["xlsx", "csv"], key="up_obj")
    ref_f = st.sidebar.file_uploader(
        "📄 Référentiel (optionnel — sinon intégré)",
        type=["xlsx", "csv"], key="up_ref")

    def _b(f):
        return f.getvalue() if f else None

    return _b(ventes_f), _b(ref_f), _b(mapr_f), _b(obj_f)


# ============================================================
# FILTRES
# ============================================================
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
# DASHBOARD  (corrigé : cas gap vide)
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
    else:
        st.info("Aucune alerte à afficher.")


# ============================================================
# MAIN
# ============================================================
def main():
    if "mois_clotures" not in st.session_state:
        st.session_state.mois_clotures = DEFAUT_MOIS_CLOTURES

    v_b, r_b, m_b, o_b = zone_upload()
    df_brut = charger_donnees(v_b, r_b, m_b, o_b)

    with st.sidebar.expander("👁️ Aperçu des données"):
        st.write(f"**Lignes :** {len(df_brut):,}")
        st.write(f"**Colonnes :** {list(df_brut.columns)}")
        st.dataframe(df_brut.head(5), use_container_width=True)

    matrice = construire_matrice(df_brut)

    filtres, mois_clotures = construire_sidebar(
        df_brut, st.session_state.mois_clotures)
    st.session_state.mois_clotures = mois_clotures

    df_per, mode = get_perimetre(df_brut, filtres)
    if df_per.empty:
        st.error("❌ Aucune donnée pour ce périmètre. Modifiez les filtres.")
        st.stop()

    realise   = calcul_realise_cumule(df_per, mois_clotures)
    indices   = calcul_indices(df_per)
    sarr      = calcul_sarr(df_per, indices)
    tendance  = calcul_tendance(sarr)
    prevision = calcul_prevision(sarr, tendance, indices, mois_clotures)
    gap       = calcul_gap(df_per, realise, prevision)

    afficher_dashboard(mode, df_per, realise, indices, sarr,
                       tendance, prevision, gap)


if __name__ == "__main__":
    main()

# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# Mode Global vs Mode Filtré — Workflow 11 étapes
# UN SEUL UPLOAD : historique des ventes
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Moteur Ventes — Historique",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAUT_MOIS_CLOTURES = 8
ANNEES_HISTO = 2

# ============================================================
# RÉFÉRENTIEL INTÉGRÉ (69 SKU du PDF Classeur2)
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

# Liste des agences (pour mapping région automatique)
AGENCES_DEMO = ["Alger Centre", "Oran", "Constantine", "Annaba", "Blida",
                "Sétif", "Tlemcen", "Béjaïa", "Batna", "Tizi Ouzou",
                "Djelfa", "Biskra", "Tiaret", "Skikda", "Chlef"]
REGIONS = ["Nord", "Ouest", "Est", "Centre", "Sud"]

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
    """Mapping Agence → Région automatique (round-robin)."""
    return pd.DataFrame({
        "Agence": agences,
        "Région": [REGIONS[i % len(REGIONS)] for i in range(len(agences))],
    })


def generer_objectifs_auto(ref, mapr):
    """Génère des objectifs annuels fictifs (5k–20k) par Article × Agence."""
    np.random.seed(7)
    obj = (ref[["Article"]].assign(key=1)
              .merge(mapr[["Agence"]].assign(key=1), on="key")
              .drop("key", axis=1))
    obj["Objectif_Annuel"] = np.random.randint(5000, 20000, size=len(obj))
    return obj


def lire_fichier(uploaded_file):
    """Lit un fichier uploadé (xlsx ou csv) et retourne un DataFrame."""
    b = uploaded_file.getvalue()
    try:
        return pd.read_excel(BytesIO(b))
    except Exception:
        try:
            return pd.read_csv(BytesIO(b))
        except Exception as e:
            st.error(f"❌ Impossible de lire le fichier : {e}")
            st.stop()


# ============================================================
# ÉTAPE 1 — CHARGEMENT + ENRICHISSEMENT + FUSION
# ============================================================
@st.cache_data(show_spinner="⏳ Chargement et enrichissement du fichier...")
def charger_et_enrichir(file_bytes):
    """
    Charge l'historique des ventes, l'enrichit avec :
    - le référentiel intégré (Positionnement, Occasion, Format, Contenance)
    - un mapping région automatique
    - des objectifs annuels automatiques
    """
    # --- Lecture du fichier uploadé ---
    try:
        ventes = pd.read_excel(BytesIO(file_bytes))
    except Exception:
        ventes = pd.read_csv(BytesIO(file_bytes))

    # --- Vérification des colonnes obligatoires ---
    cols_obligatoires = ["Date", "Article", "Agence", "Volume"]
    manquantes = [c for c in cols_obligatoires if c not in ventes.columns]
    if manquantes:
        st.error(f"❌ Colonnes manquantes dans le fichier : {manquantes}")
        st.info(f"Colonnes trouvées : {list(ventes.columns)}")
        st.stop()

    # --- Normalisation Date ---
    ventes["Date"] = pd.to_datetime(ventes["Date"], errors="coerce")
    ventes = ventes.dropna(subset=["Date"])
    ventes["Mois"]  = ventes["Date"].dt.month
    ventes["Annee"] = ventes["Date"].dt.year

    # --- Référentiel intégré ---
    ref = construire_referentiel_integre()

    # --- Si le fichier contient déjà Positionnement/Occasion, on les garde ---
    cols_ref = ["Article", "Positionnement", "Occasion", "Format",
                "Contenance_cl", "Contenance_hl"]
    ref_merge = ref[cols_ref].copy()

    # --- Fusion ventes ↔ référentiel ---
    df = ventes.merge(ref_merge, on="Article", how="left", suffixes=("", "_ref"))

    # Si Positionnement/Occasion étaient déjà dans ventes, on garde la version du fichier
    for col in ["Positionnement", "Occasion", "Format", "Contenance_cl", "Contenance_hl"]:
        if col in ventes.columns and f"{col}_ref" in df.columns:
            df[col] = df[col].fillna(df[f"{col}_ref"])
            df.drop(columns=[f"{col}_ref"], inplace=True)
        elif f"{col}_ref" in df.columns:
            df[col] = df[f"{col}_ref"]
            df.drop(columns=[f"{col}_ref"], inplace=True)

    # --- Mapping région ---
    agences = sorted(df["Agence"].dropna().unique().tolist())
    if "Région" not in df.columns:
        mapr = construire_mapping_auto(agences)
        df = df.merge(mapr, on="Agence", how="left")

    # --- Objectifs ---
    if "Objectif_Annuel" not in df.columns:
        mapr_used = df[["Agence", "Région"]].drop_duplicates() if "Région" in df.columns \
                    else construire_mapping_auto(agences)
        obj = generer_objectifs_auto(ref, mapr_used)
        df = df.merge(obj, on=["Article", "Agence"], how="left")
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
# ÉTAPE 4 — PÉRIMÈTRE (GLOBAL vs FILTRÉ)
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
# ÉTAPE 8 — TENDANCE
# ============================================================
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


# ============================================================
# ÉTAPE 9 — PRÉVISION
# ============================================================
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


# ============================================================
# ÉTAPE 10 — GAP
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
# UPLOAD — UN SEUL FICHIER
# ============================================================
def zone_upload():
    st.sidebar.header("📤 1. Charger l'historique des ventes")
    st.sidebar.caption("Un seul fichier Excel/CSV")

    f = st.sidebar.file_uploader(
        "📄 Historique des ventes (Date, Article, Agence, Volume)",
        type=["xlsx", "csv"], key="up_hist")
    return f


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
    else:
        st.info("Aucune alerte à afficher.")


# ============================================================
# MAIN
# ============================================================
def main():
    if "mois_clotures" not in st.session_state:
        st.session_state.mois_clotures = DEFAUT_MOIS_CLOTURES

    # --- Upload UNIQUE ---
    fichier = zone_upload()

    if fichier is None:
        st.info("👈 Uploadez votre historique des ventes dans la sidebar pour démarrer.")
        st.markdown("### 📋 Format attendu")
        st.markdown("""
        Un fichier **Excel** ou **CSV** avec au minimum ces colonnes :

        | Date | Article | Agence | Volume |
        |---|---|---|---|
        | 2023-01-15 | Caprice Ananas 100 cl VER | Alger Centre | 1250 |
        | 2023-01-15 | Caprice Ananas 100 cl VER | Oran | 980 |

        **Colonnes optionnelles** (auto-complétées si absentes) :
        - `Positionnement`, `Occasion` → déduits du référentiel intégré (69 SKU)
        - `Format`, `Contenance_cl` → déduits du nom de l'article
        - `Région` → généré automatiquement (mapping Agence → Région)
        - `Objectif_Annuel` → généré automatiquement

        **Le minimum absolu** : `Date`, `Article`, `Agence`, `Volume`.
        """)
        st.stop()

    # --- Chargement + enrichissement ---
    file_bytes = fichier.getvalue()
    df_brut = charger_et_enrichir(file_bytes)

    with st.sidebar.expander("👁️ Aperçu des données"):
        st.write(f"**Lignes :** {len(df_brut):,}")
        st.write(f"**Colonnes :** {list(df_brut.columns)}")
        st.dataframe(df_brut.head(5), use_container_width=True)

    # --- Matrice ---
    matrice = construire_matrice(df_brut)

    # --- Filtres ---
    filtres, mois_clotures = construire_sidebar(
        df_brut, st.session_state.mois_clotures)
    st.session_state.mois_clotures = mois_clotures

    # --- Périmètre ---
    df_per, mode = get_perimetre(df_brut, filtres)
    if df_per.empty:
        st.error("❌ Aucune donnée pour ce périmètre. Modifiez les filtres.")
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

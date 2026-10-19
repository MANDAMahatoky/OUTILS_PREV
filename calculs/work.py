# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# Version FINALE (Lecture 100% garantie avec Barre de Progression)
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

st.set_page_config(page_title="Moteur Ventes", page_icon="📊", layout="wide")

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
    ("Caprice Bonbon Anglais 50 cl PET",  "MILIEU", "IC (Individual/Immediate Consumption)"),
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

REF_DICT = {art: (pos, occ) for art, pos, occ in REFERENTIEL_DATA}

# ============================================================
# MAPPING DES RÉGIONS (15 Agences)
# ============================================================
AGENCES_DATA = [
    ("01-Tanjombato", "Centre"), ("11-Andranomahery", "Centre"), ("12-Antsirabe", "Centre"),
    ("09-Tamatave", "Est"), ("18-Ambanja", "Est"), ("19-Sambava", "Est"), ("08-Manakara", "Est"),
    ("07-Majunga", "Ouest"), ("23-Morondava", "Ouest"),
    ("24-Fort Dauphin", "Sud"), ("04-Tulear", "Sud"), ("05-Fianarantsoa", "Sud"), ("06-Ihosy", "Sud"),
    ("21-NosyBe", "Nord"), ("03-Diego", "Nord"),
]

MOIS_FR_INV = {
    "JANVIER": 1, "FÉVRIER": 2, "FEVRIER": 2, "MARS": 3, "AVRIL": 4,
    "MAI": 5, "JUIN": 6, "JUILLET": 7, "AOÛT": 8, "AOUT": 8,
    "SEPTEMBRE": 9, "OCTOBRE": 10, "NOVEMBRE": 11, "DÉCEMBRE": 12, "DECEMBRE": 12
}

def extraire_format(article: str) -> str:
    a = str(article).upper()
    if "CAN" in a: return "CAN"
    if "PET" in a: return "PET"
    if "VER" in a: return "VER"
    return "AUTRE"

def extraire_contenance(article: str) -> int:
    m = re.search(r"(\d+)\s*C?L", str(article).upper())
    return int(m.group(1)) if m else 0

# ============================================================
# LECTEUR AVEC BARRE DE PROGRESSION
# ============================================================
def extraire_ventes_sur_mesure(raw: pd.DataFrame):
    rows = []
    stats = {
        "total_lignes_fichier": len(raw), 
        "ignorees_vides": 0, 
        "ignorees_totaux": 0, 
        "ignorees_erreurs": 0,
        "valides": 0
    }
    
    progress_bar = st.progress(0, text="Lecture des données en cours...")
    
    for i in range(len(raw)):
        if i % 100 == 0:
            progress_bar.progress(i / len(raw), text=f"Lecture ligne {i:,} / {len(raw):,}...")
            
        try:
            annee_val   = raw.iloc[i, 0]
            mois_val    = raw.iloc[i, 1]
            cat_val     = raw.iloc[i, 2]
            marque_val  = raw.iloc[i, 3]
            agence_val  = raw.iloc[i, 4]
            article_val = raw.iloc[i, 5]
            volume_val  = raw.iloc[i, 6]

            if pd.isna(annee_val) or pd.isna(mois_val) or pd.isna(article_val) or pd.isna(volume_val):
                stats["ignorees_vides"] += 1
                continue

            if str(article_val).strip().upper() == "TOTAL" or str(agence_val).strip().upper() == "TOTAL":
                stats["ignorees_totaux"] += 1
                continue

            vol_str = str(volume_val).replace(" ", "").replace(",", ".").replace("\xa0", "")
            try:
                volume = float(vol_str)
            except ValueError:
                stats["ignorees_erreurs"] += 1
                continue

            try:
                annee = int(annee_val)
            except ValueError:
                stats["ignorees_erreurs"] += 1
                continue

            if isinstance(mois_val, str):
                mois_str = mois_val.strip().upper()
                mois = MOIS_FR_INV.get(mois_str)
                if not mois:
                    try: mois = int(mois_val)
                    except: mois = 1
            else:
                try: mois = int(mois_val)
                except: mois = 1

            if not mois or mois < 1 or mois > 12:
                mois = 1

            date_val = pd.Timestamp(year=annee, month=mois, day=15)

            art_propre = re.sub(r"^\d+-", "", str(article_val).strip())
            pos_occ = REF_DICT.get(art_propre, ("INCONNU", "INCONNU"))
            positionnement = pos_occ[0]
            occasion = pos_occ[1]

            segment = re.sub(r"^\d+-", "", str(cat_val).strip()).upper() if not pd.isna(cat_val) else "INCONNU"
            marque = re.sub(r"^\d+-", "", str(marque_val).strip()).upper() if not pd.isna(marque_val) else "INCONNU"

            rows.append({
                "Date": date_val, 
                "Article": art_propre, 
                "Agence": str(agence_val).strip(),
                "Volume": volume, 
                "Segment": segment,
                "Marque": marque,
                "Positionnement": positionnement,
                "Occasion": occasion
            })
            stats["valides"] += 1
        except Exception:
            stats["ignorees_erreurs"] += 1
            continue

    progress_bar.empty()
    df = pd.DataFrame(rows)
    return df, stats

# ============================================================
# ENRICHISSEMENT
# ============================================================
def enrichir_ventes(ventes: pd.DataFrame) -> pd.DataFrame:
    df = ventes.copy()
    
    df["Format"] = df["Article"].apply(extraire_format)
    df["Contenance"] = df["Article"].apply(extraire_contenance)
    
    map_region = dict(AGENCES_DATA)
    df["Région"] = df["Agence"].map(map_region).fillna("Inconnu")
    
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Mois"]  = df["Date"].dt.month.fillna(1).astype(int)
    df["Annee"] = df["Date"].dt.year.fillna(2024).astype(int)

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
            # On lit TOUT sans rien supposer
            raw = pd.read_excel(BytesIO(uploaded_file.getvalue()), header=None)
        except Exception:
            raw = pd.read_csv(BytesIO(uploaded_file.getvalue()), header=None)
        
        ventes, stats = extraire_ventes_sur_mesure(raw)
            
        if ventes.empty:
            st.sidebar.error("❌ Aucune donnée valide extraite.")
            st.stop()
            
        df_brut = enrichir_ventes(ventes)
        
        st.sidebar.success("✅ Fichier chargé !")
        with st.sidebar.expander("🔍 DIAGNOSTIC EXACT"):
            st.write(f"**Lignes dans le fichier Excel :** {stats['total_lignes_fichier']:,}")
            st.write(f"**Lignes vides (ignorées) :** {stats['ignorees_vides']:,}")
            st.write(f"**Lignes 'Total' (ignorées) :** {stats['ignorees_totaux']:,}")
            st.write(f"**Lignes avec erreurs :** {stats['ignorees_erreurs']:,}")
            st.success(f"**Lignes VALIDES conservées :** {stats['valides']:,}")

    else:
        df_brut = pd.DataFrame()
        st.sidebar.warning("⚠️ Mode Démo (Veuillez uploader votre fichier DATA_BRUT.xlsx)")

    st.sidebar.header("🎛️ 2. Filtres")
    
    toutes_les_regions = sorted(list(set([x[1] for x in AGENCES_DATA])))
    sel_regions = st.sidebar.multiselect("Région", toutes_les_regions, default=[])
    
    if len(sel_regions) > 0:
        agences_dispo = [ag for ag, reg in AGENCES_DATA if reg in sel_regions]
    else:
        agences_dispo = [ag for ag, reg in AGENCES_DATA]
    sel_agences = st.sidebar.multiselect("Agence", sorted(agences_dispo), default=[])

    if not df_brut.empty:
        segments_dispo = sorted(df_brut["Segment"].dropna().unique().tolist())
        sel_segments = st.sidebar.multiselect("Segment", segments_dispo, default=[])

        df_filtre = df_brut.copy()
        if len(sel_segments) > 0:
            df_filtre = df_filtre[df_filtre["Segment"].isin(sel_segments)]
        marques_dispo = sorted(df_filtre["Marque"].dropna().unique().tolist())
        sel_marques = st.sidebar.multiselect("Marque", marques_dispo, default=[])

        if len(sel_marques) > 0:
            df_filtre = df_filtre[df_filtre["Marque"].isin(sel_marques)]
        formats_dispo = sorted(df_filtre["Format"].dropna().unique().tolist())
        sel_formats = st.sidebar.multiselect("Format (Emballage)", formats_dispo, default=[])

        if len(sel_formats) > 0:
            df_filtre = df_filtre[df_filtre["Format"].isin(sel_formats)]
        contenances_dispo = sorted(df_filtre["Contenance"].dropna().unique().tolist())
        sel_contenances = st.sidebar.multiselect("Contenance (cl)", contenances_dispo, default=[])

        if len(sel_contenances) > 0:
            df_filtre = df_filtre[df_filtre["Contenance"].isin(sel_contenances)]
        articles_dispo = sorted(df_filtre["Article"].dropna().unique().tolist())
        sel_articles = st.sidebar.multiselect("Article (SKU)", articles_dispo, default=[])
    else:
        sel_segments, sel_marques, sel_formats, sel_contenances, sel_articles = [], [], [], [], []

    sel_positionnements = st.sidebar.multiselect("Positionnement", ["ENTREE", "MILIEU", "PREMIUM"], default=[])
    sel_occasions = st.sidebar.multiselect("Occasion", ["CU (Convivial Units)", "FC (Family/Future Consumption)", "IC (Individual/Immediate Consumption)", "SS (Single serve)"], default=[])

    mois_clotures = st.sidebar.slider("Mois clôturés (M-1)", 1, 12, DEFAUT_MOIS_CLOTURES)

    if df_brut.empty:
        st.info("👈 Uploadez le fichier `DATA_BRUT.xlsx` dans la barre latérale pour démarrer l'analyse.")
        st.stop()

    filtres = {
        "Région": sel_regions, "Agence": sel_agences, "Segment": sel_segments,
        "Marque": sel_marques, "Format": sel_formats, "Contenance": sel_contenances,
        "Article": sel_articles,
        "Positionnement": sel_positionnements,
        "Occasion": sel_occasions
    }

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

    st.title("📊 Moteur de pilotage des ventes")
    badge = "🟢 MODE GLOBAL" if mode == "GLOBAL" else "🟣 MODE FILTRÉ"
    
    # Affichage du VRAI nombre de lignes
    st.subheader(f"{badge} — {len(df_per):,} lignes de détail analysées")

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

    st.divider()
    st.markdown("### 📋 Détail complet des données lues (Preuve de lecture)")
    with st.expander("Cliquez pour afficher toutes les lignes extraites"):
        st.dataframe(
            df_per[["Date", "Segment", "Marque", "Article", "Agence", "Positionnement", "Occasion", "Format", "Contenance", "Volume"]]
            .sort_values(["Date", "Agence", "Article"]), 
            use_container_width=True, height=500
        )

if __name__ == "__main__":
    main()

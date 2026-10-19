# ============================================================
# MOTEUR DE PILOTAGE DES VENTES — Streamlit
# UN SEUL UPLOAD — LECTEUR ADAPTATIF (format reporting)
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
    """Convertit 'janvier', 'Jan', 'JANVIER', 'January' → 1..12."""
    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    if s in MOIS_FR_INV:
        return MOIS_FR_INV[s]
    if s in MOIS_EN_INV:
        return MOIS_EN_INV[s]
    # 'janv.', 'févr.', 'sept.' → 3 premières lettres
    s3 = s[:3]
    for k, v in MOIS_FR_INV.items():
        if k.startswith(s3):
            return v
    return None


# ============================================================
# DÉTECTION AUTOMATIQUE DE STRUCTURE
# ============================================================
def detecter_structure(raw: pd.DataFrame) -> dict:
    """
    Analyse les 30 premières lignes pour détecter :
    - la ligne d'en-tête
    - les colonnes Date / Article / Agence / Volume
    - la structure verticale (mois en lignes) ou croisée (mois en colonnes)
    """
    resultat = {
        "header_row": None,
        "colonnes": {},
        "structure": "inconnue",
        "annees_detectees": [],
        "mois_en_lignes": False,
        "mois_en_colonnes": False,
    }

    # --- Chercher la ligne d'en-tête (mots-clés métier) ---
    mots_cles = ["date", "article", "agence", "volume", "mois", "année",
                 "annee", "produit", "sku", "magasin", "point de vente",
                 "quantité", "quantite", "total", "qty", "year", "month",
                 "product", "store", "region"]
    best_row = None
    best_score = 0
    for i in range(min(30, len(raw))):
        row_vals = [str(v).strip().lower() for v in raw.iloc[i].values]
        score = sum(1 for v in row_vals if v in mots_cles or any(m in v for m in mots_cles))
        if score > best_score:
            best_score = score
            best_row = i
    if best_score >= 2:
        resultat["header_row"] = best_row
        resultat["colonnes"]["brut"] = [str(v).strip() for v in raw.iloc[best_row].values]

    # --- Détection années (4 chiffres 2015–2030) ---
    annees = set()
    for i in range(min(50, len(raw))):
        for v in raw.iloc[i].values:
            s = str(v).strip()
            if s.isdigit() and 2015 <= int(s) <= 2030:
                annees.add(int(s))
    resultat["annees_detectees"] = sorted(annees)

    # --- Détection mois en lignes (colonne avec 'janvier', 'février'...) ---
    for col in range(raw.shape[1]):
        col_vals = [str(v).strip().upper() for v in raw.iloc[:, col].values if pd.notna(v)]
        n_mois = sum(1 for v in col_vals if v in MOIS_FR_INV or v in MOIS_EN_INV)
        if n_mois >= 6:
            resultat["mois_en_lignes"] = True
            break

    # --- Détection mois en colonnes (header contient 'janvier', 'février'...) ---
    for row in range(min(10, len(raw))):
        row_vals = [str(v).strip().upper() for v in raw.iloc[row].values]
        n_mois = sum(1 for v in row_vals if v in MOIS_FR_INV or v in MOIS_EN_INV)
        if n_mois >= 6:
            resultat["mois_en_colonnes"] = True
            break

    # --- Structure globale ---
    if resultat["mois_en_colonnes"]:
        resultat["structure"] = "CROISÉE (mois en colonnes)"
    elif resultat["mois_en_lignes"]:
        resultat["structure"] = "VERTICALE (mois en lignes)"
    else:
        resultat["structure"] = "INCONNUE"

    return resultat


# ============================================================
# EXTRACTION INTELLIGENTE
# ============================================================
def extraire_ventes(raw: pd.DataFrame, struct: dict) -> pd.DataFrame:
    """
    Tente d'extraire une base plate (Date, Article, Agence, Volume)
    depuis différents formats de reporting.
    """
    rows = []

    # --- Cas 1 : structure VERTICALE (mois + année + article + agence + volume en lignes) ---
    if struct["structure"].startswith("VERTICALE"):
        # Identifier les colonnes par mots-clés
        header_idx = struct["header_row"] if struct["header_row"] is not None else 0
        header = [str(v).strip().lower() for v in raw.iloc[header_idx].values]

        def find_col(keywords):
            for i, h in enumerate(header):
                if any(k in h for k in keywords):
                    return i
            return None

        col_date    = find_col(["date"])
        col_annee   = find_col(["année", "annee", "year", "an"])
        col_mois    = find_col(["mois", "month"])
        col_article = find_col(["article", "produit", "sku", "product"])
        col_agence  = find_col(["agence", "magasin", "store", "point", "pdv"])
        col_volume  = find_col(["volume", "quantité", "quantite", "qty", "total", "qté"])

        if col_article is not None and col_agence is not None and col_volume is not None:
            for i in range(header_idx + 1, len(raw)):
                try:
                    art = raw.iloc[i, col_article]
                    ag  = raw.iloc[i, col_agence]
                    vol = raw.iloc[i, col_volume]
                    if pd.isna(art) or pd.isna(ag) or pd.isna(vol):
                        continue
                    try:
                        vol = float(vol)
                    except (ValueError, TypeError):
                        continue

                    # Construire la date
                    if col_date is not None and pd.notna(raw.iloc[i, col_date]):
                        date_val = pd.to_datetime(raw.iloc[i, col_date], errors="coerce")
                    elif col_annee is not None and col_mois is not None:
                        annee = int(raw.iloc[i, col_annee]) if pd.notna(raw.iloc[i, col_annee]) else None
                        mois_val = raw.iloc[i, col_mois]
                        mois = normaliser_mois(mois_val) if isinstance(mois_val, str) else mois_val
                        if annee and mois:
                            date_val = pd.Timestamp(year=annee, month=int(mois), day=15)
                        else:
                            continue
                    else:
                        continue

                    if pd.isna(date_val):
                        continue

                    rows.append({
                        "Date": date_val,
                        "Article": str(art).strip(),
                        "Agence": str(ag).strip(),
                        "Volume": vol,
                    })
                except Exception:
                    continue

            if rows:
                return pd.DataFrame(rows)

    # --- Cas 2 : structure CROISÉE (mois en colonnes) ---
    if struct["structure"].startswith("CROISÉE"):
        # Trouver la ligne d'en-tête qui contient les mois
        header_idx = None
        for i in range(min(10, len(raw))):
            row_vals = [str(v).strip().upper() for v in raw.iloc[i].values]
            if sum(1 for v in row_vals if v in MOIS_FR_INV or v in MOIS_EN_INV) >= 6:
                header_idx = i
                break

        if header_idx is None:
            return pd.DataFrame()

        header = [str(v).strip() for v in raw.iloc[header_idx].values]

        # Détecter les colonnes de mois
        mois_cols = {}
        for i, h in enumerate(header):
            m = normaliser_mois(h)
            if m:
                mois_cols[i] = m

        # Chercher les colonnes identifiantes (article, agence, année)
        header_lower = [h.lower() for h in header]
        col_annee   = next((i for i, h in enumerate(header_lower) if "ann" in h or "year" in h), None)
        col_article = next((i for i, h in enumerate(header_lower) if "article" in h or "produit" in h), None)
        col_agence  = next((i for i, h in enumerate(header_lower) if "agence" in h or "magasin" in h), None)

        # Si pas trouvé, prendre les colonnes 0-3 comme identifiants
        if col_article is None:
            col_article = 3 if len(header) > 3 else 0
        if col_agence is None:
            col_agence = 4 if len(header) > 4 else 1

        # Parcourir les lignes de données
        for i in range(header_idx + 1, len(raw)):
            annee = None
            if col_annee is not None and pd.notna(raw.iloc[i, col_annee]):
                try:
                    annee = int(raw.iloc[i, col_annee])
                except (ValueError, TypeError):
                    pass
            if annee is None:
                # Fallback : prendre l'année détectée
                annee = struct["annees_detectees"][0] if struct["annees_detectees"] else None

            art = raw.iloc[i, col_article] if pd.notna(raw.iloc[i, col_article]) else None
            ag  = raw.iloc[i, col_agence] if pd.notna(raw.iloc[i, col_agence]) else None

            if art is None or ag is None or annee is None:
                continue

            for col_idx, mois in mois_cols.items():
                try:
                    vol = float(raw.iloc[i, col_idx])
                except (ValueError, TypeError):
                    continue
                date_val = pd.Timestamp(year=annee, month=mois, day=15)
                rows.append({
                    "Date": date_val,
                    "Article": str(art).strip(),
                    "Agence": str(ag).strip(),
                    "Volume": vol,
                })

        if rows:
            return pd.DataFrame(rows)

    return pd.DataFrame()


# ============================================================
# CHARGEMENT FINAL
# ============================================================
@st.cache_data(show_spinner="⏳ Chargement du fichier...")
def charger_et_enrichir(file_bytes):
    # Lecture brute
    try:
        raw = pd.read_excel(BytesIO(file_bytes), header=None)
    except Exception:
        raw = pd.read_csv(BytesIO(file_bytes), header=None)

    return raw


def enrichir_ventes(ventes: pd.DataFrame) -> pd.DataFrame:
    """Ajoute référentiel, région, objectifs."""
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
# INTERFACE — DIAGNOSTIC + MAPPING MANUEL
# ============================================================
def interface_diagnostic(raw: pd.DataFrame):
    """Affiche le diagnostic et permet le mapping manuel si nécessaire."""
    st.subheader("🔍 Diagnostic du fichier")

    # --- Stats ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Lignes", f"{raw.shape[0]:,}")
    c2.metric("Colonnes", raw.shape[1])
    c3.metric("Cellules non vides", f"{raw.notna().sum().sum():,}")

    # --- Détection automatique ---
    struct = detecter_structure(raw)

    st.markdown("### 🤖 Détection automatique")
    st.write(f"**Structure détectée :** `{struct['structure']}`")
    st.write(f"**Ligne d'en-tête probable :** `{struct['header_row']}`")
    st.write(f"**Années détectées :** `{struct['annees_detectees']}`")
    if struct["colonnes"].get("brut"):
        st.write(f"**Colonnes de la ligne d'en-tête :** `{struct['colonnes']['brut']}`")

    # --- Aperçu brut ---
    st.markdown("### 📋 Aperçu brut (30 premières lignes)")
    st.dataframe(raw.head(30), use_container_width=True, height=400)

    return struct


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
# SIDEBAR
# ============================================================
def zone_upload():
    st.sidebar.header("📤 1. Charger l'historique des ventes")
    f = st.sidebar.file_uploader(
        "📄 Fichier Excel/CSV (toutes années)",
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
# MAIN
# ============================================================
def main():
    if "mois_clotures" not in st.session_state:
        st.session_state.mois_clotures = DEFAUT_MOIS_CLOTURES

    # --- Upload ---
    fichier = zone_upload()

    if fichier is None:
        st.title("📊 Moteur de pilotage des ventes")
        st.info("👈 Uploadez votre historique des ventes dans la sidebar pour démarrer.")
        st.markdown("""
        ### 📋 Formats acceptés

        L'application **détecte automatiquement** le format de votre fichier :

        1. **Base plate** (recommandé) :
           | Date | Article | Agence | Volume |
           |---|---|---|---|

        2. **Tableau croisé** (mois en colonnes) :
           | Année | Article | Agence | Janvier | Février | ... |
           |---|---|---|---|---|---|

        3. **Tableau vertical** (mois en lignes) :
           | Année | Mois | Article | Agence | Volume |
           |---|---|---|---|---|

        ### 🔍 Diagnostic automatique
        Une fois le fichier uploadé, un **diagnostic complet** s'affiche pour vérifier la lecture.
        """)
        st.stop()

    # --- Lecture brute ---
    file_bytes = fichier.getvalue()
    raw = charger_et_enrichir(file_bytes)

    # --- Diagnostic ---
    struct = interface_diagnostic(raw)

    # --- Extraction ---
    st.markdown("### ⚙️ Extraction des ventes")
    ventes = extraire_ventes(raw, struct)

    if ventes.empty:
        st.error("❌ Impossible d'extraire les ventes au format (Date, Article, Agence, Volume).")
        st.markdown("""
        ### 🔧 Que faire ?

        **Option 1 — Format standard** : convertissez votre fichier au format :

        | Date | Article | Agence | Volume |
        |---|---|---|---|
        | 2024-01-15 | Caprice Ananas 100 cl VER | 01-Tanjombato | 1250 |

        **Option 2 — Dites-moi la structure** : envoyez-moi les 10 premières lignes
        de votre fichier (copier-coller) et j'adapte le lecteur précisément.
        """)
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

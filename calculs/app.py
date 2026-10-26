import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import unicodedata

st.set_page_config(page_title="Étape 1 : Données Brutes", layout="wide")
st.title("Étape 1 : Ingestion & Enrichissement des Données")

# ==============================================================================
# RÉFÉRENTIEL (Simule le Fichier PDF)
# ==============================================================================
def generer_catalogue_exact():
    data_raw = [
        ("Booster Appel-Mix 50CL VER", "PREMIUM", "CU"),
        ("Booster Tornado 50CL VER VER", "PREMIUM", "CU"),
        ("Caprice Ananas 100 cl VER", "MILIEU", "FC"),
        ("Caprice Ananas 150 cl PET", "PREMIUM", "FC"),
        ("Caprice Ananas 30 cl VER", "MILIEU", "IC"),
        ("Caprice Bonbon Anglais 100 cl VER", "MILIEU", "FC"),
        ("Caprice Bonbon Anglais 150 cl PET", "PREMIUM", "FC"),
        ("Caprice Bonbon Anglais 30 cl VER", "MILIEU", "IC"),
        ("Caprice Bonbon Anglais 33 cl CAN", "MILIEU", "IC"),
        ("Caprice Bonbon Anglais 35 cl PET", "MILIEU", "IC"),
        ("Caprice Bonbon Anglais 50 cl PET", "MILIEU", "IC"),
        ("Caprice Grenadine 100 cl VER", "MILIEU", "FC"),
        ("Caprice Grenadine 150 cl PET", "PREMIUM", "FC"),
        ("Caprice Grenadine 30 cl VER", "MILIEU", "IC"),
        ("Caprice Grenadine 33 cl CAN", "MILIEU", "IC"),
        ("Caprice Grenadine 35 cl PET", "MILIEU", "IC"),
        ("Caprice Grenadine 50 cl PET", "MILIEU", "IC"),
        ("Caprice Orange 100 cl VER", "MILIEU", "FC"),
        ("Caprice Orange 150 cl PET", "PREMIUM", "FC"),
        ("Caprice Orange 30 cl VER", "MILIEU", "IC"),
        ("Caprice Orange 33 cl CAN", "MILIEU", "IC"),
        ("Caprice Orange 35 cl PET", "MILIEU", "IC"),
        ("Caprice Orange 50 cl PET", "MILIEU", "IC"),
        ("Caprice Citron 100 cl VER", "MILIEU", "FC"),
        ("Caprice Citron 150 cl PET", "PREMIUM", "FC"),
        ("Caprice Citron 30 cl VER", "MILIEU", "IC"),
        ("Caprice Citron 50 cl PET", "MILIEU", "IC"),
        ("Tonic 100 cl VER", "MILIEU", "IC"),
        ("Tonic 30 cl VER", "MILIEU", "IC"),
        ("World Cola 100cl VER", "MILIEU", "FC"),
        ("World Cola 100cl WOCO VER", "MILIEU", "FC"),
        ("World Cola 150cl PET", "PREMIUM", "FC"),
        ("World Cola 30cl VER", "MILIEU", "IC"),
        ("World Cola 30cl WOCO VER", "MILIEU", "IC"),
        ("World Cola 33 cl CAN", "MILIEU", "IC"),
        ("World Cola 35cl PET", "MILIEU", "IC"),
        ("World Cola 50cl PET", "MILIEU", "IC"),
        ("Beaufort 33 CL CAN", "MILIEU", "SS"),
        ("Beaufort 33CL VER", "PREMIUM", "SS"),
        ("FRESH 33 cl CAN", "PREMIUM", "IC"),
        ("THB Fresh 33 cl VER", "ENTREE", "SS"),
        ("THB Fresh 65 cl VER", "ENTREE", "CU"),
        ("Gold 8 50 cl CAN", "PREMIUM", "SS"),
        ("Gold 8 50 cl VER", "PREMIUM", "SS"),
        ("Gold Blanche 33cl VER", "PREMIUM", "SS"),
        ("Gold Blanche 50 cl CAN", "PREMIUM", "SS"),
        ("Gold Blanche 50 cl VER", "PREMIUM", "SS"),
        ("Gold Blonde 33 cl VER", "PREMIUM", "SS"),
        ("Gold Blonde 50 cl CAN", "PREMIUM", "SS"),
        ("Gold Blonde 50 cl VER", "PREMIUM", "SS"),
        ("Gold Blonde 65 cl VER", "PREMIUM", "CU"),
        ("Queen s 65 cl VER", "PREMIUM", "CU"),
        ("THB Pilsener 33 cl VER", "MILIEU", "SS"),
        ("THB Pilsener 50 cl CAN", "MILIEU", "CU"),
        ("THB Pilsener 65 cl VER", "MILIEU", "CU"),
        ("Cristal 100 cl VER", "PREMIUM", "IC"),
        ("Cristal 150 cl PET", "PREMIUM", "FC"),
        ("Cristal 30 cl VER", "PREMIUM", "IC"),
        ("Cristal 50 cl VER", "PREMIUM", "IC"),
        ("Cristalline 100 cl PET", "PREMIUM", "IC"),
        ("Cristalline 200 cl PET", "PREMIUM", "FC"),
        ("Eau vive 150 cl PET", "MILIEU", "FC"),
        ("Eau vive 50 cl PET", "MILIEU", "IC"),
        ("Eau vive 50 cl VER", "MILIEU", "IC"),
        ("FOSA 50 cl CAN", "PREMIUM", "IC"),
        ("XXL 30cl BOB VER", "PREMIUM", "IC"),
        ("XXL 30cl VER", "PREMIUM", "IC"),
        ("XXL 33 cl CAN", "PREMIUM", "IC"),
        ("XXL 35cl PET", "PREMIUM", "IC"),
        # Ajout d'articles manquants vus dans votre capture
        ("Skol 50cl VER", "MILIEU", "IC"),
        ("Skol 65cl VER", "MILIEU", "CU"),
        ("Castel beer 50cl VER", "MILIEU", "IC"),
        ("Libertalia 50cl VER", "MILIEU", "IC"),
    ]
    return pd.DataFrame(data_raw, columns=["article", "positionnement", "occasion"])

CATALOGUE = generer_catalogue_exact()

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def normaliser_nom(nom: str) -> str:
    texte = unicodedata.normalize("NFD", str(nom)).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9_]+", "_", texte.strip().lower()).strip("_")

def normaliser_mois(valeur) -> int:
    if pd.isna(valeur): return 1
    if isinstance(valeur, (int, float)): return int(valeur)
    mois_map = {
        "janvier": 1, "janv": 1, "jan": 1, "fevrier": 2, "fevr": 2, "fev": 2, 
        "mars": 3, "mar": 3, "avril": 4, "avr": 4, "mai": 5, "juin": 6, "jun": 6, 
        "juillet": 7, "juil": 7, "jul": 7, "aout": 8, "aug": 8, "septembre": 9, 
        "sept": 9, "sep": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11, 
        "decembre": 12, "dec": 12
    }
    texte = unicodedata.normalize("NFD", str(valeur)).encode("ascii", "ignore").decode("utf-8").lower().strip()
    return mois_map.get(texte, 1)

def extraire_article(nature_str: str) -> str:
    if pd.isna(nature_str): return "Non renseigné"
    match = re.match(r"^\d+-(.*)$", str(nature_str).strip())
    return match.group(1).strip() if match else str(nature_str).strip()

def detecter_format_pivote(df: pd.DataFrame) -> bool:
    if df.shape[1] < 7: return False
    annee0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return annee0.between(1990, 2100).sum() > len(df) * 0.3

# ==============================================================================
# ÉTAPE 1 : INGESTION
# ==============================================================================
def charger_et_enrichir(contenu_excel: bytes) -> pd.DataFrame:
    flux = io.BytesIO(contenu_excel)
    df_raw = pd.read_excel(flux, sheet_name=0, header=None)
    
    # Sauvegarde du nombre de lignes initial
    nb_lignes_initial = len(df_raw)
    
    if detecter_format_pivote(df_raw):
        rename = {df_raw.columns[i]: col for i, col in enumerate(["annee", "mois", "segment", "produit", "agence", "nature", "hl"])}
        df = df_raw.rename(columns=rename).copy()
        
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
        df["mois"] = df["mois"].apply(normaliser_mois)
        df["hl"] = pd.to_numeric(df["hl"], errors="coerce").fillna(0.0)
        
        # Suppression des lignes "Total" (les vrais totaux)
        masque_total = (
            df["segment"].astype(str).str.contains("total", case=False, na=False) |
            df["produit"].astype(str).str.contains("total", case=False, na=False) |
            df["agence"].astype(str).str.contains("total", case=False, na=False) |
            df["nature"].astype(str).str.contains("total", case=False, na=False)
        )
        df = df[~masque_total].copy()
        
        df["article"] = df["nature"].apply(extraire_article)
        df["agence"] = df["agence"].astype(str).str.strip()
        
        # On ne supprime PAS les lignes avec des NaN, on les remplace
        df["annee"] = df["annee"].fillna(2026).astype(int)
        df["mois"] = df["mois"].fillna(1).astype(int)
        
    else:
        # Format tabulaire classique
        df_raw = pd.read_excel(flux, sheet_name=0)
        df_raw.columns = [normaliser_nom(c) for c in df_raw.columns]
        df = df_raw.rename(columns={"volume": "hl", "quantite": "hl"}).copy()
        df["annee"] = pd.to_numeric(df.get("annee", 2026), errors="coerce").fillna(2026).astype(int)
        df["mois"] = df.get("mois", 1).apply(normaliser_mois)
        df["article"] = df.get("article", "Non renseigné").astype(str).str.strip()
        df["agence"] = df.get("agence", "Non renseigné").astype(str).str.strip()
        df["hl"] = pd.to_numeric(df.get("hl", 0.0), errors="coerce").fillna(0.0)

    # Fusion avec le Référentiel
    df = df.merge(CATALOGUE, on="article", how="left")
    df["positionnement"] = df["positionnement"].fillna("Non renseigné")
    df["occasion"] = df["occasion"].fillna("Non renseigné")
    
    return df, nb_lignes_initial

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
st.write("Chargez le fichier `DATA_BRUT.xlsx` pour générer le DataFrame enrichi.")

fichier = st.file_uploader("Fichier Excel (.xlsx)", type=["xlsx"])

if fichier is not None:
    with st.spinner("Lecture et enrichissement des données..."):
        df_enrichi, nb_lignes_initial = charger_et_enrichir(fichier.getvalue())
        
    st.success(f"✅ Fichier lu avec succès. Le fichier source contenait {nb_lignes_initial} lignes.")
    
    st.subheader("Aperçu du DataFrame enrichi")
    st.dataframe(df_enrichi.head(50), width="stretch")
    
    st.subheader("Vérifications de base")
    col1, col2, col3 = st.columns(3)
    col1.metric("Articles uniques", df_enrichi["article"].nunique())
    col2.metric("Agences", df_enrichi["agence"].nunique())
    col3.metric("Volume total (HL)", f"{df_enrichi['hl'].sum():,.0f}")
    
    # Vérification de l'enrichissement
    non_renseignes = df_enrichi[df_enrichi["positionnement"] == "Non renseigné"]
    if not non_renseignes.empty:
        st.warning(f"⚠️ {len(non_renseignes)} lignes n'ont pas trouvé leur correspondance dans le référentiel (mais elles sont bien conservées dans le tableau).")
        
        # Afficher les articles manquants
        articles_manquants = non_renseignes["article"].unique()
        st.write("🔍 **Articles non trouvés (Top 10) :**")
        st.write(articles_manquants[:10])
    else:
        st.success("🎉 100% des lignes ont trouvé leur correspondance !")

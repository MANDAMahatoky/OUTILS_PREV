import streamlit as st
import pandas as pd

# ==========================================
# CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(
    page_title="Workflow CALC.xlsx",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Workflow de Calcul - Fichier CALC.xlsx")
st.markdown("**Documentation interactive de la chaîne de traitement automatisée (Prévisions & S&OP)**")
st.divider()

# ==========================================
# ONGLETS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Vue d'ensemble", 
    "⚙️ Détail des Étapes", 
    "🚦 Conditions Logiques", 
    "🧮 Simulateur"
])

# ==========================================
# ONGLET 1 : VUE D'ENSEMBLE
# ==========================================
with tab1:
    st.header("Vue d'ensemble du flux")
    st.markdown("""
    Le fichier fonctionne comme une chaîne de traitement automatisée. 
    Voici les 10 étapes séquentielles :
    """)
    
    # Diagramme de flux simplifié
    etapes = [
        ("1", "Extraction", "Récupérer les données TCD2"),
        ("2", "Conversion Dates", "Transformer entêtes en mois"),
        ("3", "Réalisés", "SUMIFS par Article/Mois/Agence"),
        ("4", "Numéro Mois", "MONTH() des dates"),
        ("5", "Coefficients", "Récupérer coef Global"),
        ("6", "SARR", "Réalisé / Coefficient"),
        ("7", "Écarts", "SARR M-1 - SARR M-2"),
        ("8", "Prévision Finale", "Coef * MAX(SARR) + Tendance"),
        ("9", "Projection 5 ans", "Même logique (2026-2030)"),
        ("10", "GAP", "Total - Somme Mois 8-12"),
    ]
    
    cols = st.columns(5)
    for i, (num, titre, desc) in enumerate(etapes):
        with cols[i % 5]:
            st.info(f"**Étape {num}**\n\n**{titre}**\n\n{desc}")
    
    st.success("➔ Fin du flux : Alertes visuelles (Rouge si GAP < 0)")

# ==========================================
# ONGLET 2 : DÉTAIL DES ÉTAPES
# ==========================================
with tab2:
    st.header("Détail des Étapes (Quoi / Comment / Data / Quand)")
    
    etapes_detail = {
        "ÉTAPE 1 : Conversion des entêtes de date": {
            "Quoi": "Transformer '2024-01' en '1'",
            "Formule": "=IF(RIGHT(F2,2)*1<0, RIGHT(F2,2)*1, RIGHT(F2,3)*1)",
            "Data": "Entêtes de colonnes",
            "Quand": "Automatique"
        },
        "ÉTAPE 2 : Calcul des dates M-1, M-2...": {
            "Quoi": "Déterminer la date réelle du mois décalé",
            "Formule": "=IFERROR(EDATE(MAXIFS([1]TCD2!$C:$C, [1]TCD2!$B:$B, Article, [1]TCD2!$A:$A, Agence), F$1), \"-\")",
            "Data": "Base TCD2 (Date, Article, Agence)",
            "Quand": "À l'actualisation"
        },
        "ÉTAPE 3 : Récupération du réalisé": {
            "Quoi": "Volume réel vendu",
            "Formule": "=SUMIFS([1]TCD2!$E:$E, [1]TCD2!$B:$B, Article, [1]TCD2!$C:$C, Mois, [1]TCD2!$A:$A, Agence)",
            "Data": "Base TCD2",
            "Quand": "À l'actualisation"
        },
        "ÉTAPE 4 : Extraction du numéro de mois": {
            "Quoi": "Convertir la date en numéro de mois",
            "Formule": "=IFERROR(MONTH(F3), \"-\")",
            "Data": "Colonnes de dates calculées",
            "Quand": "Automatique"
        },
        "ÉTAPE 5 : Récupération du coefficient saisonnier": {
            "Quoi": "Coefficient lié à l'article et au mois",
            "Formule": "=SUMIFS('[1]Calcul_coef (Global)'!$D:$D, '[1]Calcul_coef (Global)'!$A:$A, Article, '[1]Calcul_coef (Global)'!$B:$B, Mois)",
            "Data": "Table Calcul_coef (Global)",
            "Quand": "Automatique"
        },
        "ÉTAPE 6 : Calcul du SARR": {
            "Quoi": "Volume lissé sans effet saisonnier",
            "Formule": "=IFERROR(R3/AP3, 0)",
            "Data": "Réalisé, Coefficient",
            "Quand": "Automatique"
        },
        "ÉTAPE 7 : Calcul des écarts": {
            "Quoi": "Variation entre deux mois consécutifs",
            "Formule": "=Tableau35[[#This Row],[SARR M-1]] - Tableau35[[#This Row],[SARR M-2]]",
            "Data": "Colonnes SARR",
            "Quand": "Automatique"
        },
        "ÉTAPE 8 : Calcul de la prévision finale": {
            "Quoi": "Prévision future combinant tendance et saisonnalité",
            "Formule": "=IF( (Coefficient * MAX(SARR M-1, AVERAGE(SARR M-1:M-3))) + AVERAGE(Ecart-1:Ecart-11) < 0, 0, (Coefficient * MAX(...)) + AVERAGE(...) )",
            "Data": "Coefficients Agence, SARR, Écarts",
            "Quand": "Temps réel"
        },
        "ÉTAPE 9 : Projection long terme (2026-2030)": {
            "Quoi": "Projection sur 5 ans",
            "Formule": "Même logique que l'étape 8 appliquée aux mois futurs (BY à EA)",
            "Data": "Coefficients Agence, SARR",
            "Quand": "Construction budgétaire"
        },
        "ÉTAPE 10 : Calcul du GAP": {
            "Quoi": "Écart entre Total Général et somme des mois 8 à 12",
            "Formule": "=Total_Général (BH) - SOMME(Colonnes 8 à 12)",
            "Data": "Total Général, Mois 8 à 12",
            "Quand": "Consolidation"
        }
    }
    
    for titre, details in etapes_detail.items():
        with st.expander(f"🔹 {titre}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Quoi :** {details['Quoi']}")
                st.markdown(f"**Data :** {details['Data']}")
            with col2:
                st.markdown(f"**Quand :** {details['Quand']}")
            st.code(details['Formule'], language='excel')
            st.caption("Formule Excel extraite du fichier CALC.xlsx")

# ==========================================
# ONGLET 3 : CONDITIONS LOGIQUES
# ==========================================
with tab3:
    st.header("Conditions Logiques (Les 'SI')")
    st.markdown("Règles de gestion automatisées intégrées au fichier :")
    
    conditions = {
        "Condition": [
            "SI (Coefficient * SARR + Tendance) < 0",
            "SI ERREUR (date introuvable)",
            "SI ERREUR (division par 0)",
            "SI GAP < 0",
            "SI Article inconnu"
        ],
        "Action": [
            "Afficher 0",
            "Afficher '-'",
            "Afficher 0",
            "Afficher en Rouge",
            "#N/A (à corriger)"
        ]
    }
    
    df_conditions = pd.DataFrame(conditions)
    st.dataframe(df_conditions, use_container_width=True, hide_index=True)
    
    st.warning("⚠️ Attention : Un GAP négatif (Rouge) indique un déficit de prévision sur le 2ème semestre.")

# ==========================================
# ONGLET 4 : SIMULATEUR
# ==========================================
with tab4:
    st.header("🧮 Simulateur de Prévision (Étape 8)")
    st.markdown("Testez la formule de calcul de la prévision finale en temps réel.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        coefficient = st.number_input("Coefficient Saisonnier", value=1.2, step=0.1)
        sarr_m1 = st.number_input("SARR M-1", value=1500.0, step=100.0)
    with col2:
        sarr_m2 = st.number_input("SARR M-2", value=1400.0, step=100.0)
        sarr_m3 = st.number_input("SARR M-3", value=1300.0, step=100.0)
    with col3:
        ecart_moyen = st.number_input("Moyenne des Écarts", value=50.0, step=10.0)
    
    # Calcul de la prévision
    moyenne_3 = (sarr_m1 + sarr_m2 + sarr_m3) / 3
    max_sarr = max(sarr_m1, moyenne_3)
    prevision_brute = (coefficient * max_sarr) + ecart_moyen
    prevision_finale = max(0, prevision_brute)
    
    st.divider()
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric("Moyenne des 3 SARR", f"{moyenne_3:,.2f}")
        st.metric("MAX (SARR M-1 vs Moyenne)", f"{max_sarr:,.2f}")
    with col_res2:
        st.metric("Prévision Brute", f"{prevision_brute:,.2f}")
        if prevision_brute < 0:
            st.error(f"Prévision Finale (Corrigée à 0) : {prevision_finale:,.2f}")
        else:
            st.success(f"Prévision Finale : {prevision_finale:,.2f}")

# ==========================================
# PIED DE PAGE
# ==========================================
st.divider()
st.caption("Application Streamlit générée à partir du document 'Workflow CALC.xlsx'")

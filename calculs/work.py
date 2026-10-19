import streamlit as st
import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(page_title="Workflow Métier - CALC", page_icon="📊", layout="wide")
st.title("📊 Workflow Métier - Fichier CALC.xlsx")
st.markdown("**Documentation conceptuelle de la chaîne de traitement (Données & Logique)**")
st.divider()

# ==========================================
# ONGLETS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Vue d'ensemble", 
    "⚙️ Détail des Étapes (Données)", 
    "🚦 Conditions Logiques", 
    "🧮 Simulateur"
])

# ==========================================
# ONGLET 1 : VUE D'ENSEMBLE
# ==========================================
with tab1:
    st.header("Vue d'ensemble du flux métier")
    st.markdown("""
    Le fichier est un **moteur de prévision** qui transforme des **données brutes de ventes** 
    en **prévisions futures** via une chaîne de 10 étapes.
    """)
    
    etapes = [
        ("1", "Extraction", "Lire la base de ventes TCD2"),
        ("2", "Dates", "Calculer les périodes M-1, M-2..."),
        ("3", "Réalisés", "Agréger les volumes vendus"),
        ("4", "Mois", "Identifier le mois de chaque vente"),
        ("5", "Coefficients", "Charger la saisonnalité"),
        ("6", "SARR", "Lisser les ventes (désaisonnaliser)"),
        ("7", "Écarts", "Mesurer la tendance"),
        ("8", "Prévision", "Combiner tendance + saisonnalité"),
        ("9", "Projection", "Simuler sur 5 ans"),
        ("10", "GAP", "Contrôler la cohérence"),
    ]
    
    cols = st.columns(5)
    for i, (num, titre, desc) in enumerate(etapes):
        with cols[i % 5]:
            st.info(f"**Étape {num}**\n\n**{titre}**\n\n{desc}")

# ==========================================
# ONGLET 2 : DÉTAIL DES ÉTAPES (DATA & LOGIQUE)
# ==========================================
with tab2:
    st.header("Détail des Étapes : Données (Data) et Logique (Comment)")
    st.caption("Chaque étape décrit les **intitulés des tables** et la **logique de calcul** (sans formule Excel).")

    etapes_metier = [
        {
            "titre": "ÉTAPE 1 : Lecture des entêtes de date",
            "data": "Colonnes d'entête de la feuille (ex: '2024-01', '2024-02'...)",
            "logique": "Lire le texte de l'entête pour en extraire le numéro du mois (1 à 12). Cela permet de relier chaque colonne à un mois précis pour les recherches futures.",
            "quand": "Automatique (à l'ouverture du fichier)."
        },
        {
            "titre": "ÉTAPE 2 : Construction des périodes glissantes (M-1, M-2...)",
            "data": "Table **TCD2** : colonnes `Date`, `Article`, `Agence`.",
            "logique": "Pour chaque Article et Agence, trouver la **dernière date de vente connue**, puis reculer de X mois pour obtenir les périodes M-1, M-2, M-3... jusqu'à M-12.",
            "quand": "À chaque actualisation de la base TCD2."
        },
        {
            "titre": "ÉTAPE 3 : Récupération des Réalisés (Volumes vendus)",
            "data": "Table **TCD2** : colonnes `Article`, `Mois`, `Agence`, `Volume` (col E).",
            "logique": "Faire une **somme conditionnelle** : additionner les volumes vendus en filtrant simultanément sur l'Article, le Mois et l'Agence. Le résultat est le **Réalisé** du mois.",
            "quand": "À chaque actualisation des ventes."
        },
        {
            "titre": "ÉTAPE 4 : Identification du mois du Réalisé",
            "data": "Colonnes de dates calculées à l'Étape 2.",
            "logique": "Extraire le **numéro du mois** (1 à 12) à partir de la date. Cela sert à faire correspondre le réalisé avec le bon coefficient saisonnier.",
            "quand": "Automatique."
        },
        {
            "titre": "ÉTAPE 5 : Chargement du Coefficient Saisonnier Global",
            "data": "Table **Calcul_coef (Global)** : colonnes `Article`, `Mois`, `Coefficient` (col D).",
            "logique": "Pour chaque Article et chaque Mois, chercher le **coefficient de saisonnalité** correspondant. Ce coefficient reflète les variations naturelles des ventes (ex: +30% en été).",
            "quand": "Automatique (dès que le coefficient est disponible)."
        },
        {
            "titre": "ÉTAPE 6 : Calcul du SARR (Ventes Désaisonnalisées)",
            "data": "Réalisé (Étape 3) + Coefficient (Étape 5).",
            "logique": "Diviser le **Réalisé** par le **Coefficient saisonnier**. Cela 'lisse' les ventes en supprimant l'effet de la saison, pour obtenir une **tendance pure** appelée SARR.",
            "quand": "Automatique."
        },
        {
            "titre": "ÉTAPE 7 : Calcul des Écarts (Tendance)",
            "data": "Colonnes de SARR (M-1, M-2, M-3...).",
            "logique": "Calculer la **différence entre deux SARR consécutifs** (SARR M-1 - SARR M-2). Ensuite, faire la **moyenne de tous ces écarts** pour obtenir la **tendance moyenne** des ventes.",
            "quand": "Automatique."
        },
        {
            "titre": "ÉTAPE 8 : Calcul de la Prévision Finale",
            "data": "Coefficient Agence + SARR + Moyenne des Écarts.",
            "logique": "Combiner trois éléments : (1) le **SARR le plus élevé** entre M-1 et la moyenne des 3 derniers mois, (2) le **Coefficient de saisonnalité** de l'agence, (3) la **tendance moyenne** (Étape 7). Si le résultat est négatif, on le ramène à **0**.",
            "quand": "Temps réel (dès qu'une donnée change)."
        },
        {
            "titre": "ÉTAPE 9 : Projection Long Terme (2026-2030)",
            "data": "Coefficients Agence + SARR historique.",
            "logique": "Appliquer la **même logique que l'Étape 8** mais sur les mois des années futures (2026 à 2030). Cela permet de simuler les ventes sur 5 ans pour le budget.",
            "quand": "Lors de la construction budgétaire annuelle."
        },
        {
            "titre": "ÉTAPE 10 : Calcul du GAP (Écart de prévision)",
            "data": "Total Général (col BH) + Somme des Mois 8 à 12.",
            "logique": "Soustraire la **somme des prévisions des mois 8 à 12** du **Total Général annuel**. Si le GAP est **négatif**, cela signifie qu'il manque des prévisions sur le 2ème semestre.",
            "quand": "Lors de la consolidation finale."
        }
    ]

    for etape in etapes_metier:
        with st.expander(f"🔹 {etape['titre']}"):
            st.markdown(f"**📁 Data (Données sources) :** {etape['data']}")
            st.markdown(f"**🧠 Comment (Logique métier) :** {etape['logique']}")
            st.markdown(f"**🕒 Quand :** {etape['quand']}")

# ==========================================
# ONGLET 3 : CONDITIONS LOGIQUES
# ==========================================
with tab3:
    st.header("Conditions Logiques (Les 'SI' du fichier)")
    st.markdown("Règles de gestion automatisées intégrées au moteur de calcul :")
    
    conditions = {
        "Si (Condition)": [
            "La prévision calculée est négative",
            "La date de vente est introuvable",
            "Une division par zéro se produit",
            "Le GAP est négatif (< 0)",
            "Un Article n'existe pas dans la table de référence"
        ],
        "Alors (Action automatique)": [
            "Afficher 0 (pas de vente négative)",
            "Afficher '-' (évite les erreurs #N/A)",
            "Afficher 0 (sécurité)",
            "Afficher en Rouge (alerte visuelle)",
            "#N/A (à corriger manuellement)"
        ]
    }
    
    st.dataframe(pd.DataFrame(conditions), use_container_width=True, hide_index=True)
    
    st.warning("⚠️ Un GAP négatif (Rouge) indique un déficit de prévision sur le 2ème semestre. Il faut ajuster les volumes.")

# ==========================================
# ONGLET 4 : SIMULATEUR
# ==========================================
with tab4:
    st.header("🧮 Simulateur de Prévision (Logique de l'Étape 8)")
    st.markdown("Testez la **logique métier** de calcul de la prévision finale.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        coefficient = st.number_input("Coefficient Saisonnier (Agence)", value=1.2, step=0.1)
        sarr_m1 = st.number_input("SARR M-1 (Ventes lissées)", value=1500.0, step=100.0)
    with col2:
        sarr_m2 = st.number_input("SARR M-2", value=1400.0, step=100.0)
        sarr_m3 = st.number_input("SARR M-3", value=1300.0, step=100.0)
    with col3:
        ecart_moyen = st.number_input("Moyenne des Écarts (Tendance)", value=50.0, step=10.0)
    
    # Logique métier
    moyenne_3 = (sarr_m1 + sarr_m2 + sarr_m3) / 3
    max_sarr = max(sarr_m1, moyenne_3)
    prevision_brute = (coefficient * max_sarr) + ecart_moyen
    prevision_finale = max(0, prevision_brute)
    
    st.divider()
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric("Moyenne des 3 SARR", f"{moyenne_3:,.2f}")
        st.metric("MAX (SARR M-1 vs Moyenne)", f"{max_sarr:,.2f}")
        st.metric("Tendance (Écart moyen)", f"{ecart_moyen:,.2f}")
    with col_res2:
        st.metric("Prévision Brute", f"{prevision_brute:,.2f}")
        if prevision_brute < 0:
            st.error(f"Prévision Finale (Corrigée à 0) : {prevision_finale:,.2f}")
        else:
            st.success(f"Prévision Finale : {prevision_finale:,.2f}")

st.divider()
st.caption("Application Streamlit - Workflow Métier du fichier CALC.xlsx")

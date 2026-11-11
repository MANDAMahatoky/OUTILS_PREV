📘 README — PREVISIONS STAR MADAGASCAR
🎯 Présentation
PREVISIONS STAR MADAGASCAR est une application web interactive développée avec Streamlit permettant de générer des prévisions de ventes (en HL ou en Colis) pour le portefeuille de produits STAR Madagascar (boissons : BG, Bières, Eaux, Energy, Jus, Vins, Négoce).

L'application repose sur un moteur de prévision hybride combinant :

🧮 Run-Rate (projection linéaire du réalisé cumulé)

📊 Indices de saisonnalité (par Agence × Article → Article → Marque → Segment → Global)

📈 CAGR historique ou Tendance linéaire ou Moyenne 3 ans

⚡ Momentum (dynamique court-terme via moyennes mobiles 3 mois)

🎯 Budget Query (écrasement optionnel des prévisions sur le périmètre budgété)

🩹 Ruptures (réintégration des volumes perdus dans le potentiel)

✨ Fonctionnalités principales
Fonctionnalité	Description
🔍 Filtres dynamiques en cascade	Région, Marque, Agence, Contenance, Segment, Emballage, Article, Positionnement, Occasion
📅 Navigation par onglets	Réalisé Cumulé, Indices & SARR, Prévisions, Pareto (ABC), Fiabilité, Ruptures, Données Brutes (optionnel)
📊 KPIs temps réel	Atterrissage vs N-1, Objectif, GAP, Fiabilité (WMAPE)
📈 Visualisation Plotly	Courbe Réalisé vs Prévision, Pareto ABC, Histogramme des ruptures
🎯 Objectif paramétrable	Automatique (taux d'ambition) ou manuel
📤 Export CSV	Tableau pivot des prévisions mensuelles au format Excel
🔬 Diagnostic du modèle	Détail des calculs (Indice, SARR, Momentum, CAGR) pour chaque ligne de prévision
🎨 Charte graphique STAR	Design premium rouge/blanc, composants stylisés (KPI cards, tabs, progress bars)
⚙️ Installation
Prérequis
Python 3.9+

Accès Internet (pour le chargement de la police Inter via Google Fonts)

Dépendances
bash
pip install streamlit pandas numpy plotly openpyxl
Lancement
bash
streamlit run app.py
L'application est accessible sur http://localhost:8501.

📂 Fichiers d'entrée
L'application accepte 4 fichiers Excel, dont 1 obligatoire et 3 optionnels :

1️⃣ Ventes (obligatoire) — DATA_BRUT.xlsx
Fichier brut des ventes, attendu en format pivot avec colonnes :
Année | Mois | Segment | Produit | Agence | Nature | Volume (HL)

Les lignes contenant "TOTAL" sont automatiquement exclues.

La colonne Nature contient l'article préfixé (ex: 12345-Caprice Orange 33 cl CAN).

Le mois peut être numérique (1-12), une date Excel ou un libellé texte (janvier, février…).

2️⃣ Référentiel (optionnel) — Classeur2.xlsx
Onglet Ref actif, colonnes :
Article | Positionnement | Occasion | Contenance (Cl)

Permet de restreindre le périmètre aux articles actifs et d'enrichir la classification (positionnement, occasion, contenance).

Si absent, l'application utilise une liste interne de 70 articles STAR (REF_DEFAUT) couvrant BG, Bières, Eaux, Energy, Alcomix.

3️⃣ Budget Query (optionnel)
Écrase les prévisions sur l'année cible avec les valeurs budgétées.

Détection automatique de la feuille contenant article + valeur + mois

Filtre automatique sur les articles 33 cl CAN

Conversion automatique Volume × Contenance / 10 000 → HL

4️⃣ Ruptures (optionnel)
Onglet Rupture (avec une ligne d'en-tête à ignorer), colonnes :
Mois (ex: "3 2025") | Agence | Article | Volume perdu (HL)

Les volumes perdus sont réintégrés dans le potentiel (hl_potentiel = hl + rupture_hl) pour ne pas biaiser les indices.

🚀 Utilisation
Étape 1 — Importation
Dans la barre latérale gauche, importez :

Le fichier Ventes (obligatoire)

Le Référentiel (optionnel)

Le Budget Query (optionnel)

Les Ruptures (optionnel)

Étape 2 — Paramétrage du modèle
Paramètre	Description	Défaut
Année Cible	Année à projeter	2026
Unité d'affichage	HL ou Colis	HL
Taux d'ambition vs N-1	Objectif = Réalisé N-1 × (1 + taux)	5 %
Forcer objectif manuel	Saisir une valeur absolue	Désactivé
Méthode de prévision	Tendance Linéaire / CAGR Classique / Moyenne 3 ans	Tendance Linéaire
Étape 3 — Paramètres avancés (expander ⚙️)
Année Min / Max IS : Fenêtre de calcul des indices de saisonnalité (défaut : 2024-2025)

Année Min / Max CAGR : Fenêtre historique pour la croissance (défaut : 2017-2025)

Année Clôture : Année du dernier réalisé connu (défaut : 2026)

Mois Cutoff : Dernier mois réalisé de l'année de clôture (défaut : Septembre)

Mois cible (filtre tableau) : Filtre le tableau des prévisions, sans impacter les KPIs globaux

Étape 4 — Filtres de périmètre
Dans l'expander "🎯 Filtres de périmètre", sélectionnez vos dimensions (multi-select en cascade) : Région → Marque → Agence → Contenance → Segment → Emballage → Article → Positionnement → Occasion.

📊 Comprendre les onglets
🗂️ Données Brutes (optionnel)
Affichage du référentiel enrichi (ventes + ruptures + potentiel) sur le périmètre filtré.

📈 Réalisé Cumulé
Tableau agrégé du réalisé jusqu'au cutoff (Ventes Réelles, Pertes Ruptures, Volume Potentiel).

🧮 Indices & SARR
Indices de Saisonnalité : tableau Agence × Article × Mois (1 à 12)

Table SARR : 5 derniers mois avec Momentum absolu et Momentum % (vs M-1)

🔮 Prévisions
Tableau pivot Article × Mois (format Excel) avec recherche, export CSV et détail des calculs (Indice, Base_EXCEL, Momentum, Base_Mensuelle, CAGR).

📊 Pareto (ABC)
Classification ABC (A : 0-80 %, B : 80-95 %, C : 95-100 %)

Graphique combiné (barres volumes + courbe cumulée) avec lignes de seuil 80 % / 95 %

Tableau détaillé par article

🎯 Fiabilité
MAE (Erreur Absolue Moyenne)

WMAPE (Weighted MAPE — standard industrie)

SMAPE (Symétrique)

Tableau mensuel Prévision vs Réalisé avec coloration conditionnelle

🩹 Ruptures
Volume total perdu + nombre de mois impactés

Histogramme mensuel des pertes

Détail par Agence / Article / Mois

🧠 Algorithme de prévision (résumé)
text
1. Périmètre actif   = couples (Agence, Article) avec ventes > 0 sur les 2 dernières années
2. Indices saison.   = Moyenne pondérée par niveau (Agence×Article → Article → Marque → Segment → Global)
3. SARR              = HL mensuel / Indice de saisonnalité
4. Base_EXCEL        = max(SARR_M, Moyenne mobile 3 mois)   ← retient le plus fort
5. Momentum          = moyenne des écarts successifs (M vs M-1, M-1 vs M-2, M-2 vs M-3)
6. Run-Rate          = YTD_HL / Cumul_Coef(mois 1 → cutoff) × 12
7. CAGR              = selon méthode choisie (Classique / Tendance linéaire / Moyenne 3 ans)
                       → borné entre -20 % et +30 %
8. Prévision année N = Base_Mensuelle × Indice × (1 + CAGR)^(N - annee_cloture)
9. Ajustement Budget = si fichier Budget fourni, prévisions année cible remplacées
10. Volume_HL        = Réalisé si ≤ cutoff, sinon Prévision
11. Volume_Cols      = Volume_HL × (10 000 / Contenance_cl)
💡 Note : L'année de clôture utilise la projection Run-Rate pure (sans CAGR) pour éviter l'explosion du momentum absolu. Les années suivantes ajoutent le CAGR.

🎨 Charte graphique
Couleur	Code	Usage
🔴 Rouge STAR	#E30613	Couleur principale, accents
🔴 Rouge foncé	#B3050F	Courbe réalisé
🔴 Rouge clair	#FDECEE	Fonds d'alerte
⚪ Blanc	#FFFFFF	Fonds de cartes
⚫ Texte	#111827	Typographie principale
🟢 Vert	#059669	Indicateurs positifs
Police : Inter (Google Fonts)

🗂️ Arborescence du projet
text
.
├── app.py                    # Application Streamlit (mono-fichier)
├── LOGO_STAR.png             # Logo affiché dans la sidebar
├── README.md                 # Ce fichier
└── (fichiers Excel à importer via l'UI)
🛠️ Points techniques
Cache Streamlit (@st.cache_data) sur le chargement et le calcul → performances optimales

Nettoyage des clés articles : normalisation Unicode + suppression des caractères spéciaux + harmonisation 33 cl / 33cl

Détection automatique du format pivot (présence d'une année valide en colonne 0 ou 1)

Gestion robuste des dates Excel (numériques, séries 1900, libellés multilingues)

Exclusion automatique des lignes "TOTAL" et des natures vides

Limite d'affichage à 5 000 lignes sur les gros tableaux pour éviter le lag

📌 Limitations connues
Un seul onglet de ventes est lu (le premier).

Le Budget Query filtre sur les articles 33 cl CAN uniquement (logique métier spécifique).

L'application ne persiste aucune donnée : tout est recalculé à chaque session.

La classification segment est heuristique (basée sur des regex d'articles) et peut nécessiter un ajustement si de nouveaux produits sont ajoutés.

👤 Auteur / Contact
STAR Madagascar — Direction Commerciale / Business Intelligence

Pour toute question ou évolution :

📧 contact@star.mg

🌐 https://www.star.m

📜 Licence
Usage interne STAR Madagascar. Toute diffusion externe est soumise à autorisation préalable.

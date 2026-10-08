# 📊 OUTILS_PREV — Moteur de Suivi Prévisionnel & Planification S&OP

Bienvenue dans le dépôt **OUTILS_PREV**. Ce projet contient le moteur automatisé de calcul prévisionnel des ventes et de planification **S&OP (Sales and Operations Planning)**. 

Il permet d'ingérer l'historique des ventes réalisées par agence et par article (SKU), de calculer les coefficients de saisonnalité et la vitesse de vente corrigée (**SARR**), puis d'extrapoler les prévisions mensuelles et multi-annuelles (sur \\(N\\) années).

---

## 🌟 Fonctionnalités Principales

- **Ingestion & Normalisation Automatique :**
  - Conversion automatique des volumes vendus en **Hectolitres (HL)** à partir des contenances en cl (`contenance_cl / 10 000`).
  - Prise en compte de la demande réelle ajustée (réintégration des ventes perdues en rupture de stock).
- **Moteur de Saisonnalité & Exceptions :**
  - Calcul des coefficients de saisonnalité mensuels par agence et SKU.
  - Gestion des règles métier (coefficients fixes pour canettes, héritage d'articles de référence).
- **Calcul du SARR & Momentum :**
  - Lissage glissant de la vitesse de vente (**Seasonally Adjusted Run Rate**).
  - Ajustement par le **Momentum** avec plancher strict à \\(0.0\\) HL.
- **CAGR & Garde-Fou Inter-Agences :**
  - Annualisation par le poids saisonnier écoulé.
  - Plafonnement du CAGR brut par la moyenne globale de l'article pour éviter les dérives.
  - Fallback automatique sur le Budget si l'historique est insuffisant ou négatif.
- **Traitements Métier Spécifiques :**
  - Allocation au prorata pour les volumes cibles (ex. FOSA 15 000 HL).
  - Reconversion dynamique des HL en **Unités Physiques** (bouteilles, canettes, caisses).
- **Projections Multi-Annuelles (\\(N\\) Années) :**
  - Génération de matrices de prévision glissantes sur 5 ans (ex. 2026 à 2030) ventilées par Agence, SKU, Format et Mois.

---

## 📁 Arborescence du Projet

```text
OUTILS_PREV/
├── .github/
│   └── workflows/
│       └── tests.yml            # CI/CD - Tests automatisés sur GitHub Actions
├── calculs/
│   ├── main_cli-v2.py           # Point d'entrée principal en ligne de commande
│   ├── main_cli.py              # Ancien script CLI
│   ├── suivi_prev_engine.py     # Moteur de calcul Python complet (Core Engine)
│   └── data/
│       └── input/               # Dossier pour déposer les fichiers réels d'entrée
│           ├── DATA_THB65cl.xlsx
│           └── liste_articles_actif.xlsx
├── metier/
│   └── data/                    # Dossier où sont enregistrés les rapports S&OP finaux
│       └── Export_Suivi_PREV_SOP_2026.xlsx
├── requirements.txt             # Dépendances Python du projet
└── README.md                    # Documentation du projet

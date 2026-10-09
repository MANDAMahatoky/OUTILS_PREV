# OUTILS_PREV — Moteur de Suivi Prévisionnel S&OP

Bienvenue dans le dépôt `OUTILS_PREV`. Ce projet met à disposition un moteur Python de planification et de prévision commerciale pour le suivi S&OP (Sales & Operations Planning).

Il permet d:
- ingérer un export de ventes et un référentiel actif,
- convertir les quantités vendues en hectolitres (HL),
- calculer les coefficients saisonniers et la vitesse de vente ajustée (SARR),
- projeter le volume annuel avec garde-fou de croissance (CAGR),
- appliquer les règles métier spécifiques (FOSA, articles de référence, cas particuliers),
- produire un rapport Excel de restitution prêt à exploiter.

---

## Objectif du projet

Le moteur remplace les calculs manuels et les outils Excel fragiles par une chaîne de traitement automatisée, reproductible et traçable.

Le processus couvre :
1. ingestion des données d'export et du référentiel,
2. normalisation et conversion des volumes,
3. calcul de la saisonnalité et du momentum,
4. annualisation et projection de l'année en cours,
5. génération d'un fichier Excel S&OP multi-onglets.

---

## Arborescence du dépôt

```text
OUTILS_PREV/
├── .github/
│   └── workflows/
│       └── tests.yml
├── calculs/
│   ├── main_cli.py                 # Point d'entrée CLI principal
│   ├── requirements.txt            # Dépendances Python du moteur
│   └── src/
│       └── suivi_prev_engine.py    # Moteur de calcul principal
├── config/
│   └── rules_config.yaml           # Règles métier et paramètres de calcul
├── metier/
│   └── data/
│       └── Export_Suivi_PREV_SOP.xlsx  # Sortie Excel générée localement
├── .gitignore
├── README.md
└── Export_Suivi_PREV_SOP.xlsx       # Fichier de sortie généré au niveau racine
```

---

## Pré-requis

- Python 3.10+
- `pip` et un environnement virtuel conseillé

Installation des dépendances :

```bash
cd OUTILS_PREV
python -m venv .venv
source .venv/bin/activate
pip install -r calculs/requirements.txt
```

---

## Utilisation rapide

Le point d'entrée principal est :

```bash
python calculs/main_cli.py --config config/rules_config.yaml --output Export_Suivi_PREV_SOP.xlsx
```

### Avec fichiers d'entrée explicites

```bash
python calculs/main_cli.py \
  --config config/rules_config.yaml \
  --export ./chemin/vers/export_ventes.xlsx \
  --actif ./chemin/vers/referentiel_actif.xlsx \
  --output ./metier/data/Export_Suivi_PREV_SOP.xlsx
```

### Cas sans données fournies

Si aucun export ni référentiel n'est fourni, le script génère automatiquement un jeu de données de démonstration pour valider le moteur et produire un rapport exemple.

---

## Fonctionnalités principales

### 1) Ingestion et normalisation
- lecture des données de vente et du référentiel actif,
- conversion des quantités vendues en hectolitres (HL),
- calcul du volume ajusté par prise en compte des ventes perdues en rupture,
- alignement des dates, agences et SKU.

### 2) Calcul de saisonnalité
- calcul des coefficients mensuels par agence et SKU,
- gestion des exceptions métier via configuration YAML,
- héritage de profil de saisonnalité depuis un article de référence,
- coefficients fixes pour certains produits (ex. canettes).

### 3) SARR et momentum
- calcul du run rate saisonnalisé (SARR),
- lissage glissant sur 4 mois,
- calcul de momentum sur la variation de la vitesse de vente,
- plancher strict à `0.0` en garde-fou.

### 4) Projection annuelle et CAGR
- annualisation selon le poids saisonnier écoulé,
- calcul du CAGR brut,
- plafonnement sur la moyenne globale de l'article pour limiter les dérives,
- fallback automatique sur le budget si le signal historique est insuffisant ou nul.

### 5) Cas métier spécifiques
- ventilation des volumes FOSA selon un objectif cible,
- reconversion des HL en unités physiques (bouteilles, canettes, caisses),
- prise en charge des règles métier dans le fichier de configuration.

### 6) Rapport Excel S&OP
Le moteur génère un classeur avec plusieurs onglets, dont :
- synthèse S&OP,
- base détaillée plate,
- déclinaisons en unités physiques,
- audit et traçabilité.

---

## Fichier de configuration

Le fichier `config/rules_config.yaml` centralise les règles métier du projet.

Exemple de contenu :

```yaml
conversions:
  divisor_hl: 10000.0

seasonality_exceptions:
  fixed_coefficients:
    - pattern: "CAN_33CL"
      value: 1.0
  reference_mapping:
    "CAPRICE_35CL": "ARTICLE_REF_BOISSON"

guardrails:
  momentum_floor: 0.0
  cagr_fallback_triggers: [0.0, -1.0]
  budget_divisor_default: 1.0

special_cases:
  fosa:
    target_volume_hl: 15000.0
  cap_citron:
    unit_conversion: true
```

Ces paramètres permettent d'adapter le moteur à la logique métier sans modifier le code Python.

---

## Détails techniques

### Moteur principal
- `calculs/src/suivi_prev_engine.py`

Contient les classes suivantes :
- `RulesConfig`
- `DataIngestionPipeline`
- `SeasonalityEngine`
- `SARREngine`
- `CAGREngine`
- `SpecialCasesEngine`
- `SOPReporter`

### Point d'entrée CLI
- `calculs/main_cli.py`

Le script supporte :
- `--config` : chemin vers le fichier YAML de configuration,
- `--export` : fichier Excel/CSV des ventes,
- `--actif` : fichier Excel/CSV du référentiel actif,
- `--output` : chemin de sortie du rapport Excel final.

---

## CI / Qualité

Le dépôt inclut une pipeline GitHub Actions dans :

```text
.github/workflows/tests.yml
```

Cette configuration permet de lancer les vérifications automatisées sur le projet.

---

## Exemple de sortie

La sortie générée est un fichier Excel de type :

```text
Export_Suivi_PREV_SOP.xlsx
```

avec un ensemble d'onglets dédiés à la synthèse, au plan de demande, aux déclinaisons unités et à l'audit.

---

## À noter

- Le projet est conçu pour un usage analytique et décisionnel en S&OP.
- Les règles métier peuvent être modifiées dans `config/rules_config.yaml` sans toucher au moteur de calcul.
- L'architecture actuelle est fonctionnelle et orientée vers la reproductibilité, la traçabilité et l'automatisation des prévisions.

---

## Licence

Aucune licence n'est explicitement définie dans le dépôt pour l'instant.

---

## Contribution

Pour faire évoluer le moteur :
1. modifier le code dans `calculs/src/suivi_prev_engine.py`,
2. ajuster le fichier de config si nécessaire,
3. valider le comportement via le CLI ou la CI.

---

## Résumé

`OUTILS_PREV` est un moteur Python de prévision commerciale et de planification S&OP, capable de transformer des données de vente brutes en projections exploitables et en rapports Excel structurés.

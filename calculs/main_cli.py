#!/usr/bin/env python3
"""
main_cli.py - Interface Ligne de Commande (CLI) pour Suivi PREV S&OP
===================================================================
Permet d'exécuter la chaîne de prévision directement depuis le terminal.

Usage:
    python3 main_cli.py --config config/rules_config.yaml --output Export_Suivi_PREV_SOP.xlsx
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import argparse
import pandas as pd

from src.suivi_prev_engine import (
    RulesConfig,
    DataIngestionPipeline,
    SeasonalityEngine,
    SARREngine,
    CAGREngine,
    SpecialCasesEngine,
    SOPReporter
)

def print_banner():
    print("=" * 75)
    print("        MOTEUR SUIVI PREV S&OP - EXÉCUTION TERMINAL / CLI        ")
    print("=" * 75)

def generate_sample_inputs():
    os.makedirs(os.path.join(SCRIPT_DIR, 'data/input'), exist_ok=True)
    agences = ['AGENCE_DOUALA', 'AGENCE_YAOUNDE']
    skus = ['CAN_33CL', 'CAPRICE_35CL', 'ARTICLE_REF_BOISSON', 'FOSA_50CL']
    
    dates = pd.date_range('2024-01-01', '2026-09-01', freq='MS')
    records = []
    for d in dates:
        for a in agences:
            for s in skus:
                base = 100.0 if 'CAN' in s else 50.0
                sales = base + (d.month * 2.5)
                records.append({
                    'date': d, 'code_agence': a, 'code_sku': s, 'quantite_vendue': sales
                })
    df_export = pd.DataFrame(records)
    
    df_actif = pd.DataFrame([
        {'code_sku': 'CAN_33CL', 'libelle_sku': 'Canette 33cl', 'contenance_cl': 33.0, 'segment': 'CANETTES'},
        {'code_sku': 'CAPRICE_35CL', 'libelle_sku': 'Caprice 35cl', 'contenance_cl': 35.0, 'segment': 'PET'},
        {'code_sku': 'ARTICLE_REF_BOISSON', 'libelle_sku': 'Ref Boisson 50cl', 'contenance_cl': 50.0, 'segment': 'PET'},
        {'code_sku': 'FOSA_50CL', 'libelle_sku': 'Fosa 50cl', 'contenance_cl': 50.0, 'segment': 'BOUTEILLES'}
    ])
    return df_export, df_actif

def main():
    parser = argparse.ArgumentParser(description="Moteur de Calcul Suivi PREV - Interface CLI Terminal")
    config_default = os.path.join(SCRIPT_DIR, "config/rules_config.yaml")
    out_default = os.path.join(SCRIPT_DIR, "Export_Suivi_PREV_SOP.xlsx")
    
    parser.add_argument("--config", type=str, default=config_default, help="Fichier YAML de configuration")
    parser.add_argument("--export", type=str, default=None, help="Fichier Excel/CSV d'export des ventes")
    parser.add_argument("--actif", type=str, default=None, help="Fichier Excel/CSV du référentiel actif")
    parser.add_argument("--output", type=str, default=out_default, help="Fichier Excel de sortie")
    
    args = parser.parse_args()
    print_banner()
    
    if not os.path.exists(args.config):
        print(f"[!] Configuration non trouvée: {args.config}. Utilisation des règles par défaut.")
        config_dict = {
            'conversions': {'divisor_hl': 10000.0},
            'seasonality_exceptions': {'fixed_coefficients': [{'pattern': 'CAN_33CL', 'value': 1.0}]},
            'guardrails': {'momentum_floor': 0.0, 'cagr_fallback_triggers': [0.0, -1.0], 'budget_divisor_default': 1.0},
            'special_cases': {'fosa': {'target_volume_hl': 15000.0}}
        }
        config = RulesConfig(config_dict)
    else:
        print(f"[✓] Chargement de la configuration : {args.config}")
        config = RulesConfig(args.config)
        
    if args.export and args.actif:
        print(f"[✓] Lecture Ventes : {args.export}")
        df_export = pd.read_excel(args.export) if args.export.endswith('.xlsx') else pd.read_csv(args.export)
        print(f"[✓] Lecture Référentiel : {args.actif}")
        df_actif = pd.read_excel(args.actif) if args.actif.endswith('.xlsx') else pd.read_csv(args.actif)
    else:
        print("[i] Aucun fichier fourni. Génération de données de démonstration...")
        df_export, df_actif = generate_sample_inputs()
        
    print("\n[1/5] Ingestion & Conversions en Hectolitres (HL)...")
    ingestion = DataIngestionPipeline(config)
    export_clean, budget_clean = ingestion.prepare_data(df_export, df_actif)
    print(f"      -> Volume total ingéré : {export_clean['volume_hl'].sum():,.2f} HL")
    
    print("[2/5] Calcul du Moteur de Saisonnalité & Exceptions...")
    season_engine = SeasonalityEngine(config)
    df_coef = season_engine.compute_coefficients(export_clean)
    print(f"      -> Coefficients calculés pour {len(df_coef)} combinaisons.")
    
    print("[3/5] Calcul du SARR & Momentum (Plancher strict à 0)...")
    sarr_engine = SARREngine(config)
    df_sarr = sarr_engine.compute_sarr(export_clean, df_coef)
    
    print("[4/5] Annualisation, CAGR & Garde-Fou Inter-Agences...")
    cagr_engine = CAGREngine(config)
    df_proj = cagr_engine.compute_forecast(export_clean, df_coef, budget_clean, year_current=2026, year_ref=2025, elapsed_months=9)
    
    months_future = list(range(10, 13))
    flat_rows = []
    for _, row in df_proj.iterrows():
        base_monthly = row['base_annuelle_retenue_hl'] / 12.0
        for m in months_future:
            c_val = df_coef[(df_coef['code_agence'] == row['code_agence']) & (df_coef['code_sku'] == row['code_sku']) & (df_coef['mois'] == m)]['coef_saisonnier'].values
            coef_m = c_val[0] if len(c_val) > 0 else 1.0
            flat_rows.append({
                'code_agence': row['code_agence'],
                'code_sku': row['code_sku'],
                'segment': df_actif[df_actif['code_sku'] == row['code_sku']]['segment'].values[0] if row['code_sku'] in df_actif['code_sku'].values else 'AUTRE',
                'annee': 2026,
                'mois': m,
                'prevision_hl': base_monthly * coef_m,
                'source_calcul': row['source_calcul']
            })
    df_flat = pd.DataFrame(flat_rows)
    
    print("[5/5] Traitement des Cas Spéciaux (Ventilation FOSA & Unités Physiques)...")
    special_engine = SpecialCasesEngine(config)
    df_flat = special_engine.apply_fosa_allocation(df_flat)
    df_flat = special_engine.convert_to_physical_units(df_flat, df_actif)
    
    print(f"\n[✓] Génération du Rapport Excel S&OP : {args.output}")
    SOPReporter.generate_excel_report(df_flat, df_sarr, args.output)
    
    print("\n" + "=" * 75)
    print(" RÉSUMÉ DES PRÉVISIONS GÉNÉRÉES (HL & UNITÉS)")
    print("=" * 75)
    summary = df_flat.groupby(['segment', 'mois'])[['prevision_hl', 'prevision_unites']].sum().reset_index()
    print(summary.to_string(index=False))
    print("=" * 75)
    print(f"[SUCCÈS] Exécution terminée avec succès. Fichier généré : {args.output}\n")

if __name__ == "__main__":
    main()

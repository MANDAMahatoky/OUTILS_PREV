"""
suivi_prev_engine.py
====================
Moteur de calcul automatisé pour le Suivi Prévisionnel & Planification S&OP.
Remplace le classeur Excel 'Tableau_formules_Suivi_PREV.docx'.

Auteur : Moteur Python Suivi PREV
"""

import os
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple

class RulesConfig:
    """Gestionnaire de la configuration des règles et exceptions métier."""
    def __init__(self, config_path_or_dict: Any):
        if isinstance(config_path_or_dict, str):
            with open(config_path_or_dict, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        elif isinstance(config_path_or_dict, dict):
            self.config = config_path_or_dict
        else:
            raise ValueError("Configuration invalide : fournissez un chemin YAML ou un dictionnaire.")

    @property
    def divisor_hl(self) -> float:
        return float(self.config.get('conversions', {}).get('divisor_hl', 10000.0))

    @property
    def fixed_coefficients(self) -> list:
        return self.config.get('seasonality_exceptions', {}).get('fixed_coefficients', [])

    @property
    def reference_mapping(self) -> dict:
        return self.config.get('seasonality_exceptions', {}).get('reference_mapping', {})

    @property
    def momentum_floor(self) -> float:
        return float(self.config.get('guardrails', {}).get('momentum_floor', 0.0))

    @property
    def fallback_triggers(self) -> list:
        return self.config.get('guardrails', {}).get('cagr_fallback_triggers', [0.0, -1.0])

    @property
    def budget_divisor(self) -> float:
        return float(self.config.get('guardrails', {}).get('budget_divisor_default', 1.0))

    @property
    def fosa_target_hl(self) -> float:
        return float(self.config.get('special_cases', {}).get('fosa', {}).get('target_volume_hl', 15000.0))


class DataIngestionPipeline:
    """Ingestion, typage et normalisation des flux de données sources."""
    def __init__(self, config: RulesConfig):
        self.config = config

    def prepare_data(
        self,
        df_export: pd.DataFrame,
        df_actif: pd.DataFrame,
        df_ruptures: Optional[pd.DataFrame] = None,
        df_budget: Optional[pd.DataFrame] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Normalise et enrichit les données d'export avec les contenances en HL,
        les ajustements de mois partiel et les ventes perdues en rupture.
        """
        export = df_export.copy()
        actif = df_actif.copy()

        # Formatage strict des dates
        export['date'] = pd.to_datetime(export['date'])
        export['annee'] = export['date'].dt.year
        export['mois'] = export['date'].dt.month
        export['mois_nom'] = export['date'].dt.strftime('%B')

        # Jointure avec le référentiel actif pour obtenir la contenance
        export = export.merge(
            actif[['code_sku', 'libelle_sku', 'contenance_cl', 'segment']],
            on='code_sku',
            how='left'
        )
        export['contenance_cl'] = export['contenance_cl'].fillna(33.0)

        # Conversion automatique des unités physiques vendues en Hectolitres (HL)
        export['volume_hl'] = export['quantite_vendue'] * (export['contenance_cl'] / self.config.divisor_hl)

        # Prise en compte des ruptures si le fichier est fourni
        if df_ruptures is not None and not df_ruptures.empty:
            rupt = df_ruptures.copy()
            rupt['date'] = pd.to_datetime(rupt['date'])
            export = export.merge(
                rupt[['date', 'code_agence', 'code_sku', 'volume_perdu_hl']],
                on=['date', 'code_agence', 'code_sku'],
                how='left'
            )
            export['volume_perdu_hl'] = export['volume_perdu_hl'].fillna(0.0)
        else:
            export['volume_perdu_hl'] = 0.0

        # Volume réalisé ajusté (Demande réelle = Ventes réelles + Ventes perdues en rupture)
        export['realise_ajuste_hl'] = export['volume_hl'] + export['volume_perdu_hl']

        # Normalisation du Budget
        budget_clean = pd.DataFrame()
        if df_budget is not None and not df_budget.empty:
            bgt = df_budget.copy()
            bgt['date'] = pd.to_datetime(bgt['date'])
            bgt['annee'] = bgt['date'].dt.year
            bgt['mois'] = bgt['date'].dt.month
            bgt = bgt.merge(
                actif[['code_sku', 'contenance_cl']],
                on='code_sku',
                how='left'
            )
            bgt['contenance_cl'] = bgt['contenance_cl'].fillna(33.0)
            if 'volume_budget_hl' not in bgt.columns and 'volume_budget_unites' in bgt.columns:
                bgt['volume_budget_hl'] = bgt['volume_budget_unites'] * (bgt['contenance_cl'] / self.config.divisor_hl)
            budget_clean = bgt[['date', 'annee', 'mois', 'code_agence', 'code_sku', 'volume_budget_hl']]

        return export, budget_clean


class SeasonalityEngine:
    """Calcul des coefficients saisonniers et gestion des exceptions."""
    def __init__(self, config: RulesConfig):
        self.config = config

    def compute_coefficients(self, df_export: pd.DataFrame) -> pd.DataFrame:
        """
        Calcul de la moyenne des ventes du mois rapportée à la moyenne mensuelle globale
        de l'article par agence.
        """
        df = df_export.copy()

        # Moyenne des ventes par (code_agence, code_sku, mois)
        monthly_avg = df.groupby(['code_agence', 'code_sku', 'mois'])['realise_ajuste_hl'].mean().reset_index()
        monthly_avg.rename(columns={'realise_ajuste_hl': 'moyenne_mois_hl'}, inplace=True)

        # Moyenne globale mensuelle par (code_agence, code_sku)
        global_avg = df.groupby(['code_agence', 'code_sku'])['realise_ajuste_hl'].mean().reset_index()
        global_avg.rename(columns={'realise_ajuste_hl': 'moyenne_globale_hl'}, inplace=True)

        coef_df = monthly_avg.merge(global_avg, on=['code_agence', 'code_sku'], how='left')

        # Coefficient brut = Moyenne du mois / Moyenne globale
        coef_df['coef_saisonnier'] = np.where(
            coef_df['moyenne_globale_hl'] > 0,
            coef_df['moyenne_mois_hl'] / coef_df['moyenne_globale_hl'],
            1.0
        )

        # Application des exceptions métier
        # 1. Articles à coefficient fixe (ex: Canettes 33cl = 1.0)
        for rule in self.config.fixed_coefficients:
            pattern = rule.get('pattern', '')
            val = float(rule.get('value', 1.0))
            mask = coef_df['code_sku'].str.contains(pattern, case=False, na=False)
            coef_df.loc[mask, 'coef_saisonnier'] = val

        # 2. Articles de référence (ex: Caprice 35cl hérite du profil d'un article actif)
        ref_map = self.config.reference_mapping
        for new_sku, ref_sku in ref_map.items():
            ref_data = coef_df[coef_df['code_sku'] == ref_sku][['code_agence', 'mois', 'coef_saisonnier']].copy()
            ref_data.rename(columns={'coef_saisonnier': 'ref_coef'}, inplace=True)

            target_mask = coef_df['code_sku'] == new_sku
            if target_mask.any():
                coef_df = coef_df.merge(ref_data, on=['code_agence', 'mois'], how='left')
                coef_df.loc[target_mask & coef_df['ref_coef'].notna(), 'coef_saisonnier'] = coef_df['ref_coef']
                coef_df.drop(columns=['ref_coef'], inplace=True, errors='ignore')

        return coef_df[['code_agence', 'code_sku', 'mois', 'coef_saisonnier']]


class SARREngine:
    """Calcul du SARR (Seasonally Adjusted Run Rate) et du Momentum."""
    def __init__(self, config: RulesConfig):
        self.config = config

    def compute_sarr(self, df_export: pd.DataFrame, df_coef: pd.DataFrame, window: int = 4) -> pd.DataFrame:
        df = df_export.merge(df_coef, on=['code_agence', 'code_sku', 'mois'], how='left')
        df['coef_saisonnier'] = df['coef_saisonnier'].fillna(1.0)

        df = df.sort_values(['code_agence', 'code_sku', 'date']).copy()

        # SARR brut mensuel = Réalisé / Coefficient
        df['sarr_brut'] = np.where(
            df['coef_saisonnier'] > 0,
            df['realise_ajuste_hl'] / df['coef_saisonnier'],
            0.0
        )

        # Lissage glissant (SARR Moyen)
        df['sarr_lisse'] = df.groupby(['code_agence', 'code_sku'])['sarr_brut'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )

        # Momentum (Variation SARR M-1 vs M-2)
        df['sarr_diff'] = df.groupby(['code_agence', 'code_sku'])['sarr_brut'].diff()
        df['momentum'] = df.groupby(['code_agence', 'code_sku'])['sarr_diff'].transform(
            lambda x: x.rolling(window=3, min_periods=1).mean()
        ).fillna(0.0)

        # Prévision SARR ajustée avec plancher strict à 0.0
        df['prev_sarr_brute'] = (df['sarr_lisse'] * df['coef_saisonnier']) + df['momentum']
        df['prev_sarr_hl'] = np.maximum(self.config.momentum_floor, df['prev_sarr_brute'])

        return df


class CAGREngine:
    """Projection annuelle, calcul du CAGR avec garde-fou et Fallback Budget."""
    def __init__(self, config: RulesConfig):
        self.config = config

    def compute_forecast(
        self,
        df_export: pd.DataFrame,
        df_coef: pd.DataFrame,
        df_budget: Optional[pd.DataFrame] = None,
        year_current: int = 2026,
        year_ref: int = 2025,
        elapsed_months: int = 9
    ) -> pd.DataFrame:
        """
        Extrapole l'année sur 12 mois selon le poids saisonnier écoulé,
        calcule le CAGR avec garde-fou et bascule sur le Budget si nécessaire.
        """
        # Filtrer le réalisé écoulé de l'année en cours
        ecoule = df_export[(df_export['annee'] == year_current) & (df_export['mois'] <= elapsed_months)].copy()

        # Cumul du réalisé à date
        cumul_realise = ecoule.groupby(['code_agence', 'code_sku'])['realise_ajuste_hl'].sum().reset_index()
        cumul_realise.rename(columns={'realise_ajuste_hl': 'realise_cumule_hl'}, inplace=True)

        # Somme des coefficients des mois écoulés
        coef_ecoule = df_coef[df_coef['mois'] <= elapsed_months].groupby(['code_agence', 'code_sku'])['coef_saisonnier'].sum().reset_index()
        coef_ecoule.rename(columns={'coef_saisonnier': 'sum_coef_ecoules'}, inplace=True)

        proj = cumul_realise.merge(coef_ecoule, on=['code_agence', 'code_sku'], how='left')
        proj['sum_coef_ecoules'] = proj['sum_coef_ecoules'].fillna(float(elapsed_months))

        # Annualisation par le poids saisonnier réel
        proj['projection_annee_hl'] = np.where(
            proj['sum_coef_ecoules'] > 0,
            (proj['realise_cumule_hl'] / proj['sum_coef_ecoules']) * 12.0,
            0.0
        )

        # Réalisé de l'année de référence
        ref_df = df_export[df_export['annee'] == year_ref].groupby(['code_agence', 'code_sku'])['realise_ajuste_hl'].sum().reset_index()
        ref_df.rename(columns={'realise_ajuste_hl': 'realise_ref_hl'}, inplace=True)

        proj = proj.merge(ref_df, on=['code_agence', 'code_sku'], how='left')
        proj['realise_ref_hl'] = proj['realise_ref_hl'].fillna(0.0)

        # Calcul du CAGR brut
        nb_years = year_current - year_ref
        if nb_years <= 0:
            nb_years = 1.0

        has_ref = (proj['realise_ref_hl'] > 0) & (proj['projection_annee_hl'] > 0)
        proj['cagr_brut'] = np.where(
            has_ref,
            (proj['projection_annee_hl'] / proj['realise_ref_hl']) ** (1.0 / nb_years) - 1.0,
            0.0
        )

        # Garde-fou de croissance : Plafond à la moyenne du CAGR de cet article sur TOUTES les agences
        avg_cagr_global = proj.groupby('code_sku')['cagr_brut'].transform('mean')
        proj['cagr_retenu'] = np.minimum(proj['cagr_brut'], avg_cagr_global)

        # Ingestion du budget pour Fallback
        if df_budget is not None and not df_budget.empty:
            bgt_sum = df_budget[df_budget['annee'] == year_current].groupby(['code_agence', 'code_sku'])['volume_budget_hl'].sum().reset_index()
            proj = proj.merge(bgt_sum, on=['code_agence', 'code_sku'], how='left')
            proj['volume_budget_hl'] = proj['volume_budget_hl'].fillna(0.0)
        else:
            proj['volume_budget_hl'] = 0.0

        # Application du Fallback Budget
        triggers = self.config.fallback_triggers
        fallback_mask = proj['cagr_retenu'].isin(triggers) | (~has_ref) | (proj['projection_annee_hl'] == 0)

        divisor = self.config.budget_divisor
        proj['base_annuelle_retenue_hl'] = np.where(
            fallback_mask,
            proj['volume_budget_hl'] / divisor,
            proj['projection_annee_hl'] * (1.0 + proj['cagr_retenu'])
        )

        proj['source_calcul'] = np.where(fallback_mask, 'BUDGET_FALLBACK', 'CAGR_PROJECTION')

        return proj


class SpecialCasesEngine:
    """Traitements spécifiques : Allocations FOSA & Conversions CAP Citron."""
    def __init__(self, config: RulesConfig):
        self.config = config

    def apply_fosa_allocation(self, df_flat: pd.DataFrame) -> pd.DataFrame:
        """Ventilation du volume cible imposé (15 000 HL) au prorata de l'historique."""
        df = df_flat.copy()
        fosa_mask = df['code_sku'].str.contains('FOSA', case=False, na=False)

        if fosa_mask.any():
            target_hl = self.config.fosa_target_hl
            fosa_total = df.loc[fosa_mask, 'prevision_hl'].sum()

            if fosa_total > 0:
                df.loc[fosa_mask, 'prevision_hl'] = target_hl * (df.loc[fosa_mask, 'prevision_hl'] / fosa_total)
                df.loc[fosa_mask, 'source_calcul'] = 'FOSA_TARGET_ALLOCATION'

        return df

    def convert_to_physical_units(self, df_flat: pd.DataFrame, df_actif: pd.DataFrame) -> pd.DataFrame:
        """Reconversion des Hectolitres en Unités physiques (Bouteilles/Canettes/Caisses)."""
        df = df_flat.merge(df_actif[['code_sku', 'contenance_cl']], on='code_sku', how='left')
        df['contenance_cl'] = df['contenance_cl'].fillna(33.0)

        # Unités physiques = HL / (contenance_cl / 10 000)
        df['prevision_unites'] = df['prevision_hl'] / (df['contenance_cl'] / self.config.divisor_hl)
        return df


class SOPReporter:
    """Génération du classeur de restitution Excel S&OP multi-onglets."""
    @staticmethod
    def generate_excel_report(
        df_flat: pd.DataFrame,
        df_audit: pd.DataFrame,
        output_path: str
    ):
        """Génère le classeur Excel final avec 4 onglets formatés."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. Synthèse S&OP par Segment
            synth = df_flat.groupby(['segment', 'annee', 'mois'])['prevision_hl'].sum().unstack(level='mois')
            synth.to_excel(writer, sheet_name='1_Synthese_SOP')

            # 2. Base Mide à plat (Flat / Tidy Data)
            df_flat.to_excel(writer, sheet_name='2_Plan_Demande_Flat', index=False)

            # 3. Déclinaisons en Unités Physiques
            decl = df_flat[['code_agence', 'code_sku', 'segment', 'annee', 'mois', 'prevision_hl', 'prevision_unites', 'source_calcul']]
            decl.to_excel(writer, sheet_name='3_Declinaisons_Unites', index=False)

            # 4. Audit & Traçabilité
            df_audit.to_excel(writer, sheet_name='4_Audit_Traçabilite', index=False)

        print(f"[SUCCESS] Rapport S&OP généré avec succès : {output_path}")

@st.cache_data(show_spinner="Calcul ultra-rapide des prévisions...")
def calculer_etape_5(df_perimetre: pd.DataFrame, annee_min_is: int, annee_max_is: int, annee_min_cagr: int, annee_max_cagr: int, annee_cloture: int, mois_cutoff: int, annee_cible: int):
    
    articles_avec_vente = df_perimetre.groupby('article')['hl'].sum()
    articles_avec_vente = articles_avec_vente[articles_avec_vente > 0].index
    df_perimetre_filtre = df_perimetre[df_perimetre['article'].isin(articles_avec_vente)].copy()
    
    if df_perimetre_filtre.empty:
        return None, None, None, None, df_perimetre

    df_limite = df_perimetre_filtre[(df_perimetre_filtre["annee"] < annee_cloture) | ((df_perimetre_filtre["annee"] == annee_cloture) & (df_perimetre_filtre["mois"] <= mois_cutoff))].copy()
    df_realise = df_limite[df_limite["annee"] <= annee_cloture].copy()
    if df_realise.empty: return None, None, None, None, df_perimetre_filtre

    # Indice de Saisonnalité (Filtre strict 12 mois)
    df_hist_is = df_realise[(df_realise["annee"] >= annee_min_is) & (df_realise["annee"] <= annee_max_is)].copy()
    if df_hist_is.empty: return None, None, None, None, df_realise

    mois_par_annee = df_hist_is.groupby(['agence', 'article', 'annee'])['mois'].nunique().reset_index()
    df_hist_is_complet = df_hist_is.merge(mois_par_annee[mois_par_annee['mois'] == 12][['agence', 'article', 'annee']], on=['agence', 'article', 'annee'], how='inner')
    if df_hist_is_complet.empty: return None, None, None, None, df_realise

    vols = df_hist_is_complet.groupby(['agence', 'article', 'annee', 'mois'])['hl'].sum().unstack('mois').fillna(0.0).reindex(columns=range(1, 13), fill_value=0.0) 
    vols_mois_cumules = vols.groupby(['agence', 'article']).sum()
    vols_annuels_cumules = vols.sum(axis=1).groupby(['agence', 'article']).sum()
    
    # Calcul de l'indice
    indices = vols_mois_cumules.div(vols_annuels_cumules / 12.0, axis=0).replace([np.inf, -np.inf], np.nan).fillna(0.0) # Remplacer par 0.0 au lieu de 1.0

    table_indices = indices.reset_index().melt(id_vars=['agence', 'article'], var_name='mois', value_name='Indice')
    table_indices['mois'] = table_indices['mois'].astype(int) 

    # SARR (pour info)
    df_sarr = df_realise.merge(table_indices, on=['agence', 'article', 'mois'], how='left')
    df_sarr['Indice'] = df_sarr['Indice'].fillna(1.0)
    df_sarr['SARR_HL'] = df_sarr['hl'] / df_sarr['Indice'].replace(0, 1.0)

    # Préparation des éléments
    df_perim_unique = df_perimetre_filtre[['agence', 'article', 'contenance_cl']].drop_duplicates(subset=['agence', 'article'])
    
    # 1. YTD
    df_ytd = df_realise[(df_realise['annee'] == annee_cloture) & (df_realise['mois'] <= mois_cutoff)].groupby(['agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'YTD_HL'})
    
    # 2. Cumul des coefficients
    df_cumul_coef = table_indices[table_indices['mois'] <= mois_cutoff].groupby(['agence', 'article'])['Indice'].sum().reset_index().rename(columns={'Indice': 'Cumul_Coef'})

    # 3. Base Historique
    df_base_min = df_realise[df_realise['annee'] == annee_min_cagr].groupby(['agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'Base_Hist'})
    df_base_max = df_realise[df_realise['annee'] == annee_max_cagr].groupby(['agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'Final_Hist'})

    df_base = pd.merge(df_perim_unique, df_ytd, on=['agence', 'article'], how='left')
    df_base = pd.merge(df_base, df_cumul_coef, on=['agence', 'article'], how='left')
    df_base = pd.merge(df_base, df_base_min, on=['agence', 'article'], how='left')
    df_base = pd.merge(df_base, df_base_max, on=['agence', 'article'], how='left')

    df_base['YTD_HL'] = df_base['YTD_HL'].fillna(0.0)
    df_base['Base_Hist'] = df_base['Base_Hist'].fillna(0.0)
    df_base['Final_Hist'] = df_base['Final_Hist'].fillna(0.0)
    
    # Si le Cumul Coef est à 0 (article vendu uniquement en fin d'année), on met 1 pour éviter la division par zéro
    df_base['Cumul_Coef'] = df_base['Cumul_Coef'].replace(0, 1.0) 

    # --- MÉTHODE EXCEL ---
    df_base['Projection_CurrentYear'] = np.where(
        df_base['Cumul_Coef'] > 0,
        df_base['YTD_HL'] / (df_base['Cumul_Coef'] / 12.0),
        0.0
    )

    df_base['Nb_Annees'] = annee_max_cagr - annee_min_cagr
    df_base['CAGR_val'] = np.where(
        (df_base['Base_Hist'] > 0) & (df_base['Final_Hist'] > 0) & (df_base['Nb_Annees'] > 0),
        ((df_base['Final_Hist'] / df_base['Base_Hist']) ** (1 / df_base['Nb_Annees'])) - 1,
        0.0
    )

    # --- PROJECTION MENSUELLE ---
    annees_cibles = list(range(annee_cloture, annee_cible + 1))
    mois_cibles = list(range(1, 13))
    
    df_cross = df_base.assign(key=1).merge(pd.DataFrame({'annee': annees_cibles, 'key': 1}), on='key').drop('key', axis=1)
    df_cross = df_cross.assign(key=1).merge(pd.DataFrame({'mois': mois_cibles, 'key': 1}), on='key').drop('key', axis=1)
    
    df_cross = pd.merge(df_cross, table_indices, on=['agence', 'article', 'mois'], how='left')
    
    # CORRECTION ICI : Si l'indice est manquant (pas d'historique ce mois-là), on force à 0 au lieu de 1.0
    df_cross['Indice'] = df_cross['Indice'].fillna(0.0) 
    
    df_realise_grouped = df_realise.groupby(['annee', 'mois', 'agence', 'article'])['hl'].sum().reset_index().rename(columns={'hl': 'hl_reel'})
    df_cross = pd.merge(df_cross, df_realise_grouped, on=['annee', 'mois', 'agence', 'article'], how='left')
    
    df_cross['is_realise'] = (df_cross['annee'] == annee_cloture) & (df_cross['mois'] <= mois_cutoff)
    df_cross['Statut'] = np.where(df_cross['is_realise'], "Réalisé", "Prévision")
    
    df_cross['multiplicateur_cagr'] = (1 + df_cross['CAGR_val']) ** (df_cross['annee'] - annee_cloture)
    
    # Formule : Projection * Indice (qui est 0 si pas d'historique) / 12
    df_cross['Prevision_HL'] = np.maximum(0.0, (df_cross['Projection_CurrentYear'] * df_cross['multiplicateur_cagr']) * (df_cross['Indice'] / 12.0))
    
    df_cross['Volume_HL'] = np.where(df_cross['is_realise'], df_cross['hl_reel'].fillna(0.0), df_cross['Prevision_HL'])
    df_cross['Volume_HL'] = np.maximum(0.0, df_cross['Volume_HL'])
    
    # La conversion en Cols utilise la vraie contenance
    df_cross['Volume_Cols'] = df_cross['Volume_HL'] * (10000 / df_cross['contenance_cl'].replace(0, 100))
    
    df_cross['CAGR (%)'] = df_cross['CAGR_val'] * 100
    df_cross['Date'] = df_cross['mois'].apply(lambda m: MOIS_NOMS[m-1]) + '-' + df_cross['annee'].astype(str).str[-2:]
    
    df_cross = df_cross.rename(columns={'Projection_CurrentYear': 'Projection_Annuelle'})
    
    cols_finales = ["annee", "mois", "agence", "article", "contenance_cl", "Date", "Statut", "Indice", "Projection_Annuelle", "CAGR (%)", "Volume_HL", "Volume_Cols"]
    
    return table_indices, df_sarr, None, df_cross[cols_finales].copy(), df_realise

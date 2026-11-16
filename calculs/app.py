with tab_placeholder.container():
    if active_tab == "Données Brutes":
        st.markdown("### Données Brutes Enrichies")
        with st.expander("📊 Afficher le tableau des données brutes", expanded=True):
            cols_to_show = ["annee", "mois", "region", "agence", "article", "hl", "rupture_hl", "hl_potentiel"]
            df_to_show = df_enrichi[cols_to_show].copy()
            df_to_show.columns = ["Année", "Mois", "Région", "Agence", "Article", "Ventes Réelles (HL)", "Pertes Ruptures (HL)", "Volume Potentiel (HL)"]
            total_reel = df_to_show['Ventes Réelles (HL)'].sum()
            small_kpi("TOTAL Ventes Réelles", format_fr(total_reel))
            if len(df_to_show) > N_MAX_DISPLAY:
                st.caption(f"⚠️ Affichage limité à {format_fr(N_MAX_DISPLAY)} lignes sur {format_fr(len(df_to_show))}.")
                df_show_limited = ajouter_total(df_to_show.head(N_MAX_DISPLAY - 1), label_col="Année", label="TOTAL (affiché)")
                st.dataframe(bold_total_row(df_show_limited), use_container_width=True, hide_index=True)
            else:
                df_show_full = ajouter_total(df_to_show, label_col="Année")
                st.dataframe(bold_total_row(df_show_full), use_container_width=True, hide_index=True)

    elif active_tab == "Réalisé Cumulé":
        st.markdown("### Réalisé Cumulé (Jusqu'au Cutoff)")
        with st.expander("📊 Afficher le tableau du réalisé", expanded=True):
            if df_realise is not None and not df_realise.empty:
                df_real_agg = (df_realise.groupby(['annee', 'mois', 'region', 'agence', 'article'], observed=True)[['hl', 'rupture_hl', 'hl_potentiel']].sum().reset_index())
                df_real_agg.columns = ["Année", "Mois", "Région", "Agence", "Article", "Ventes Réelles", "Pertes Ruptures", "Volume Potentiel"]
                total_reel = df_real_agg['Ventes Réelles'].sum()
                small_kpi("TOTAL Ventes Réelles", format_fr(total_reel))
                if len(df_real_agg) > N_MAX_DISPLAY:
                    df_real_agg_aff = ajouter_total(df_real_agg.head(N_MAX_DISPLAY - 1), label_col="Année", label="TOTAL (affiché)")
                else:
                    df_real_agg_aff = ajouter_total(df_real_agg, label_col="Année")
                st.dataframe(bold_total_row(df_real_agg_aff), use_container_width=True, hide_index=True)
            else: st.info("Aucune donnée réalisée pour le moment.")

    elif active_tab == "Indices & SARR":
        st.markdown("### Indices de Saisonnalité & SARR")
        df_sarr_calc = df_sarr.sort_values(['agence', 'article', 'annee', 'mois']).copy()
        df_sarr_calc["SARR_Aff"] = (df_sarr_calc["SARR_HL"] * (10000 / df_sarr_calc["contenance_cl"].replace(0, 100)) if unite_affichage == "Cols" else df_sarr_calc["SARR_HL"])
        df_sarr_calc["SARR_M1_Aff"] = (df_sarr_calc["SARR_M1"] * (10000 / df_sarr_calc["contenance_cl"].replace(0, 100)) if unite_affichage == "Cols" else df_sarr_calc["SARR_M1"])
        df_sarr_calc["Mois M"] = df_sarr_calc.apply(lambda r: f"{MOIS_NOMS[int(r['mois'])-1]}-{int(r['annee'])}", axis=1)
        df_sarr_calc["Mois M-1"] = df_sarr_calc.groupby(['agence', 'article'])["Mois M"].shift(1)
        df_sarr_calc["Momentum_Abs"] = df_sarr_calc["SARR_Aff"] - df_sarr_calc["SARR_M1_Aff"]
        df_sarr_calc["Momentum_Pct"] = (df_sarr_calc["Momentum_Abs"] / df_sarr_calc["SARR_M1_Aff"] * 100).replace([np.inf, -np.inf], np.nan)
        df_sarr_derniers = df_sarr_calc.groupby(['agence', 'article'], observed=True).tail(5)

        filtre_sarr = st.radio("Afficher le SARR et Graphes :", ["Tous", "Momentum Positif (+)", "Momentum Négatif (-)"], horizontal=True, label_visibility="collapsed")
        df_sarr_affiche = df_sarr_derniers.copy()
        if filtre_sarr == "Momentum Positif (+)":
            df_sarr_affiche = df_sarr_affiche[df_sarr_affiche["Momentum_Abs"] > 0]
        elif filtre_sarr == "Momentum Négatif (-)":
            df_sarr_affiche = df_sarr_affiche[df_sarr_affiche["Momentum_Abs"] < 0]

        c_idx, c_sarr = st.columns(2)
        with c_idx:
            st.markdown("**Indices de Saisonnalité (Glissant par Année)**")
            st.caption("💡 Note : L'indice global est recalculé pour chaque année en utilisant les 2 années précédentes (ex: 2023 utilise 2021-2022).")
            with st.expander("📊 Afficher les indices globaux par année", expanded=True):
                if not df_global_rolling.empty:
                    pivot_global = df_global_rolling.pivot(index='annee', columns='mois', values='Indice_glob')
                    pivot_global.columns = [MOIS_NOMS[int(c)-1] for c in pivot_global.columns]
                    pivot_global.index = [f"Année {int(y)}" for y in pivot_global.index]
                    st.dataframe(pivot_global.style.format("{:.2f}"), use_container_width=True)
                    st.markdown("---")
                st.markdown("**Détail par Article (Base Prévision)**")
                if not table_indices_forecast.empty:
                    pivot_indices = _pivot_indices_cached(table_indices_forecast)
                    st.dataframe(pivot_indices, use_container_width=True)
                else: st.info("Pas d'historique complet.")
        with c_sarr:
            st.markdown("**Table SARR (5 derniers mois) avec Momentum**")
            with st.expander("📊 Afficher le SARR & Momentum", expanded=True):
                df_sarr_aff = df_sarr_affiche[["annee", "mois", "agence", "article", "Mois M-1", "SARR_M1_Aff", "Mois M", "SARR_Aff", "Momentum_Abs", "Momentum_Pct"]].rename(columns={"annee": "Année", "mois": "Mois (Num)", "agence": "Agence", "article": "Article", "SARR_M1_Aff": "SARR M-1", "SARR_Aff": "SARR M", "Momentum_Abs": "Momentum (SARR M - SARR M-1)", "Momentum_Pct": "Momentum (%)"}).sort_values(["Agence", "Article", "Année", "Mois (Num)"])
                def calc_mom_pct(r):
                    if r.get("SARR M-1", 0) > 0:
                        return (r.get("Momentum (SARR M - SARR M-1)", 0) / r["SARR M-1"]) * 100
                    return np.nan
                df_sarr_aff = ajouter_total(df_sarr_aff, label_col="Agence", exclude_cols=["Momentum (%)"], custom_total_calc={"Momentum (%)": calc_mom_pct})
                small_kpi("TOTAL SARR M", format_fr(df_sarr_aff["SARR M"].iloc[-1]))
                st.dataframe(bold_total_row(df_sarr_aff), use_container_width=True, hide_index=True,
                    column_config={"Année": st.column_config.NumberColumn(format="%d"), "Mois (Num)": None, "SARR M": st.column_config.NumberColumn(format="%.0f"), "SARR M-1": st.column_config.NumberColumn(format="%.0f"), "Momentum (SARR M - SARR M-1)": st.column_config.NumberColumn(format="%.1f"), "Momentum (%)": st.column_config.NumberColumn(format="%.2f %%")})
        st.markdown("---")
        st.markdown("### 📈 Visualisation Graphique")
        c_graph1, c_graph2 = st.columns(2)
        with c_graph1:
            st.markdown("**Graphique du Momentum (Barres Verticales)**")
            if not df_sarr_affiche.empty:
                df_momentum_plot = df_sarr_affiche.copy()
                df_momentum_plot["Label"] = df_momentum_plot["agence"] + " - " + df_momentum_plot["article"]
                df_momentum_plot = df_momentum_plot.sort_values(['agence', 'article', 'annee', 'mois']).groupby(['agence', 'article', 'Label']).tail(1).reset_index()
                if filtre_sarr == "Tous":
                    df_momentum_plot["Abs_Mom"] = df_momentum_plot["Momentum_Abs"].abs()
                    df_momentum_plot = df_momentum_plot.sort_values("Abs_Mom", ascending=False).head(10)
                df_momentum_plot = df_momentum_plot.sort_values("Momentum_Abs", ascending=False)
                df_momentum_plot["Label_Court"] = df_momentum_plot["Label"].apply(lambda x: x if len(x) <= 25 else x[:22] + '...')
                moy_momentum_global = df_momentum_plot["Momentum_Abs"].mean()
                fig_mom = go.Figure()
                fig_mom.add_trace(go.Bar(x=df_momentum_plot["Label_Court"], y=df_momentum_plot["Momentum_Abs"], marker_color=[COLORS["VERT"] if x >= 0 else COLORS["ROUGE"] for x in df_momentum_plot["Momentum_Abs"]], text=df_momentum_plot["Momentum_Abs"].apply(lambda x: format_fr(x, signed=True)), textposition="auto", hovertemplate="<b>%{x}</b><br>Momentum: %{y:,.1f} HL<extra></extra>"))
                fig_mom.add_hline(y=0, line_dash="dash", line_color=COLORS['GRIS'])
                fig_mom.add_hline(y=moy_momentum_global, line_dash="dot", line_color=COLORS['TEXTE'], annotation_text=f"Moy. Globale ({format_fr(moy_momentum_global, 1, signed=True)})", annotation_position="top right")
                fig_mom.update_layout(plot_bgcolor=COLORS['BLANC'], paper_bgcolor=COLORS['BLANC'], margin=dict(l=10, r=10, t=30, b=60), xaxis=dict(title="SKU", showgrid=False, tickangle=-45, tickfont=dict(family="Inter", size=11, color=COLORS['TEXTE'], weight="bold")), yaxis=dict(title=f"Momentum ({unite_affichage})", showgrid=True, gridcolor=COLORS['BORDURE'], tickfont=dict(family="Inter", size=11, color=COLORS['TEXTE'], weight="bold")), height=500, separators=" ,")
                st.plotly_chart(fig_mom, use_container_width=True, config={'displayModeBar': False})
            else: st.info("Aucune donnée de Momentum à afficher avec ce filtre.")
        with c_graph2:
            st.markdown("**Courbe de Saisonnalité Globale**")
            if not df_perimetre.empty:
                df_global_hl = df_perimetre.groupby('mois', observed=True)['hl'].sum().reset_index()
                total_hl = df_global_hl['hl'].sum()
                df_global_hl['Indice_Glob'] = df_global_hl['hl'] / (total_hl / 12.0) if total_hl > 0 else 1.0
                df_global_hl['Mois_Nom'] = df_global_hl['mois'].apply(lambda m: MOIS_NOMS[int(m)-1])
                fig_season = go.Figure()
                fig_season.add_trace(go.Scatter(x=df_global_hl['Mois_Nom'], y=df_global_hl['Indice_Glob'], mode='lines+markers', line=dict(color=COLORS['ROUGE'], width=4, shape='spline'), marker=dict(size=8, color=COLORS['ROUGE'], line=dict(color='white', width=2)), fill='tozeroy', fillcolor='rgba(227, 6, 19, 0.1)', hovertemplate="<b>%{x}</b><br>Indice global: %{y:.2f}<extra></extra>"))
                fig_season.add_hline(y=1.0, line_dash="dot", line_color=COLORS['TEXTE'], annotation_text="Moyenne Globale (1.0)", annotation_position="top left")
                fig_season.update_layout(plot_bgcolor=COLORS['BLANC'], paper_bgcolor=COLORS['BLANC'], margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(title="Mois", showgrid=True, gridcolor=COLORS['BORDURE'], tickfont=dict(family="Inter", size=11, color=COLORS['TEXTE'], weight="bold")), yaxis=dict(title="Indice global de saisonnalité", showgrid=True, gridcolor=COLORS['BORDURE'], tickfont=dict(family="Inter", size=11, color=COLORS['TEXTE'], weight="bold")), height=500, separators=" ,")
                st.plotly_chart(fig_season, use_container_width=True, config={'displayModeBar': False})
            else: st.info("Pas de données de saisonnalité disponibles.")

    elif active_tab == "Prévisions":
        st.markdown("### Prévisions Détaillées")
        st.markdown(f"Projections mensuelles pour : **<span style='color: {COLORS['ROUGE']};'>{label_mois_str}</span>**", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col_search, col_export = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("Rechercher", "", placeholder="Rechercher un article ou une agence...", label_visibility="collapsed", key="search_previsions")
        with st.expander("📊 Afficher le tableau des prévisions détaillées (Format Excel)", expanded=True):
            df_seg = df_perimetre[['article', 'segment']].drop_duplicates(subset=['article'])
            df_prev_cible_t = df_previsions_filtre[df_previsions_filtre['annee'] == annee_cible].copy()
            df_prev_seg = df_prev_cible_t.merge(df_seg, on='article', how='left')
            pivot_mensuel = df_prev_seg.pivot_table(index=['article', 'segment'], columns='mois', values=col_prev_aff, aggfunc='sum')
            pivot_mensuel = pivot_mensuel.reindex(columns=range(1, 13), fill_value=0)
            pivot_mensuel.columns = [MOIS_NOMS[int(c) - 1] for c in pivot_mensuel.columns]
            if not mois_cibles_selection or len(mois_cibles_selection) == 12: nom_total = "Total Année"
            else: nom_total = "Total Période"
            pivot_mensuel[nom_total] = pivot_mensuel.sum(axis=1)
            pivot_mensuel = pivot_mensuel[pivot_mensuel[nom_total] > 0]
            pivot_mensuel_reset = pivot_mensuel.reset_index().rename(columns={'article': 'Articles', 'segment': 'Segments'})
            if search_query:
                mask = pivot_mensuel_reset.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                pivot_mensuel_display = pivot_mensuel_reset[mask]
            else: pivot_mensuel_display = pivot_mensuel_reset
            total_periode = pivot_mensuel_display[nom_total].sum()
            small_kpi(f"TOTAL {nom_total} ({unite_affichage})", format_fr(total_periode))
            pivot_mensuel_display = ajouter_total(pivot_mensuel_display, label_col="Articles")
            col_config = {"Articles": st.column_config.TextColumn("Articles", width="medium"), "Segments": st.column_config.TextColumn("Segments", width="small")}
            for mois in MOIS_NOMS:
                if mois in pivot_mensuel_display.columns: col_config[mois] = st.column_config.NumberColumn(mois, format="%.2f")
            if nom_total in pivot_mensuel_display.columns: col_config[nom_total] = st.column_config.NumberColumn(nom_total, format="%.2f")
            st.dataframe(bold_total_row(pivot_mensuel_display), use_container_width=True, hide_index=True, column_config=col_config, height=600)
        with st.expander("🔍 Voir le détail des calculs (Hybride)"):
            st.markdown("**Note :** L'année de clôture utilise la projection du Run-Rate (Base Mensuelle) pour éviter l'explosion du Momentum absolu. Les années suivantes ajoutent le CAGR calculé.")
            cols_to_show = ["annee", "mois", "Statut", "agence", "article", "Indice", "Base_EXCEL", "Momentum", "Base_Mensuelle", "CAGR (%)", col_prev_aff]
            df_detail = df_previsions_filtre[cols_to_show].sort_values(["annee", "mois", "agence", "article"])
            if len(df_detail) > N_MAX_DISPLAY:
                df_detail_aff = ajouter_total(df_detail.head(N_MAX_DISPLAY - 1), label_col="annee", label="TOTAL (affiché)", exclude_cols=["CAGR (%)", "Indice"])
            else:
                df_detail_aff = ajouter_total(df_detail, label_col="annee", exclude_cols=["CAGR (%)", "Indice"])
            st.dataframe(bold_total_row(df_detail_aff), use_container_width=True, hide_index=True, height=400, column_config={"Base_EXCEL": st.column_config.NumberColumn(format="%.1f"), "Momentum": st.column_config.NumberColumn(format="%.1f"), "Base_Mensuelle": st.column_config.NumberColumn(format="%.1f"), "CAGR (%)": st.column_config.NumberColumn(format="%.2f %%")})

    elif active_tab == "Suivi Écart (Rupt vs Réalisé)":
        st.markdown("### 🔀 Suivi Écart (Rupt vs Réalisé)")
        st.markdown("Tableau comparatif professionnel : Réalisé vs Prévision, avec et sans rupture.")
        st.markdown("<br>", unsafe_allow_html=True)
        has_rupture = df_perimetre['rupture_hl'].fillna(0).sum() > 0
        if not has_rupture:
            st.info("ℹ️ Aucune donnée de rupture détectée dans le périmètre sélectionné. Les prévisions 'avec' et 'sans' rupture sont identiques.")
        col_vol_sans = "Volume_Cols_sans_rupture" if unite_affichage == "Cols" else "Volume_HL_sans_rupture"
        df_year = df_previsions_filtre[df_previsions_filtre['annee'] == annee_cible].copy()
        if df_year.empty:
            st.warning("Aucune donnée de prévision pour l'année cible.")
        else:
            total_avec = df_year[col_prev_aff].fillna(0).sum()
            total_sans = df_year[col_vol_sans].fillna(0).sum()
            diff = total_sans - total_avec
            diff_pct = (diff / total_avec * 100) if total_avec > 0 else 0
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.markdown(f"""<div class="kpi-card" style="border-left-color: {COLORS['ROUGE']};"><div class="kpi-label">Total AVEC rupture ({unite_affichage})</div><div class="kpi-value">{format_fr(total_avec)}</div><div class="kpi-delta" style="color: {COLORS['TEXTE_SECONDAIRE']};">Base : ventes réelles</div></div>""", unsafe_allow_html=True)
            with rc2:
                st.markdown(f"""<div class="kpi-card" style="border-left-color: {COLORS['VERT']};"><div class="kpi-label">Total SANS rupture ({unite_affichage})</div><div class="kpi-value">{format_fr(total_sans)}</div><div class="kpi-delta" style="color: {COLORS['TEXTE_SECONDAIRE']};">Base : volume potentiel</div></div>""", unsafe_allow_html=True)
            with rc3:
                ecart_color = COLORS['VERT'] if diff >= 0 else COLORS['ROUGE']
                st.markdown(f"""<div class="kpi-card" style="border-left-color: {ecart_color};"><div class="kpi-label">Manque à gagner (rupture)</div><div class="kpi-value" style="color: {ecart_color};">{format_fr(diff, signed=True)}</div><div class="kpi-delta" style="color: {ecart_color};">{format_fr(diff_pct, 1, signed=True)}% vs prévision avec rupture</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            col_search_tab, col_view_mode = st.columns([2, 1])
            with col_search_tab:
                search_query = st.text_input("🔍 Rechercher un article ou une marque", "", placeholder="Ex: World Cola, FOSA...", key="search_recap")
            with col_view_mode:
                view_mode = st.radio("Vue", ["Compacte", "Complète"], horizontal=True, label_visibility="collapsed")
            mode_affichage = st.radio("Mode d'affichage", ["Récap Annuel par Article", "Détail Mensuel Côte-à-côte"], horizontal=True, label_visibility="collapsed", key="recap_mode_tab")
            df_meta = df_perimetre[['article', 'segment', 'marque', 'contenance_cl']].drop_duplicates(subset=['article'])
            df_year = df_year.merge(df_meta, on='article', how='left')

            # PATCH : conversion hl_reel en Cols si nécessaire
            if unite_affichage == "Cols":
                _cont_safe = df_year['contenance_cl'].replace(0, 100).fillna(100.0)
                df_year['hl_reel_aff'] = df_year['hl_reel'].fillna(0.0) * (10000.0 / _cont_safe)
            else:
                df_year['hl_reel_aff'] = df_year['hl_reel'].fillna(0.0)

            if mode_affichage == "Récap Annuel par Article":
                recap_df = df_year.groupby(['marque', 'article'], as_index=False).agg(
                    Realise=('hl_reel_aff', 'sum'),
                    Prevision=(col_prev_pure, 'sum')
                )
                df_rupture_sum = df_perimetre[(df_perimetre['annee'] == annee_cible) & (df_perimetre['mois'].isin(mois_cibles_nums))]
                df_rupture_sum = df_rupture_sum.groupby('article', as_index=False)['rupture_hl'].sum()
                recap_df = recap_df.merge(df_rupture_sum, on='article', how='left').fillna({'rupture_hl': 0})
                recap_df['Réalisé + Rupture'] = recap_df['Realise'] + recap_df['rupture_hl']
                recap_df['Écart PV'] = recap_df['Prevision'] - recap_df['Réalisé + Rupture']
                recap_df['% PV'] = np.where(recap_df['Prevision'] > 0, (recap_df['Réalisé + Rupture'] - recap_df['Prevision']) / recap_df['Prevision'] * 100, 0)
                recap_df = recap_df.rename(columns={'marque': 'Marque', 'article': 'Article', 'Realise': 'Réalisé', 'Prevision': 'Prévision', 'rupture_hl': 'Rupture'})
                recap_df = recap_df[(recap_df['Réalisé'] > 0) | (recap_df['Prévision'] > 0)].sort_values('Réalisé', ascending=False)
                if search_query:
                    mask = recap_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                    recap_df = recap_df[mask]
                if view_mode == "Compacte":
                    cols_to_keep = ['Marque', 'Article', 'Réalisé', 'Prévision', 'Écart PV', '% PV']
                else:
                    cols_to_keep = ['Marque', 'Article', 'Réalisé', 'Prévision', 'Rupture', 'Réalisé + Rupture', 'Écart PV', '% PV']
                recap_df = recap_df[cols_to_keep]

                # PATCH : TOTAL % PV cohérent avec la formule ligne (Réalisé + Rupture)
                def calc_total_pct(r):
                    if r.get("Prévision", 0) > 0:
                        num = r.get("Réalisé + Rupture", r.get("Réalisé", 0))
                        return (num - r["Prévision"]) / r["Prévision"] * 100
                    return 0
                recap_df = ajouter_total(recap_df, label_col="Marque", label="TOTAL", exclude_cols=["% PV"], custom_total_calc={"% PV": calc_total_pct})

                def style_dataframe(df):
                    def color_ecart(val):
                        if pd.isna(val): return ''
                        if val > 0: return f'background-color: {COLORS["ROUGE_CLAIR"]}; color: {COLORS["ROUGE"]}; font-weight: 700; border-left: 2px solid {COLORS["ROUGE"]};'
                        elif val < 0: return f'background-color: {COLORS["VERT_CLAIR"]}; color: {COLORS["VERT"]}; font-weight: 700; border-left: 2px solid {COLORS["VERT"]};'
                        return ''
                    def color_pct(val):
                        if pd.isna(val): return ''
                        if val >= 0: return f'background-color: {COLORS["VERT_CLAIR"]}; color: {COLORS["VERT"]}; font-weight: 700;'
                        return f'background-color: {COLORS["ROUGE_CLAIR"]}; color: {COLORS["ROUGE"]}; font-weight: 700;'
                    def color_rupture(val):
                        if pd.isna(val): return ''
                        if val > 0: return f'color: {COLORS["ORANGE"]}; font-weight: 700;'
                        return ''
                    fmt_dict = {'Réalisé': '{:,.0f}', 'Prévision': '{:,.0f}', 'Rupture': '{:,.0f}', 'Réalisé + Rupture': '{:,.0f}', 'Écart PV': '{:+,.0f}', '% PV': '{:+.1f} %'}
                    styled = df.style.format(fmt_dict)
                    if 'Écart PV' in df.columns: styled = styled.map(color_ecart, subset=['Écart PV'])
                    if '% PV' in df.columns: styled = styled.map(color_pct, subset=['% PV'])
                    if 'Rupture' in df.columns: styled = styled.map(color_rupture, subset=['Rupture'])
                    def highlight_total(row):
                        if row.name == len(df) - 1:
                            return [f'background-color: #F3F4F6; font-weight: 800; color: {COLORS["TEXTE"]}; border-top: 2px solid #9CA3AF;'] * len(row)
                        return [''] * len(row)
                    return styled.apply(highlight_total, axis=1)

                with st.container(border=True):
                    st.markdown(f"#### 📊 Récap Annuel par Article")
                    st.caption("🟢 Vert = Objectif dépassé / 🔴 Rouge = Objectif manqué / 🟠 Orange = Rupture")
                    st.dataframe(style_dataframe(recap_df), use_container_width=True, hide_index=True, height=600)
            else:
                pivot_avec = df_year.pivot_table(index=['article', 'segment'], columns='mois', values=col_prev_aff, aggfunc='sum').fillna(0)
                pivot_avec = pivot_avec.reindex(columns=range(1, 13), fill_value=0)
                pivot_avec.columns = [MOIS_NOMS[int(c) - 1] for c in pivot_avec.columns]
                pivot_sans = df_year.pivot_table(index=['article', 'segment'], columns='mois', values=col_vol_sans, aggfunc='sum').fillna(0)
                pivot_sans = pivot_sans.reindex(columns=range(1, 13), fill_value=0)
                pivot_sans.columns = [MOIS_NOMS[int(c) - 1] for c in pivot_sans.columns]
                pivot_avec_reset = pivot_avec.reset_index().rename(columns={'article': 'Article', 'segment': 'Segment'})
                pivot_avec_reset = ajouter_total(pivot_avec_reset, label_col="Article")
                pivot_sans_reset = pivot_sans.reset_index().rename(columns={'article': 'Article', 'segment': 'Segment'})
                pivot_sans_reset = ajouter_total(pivot_sans_reset, label_col="Article")
                c_avec, c_sans = st.columns(2)
                with c_avec:
                    with st.container(border=True):
                        st.markdown(f"**🟥 AVEC rupture ({unite_affichage})**")
                        st.dataframe(bold_total_row(pivot_avec_reset), use_container_width=True, height=600, hide_index=True)
                with c_sans:
                    with st.container(border=True):
                        st.markdown(f"**🟩 SANS rupture ({unite_affichage})**")
                        st.dataframe(bold_total_row(pivot_sans_reset), use_container_width=True, height=600, hide_index=True)

    elif active_tab == "Pareto (ABC)":
        st.markdown("### Analyse Pareto & Classification ABC")
        st.markdown("La classification ABC est une méthode de gestion des stocks qui consiste à diviser les articles en trois classes en fonction de leur contribution au volume total :")
        st.markdown("- **Classe A (0-80.5%)** : Les articles vitaux (généralement 20% des articles qui font 80% des ventes).\n- **Classe B (80.5-95%)** : Les articles intermédiaires.\n- **Classe C (95-100%)** : Les articles à faible rotation (la longue traîne).")
        st.markdown("---")
        st.markdown("#### 🧩 Matrice ABC-XYZ")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            seuil_x_pct = st.number_input("Seuil X (Stable) - CV < (%)", min_value=1.0, max_value=100.0, value=25.0, step=1.0, key="param_seuil_x")
        with col_s2:
            seuil_y_pct = st.number_input("Seuil Y (Variable) - CV < (%)", min_value=seuil_x_pct, max_value=200.0, value=50.0, step=1.0, key="param_seuil_y")
        st.markdown(f"La classification **XYZ** est basée sur la volatilité des ventes (Coefficient de Variation = Écart-type / Moyenne) :\n- **X** : Faible volatilité (CV < {format_fr(seuil_x_pct, 0)}%) - Ventes régulières\n- **Y** : Volatilité moyenne ({format_fr(seuil_x_pct, 0)}% <= CV < {format_fr(seuil_y_pct, 0)}%)\n- **Z** : Forte volatilité (CV >= {format_fr(seuil_y_pct, 0)}%) - Ventes irrégulières")
        df_pareto = df_previsions_filtre[df_previsions_filtre['annee'] == annee_cible].groupby('article', observed=True)[col_prev_aff].sum().sort_values(ascending=False).reset_index()
        df_pareto = df_pareto[df_pareto[col_prev_aff] > 0]
        if not df_pareto.empty:
            total_vol = df_pareto[col_prev_aff].sum()
            df_pareto['Cumul_Pct'] = (df_pareto[col_prev_aff].cumsum() / total_vol) * 100
            df_pareto['Classe'] = np.select([df_pareto['Cumul_Pct'] <= 80.5, df_pareto['Cumul_Pct'] <= 95], ['A', 'B'], default='C')
            pivot_vol = df_previsions_filtre[df_previsions_filtre['annee'] == annee_cible].pivot_table(index='article', columns='mois', values=col_prev_aff, aggfunc='sum').fillna(0)
            if not pivot_vol.empty:
                df_xyz = pd.DataFrame({'Mean': pivot_vol.mean(axis=1), 'Std': pivot_vol.std(axis=1)}).reset_index()
                df_xyz['CV'] = df_xyz['Std'] / df_xyz['Mean']
                df_xyz['CV'] = df_xyz['CV'].replace([np.inf, -np.inf], np.nan).fillna(0)
                seuil_x_dec = seuil_x_pct / 100.0
                seuil_y_dec = seuil_y_pct / 100.0
                df_xyz['XYZ'] = np.select([df_xyz['CV'] < seuil_x_dec, df_xyz['CV'] < seuil_y_dec], ['X', 'Y'], default='Z')
                df_pareto_xyz = df_pareto.merge(df_xyz[['article', 'XYZ']], on='article', how='left')
                df_pareto_xyz['XYZ'] = df_pareto_xyz['XYZ'].fillna('Z')
                df_matrix = pd.crosstab(df_pareto_xyz['Classe'], df_pareto_xyz['XYZ'], margins=True, margins_name='Total')
                df_matrix = df_matrix.reindex(index=['A', 'B', 'C', 'Total'], columns=['X', 'Y', 'Z', 'Total'], fill_value=0)
                st.dataframe(df_matrix, use_container_width=True)
            else: st.info("Pas assez de données pour calculer la matrice XYZ.")
            st.markdown("---")
            df_pareto_graph = df_pareto.head(15).copy()
            df_pareto_graph['Index'] = range(len(df_pareto_graph))
            df_pareto_graph['Article_Court'] = df_pareto_graph['article'].apply(lambda x: x if len(str(x)) <= 22 else str(x)[:19] + '...')
            fig2 = go.Figure()
            couleurs = {'A': COLORS['ROUGE'], 'B': '#F59E0B', 'C': '#9CA3AF'}
            for classe in ['A', 'B', 'C']:
                df_class = df_pareto_graph[df_pareto_graph['Classe'] == classe]
                if not df_class.empty:
                    fig2.add_trace(go.Bar(x=df_class['Index'], y=df_class[col_prev_aff], name=f'Classe {classe}', marker_color=couleurs[classe], customdata=df_class['article'], hovertemplate="<b>%{customdata}</b><br>Volume: %{y:,.0f}<extra></extra>"))
            fig2.add_trace(go.Scatter(x=df_pareto_graph['Index'], y=df_pareto_graph['Cumul_Pct'], name='% Cumulé', mode='lines+markers', line=dict(color=COLORS['TEXTE'], width=2), marker=dict(size=6, color=COLORS['TEXTE']), yaxis='y2', customdata=df_pareto_graph['article'], hovertemplate="<b>%{customdata}</b><br>% Cumulé: %{y:.1f}%<extra></extra>"))
            for seuil, color in [(80.5, COLORS['ROUGE']), (95, '#F59E0B')]:
                fig2.add_shape(type="line", x0=-0.5, x1=len(df_pareto_graph)-0.5, y0=seuil, y1=seuil, line=dict(color=color, width=1.5, dash="dot"), xref='x', yref='y2')
            fig2.update_layout(separators=" ,", plot_bgcolor=COLORS['BLANC'], paper_bgcolor=COLORS['BLANC'], margin=dict(l=0, r=0, t=20, b=60), yaxis=dict(title=f"Volume ({unite_affichage})", showgrid=True, gridcolor=COLORS['BORDURE'], tickfont=dict(family="Inter", size=12, weight="bold")), yaxis2=dict(title="% Cumulé", overlaying='y', side='right', range=[0, 110], tickvals=[0, 20, 40, 60, 80, 100], showgrid=False, ticksuffix="%", tickfont=dict(family="Inter", size=12, weight="bold")), xaxis=dict(tickmode='array', tickvals=df_pareto_graph['Index'], ticktext=df_pareto_graph['Article_Court'], tickangle=-45, showgrid=False, tickfont=dict(size=11, family="Inter", weight="bold")), legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5), height=450, bargap=0.3, hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
            with st.expander("📋 Voir le détail par article", expanded=True):
                df_table = df_pareto_xyz[['article', 'Classe', 'XYZ', col_prev_aff, 'Cumul_Pct']].copy()
                df_table.columns = ['Article', 'Classe ABC', 'Classe XYZ', f'Volume ({unite_affichage})', '% Cumulé']
                df_table = ajouter_total(df_table, label_col="Article", exclude_cols=["% Cumulé"], custom_total_calc={"% Cumulé": lambda r: 100.0})
                small_kpi("TOTAL Volume", format_fr(df_table[f'Volume ({unite_affichage})'].iloc[-1]))
                st.dataframe(bold_total_row(df_table), use_container_width=True, hide_index=True, column_config={f'Volume ({unite_affichage})': st.column_config.NumberColumn(format="localized"), '% Cumulé': st.column_config.NumberColumn(format="%.1f %%"), 'Classe ABC': st.column_config.TextColumn(width="small"), 'Classe XYZ': st.column_config.TextColumn(width="small")}, height=400)
        else: st.info("Pas assez de données pour l'analyse.")

    elif active_tab == "Analyse Comportementale":
        st.markdown("### 🧠 Analyse Comportementale par SKU")
        st.markdown("Cette section analyse le comportement de chaque article (croissance, saisonnalité, momentum) et génère un diagnostic automatique.")
        st.markdown("<br>", unsafe_allow_html=True)
        df_analyse = analyser_comportement_sku(df_sarr, df_perimetre)
        if df_analyse.empty:
            st.info("Pas assez de données pour l'analyse comportementale (minimum 6 mois d'historique par SKU).")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtre_profil = st.multiselect("Filtrer par profil", options=sorted(df_analyse['Profil'].unique()), default=[], placeholder="Tous les profils")
            with col_f2:
                search_sku = st.text_input("Rechercher un SKU", "", placeholder="Nom de l'article ou agence...")
            df_display = df_analyse.copy()
            if filtre_profil: df_display = df_display[df_display['Profil'].isin(filtre_profil)]
            if search_sku:
                mask = df_display['Article'].str.contains(search_sku, case=False, na=False) | df_display['Agence'].str.contains(search_sku, case=False, na=False)
                df_display = df_display[mask]
            st.markdown("<br>", unsafe_allow_html=True)
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                nb_star = (df_analyse['Profil'].str.contains("Star")).sum()
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">🌟 SKU Stars</div><div class="kpi-value">{format_fr(nb_star)}</div><div class="kpi-delta up">Priorité réappro</div></div>""", unsafe_allow_html=True)
            with k2:
                nb_declin = (df_analyse['Profil'].str.contains("déclin")).sum()
                st.markdown(f"""<div class="kpi-card" style="border-left-color: {COLORS['ROUGE']};"><div class="kpi-label">📉 SKU En Déclin</div><div class="kpi-value" style="color: {COLORS['ROUGE']};">{format_fr(nb_declin)}</div><div class="kpi-delta down">À arbitrer</div></div>""", unsafe_allow_html=True)
            with k3:
                nb_saison = (df_analyse['Profil'].str.contains("Saisonnier")).sum()
                st.markdown(f"""<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-label">🏔️ SKU Saisonniers</div><div class="kpi-value" style="color: #F59E0B;">{format_fr(nb_saison)}</div><div class="kpi-delta">Stock anticipé</div></div>""", unsafe_allow_html=True)
            with k4:
                st.markdown(f"""<div class="kpi-card" style="border-left-color: {COLORS['TEXTE']};"><div class="kpi-label">📊 SKU Analysés</div><div class="kpi-value">{format_fr(len(df_analyse))}</div><div class="kpi-delta" style="color: {COLORS['TEXTE_SECONDAIRE']};">Total</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander(f"📋 Diagnostic détaillé ({format_fr(len(df_display))} SKU)", expanded=True):
                for _, row in df_display.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        with c1:
                            st.markdown(f"**{row['Article']}**")
                            st.caption(f"_{row['Agence']}_")
                            st.markdown(f"### {row['Profil']}")
                        with c2:
                            st.markdown(row['Commentaire'])
                            st.info(f"**Recommandation :** {row['Recommandation']}")
                            mc1, mc2, mc3, mc4 = st.columns(4)
                            mc1.metric("SARR moyen", f"{format_fr(row['SARR moyen (HL/mois)'])} HL")
                            mc2.metric("Momentum", f"{format_fr(row['Momentum (HL)'], signed=True)} HL")
                            mc3.metric("CAGR", f"{format_fr(row['CAGR (%)'], 1, signed=True)}%")
                            mc4.metric("Pic", row['Mois Pic'])

    elif active_tab == "Fiabilité":
        st.markdown("### Qualité et Fiabilité du Modèle")
        st.markdown("Cette section évalue la précision de l'algorithme sur les mois déjà réalisés (période de cutoff). Elle permet de savoir si l'on peut faire confiance aux prévisions futures.")
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f"""<div class="white-card" style="border-top: 4px solid {COLORS['TEXTE_SECONDAIRE']};"><div class="kpi-label">MAE (Erreur Absolue Moyenne)</div><div class="kpi-value kpi-value-dark" style="font-size: 1.8rem;">{format_fr(mae, 2)}</div><div class="kpi-footer">Marge d'erreur moyenne en {unite_affichage}</div></div>""", unsafe_allow_html=True)
        with m2: st.markdown(f"""<div class="white-card" style="border-top: 4px solid {COLORS['TEXTE_SECONDAIRE']};"><div class="kpi-label">WMAPE (Erreur % Pondérée)</div><div class="kpi-value kpi-value-dark" style="font-size: 1.8rem;">{format_fr(wmape, 2)}%</div><div class="kpi-footer">Précision sur le volume total (Standard industrie)</div></div>""", unsafe_allow_html=True)
        with m3: st.markdown(f"""<div class="white-card" style="border-top: 4px solid {COLORS['TEXTE_SECONDAIRE']};"><div class="kpi-label">SMAPE (Erreur % Symétrique)</div><div class="kpi-value kpi-value-dark" style="font-size: 1.8rem;">{format_fr(smape, 2)}%</div><div class="kpi-footer">Précision sur les articles à faibles volumes</div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📊 Afficher le détail mensuel (Prévision vs Réalisé)", expanded=True):
            st.markdown("Ce tableau compare ce que le modèle prévoyait pour chaque mois écoulé par rapport à ce qui a réellement été vendu. Les cellules rouges indiquent une erreur critique (>10%).")
            if not df_eval_agg.empty:
                df_error_monthly = df_eval_agg.copy()
                df_error_monthly['Ecart'] = df_error_monthly[col_prev_aff] - df_error_monthly[col_prev_pure]
                df_error_monthly['Erreur_Absolue'] = df_error_monthly['Ecart'].abs()
                df_error_monthly['Erreur_Pct (%)'] = np.where(df_error_monthly[col_prev_aff] > 0, (df_error_monthly['Erreur_Absolue'] / df_error_monthly[col_prev_aff]) * 100, 0)
                df_error_monthly['Mois_Label'] = df_error_monthly['mois'].apply(lambda m: MOIS_NOMS[int(m)-1])
                df_error_monthly = df_error_monthly[['annee', 'Mois_Label', col_prev_aff, col_prev_pure, 'Ecart', 'Erreur_Pct (%)']]
                df_error_monthly.columns = ['Année', 'Mois', f'Réalisé ({unite_affichage})', f'Prévision ({unite_affichage})', 'Écart', 'Erreur (%)']
                def calc_err_pct(r):
                    if r.get(f'Réalisé ({unite_affichage})', 0) > 0:
                        return (abs(r.get('Écart', 0)) / r[f'Réalisé ({unite_affichage})']) * 100
                    return np.nan
                df_error_monthly = ajouter_total(df_error_monthly, label_col="Année", exclude_cols=["Erreur (%)"], custom_total_calc={"Erreur (%)": calc_err_pct})
                styled_error_df = df_error_monthly.style.map(color_error, subset=['Erreur (%)']).apply(lambda x: ['font-weight: bold; background-color: #F9FAFB;'] * len(x) if x.name == len(df_error_monthly)-1 else [''] * len(x), axis=1)
                st.dataframe(styled_error_df, use_container_width=True, hide_index=True, column_config={f'Réalisé ({unite_affichage})': st.column_config.NumberColumn(format="localized"), f'Prévision ({unite_affichage})': st.column_config.NumberColumn(format="localized"), 'Écart': st.column_config.NumberColumn(format="localized"), 'Erreur (%)': st.column_config.NumberColumn(format="%.2f %%")})
            else: st.info("Aucune donnée réalisée à évaluer pour le moment (le mois de cutoff n'est peut-être pas encore passé).")

    elif active_tab == "Ruptures":
        st.markdown("### Analyse de Rupture de Tendance")
        st.markdown("Cette section affiche les volumes perdus à cause des ruptures de stock, par SKU et par mois.")
        st.markdown("<br>", unsafe_allow_html=True)
        df_rupture_hist = df_perimetre[df_perimetre['rupture_hl'] > 0].copy()
        if not df_rupture_hist.empty:
            kr1, kr2, kr3 = st.columns(3)
            with kr1:
                vol_perdu_total = df_rupture_hist['rupture_hl'].sum()
                st.markdown(f"""<div class="white-card" style="border-top: 4px solid #F59E0B;"><div class="kpi-label">Volume Total Perdu</div><div class="kpi-value kpi-value-dark">{format_fr(vol_perdu_total)} HL</div><div class="kpi-footer">Sur le périmètre filtré</div></div>""", unsafe_allow_html=True)
            with kr2:
                nb_mois_ruptures = df_rupture_hist.groupby(['annee', 'mois']).ngroups
                st.markdown(f"""<div class="white-card" style="border-top: 4px solid #F59E0B;"><div class="kpi-label">Mois impactés</div><div class="kpi-value kpi-value-dark">{format_fr(nb_mois_ruptures)}</div><div class="kpi-footer">Nombre de mois avec au moins une rupture</div></div>""", unsafe_allow_html=True)
            with kr3:
                nb_sku_impactes = df_rupture_hist['article'].nunique()
                st.markdown(f"""<div class="white-card" style="border-top: 4px solid #F59E0B;"><div class="kpi-label">SKU Impactés</div><div class="kpi-value kpi-value-dark">{format_fr(nb_sku_impactes)}</div><div class="kpi-footer">Nombre d'articles différents</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("#### Top 15 des SKU les plus impactés")
                df_rupture_sku_all = df_rupture_hist.groupby('article', observed=True)['rupture_hl'].sum().reset_index()
                df_rupture_sku_top15 = df_rupture_sku_all.sort_values(by='rupture_hl', ascending=True).tail(15)
                fig_sku = go.Figure(go.Bar(x=df_rupture_sku_top15['rupture_hl'], y=df_rupture_sku_top15['article'], orientation='h', marker_color='#F59E0B', text=df_rupture_sku_top15['rupture_hl'].apply(lambda x: format_fr(x)), textposition='auto', hovertemplate="<b>%{y}</b><br>Perte: %{x:,.1f} HL<extra></extra>"))
                fig_sku.update_layout(separators=" ,", plot_bgcolor=COLORS['BLANC'], paper_bgcolor=COLORS['BLANC'], margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(title="Volume Perdu (HL)", showgrid=True, gridcolor=COLORS['BORDURE']), yaxis=dict(showgrid=False, tickfont=dict(size=11)), height=450)
                st.plotly_chart(fig_sku, use_container_width=True, config={'displayModeBar': False})
            with col_chart2:
                st.markdown("#### Évolution mensuelle des pertes (Top 5 SKU)")
                top_5_skus = df_rupture_sku_all.nlargest(5, 'rupture_hl')['article'].tolist()
                df_top = df_rupture_hist[df_rupture_hist['article'].isin(top_5_skus)].copy()
                df_top['Date_Str'] = df_top['annee'].astype(str) + '-' + df_top['mois'].astype(str).str.zfill(2) + '-01'
                df_top['Date_Plot'] = pd.to_datetime(df_top['Date_Str'])
                df_top_agg = df_top.groupby(['Date_Plot', 'article'], observed=True)['rupture_hl'].sum().reset_index()
                fig_trend = go.Figure()
                palette = [COLORS['ROUGE'], '#F59E0B', COLORS['TEXTE'], COLORS['VERT'], COLORS['GRIS']]
                for i, sku in enumerate(top_5_skus):
                    df_sku = df_top_agg[df_top_agg['article'] == sku].sort_values('Date_Plot')
                    fig_trend.add_trace(go.Scatter(x=df_sku['Date_Plot'], y=df_sku['rupture_hl'], mode='lines+markers', name=str(sku)[:25], line=dict(color=palette[i % len(palette)], width=2.5), marker=dict(size=7), hovertemplate="<b>%{fullData.name}</b><br>%{x|%b-%y}: %{y:,.1f} HL<extra></extra>"))
                fig_trend.update_layout(separators=" ,", plot_bgcolor=COLORS['BLANC'], paper_bgcolor=COLORS['BLANC'], margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(showgrid=True, gridcolor=COLORS['BORDURE'], tickformat="%b-%y", tickangle=-45), yaxis=dict(title="Volume perdu (HL)", showgrid=True, gridcolor=COLORS['BORDURE']), legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, font=dict(size=11)), height=450, hovermode="x unified")
                st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("📋 Tableau détaillé des ruptures", expanded=False):
                df_rupture_detail = df_rupture_hist.groupby(['annee', 'mois', 'agence', 'article'], observed=True)['rupture_hl'].sum().reset_index()
                df_rupture_detail['Mois_Label'] = df_rupture_detail['mois'].apply(lambda m: MOIS_NOMS[int(m)-1])
                df_rupture_detail = df_rupture_detail[['annee', 'Mois_Label', 'agence', 'article', 'rupture_hl']]
                df_rupture_detail.columns = ['Année', 'Mois', 'Agence', 'Article', 'Volume Perdu (HL)']
                df_rupture_detail = df_rupture_detail.sort_values('Volume Perdu (HL)', ascending=False)
                total_perdu = df_rupture_detail['Volume Perdu (HL)'].sum()
                small_kpi("TOTAL Volume Perdu", format_fr(total_perdu))
                if len(df_rupture_detail) > N_MAX_DISPLAY:
                    df_rup_aff = ajouter_total(df_rupture_detail.head(N_MAX_DISPLAY - 1), label_col="Année", label="TOTAL (affiché)")
                else:
                    df_rup_aff = ajouter_total(df_rupture_detail, label_col="Année")
                st.dataframe(bold_total_row(df_rup_aff), use_container_width=True, hide_index=True, column_config={'Volume Perdu (HL)': st.column_config.NumberColumn(format="%.2f")})
        else:
            st.info("Aucune rupture enregistrée sur le périmètre sélectionné.")

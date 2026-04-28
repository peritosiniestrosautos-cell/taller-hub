"""
================================================================================
VISUALIZACIONES - Taller Hub
================================================================================
Funciones para renderizar gráficos, KPIs y tablas.
RF-003: Componentes de visualización
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import PORCENTAJE_HONORARIOS
from .data_processor import add_log, filter_authorized_savings_records
from .fee_config import calculate_fee, load_fee_config, calculate_fees_for_df
from .chart_config import get_chart_type_for_id, CHART_TYPE_BAR, CHART_TYPE_LINE
from .imprevistos_processor import resumir_imprevistos_mensuales


# ============================================================================
# KPIs PRINCIPALES
# ============================================================================

def render_kpis(df):
    """
    RF-003.1: KPIs principales
    - Ahorro acumulado
    - Debe cobrar (con regla de umbral por taller)
    - Utilidad taller
    - Promedio por reparación
    """
    add_log("render_kpis: Iniciando")

    if 'DIFERENCIA' not in df.columns:
        st.warning("No se encontró columna de DIFERENCIA/AHORRO")
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        st.info("No hay registros AUTORIZADO para calcular métricas de ahorro.")
        return

    total_ahorro = df['DIFERENCIA'].sum()
    total_registros = len(df)
    reparaciones_con_ahorro = len(df[df['DIFERENCIA'] > 0])
    promedio_ahorro = df[df['DIFERENCIA'] > 0]['DIFERENCIA'].mean() if reparaciones_con_ahorro > 0 else 0

    # Cálculo de honorarios con regla de umbral por taller
    fee_config = load_fee_config()
    fee_info = calculate_fees_for_df(df, fee_config)
    
    # Total honorarios (sum of all workshops if multitaller)
    honorarios = fee_info['total']['fee_amount']
    utilidad = total_ahorro - honorarios
    
    # Check presentation mode
    hide_fees = fee_config.get('hide_fees_presentation', False)
    
    # Determine if multitaller
    es_multitaller = 'TALLER_ORIGEN' in df.columns and df['TALLER_ORIGEN'].nunique() > 1

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-container kpi-ahorro">
            <div class="kpi-value">${total_ahorro:,.0f}</div>
            <div class="kpi-label">💰 Ahorro Acumulado</div>
            <div class="kpi-delta">{reparaciones_con_ahorro} reparaciones con ahorro</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if hide_fees:
            st.markdown(f"""
            <div class="kpi-container kpi-honorarios">
                <div class="kpi-value">🔒</div>
                <div class="kpi-label">📊 Valor Honorarios</div>
                <div class="kpi-delta">Oculto en modo presentación</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show fee breakdown
            if es_multitaller and fee_info['by_taller']:
                # Show total and mention per-taller calculation
                rule_label = "Mixto (ver detalle)"
                st.markdown(f"""
                <div class="kpi-container kpi-honorarios">
                    <div class="kpi-value">${honorarios:,.0f}</div>
                    <div class="kpi-label">📊 Debe Cobrar (Total)</div>
                    <div class="kpi-delta">{len(fee_info['by_taller'])} talleres con tarifas individuales</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show per-taller breakdown in expander
                with st.expander("🔍 Ver detalle por taller"):
                    for taller_id, taller_fee in fee_info['by_taller'].items():
                        regla = "Premium" if taller_fee['rule_applied'] == 'premium' else "Base"
                        st.markdown(
                            f"**{taller_id}**: ${taller_fee['fee_amount']:,.0f} "
                            f"({taller_fee['fee_percentage']*100:.0f}% - {regla})"
                        )
            else:
                # Single workshop
                regla = "Premium" if fee_info['total']['rule_applied'] == 'premium' else "Base"
                st.markdown(f"""
                <div class="kpi-container kpi-honorarios">
                    <div class="kpi-value">${honorarios:,.0f}</div>
                    <div class="kpi-label">📊 Debe Cobrar ({fee_info['total']['fee_percentage']*100:.0f}%)</div>
                    <div class="kpi-delta">Regla: {regla}</div>
                </div>
                """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-container kpi-utilidad">
            <div class="kpi-value">${utilidad:,.0f}</div>
            <div class="kpi-label">🏆 Utilidad Taller</div>
            <div class="kpi-delta">Ahorro - Honorarios</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-container kpi-promedio">
            <div class="kpi-value">${promedio_ahorro:,.0f}</div>
            <div class="kpi-label">📈 Promedio/Reparación</div>
            <div class="kpi-delta">Solo reparaciones con ahorro positivo</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# GRÁFICO DE AHORRO POR MES
# ============================================================================

def render_grafico_ahorro_mes(df):
    """
    RF-003.4: Gráfico de ahorro por mes (línea o barras según configuración)
    """
    add_log("render_grafico_ahorro_mes: Iniciando")

    if 'AÑO' not in df.columns or 'MES' not in df.columns:
        st.warning("Datos de fecha incompletos para gráfico mensual")
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        st.info("No hay registros AUTORIZADO para construir el gráfico de ahorro.")
        return
    add_log(f"render_grafico_ahorro_mes: registros autorizados={len(df)}")

    # Filtrar solo registros con AÑO y MES válidos
    df_valid = df[(df['AÑO'].notna()) & (df['MES'].notna()) &
                  (df['AÑO'] > 2000) & (df['MES'] >= 1) & (df['MES'] <= 12)]

    if df_valid.empty:
        st.warning("No hay datos con fechas válidas para el gráfico")
        return
    add_log(f"render_grafico_ahorro_mes: registros válidos con fecha={len(df_valid)}")

    df_mes = df_valid.groupby(['AÑO', 'MES']).agg({
        'DIFERENCIA': 'sum',
        'PLACA': 'nunique'
    }).reset_index()

    # Asegurar que AÑO y MES sean enteros válidos
    df_mes['AÑO'] = df_mes['AÑO'].astype(int)
    df_mes['MES'] = df_mes['MES'].astype(int)

    # Crear fecha con manejo de errores
    try:
        df_mes['FECHA'] = pd.to_datetime(
            df_mes['AÑO'].astype(str) + '-' + df_mes['MES'].astype(str) + '-01',
            format='%Y-%m-%d',
            errors='coerce'
        )
    except Exception as e:
        st.error(f"Error creando fechas: {e}")
        st.write(f"Valores de AÑO: {df_mes['AÑO'].tolist()}")
        st.write(f"Valores de MES: {df_mes['MES'].tolist()}")
        return

    # Filtrar fechas que no se pudieron crear
    df_mes = df_mes[df_mes['FECHA'].notna()]
    df_mes = df_mes.sort_values('FECHA')
    df_mes['TEXTO_FECHA'] = df_mes['FECHA'].dt.strftime('%b %Y')
    add_log(
        "render_grafico_ahorro_mes: resumen mensual=" +
        "; ".join(
            f"{row['TEXTO_FECHA']}=${row['DIFERENCIA']:,.0f}"
            for _, row in df_mes.iterrows()
        )
    )

    # Get chart type from config
    chart_type = get_chart_type_for_id('ahorro_mes')

    fig = go.Figure()

    if chart_type == CHART_TYPE_BAR:
        # Bar chart
        fig.add_trace(go.Bar(
            x=df_mes['TEXTO_FECHA'],
            y=df_mes['DIFERENCIA'],
            name='Ahorro Mensual',
            marker_color='#0066CC',
            marker_line_width=0
        ))
    else:
        # Line chart (default)
        fig.add_trace(go.Scatter(
            x=df_mes['TEXTO_FECHA'],
            y=df_mes['DIFERENCIA'],
            mode='lines+markers',
            name='Ahorro Mensual',
            line=dict(color='#0066CC', width=3),
            marker=dict(size=8, color='#00A8E8', line=dict(width=2, color='white')),
            fill='tozeroy',
            fillcolor='rgba(0, 102, 204, 0.1)'
        ))

        # Línea de tendencia (only for line chart)
        if len(df_mes) > 2:
            fig.add_trace(go.Scatter(
                x=df_mes['TEXTO_FECHA'],
                y=df_mes['DIFERENCIA'].rolling(window=3, min_periods=1).mean(),
                mode='lines',
                name='Tendencia (media móvil)',
                line=dict(color='#00CC66', width=2, dash='dash')
            ))

    fig.update_layout(
        title='📈 Evolución de Ahorros por Mes',
        xaxis_title='Mes',
        yaxis_title='Ahorro ($)',
        height=400,
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    # Formato de eje Y como moneda
    fig.update_yaxes(tickformat='$,.0f')

    st.plotly_chart(fig, width='stretch')


# ============================================================================
# GRÁFICO DE CAUSALES
# ============================================================================

def render_grafico_causales(df):
    """
    RF-003.5: Gráfico de causales de cambio (barras horizontales o líneas verticales)
    """
    if 'CAUSAL' not in df.columns:
        st.warning("No se encontró columna de CAUSAL")
        return

    df_causal = df[df['CAUSAL'].notna() & (df['CAUSAL'] != '')].groupby('CAUSAL').agg({
        'DIFERENCIA': ['sum', 'count']
    }).reset_index()
    df_causal.columns = ['CAUSAL', 'AHORRO_TOTAL', 'CANTIDAD']
    df_causal = df_causal.sort_values('AHORRO_TOTAL', ascending=True).tail(10)

    # Get chart type from config
    chart_type = get_chart_type_for_id('causales')

    if chart_type == CHART_TYPE_LINE:
        # Vertical line chart alternative
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_causal['CAUSAL'],
            y=df_causal['AHORRO_TOTAL'],
            mode='lines+markers',
            name='Ahorro Total',
            line=dict(color='#0066CC', width=3),
            marker=dict(size=10, color='#00A8E8', line=dict(width=2, color='white'))
        ))
        
        fig.update_layout(
            title='📊 Top Causales de Cambio por Valor de Ahorro',
            xaxis_title='Causal',
            yaxis_title='Ahorro Total ($)',
            height=400,
            hovermode='x unified',
            showlegend=False,
            xaxis_tickangle=-45
        )
        
        fig.update_yaxes(tickformat='$,.0f')
    else:
        # Horizontal bar chart (default)
        fig = px.bar(
            df_causal,
            y='CAUSAL',
            x='AHORRO_TOTAL',
            orientation='h',
            color='CANTIDAD',
            color_continuous_scale='Blues',
            title='📊 Top Causales de Cambio por Valor de Ahorro',
            labels={'AHORRO_TOTAL': 'Ahorro Total ($)', 'CAUSAL': 'Causal', 'CANTIDAD': 'Frecuencia'},
            height=400
        )

        fig.update_traces(
            texttemplate='${x:,.0f}',
            textposition='outside'
        )

        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_colorbar=dict(title="Cantidad")
        )

    st.plotly_chart(fig, width='stretch')


# ============================================================================
# TABLA DE DETALLE
# ============================================================================

def render_tabla_detalle(df):
    """
    RF-003.6: Tabla de ahorro por día con filtro de fechas
    """
    st.subheader("📋 Detalle de Reparaciones")
    
    # Seleccionar columnas para mostrar
    columnas_display = []
    fecha_display_col = 'FECHA_COMPLETA' if 'FECHA_COMPLETA' in df.columns else 'FECHA_INGR'
    columnas_posibles = [fecha_display_col, 'PLACA', 'MARCA', 'LINEA', 'COMPAÑIA_DE_SEGUROS',
                        'IMPREVISTO', 'ACCION', 'CAUSAL', 'M._DE_O._INICIAL', 
                        'M._DE_O._FINAL', 'DIFERENCIA', 'ESTATUS', 'OBSERVACION']
    
    for col in columnas_posibles:
        if col in df.columns:
            columnas_display.append(col)
    
    df_display = df[columnas_display].copy()
    
    # Ordenar por ahorro descendente
    if 'DIFERENCIA' in df_display.columns:
        df_display = df_display.sort_values('DIFERENCIA', ascending=False)
    
    # Formatear monedas
    for col in ['M._DE_O._INICIAL', 'M._DE_O._FINAL', 'DIFERENCIA']:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x != 0 else "")
    
    # Formatear fechas
    if fecha_display_col in df_display.columns:
        df_display[fecha_display_col] = pd.to_datetime(
            df_display[fecha_display_col], errors='coerce'
        ).dt.strftime('%d/%m/%Y')
        df_display = df_display.rename(columns={fecha_display_col: 'FECHA'})
    
    # Badge para estatus
    if 'ESTATUS' in df_display.columns:
        def badge_status(status):
            if pd.isna(status):
                return ""
            status = str(status).upper()
            if 'AUTORIZ' in status:
                return '<span class="badge-autorizado">AUTORIZADO</span>'
            elif 'RECHAZ' in status:
                return '<span class="badge-rechazado">RECHAZADO</span>'
            else:
                return '<span class="badge-pendiente">PENDIENTE</span>'
        
        df_display['ESTATUS'] = df_display['ESTATUS'].apply(badge_status)
    
    # Paginación simple
    items_por_pagina = 50
    total_paginas = max(1, (len(df_display) + items_por_pagina - 1) // items_por_pagina)
    
    col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
    with col_pag2:
        pagina = st.number_input(f"Página (1-{total_paginas})", min_value=1, max_value=total_paginas, value=1)
    
    inicio = (pagina - 1) * items_por_pagina
    fin = min(inicio + items_por_pagina, len(df_display))
    
    st.caption(f"Mostrando {inicio+1}-{fin} de {len(df_display)} registros")
    
    # Mostrar tabla
    st.dataframe(
        df_display.iloc[inicio:fin],
        width='stretch',
        height=500,
        hide_index=True
    )


# ============================================================================
# RECUPERACIÓN MENSUAL
# ============================================================================

def render_recuperacion_mensual(df):
    """
    RF-003.7: Tabla de recuperación mensual con % de honorarios (umbral dinámico por taller)
    """
    st.subheader("📊 Recuperación Mensual con % de Honorarios")

    if 'AÑO' not in df.columns or 'MES' not in df.columns:
        return

    # Filtrar solo registros con AÑO y MES válidos
    df_valid = df[(df['AÑO'].notna()) & (df['MES'].notna()) &
                  (df['AÑO'] > 2000) & (df['MES'] >= 1) & (df['MES'] <= 12)]

    if df_valid.empty:
        st.warning("No hay datos con fechas válidas")
        return

    # Load fee configuration
    fee_config = load_fee_config()
    hide_fees = fee_config.get('hide_fees_presentation', False)
    
    # Determine if multitaller
    es_multitaller = 'TALLER_ORIGEN' in df_valid.columns

    resumen = df_valid.groupby(['AÑO', 'MES']).agg({
        'DIFERENCIA': ['sum', 'count'],
        'PLACA': 'nunique'
    }).reset_index()

    resumen.columns = ['AÑO', 'MES', 'RECUPERACION', 'CANTIDAD', 'VEHICULOS']
    
    # Apply threshold rule based on total recuperacion
    # For multitaller, we calculate fees on the total across all workshops
    fee_info = calculate_fees_for_df(df_valid, fee_config)
    
    # Use overall fee percentage for the monthly breakdown
    fee_percentage = fee_info['total']['fee_percentage'] * 100
    
    resumen['%_HONORARIOS'] = fee_percentage
    resumen['VALOR_HONORARIOS'] = resumen['RECUPERACION'] * (fee_percentage / 100)
    resumen['PAGOS'] = resumen['RECUPERACION'] - resumen['VALOR_HONORARIOS']

    # Formatear para display
    resumen_display = resumen.copy()
    for col in ['RECUPERACION', 'VALOR_HONORARIOS', 'PAGOS']:
        resumen_display[col] = resumen_display[col].apply(lambda x: f"${x:,.0f}")
    resumen_display['%_HONORARIOS'] = resumen_display['%_HONORARIOS'].apply(lambda x: f"{x:.1f}%")

    resumen_display['PERIODO'] = resumen_display.apply(lambda x: f"{x['MES']:02d}/{x['AÑO']}", axis=1)

    # Build period labels for chart
    resumen = resumen.copy()
    resumen['PERIODO'] = resumen['MES'].astype(int).astype(str).str.zfill(2) + '/' + resumen['AÑO'].astype(int).astype(str)

    # Render chart for monthly recovery
    chart_type = get_chart_type_for_id('recuperacion_mensual')

    fig = go.Figure()

    if chart_type == CHART_TYPE_BAR:
        fig.add_trace(go.Bar(
            x=resumen['PERIODO'],
            y=resumen['RECUPERACION'],
            name='Recuperación',
            marker_color='#0066CC',
            marker_line_width=0
        ))
    else:
        fig.add_trace(go.Scatter(
            x=resumen['PERIODO'],
            y=resumen['RECUPERACION'],
            mode='lines+markers',
            name='Recuperación',
            line=dict(color='#0066CC', width=3),
            marker=dict(size=8, color='#00A8E8', line=dict(width=2, color='white')),
            fill='tozeroy',
            fillcolor='rgba(0, 102, 204, 0.1)'
        ))

    fig.update_layout(
        title='📊 Evolución de Recuperación Mensual',
        xaxis_title='Mes',
        yaxis_title='Recuperación ($)',
        height=400,
        hovermode='x unified',
        showlegend=False
    )

    fig.update_yaxes(tickformat='$,.0f')

    st.plotly_chart(fig, width='stretch')

    # Hide fees in presentation mode
    if hide_fees:
        st.dataframe(
            resumen_display[['PERIODO', 'VEHICULOS', 'CANTIDAD', 'RECUPERACION', 'PAGOS']],
            width='stretch',
            hide_index=True,
            height=400
        )
        st.info("🔒 Modo presentación activo - Columnas de honorarios ocultas")
    else:
        # Show additional info for multitaller
        if es_multitaller:
            st.caption(f"💡 Usando tarifa ponderada para {len(fee_info['by_taller'])} taller(es). Ver KPIs para detalle por taller.")
        
        # Mostrar como tabla estilo Excel
        st.dataframe(
            resumen_display[['PERIODO', 'VEHICULOS', 'CANTIDAD', 'RECUPERACION',
                            '%_HONORARIOS', 'VALOR_HONORARIOS', 'PAGOS']],
            width='stretch',
            hide_index=True,
            height=400
        )


# ============================================================================
# EFECTIVIDAD EN LA VALORACION
# ============================================================================

def render_efectividad_valoracion(df):
    """
    Muestra la eficiencia mensual de valoración:
    (1 - vehículos con imprevistos / total vehículos cotizados) * 100
    """
    st.subheader("📐 Efectividad en la Valoración")

    required_cols = {'AÑO', 'MES', 'PLACA'}
    if df is None or df.empty:
        st.warning("No hay datos disponibles para calcular la efectividad de valoración.")
        return

    if not required_cols.issubset(df.columns):
        st.warning("Faltan columnas requeridas (AÑO, MES, PLACA) para calcular la efectividad.")
        return

    df_valid = df.copy()
    df_valid['AÑO'] = pd.to_numeric(df_valid['AÑO'], errors='coerce')
    df_valid['MES'] = pd.to_numeric(df_valid['MES'], errors='coerce')
    df_valid['PLACA_NORMALIZADA'] = df_valid['PLACA'].astype(str).str.upper().str.strip()

    df_valid = df_valid[
        df_valid['AÑO'].notna() &
        df_valid['MES'].notna() &
        (df_valid['AÑO'] > 2000) &
        (df_valid['MES'] >= 1) &
        (df_valid['MES'] <= 12) &
        df_valid['PLACA_NORMALIZADA'].ne('') &
        df_valid['PLACA_NORMALIZADA'].ne('NAN')
    ].copy()

    if df_valid.empty:
        st.warning("No hay datos válidos de fecha y placa para calcular la efectividad.")
        return

    df_valid['AÑO'] = df_valid['AÑO'].astype(int)
    df_valid['MES'] = df_valid['MES'].astype(int)

    # Solo registros con estatus AUTORIZADO
    df_valid = filter_authorized_savings_records(df_valid)
    if df_valid.empty:
        st.warning("No hay registros AUTORIZADOS para calcular la efectividad de valoración.")
        return

    # Clave única: PLACA + SINIESTRO (si siniestro cambia, cuenta como otro vehículo cotizado)
    df_valid['SINIESTRO_NORM'] = df_valid.get('SINIESTRO', pd.Series('', index=df_valid.index)).astype(str).str.upper().str.strip()
    df_valid['PLACA_SINIESTRO'] = df_valid['PLACA_NORMALIZADA'] + '|' + df_valid['SINIESTRO_NORM']

    total_vehiculos = (
        df_valid.groupby(['AÑO', 'MES'])['PLACA_SINIESTRO']
        .nunique()
        .reset_index(name='Cantidad vehículos cotizados')
    )

    # Vehículos con imprevistos = los que tienen ACCION que contenga "CAMBIO"
    if 'ACCION' in df_valid.columns:
        df_imprevistos = df_valid[
            df_valid['ACCION'].astype(str).str.contains('CAMBIO', na=False, case=False)
        ].copy()
    else:
        df_imprevistos = pd.DataFrame()

    if not df_imprevistos.empty:
        imprevistos_por_mes = (
            df_imprevistos.groupby(['AÑO', 'MES'])['PLACA_SINIESTRO']
            .nunique()
            .reset_index(name='Vehículos con imprevistos')
        )
    else:
        imprevistos_por_mes = pd.DataFrame(columns=['AÑO', 'MES', 'Vehículos con imprevistos'])

    resumen = total_vehiculos.merge(imprevistos_por_mes, on=['AÑO', 'MES'], how='left')
    resumen['Vehículos con imprevistos'] = resumen['Vehículos con imprevistos'].fillna(0).astype(int)
    resumen['Eficiencia (%)'] = (
        1 - (resumen['Vehículos con imprevistos'] / resumen['Cantidad vehículos cotizados'])
    ) * 100
    resumen['Eficiencia (%)'] = resumen['Eficiencia (%)'].clip(lower=0, upper=100).round(1)

    resumen['FECHA'] = pd.to_datetime(
        resumen['AÑO'].astype(str) + '-' + resumen['MES'].astype(str) + '-01',
        format='%Y-%m-%d',
        errors='coerce'
    )
    resumen = resumen[resumen['FECHA'].notna()].sort_values('FECHA').reset_index(drop=True)

    if resumen.empty:
        st.warning("No se pudo construir la serie mensual de efectividad.")
        return

    resumen['Mes'] = resumen['FECHA'].dt.strftime('%b %Y')

    eficiencia_promedio = resumen['Eficiencia (%)'].mean()
    mejor_mes = resumen.loc[resumen['Eficiencia (%)'].idxmax()]
    peor_mes = resumen.loc[resumen['Eficiencia (%)'].idxmin()]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Eficiencia promedio", f"{eficiencia_promedio:.1f}%")
    with col2:
        st.metric("Mejor mes", mejor_mes['Mes'], f"{mejor_mes['Eficiencia (%)']:.1f}%")
    with col3:
        st.metric("Peor mes", peor_mes['Mes'], f"{peor_mes['Eficiencia (%)']:.1f}%", delta_color="inverse")

    tabla_resumen = resumen[[
        'Mes',
        'Cantidad vehículos cotizados',
        'Vehículos con imprevistos',
        'Eficiencia (%)'
    ]].copy()
    tabla_resumen['Eficiencia (%)'] = tabla_resumen['Eficiencia (%)'].map(lambda x: f"{x:.1f}%")

    # Debug temporal para validar cálculo
    with st.expander("🔍 Debug del cálculo de efectividad"):
        st.write("**Total vehículos cotizados (por PLACA+SINIESTRO):**")
        st.write(total_vehiculos)
        st.write("**Vehículos con imprevistos (por PLACA+SINIESTRO):**")
        st.write(imprevistos_por_mes if not imprevistos_por_mes.empty else "Sin imprevistos detectados")
        st.write("**Resumen crudo antes de formatear:**")
        st.write(resumen[['Mes', 'Cantidad vehículos cotizados', 'Vehículos con imprevistos', 'Eficiencia (%)']])

    st.dataframe(
        tabla_resumen,
        width='stretch',
        hide_index=True,
        height=350
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=resumen['Mes'],
        y=resumen['Eficiencia (%)'],
        mode='lines+markers',
        name='Eficiencia',
        line=dict(color='#0066CC', width=3),
        marker=dict(size=8, color='#00A8E8', line=dict(width=2, color='white'))
    ))

    fig.update_layout(
        title='📈 Eficiencia Mensual en la Valoración',
        xaxis_title='Mes',
        yaxis_title='Eficiencia (%)',
        height=400,
        hovermode='x unified',
        showlegend=False
    )
    fig.update_yaxes(range=[0, 100], ticksuffix='%')

    st.plotly_chart(fig, width='stretch')


# ============================================================================
# GRÁFICO DE AHORRO POR COMPAÑÍA DE SEGUROS
# ============================================================================

def render_grafico_ahorro_por_compania(df):
    """
    Gráfico de distribución de ahorros por Compañía de Seguros.
    Muestra una dona con el % de ahorro por compañía y una tabla
    con columna de compañías, recuperado y porcentaje.
    """
    if df is None or df.empty:
        st.info("No hay datos para mostrar distribución por compañía de seguros.")
        return

    if 'COMPAÑIA_DE_SEGUROS' not in df.columns:
        st.warning("No se encontró la columna 'COMPAÑIA_DE_SEGUROS' en los datos.")
        return

    # Filtrar solo registros autorizados para métricas de ahorro
    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        st.info("No hay registros AUTORIZADO para mostrar distribución por compañía.")
        return

    # Agrupar por compañía de seguros y sumar la diferencia
    resumen = (
        df.groupby('COMPAÑIA_DE_SEGUROS')['DIFERENCIA']
        .sum()
        .reset_index()
    )

    # Limpiar: quitar vacíos y ordenar descendente
    resumen = resumen[resumen['COMPAÑIA_DE_SEGUROS'].notna()]
    resumen = resumen[resumen['COMPAÑIA_DE_SEGUROS'].astype(str).str.strip() != '']
    resumen = resumen.sort_values('DIFERENCIA', ascending=False)

    if resumen.empty:
        st.info("No hay datos de ahorro por compañía de seguros.")
        return

    total_ahorro = resumen['DIFERENCIA'].sum()

    # Calcular porcentaje
    resumen['PORCENTAJE'] = (resumen['DIFERENCIA'] / total_ahorro) * 100

    # Colores corporativos + variaciones
    colors = [
        '#0066CC', '#00A8E8', '#00CC66', '#F59E0B',
        '#DC2626', '#8B5CF6', '#EC4899', '#14B8A6',
        '#F97316', '#6366F1', '#84CC16', '#06B6D4'
    ]

    # Replicar colores si hay más compañías que colores
    color_list = []
    for i in range(len(resumen)):
        color_list.append(colors[i % len(colors)])

    # Subtítulo
    st.subheader("🏢 Distribución de Ahorros por Compañía de Seguros")

    # Gráfico de dona
    fig = go.Figure(data=[go.Pie(
        labels=resumen['COMPAÑIA_DE_SEGUROS'],
        values=resumen['DIFERENCIA'],
        hole=0.5,
        marker_colors=color_list,
        textinfo="label+percent",
        textposition="outside",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Ahorro: $%{value:,.0f}<br>"
            "Porcentaje: %{percent}<extra></extra>"
        )
    )])

    # Anotación central con total
    fig.add_annotation(
        text=f"<b>Total</b><br>${total_ahorro:,.0f}",
        showarrow=False,
        font=dict(size=16)
    )

    fig.update_layout(
        title_text="Distribución de Ahorros por CIA",
        title_x=0.5,
        height=450,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabla con compañía, recuperado y %
    tabla_display = resumen.copy()
    tabla_display['DIFERENCIA_FMT'] = tabla_display['DIFERENCIA'].apply(lambda x: f"${x:,.0f}")
    tabla_display['PORCENTAJE_FMT'] = tabla_display['PORCENTAJE'].apply(lambda x: f"{x:.1f}%")

    st.markdown("**📋 Resumen por Compañía de Seguros**")

    st.dataframe(
        tabla_display[['COMPAÑIA_DE_SEGUROS', 'DIFERENCIA_FMT', 'PORCENTAJE_FMT']]
        .rename(columns={
            'COMPAÑIA_DE_SEGUROS': 'Compañía de Seguros',
            'DIFERENCIA_FMT': 'Recuperado',
            'PORCENTAJE_FMT': '%'
        }),
        width='stretch',
        hide_index=True,
        height=min(400, (len(tabla_display) + 1) * 35 + 10)
    )

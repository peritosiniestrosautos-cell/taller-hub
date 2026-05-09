"""
================================================================================
VISUALIZACIONES - Taller Hub
================================================================================
Funciones para renderizar gráficos, KPIs y tablas.
RF-003: Componentes de visualización
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from .config import PORCENTAJE_HONORARIOS
from .data_processor import add_log, filter_authorized_savings_records
from .fee_config import load_fee_config, calculate_fees_per_month
from .chart_config import get_chart_type_for_id, CHART_TYPE_BAR
from .imprevistos_processor import resumir_imprevistos_mensuales
from .theme import (
    BrandColors, SemanticColors, GrayScale, ChartHeights, CHART_COLORS,
    get_plotly_theme, get_chart_color, hex_to_plotly_fill
)


# ============================================================================
# KPIs PRINCIPALES
# ============================================================================

def format_period_label(mes, anio):
    """Formatea MM/YYYY tolerando valores numéricos float de pandas."""
    return f"{int(mes):02d}/{int(anio)}"


def calculate_accumulated_savings_kpi(df):
    """
    Calcula el KPI de ahorro acumulado usando todos los registros disponibles
    en DIFERENCIA/RECUPERADO, sin filtrar por estatus ni deduplicar.
    """
    if df is None or df.empty or 'DIFERENCIA' not in df.columns:
        return {
            'total_ahorro': 0,
            'reparaciones_con_ahorro': 0,
        }

    diferencia = pd.to_numeric(df['DIFERENCIA'], errors='coerce').fillna(0)
    return {
        'total_ahorro': diferencia.sum(),
        'reparaciones_con_ahorro': int((diferencia > 0).sum()),
    }

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

    ahorro_kpi = calculate_accumulated_savings_kpi(df)
    total_ahorro = ahorro_kpi['total_ahorro']
    reparaciones_con_ahorro = ahorro_kpi['reparaciones_con_ahorro']

    df_honorarios = filter_authorized_savings_records(df)
    if df_honorarios is None:
        df_honorarios = pd.DataFrame(columns=df.columns)

    df_metricas = df_honorarios.copy()

    # RF-005.3: Deduplicar por PLACA + SINIESTRO — misma placa con mismo
    # siniestro solo cuenta una vez. Placas con siniestros distintos sí cuentan.
    if 'PLACA' in df_metricas.columns and 'SINIESTRO' in df_metricas.columns:
        df_metricas = df_metricas.drop_duplicates(subset=['PLACA', 'SINIESTRO'], keep='first')

    total_ahorro_metricas = df_metricas['DIFERENCIA'].sum() if not df_metricas.empty else 0
    reparaciones_metricas = len(df_metricas[df_metricas['DIFERENCIA'] > 0]) if not df_metricas.empty else 0
    promedio_ahorro = (
        df_metricas[df_metricas['DIFERENCIA'] > 0]['DIFERENCIA'].mean()
        if reparaciones_metricas > 0 else 0
    )

    # Cálculo de honorarios por mes (regla de umbral por taller, evaluada mes a mes)
    fee_config = load_fee_config()
    fee_info = calculate_fees_per_month(df_honorarios, fee_config)
    
    # Total honorarios = sum of per-month (and per-taller) fees
    honorarios = fee_info['total_honorarios']
    utilidad = total_ahorro_metricas - honorarios
    
    # Check presentation mode
    hide_fees = fee_config.get('hide_fees_presentation', False)
    
    # Determine if multitaller
    es_multitaller = 'TALLER_ORIGEN' in df_metricas.columns and df_metricas['TALLER_ORIGEN'].nunique() > 1

    col1, col2 = st.columns(2, gap="medium")

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
            # Calculate effective rate for display
            effective_rate = (honorarios / total_ahorro_metricas * 100) if total_ahorro_metricas > 0 else 0
            
            if es_multitaller and fee_info['by_taller']:
                st.markdown(f"""
                <div class="kpi-container kpi-honorarios">
                    <div class="kpi-value">${honorarios:,.0f}</div>
                    <div class="kpi-label">📊 Debe Cobrar (Total)</div>
                    <div class="kpi-delta">{len(fee_info['by_taller'])} talleres - Efectivo: {effective_rate:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("🔍 Ver detalle por taller"):
                    for taller_id, taller_data in fee_info['by_taller'].items():
                        t_honorarios = taller_data['total_honorarios']
                        t_ahorro = taller_data['total_savings']
                        t_efectivo = (t_honorarios / t_ahorro * 100) if t_ahorro > 0 else 0
                        meses_base = sum(1 for m in taller_data['by_month'] if m['rule_applied'] == 'base')
                        meses_premium = sum(1 for m in taller_data['by_month'] if m['rule_applied'] == 'premium')
                        st.markdown(
                            f"**{taller_id}**: ${t_honorarios:,.0f} "
                            f"(Efectivo: {t_efectivo:.1f}% | Base: {meses_base} meses, Premium: {meses_premium} meses)"
                        )
            else:
                # Single workshop: count base vs premium months
                meses_base = sum(1 for m in fee_info['by_month'] if m['rule_applied'] == 'base')
                meses_premium = sum(1 for m in fee_info['by_month'] if m['rule_applied'] == 'premium')
                reglas = []
                if meses_base:
                    reglas.append(f"Base: {meses_base} meses")
                if meses_premium:
                    reglas.append(f"Premium: {meses_premium} meses")
                regla_label = " | ".join(reglas) if reglas else "Sin datos"
                
                st.markdown(f"""
                <div class="kpi-container kpi-honorarios">
                    <div class="kpi-value">${honorarios:,.0f}</div>
                    <div class="kpi-label">📊 Debe Cobrar (Efectivo: {effective_rate:.1f}%)</div>
                    <div class="kpi-delta">{regla_label}</div>
                </div>
                """, unsafe_allow_html=True)

    col3, col4 = st.columns(2, gap="medium")

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
        # Preparar textos abreviados para cada barra
        textos = []
        for v in df_mes['DIFERENCIA']:
            if pd.isna(v):
                textos.append('')
            elif abs(v) >= 1000000:
                textos.append(f'{v/1000000:.1f}M')
            else:
                textos.append(f'{v/1000:.1f}k')

        fig.add_trace(go.Bar(
            x=df_mes['TEXTO_FECHA'],
            y=df_mes['DIFERENCIA'],
            name='Ahorro Mensual',
            marker_color=BrandColors.PRIMARY,
            marker_line_width=0,
            text=textos,
            textposition='outside',
            textfont=dict(size=13, color='white', family='Inter')
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_mes['TEXTO_FECHA'],
            y=df_mes['DIFERENCIA'],
            mode='lines+markers',
            name='Ahorro Mensual',
            line=dict(color=BrandColors.PRIMARY, width=3),
            marker=dict(size=8, color=BrandColors.SECONDARY, line=dict(width=2, color='white')),
            fill='tozeroy',
            fillcolor=hex_to_plotly_fill(BrandColors.PRIMARY, 0.1)
        ))

        if len(df_mes) > 2:
            fig.add_trace(go.Scatter(
                x=df_mes['TEXTO_FECHA'],
                y=df_mes['DIFERENCIA'].rolling(window=3, min_periods=1).mean(),
                mode='lines',
                name='Tendencia (media móvil)',
                line=dict(color=BrandColors.ACCENT, width=2, dash='dash')
            ))

    theme = get_plotly_theme(
        title='📈 Evolución de Ahorros por Mes',
        height=ChartHeights.LARGE,
    )
    theme["margin"] = {"l": 60, "r": 20, "t": 80, "b": 60}
    fig.update_layout(**theme)
    fig.update_xaxes(title_text='Mes')
    fig.update_yaxes(title_text='Ahorro ($)', tickformat='$,.0f')

    st.plotly_chart(fig, width='stretch')


# ============================================================================
# GRÁFICO DE CAUSALES
# ============================================================================

def render_grafico_causales(df):
    """
    RF-003.5: Gráfico de causales de cambio (barras horizontales)
    """
    if 'CAUSAL' not in df.columns:
        st.warning("No se encontró columna de CAUSAL")
        return

    df_causal = df[df['CAUSAL'].notna() & (df['CAUSAL'] != '')].groupby('CAUSAL').agg({
        'DIFERENCIA': ['sum', 'count']
    }).reset_index()
    df_causal.columns = ['CAUSAL', 'AHORRO_TOTAL', 'CANTIDAD']
    df_causal = df_causal.sort_values('AHORRO_TOTAL', ascending=True).tail(10)

    if df_causal.empty:
        st.info("No hay causales de cambio para mostrar.")
        return

    # Wrap long causal names for readability
    def wrap_text(text, max_chars=25):
        text = str(text)
        if len(text) <= max_chars:
            return text
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > max_chars and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = f"{current_line} {word}".strip()
        if current_line:
            lines.append(current_line)
        return "<br>".join(lines)

    df_causal['CAUSAL_DISPLAY'] = df_causal['CAUSAL'].apply(wrap_text)

    # Dynamic height based on number of items
    n_items = len(df_causal)
    chart_height = max(ChartHeights.SMALL, n_items * 45 + 80)

    # Color gradient based on quantity
    colors = []
    max_cantidad = df_causal['CANTIDAD'].max()
    for _, row in df_causal.iterrows():
        intensity = row['CANTIDAD'] / max_cantidad if max_cantidad > 0 else 0.3
        r = int(0 + intensity * 0)
        g = int(102 + intensity * (168 - 102))
        b = int(204 + intensity * (232 - 204))
        colors.append(f'rgb({r}, {g}, {b})')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_causal['CAUSAL_DISPLAY'],
        x=df_causal['AHORRO_TOTAL'],
        orientation='h',
        marker_color=colors,
        text=df_causal['AHORRO_TOTAL'].apply(lambda x: f'${x:,.0f}'),
        textposition='outside',
        textfont=dict(size=11, color='#FFFFFF'),
        hovertemplate='<b>%{y}</b><br>Ahorro: $%{x:,.0f}<br>Cantidad: %{customdata}<extra></extra>',
        customdata=df_causal['CANTIDAD']
    ))

    fig.update_layout(
        title='📊 Top Causales de Cambio por Valor de Ahorro',
        xaxis_title='Ahorro Total ($)',
        yaxis_title=None,
        height=chart_height,
        hovermode='y unified',
        showlegend=False,
        margin=dict(l=150, r=20, t=60, b=40),
        xaxis=dict(
            tickformat='$,.0f',
            gridcolor=GrayScale.SLATE_200,
        ),
        yaxis=dict(
            autorange='reversed',
            tickfont=dict(size=11),
        )
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
    
    # Apply threshold rule per month (not accumulated)
    # Each month's recovery determines its own fee percentage independently
    fee_info = calculate_fees_per_month(df_valid, fee_config)
    
    # Build per-month fee lookup from the per-month calculation
    monthly_pct = fee_info.get('monthly_percentages', {})
    
    if monthly_pct:
        # Apply per-month fee percentages
        resumen['%_HONORARIOS'] = resumen.apply(
            lambda row: monthly_pct.get(
                f"{int(row['MES']):02d}/{int(row['AÑO'])}", 18.0
            ), axis=1
        )
    else:
        # Fallback for multitaller: use by_taller data to build percentages
        by_taller = fee_info.get('by_taller', {})
        if by_taller:
            resumen['%_HONORARIOS'] = fee_config['global_defaults']['base_percentage'] * 100
        else:
            resumen['%_HONORARIOS'] = fee_config['global_defaults']['base_percentage'] * 100
    
    resumen['VALOR_HONORARIOS'] = resumen['RECUPERACION'] * (resumen['%_HONORARIOS'] / 100)
    resumen['PAGOS'] = resumen['RECUPERACION'] - resumen['VALOR_HONORARIOS']

    # Formatear para display
    resumen_display = resumen.copy()
    for col in ['RECUPERACION', 'VALOR_HONORARIOS', 'PAGOS']:
        resumen_display[col] = resumen_display[col].apply(lambda x: f"${x:,.0f}")
    resumen_display['%_HONORARIOS'] = resumen_display['%_HONORARIOS'].apply(lambda x: f"{x:.1f}%")

    resumen_display['PERIODO'] = resumen_display.apply(
        lambda x: format_period_label(x['MES'], x['AÑO']), axis=1
    )

    # Build period labels for chart
    resumen = resumen.copy()
    resumen['PERIODO'] = resumen.apply(
        lambda x: format_period_label(x['MES'], x['AÑO']), axis=1
    )

    # Render chart: VALOR_HONORARIOS as primary metric, RECUPERACION as reference
    chart_type = get_chart_type_for_id('recuperacion_mensual')

    fig = go.Figure()

    if chart_type == CHART_TYPE_BAR:
        # Preparar textos con % de honorarios para cada barra
        textos = []
        for _, r in resumen.iterrows():
            pct = r['%_HONORARIOS']
            textos.append(f'{pct:.1f}%')

        fig.add_trace(go.Bar(
            x=resumen['PERIODO'],
            y=resumen['VALOR_HONORARIOS'],
            name='Honorarios',
            marker_color=BrandColors.SECONDARY,
            marker_line_width=0,
            text=textos,
            textposition='outside',
            textfont=dict(size=13, color='white')
        ))
        
        # RECUPERACION as faint reference bars behind
        fig.add_trace(go.Bar(
            x=resumen['PERIODO'],
            y=resumen['RECUPERACION'],
            name='Recuperación',
            marker_color=BrandColors.PRIMARY,
            marker_line_width=0,
            opacity=0.25,
            textposition='none'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=resumen['PERIODO'],
            y=resumen['VALOR_HONORARIOS'],
            mode='lines+markers',
            name='Honorarios',
            line=dict(color=BrandColors.SECONDARY, width=3),
            marker=dict(size=8, color=BrandColors.SECONDARY, line=dict(width=2, color='white')),
            fill='tozeroy',
            fillcolor=hex_to_plotly_fill(BrandColors.SECONDARY, 0.15)
        ))

        # RECUPERACION as faint reference line
        fig.add_trace(go.Scatter(
            x=resumen['PERIODO'],
            y=resumen['RECUPERACION'],
            mode='lines',
            name='Recuperación',
            line=dict(color=BrandColors.PRIMARY, width=1.5, dash='dot'),
            opacity=0.5
        ))

    theme = get_plotly_theme(
        title=' Evolución de Honorarios Mensuales',
        height=ChartHeights.LARGE,
        show_legend=True
    )
    theme["margin"] = {"l": 60, "r": 20, "t": 80, "b": 60}
    fig.update_layout(**theme)
    fig.update_xaxes(title_text='Mes')
    fig.update_yaxes(title_text='Honorarios ($)', tickformat='$,.0f')

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
    Muestra la eficiencia mensual de valoración usando el mismo cálculo
    que la Tasa de Imprevistos mensual, pero invertido:
    Eficiencia = (1 - tasa_imprevistos) = (1 - total_imprevistos / total_vehiculos) * 100
    """
    st.subheader("📐 Efectividad en la Valoración")

    if df is None or df.empty:
        st.warning("No hay datos disponibles para calcular la efectividad de valoración.")
        return

    required_cols = {'AÑO', 'MES', 'PLACA'}
    if not required_cols.issubset(df.columns):
        st.warning("Faltan columnas requeridas (AÑO, MES, PLACA) para calcular la efectividad.")
        return

    # ------------------------------------------------------------------
    # 1. Obtener imprevistos mensuales (misma lógica que tasa de imprevistos)
    # ------------------------------------------------------------------
    df_imp_mes = resumir_imprevistos_mensuales(df=df)

    if df_imp_mes.empty:
        st.info("No se encontraron registros de imprevistos en los datos actuales.")
        return

    # ------------------------------------------------------------------
    # 2. Total vehículos desde la hoja "TASA DE IMPREVISTOS"
    # ------------------------------------------------------------------
    df_all = df.copy()
    df_all['año'] = pd.to_numeric(df_all['AÑO'], errors='coerce')
    df_all['mes'] = pd.to_numeric(df_all['MES'], errors='coerce')

    df_tasa_sheets = st.session_state.get("tasa_imprevistos_data")
    if df_tasa_sheets is not None and not df_tasa_sheets.empty:
        df_vehiculos = df_tasa_sheets.groupby(['AÑO', 'MES']).agg(
            total_vehiculos=('TOTAL', 'sum')
        ).reset_index()
        df_vehiculos = df_vehiculos.rename(columns={'AÑO': 'año', 'MES': 'mes'})
        df_vehiculos['año'] = df_vehiculos['año'].astype(int)
        df_vehiculos['mes'] = df_vehiculos['mes'].astype(int)
    else:
        st.warning("⚠️ No se encontraron datos de la hoja 'TASA DE IMPREVISTOS'. Usando conteo del DataFrame como fallback.")
        df_vehiculos = df_all.groupby(['año', 'mes']).agg(
            total_vehiculos=('PLACA', 'count')
        ).reset_index()
        df_vehiculos['año'] = df_vehiculos['año'].astype(int)
        df_vehiculos['mes'] = df_vehiculos['mes'].astype(int)

    # ------------------------------------------------------------------
    # 3. Merge y cálculo de eficiencia (1 - tasa)
    # ------------------------------------------------------------------
    df_resumen = df_vehiculos.merge(df_imp_mes, on=['año', 'mes'], how='outer')
    df_resumen['total_vehiculos'] = df_resumen['total_vehiculos'].fillna(0).astype(int)
    df_resumen['total_imprevistos'] = df_resumen['total_imprevistos'].fillna(0).astype(int)
    df_resumen['culpa_taller'] = df_resumen['culpa_taller'].fillna(0).astype(int)

    # Tasa de imprevistos
    df_resumen['tasa'] = df_resumen.apply(
        lambda r: (r['total_imprevistos'] / r['total_vehiculos'] * 100) if r['total_vehiculos'] > 0 else 0,
        axis=1
    ).round(1)

    # Eficiencia = 1 - tasa (expresada en porcentaje)
    df_resumen['Eficiencia (%)'] = (100 - df_resumen['tasa']).clip(lower=0, upper=100).round(1)

    # Crear etiquetas de mes
    df_resumen["mes_nombre"] = df_resumen.apply(
        lambda row: datetime(int(row["año"]), int(row["mes"]), 1).strftime('%b %Y'),
        axis=1
    )
    df_resumen = df_resumen.sort_values(['año', 'mes']).reset_index(drop=True)

    if df_resumen.empty:
        st.warning("No se pudo construir la serie mensual de efectividad.")
        return

    # ------------------------------------------------------------------
    # 4. KPIs resumen
    # ------------------------------------------------------------------
    eficiencia_promedio = df_resumen['Eficiencia (%)'].mean()
    mejor_idx = df_resumen['Eficiencia (%)'].idxmax()
    peor_idx = df_resumen['Eficiencia (%)'].idxmin()
    mejor_mes = df_resumen.loc[mejor_idx]
    peor_mes = df_resumen.loc[peor_idx]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Eficiencia promedio", f"{eficiencia_promedio:.1f}%")
    with col2:
        st.metric("Mejor mes", mejor_mes['mes_nombre'], f"{mejor_mes['Eficiencia (%)']:.1f}%")
    with col3:
        st.metric("Peor mes", peor_mes['mes_nombre'], f"{peor_mes['Eficiencia (%)']:.1f}%", delta_color="inverse")

    # ------------------------------------------------------------------
    # 5. Gráfico de línea
    # ------------------------------------------------------------------
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_resumen['mes_nombre'],
        y=df_resumen['Eficiencia (%)'],
        mode='lines+markers+text',
        name='Eficiencia',
        line=dict(color=BrandColors.PRIMARY, width=3),
        marker=dict(size=8, color=BrandColors.SECONDARY, line=dict(width=2, color='white')),
        text=df_resumen['Eficiencia (%)'].apply(lambda x: f'{x:.1f}%'),
        textposition='top center',
        textfont=dict(size=11, color='white')
    ))

    fig.add_shape(
        type="line",
        x0=df_resumen['mes_nombre'].iloc[0],
        x1=df_resumen['mes_nombre'].iloc[-1],
        y0=100, y1=100,
        line=dict(color=BrandColors.ACCENT, width=2, dash="dash"),
    )

    theme = get_plotly_theme(
        title=' Eficiencia Mensual en la Valoración',
        height=ChartHeights.LARGE,
        show_legend=False
    )
    theme["margin"] = {"l": 60, "r": 20, "t": 80, "b": 60}
    fig.update_layout(**theme)
    fig.update_xaxes(title_text='Mes')
    fig.update_yaxes(title_text='Eficiencia (%)', range=[0, 100], ticksuffix='%')

    st.plotly_chart(fig, width='stretch')

    # ------------------------------------------------------------------
    # 6. Tabla resumen
    # ------------------------------------------------------------------
    tabla_resumen = df_resumen[[
        'mes_nombre',
        'total_vehiculos',
        'total_imprevistos',
        'Eficiencia (%)'
    ]].copy()
    tabla_resumen = tabla_resumen.rename(columns={
        'mes_nombre': 'Mes',
        'total_vehiculos': 'Cantidad vehículos cotizados',
        'total_imprevistos': 'Vehículos con imprevistos'
    })
    tabla_resumen['Eficiencia (%)'] = tabla_resumen['Eficiencia (%)'].map(lambda x: f"{x:.1f}%")

    st.dataframe(
        tabla_resumen,
        width='stretch',
        hide_index=True,
        height=350
    )


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

    # Replicar colores si hay más compañías que colores
    color_list = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(resumen))]

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
        height=ChartHeights.XLARGE,
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

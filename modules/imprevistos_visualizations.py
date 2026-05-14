"""
================================================================================
IMPREVISTOS VISUALIZATIONS - Taller Hub
================================================================================
Visualization components for the Tasa de Imprevistos module.

Features:
- Combined bar+line chart (like the reference image)
- Monthly summary table
- Fault classification breakdown
- Interactive filters
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime

from .imprevistos_config import (
    get_resumen_mensual,
    IMPREVISTO_TIPOS,
)
from .imprevistos_processor import (
    procesar_datos_imprevistos,
    calcular_estadisticas,
    calcular_estadisticas_por_tipo,
    calcular_estadisticas_por_causal,
    resumir_imprevistos_mensuales,
)
from .date_utils import parse_source_date_column
from .theme import (
    BrandColors, SemanticColors, GrayScale, ChartHeights,
    get_plotly_theme, get_chart_color, hex_with_opacity
)


# ============================================================================
# COMBINED BAR + LINE CHART
# ============================================================================

def render_grafico_tasa_imprevistos_nuevo(
    df=None,
    taller_id: str = None,
    año: int = None,
    key_suffix: str = ""
):
    """
    Gráfico simple de línea: tasa de imprevistos mensual (%).
    """
    
    st.subheader("📊 Tasa de Imprevistos Mensual")
    
    if df is None or df.empty:
        st.info("No hay datos disponibles para mostrar.")
        return
    
    from .imprevistos_processor import extraer_imprevistos_from_dataframe
    
    df_imprevistos = extraer_imprevistos_from_dataframe(df)
    
    if df_imprevistos.empty:
        st.info("No se encontraron registros de imprevistos en los datos actuales.")
        st.caption("💡 Los imprevistos se detectan cuando ACCION='CAMBIO' o IMPREVISTO no está vacío")
        return
    
    df_all = df.copy()
    if 'AÑO' in df_all.columns and 'MES' in df_all.columns:
        df_all['año'] = pd.to_numeric(df_all['AÑO'], errors='coerce')
        df_all['mes'] = pd.to_numeric(df_all['MES'], errors='coerce')
        
        if año:
            df_all = df_all[df_all['año'] == año]
            df_imprevistos = df_imprevistos[df_imprevistos['año'] == año]
        
        df_imp_mes = resumir_imprevistos_mensuales(df=df, año=año)
        
        df_tasa_sheets = st.session_state.get("tasa_imprevistos_data")
        if df_tasa_sheets is not None and not df_tasa_sheets.empty:
            df_tasa_filtered = df_tasa_sheets.copy()
            if año:
                df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['AÑO'] == año]
            
            df_vehiculos = df_tasa_filtered.groupby(['AÑO', 'MES']).agg(
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
        
        df_resumen = df_vehiculos.merge(df_imp_mes, on=['año', 'mes'], how='outer')
        df_resumen['total_vehiculos'] = df_resumen['total_vehiculos'].fillna(0).astype(int)
        df_resumen['total_imprevistos'] = df_resumen['total_imprevistos'].fillna(0).astype(int)
        
        df_resumen['tasa'] = df_resumen.apply(
            lambda r: (r['total_imprevistos'] / r['total_vehiculos'] * 100) if r['total_vehiculos'] > 0 else 0,
            axis=1
        ).round(1)
        
        df_resumen["mes_nombre"] = df_resumen.apply(
            lambda row: datetime(int(row["año"]), int(row["mes"]), 1).strftime('%b %Y'),
            axis=1
        )
        
        df_resumen = df_resumen.sort_values(['año', 'mes'])
    else:
        st.warning("No se encontraron columnas de fecha (AÑO/MES) en los datos.")
        return
    
    if df_resumen.empty:
        st.info("No hay datos para el período seleccionado.")
        return
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df_resumen["mes_nombre"],
            y=df_resumen["tasa"],
            mode='lines+markers',
            name='Tasa de Imprevistos (%)',
            line=dict(color=BrandColors.PRIMARY, width=3),
            marker=dict(size=8, color=BrandColors.PRIMARY, line=dict(width=2, color='white')),
            hovertemplate='%{x}: %{y}%<extra></extra>',
        )
    )
    
    fig.update_layout(
        title='Tasa de Imprevistos Mensual',
        height=ChartHeights.XLARGE,
        hovermode='x unified',
        margin=dict(t=50, b=20, l=20, r=20),
    )
    
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Tasa (%)", ticksuffix="%")
    
    for _, row in df_resumen.iterrows():
        fig.add_annotation(
            x=row["mes_nombre"],
            y=row["tasa"],
            text=f"{row['tasa']:.1f}%",
            showarrow=False,
            yshift=10,
            font=dict(size=10, color=BrandColors.PRIMARY)
        )
    
    st.plotly_chart(fig, width="stretch", use_container_width=True)


# ============================================================================
# DETAILED SUMMARY TABLE
# ============================================================================

def render_tabla_resumen_imprevistos(
    df=None,
    taller_id: str = None,
    año: int = None
):
    """
    Render the detailed summary table:
    mes | cantidad vehículos | cantidad imprevistos | tasa (%)
    Plus fault classification breakdown.
    """
    
    st.subheader("📋 Tabla Resumen Mensual")
    
    if df is None or df.empty:
        st.info("No hay datos disponibles.")
        return
    
    from .imprevistos_processor import extraer_imprevistos_from_dataframe
    
    df_imprevistos = extraer_imprevistos_from_dataframe(df)
    
    if df_imprevistos.empty:
        st.info("No se encontraron registros de imprevistos.")
        return
    
    # Get monthly data
    df_all = df.copy()
    if 'AÑO' in df_all.columns and 'MES' in df_all.columns:
        df_all['año'] = pd.to_numeric(df_all['AÑO'], errors='coerce')
        df_all['mes'] = pd.to_numeric(df_all['MES'], errors='coerce')
        
        if año:
            df_all = df_all[df_all['año'] == año]
            df_imprevistos = df_imprevistos[df_imprevistos['año'] == año]
        
        df_vehiculos = df_all.groupby(['año', 'mes']).agg(
            total_vehiculos=('PLACA', 'count')
        ).reset_index()
        
        df_imp_mes = df_imprevistos.groupby(['año', 'mes']).agg(
            total_imprevistos=('placa', 'count'),
            culpa_taller=('es_culpa_taller', 'sum')
        ).reset_index()
        
        df_resumen = df_vehiculos.merge(df_imp_mes, on=['año', 'mes'], how='left')
        df_resumen['total_imprevistos'] = df_resumen['total_imprevistos'].fillna(0).astype(int)
        df_resumen['culpa_taller'] = df_resumen['culpa_taller'].fillna(0).astype(int)
        df_resumen['no_culpa_taller'] = df_resumen['total_imprevistos'] - df_resumen['culpa_taller']
        df_resumen['tasa'] = ((df_resumen['total_imprevistos'] / df_resumen['total_vehiculos'] * 100)).round(1)
        df_resumen['tasa_culpa_taller'] = ((df_resumen['culpa_taller'] / df_resumen['total_vehiculos'] * 100)).round(1)
        df_resumen['tasa_no_culpa_taller'] = ((df_resumen['no_culpa_taller'] / df_resumen['total_vehiculos'] * 100)).round(1)
        df_resumen['mes_nombre'] = df_resumen["mes"].apply(
            lambda x: datetime(2000, int(x), 1).strftime('%B %Y')
        )
        df_resumen = df_resumen.sort_values(['año', 'mes'])
    else:
        st.warning("No hay datos de fecha disponibles.")
        return
    
    if df_resumen.empty:
        st.info("No hay datos para el período seleccionado.")
        return
    
    # Create display DataFrame
    df_display = df_resumen[[
        "mes_nombre", "total_vehiculos", "total_imprevistos",
        "culpa_taller", "no_culpa_taller",
        "tasa", "tasa_culpa_taller", "tasa_no_culpa_taller"
    ]].copy()
    
    df_display = df_display.rename(columns={
        "mes_nombre": "Mes",
        "total_vehiculos": "Cantidad Vehículos",
        "total_imprevistos": "Cantidad Imprevistos",
        "culpa_taller": "Culpa del Taller",
        "no_culpa_taller": "No Culpa del Taller",
        "tasa": "Tasa Total (%)",
        "tasa_culpa_taller": "Tasa Culpa Taller (%)",
        "tasa_no_culpa_taller": "Tasa No Culpa Taller (%)"
    })
    
    # Format percentages
    for col in ["Tasa Total (%)", "Tasa Culpa Taller (%)", "Tasa No Culpa Taller (%)"]:
        df_display[col] = df_display[col].apply(lambda x: f"{x:.1f}%")
    
    # Display table
    st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        height=400
    )
    
    # Add explanation
    with st.expander("ℹ️ ¿Cómo se calcula la tasa?"):
        st.markdown("""
        **Fórmula de cálculo:**
        
        ```
        Tasa (%) = (Cantidad de Imprevistos / Cantidad de Vehículos) × 100
        ```
        
        **Reglas de clasificación:**
        
        - **Culpa del Taller:**
          - Imprevistos con acción = "cambio" y causales como:
            - Digitación
            - No cotizado
            - Predesarme
            - Sin fotos claras
            - Sin diagnóstico
            - Error de diagnóstico
            - Daño adicional
        
        - **NO es Culpa del Taller:**
          - Imprevistos con cambio de repuestos
          - Imprevistos con acción = "cambio" y causal = "No visible"
        
        **Deduplicación:**
        - Si una placa+siniestro tiene más de 1 imprevisto, se cuenta solo 1
        """)


# ============================================================================
# FAULT CLASSIFICATION CHART
# ============================================================================

def render_grafico_clasificacion_faltas(
    df=None,
    taller_id: str = None,
    año: int = None
):
    """
    Render a pie/donut chart showing fault classification breakdown.
    """
    
    st.subheader("🏪 Clasificación por Responsabilidad")
    
    if df is None or df.empty:
        st.info("No hay datos disponibles.")
        return
    
    stats = calcular_estadisticas(df=df, taller_id=taller_id, año=año)
    
    if stats["total_imprevistos"] == 0:
        st.info("No se encontraron imprevistos en los datos actuales.")
        return
    
    # Create pie chart
    labels = ['Culpa del Taller', 'No es Culpa del Taller']
    values = [stats["culpa_taller_total"], stats["no_culpa_taller_total"]]
    colors = [SemanticColors.ERROR, SemanticColors.SUCCESS]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors),
        hole=0.4,
        textinfo='label+percent',
        hoverinfo='label+value+percent'
    )])
    
    fig.update_layout(
        title=f'Distribución de Responsabilidad\n(Total: {stats["total_imprevistos"]} imprevistos)',
        height=400,
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.1,
            xanchor='center',
            x=0.5
        )
    )
    
    st.plotly_chart(fig, width="stretch", use_container_width=True)
    
    # Show metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📊 Total Imprevistos",
            stats["total_imprevistos"]
        )
    
    with col2:
        st.metric(
            "🏪 Culpa del Taller",
            stats["culpa_taller_total"],
            delta=f"{stats['porcentaje_culpa_taller']:.1f}%"
        )
    
    with col3:
        st.metric(
            "✅ No Culpa del Taller",
            stats["no_culpa_taller_total"],
            delta=f"{100 - stats['porcentaje_culpa_taller']:.1f}%"
        )


# ============================================================================
# STATISTICS BY TYPE
# ============================================================================

def render_estadisticas_por_tipo(
    df=None,
    taller_id: str = None,
    año: int = None
):
    """
    Render statistics by imprevisto type.
    """
    
    st.subheader("⚠️ Estadísticas por Tipo de Imprevisto")
    
    if df is None or df.empty:
        st.info("No hay datos disponibles.")
        return
    
    df_stats = calcular_estadisticas_por_tipo(df=df, taller_id=taller_id, año=año)
    
    if df_stats.empty:
        st.info("No hay datos de tipos de imprevistos disponibles.")
        return
    
    # Display as bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_stats["tipo_label"],
        y=df_stats["cantidad"],
        marker_color=[BrandColors.PRIMARY, SemanticColors.WARNING][:len(df_stats)],
        text=df_stats["cantidad"],
        textposition='outside'
    ))

    fig.update_layout(
        **get_plotly_theme(
            title='Cantidad de Imprevistos por Tipo',
            height=ChartHeights.SMALL,
            show_legend=False
        )
    )
    fig.update_xaxes(title_text='Tipo')
    fig.update_yaxes(title_text='Cantidad')
    
    st.plotly_chart(fig, width="stretch", use_container_width=True)
    
    # Show table
    df_table = df_stats[[
        "tipo_label", "cantidad", "culpa_taller", "no_culpa_taller", "porcentaje"
    ]].rename(columns={
        "tipo_label": "Tipo",
        "cantidad": "Cantidad",
        "culpa_taller": "Culpa Taller",
        "no_culpa_taller": "No Culpa Taller",
        "porcentaje": "Porcentaje (%)"
    })
    
    df_table["Porcentaje (%)"] = df_table["Porcentaje (%)"].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(df_table, width="stretch", hide_index=True)


# ============================================================================
# STATISTICS BY CAUSE
# ============================================================================

def render_estadisticas_por_causal(
    df=None,
    taller_id: str = None,
    año: int = None
):
    """
    Render statistics by cause (for MANO_OBRA type).
    """
    
    st.subheader("🔍 Estadísticas por Causal (Mano de Obra)")
    
    if df is None or df.empty:
        st.info("No hay datos disponibles.")
        return
    
    df_stats = calcular_estadisticas_por_causal(df=df, taller_id=taller_id, año=año)
    
    if df_stats.empty:
        st.info("No hay datos de causales disponibles.")
        return
    
    # Display as horizontal bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df_stats["causal"],
        x=df_stats["cantidad"],
        orientation='h',
        marker_color=SemanticColors.WARNING,
        text=df_stats["cantidad"],
        textposition='outside'
    ))

    fig.update_layout(
        title='Cantidad de Imprevistos por Causal',
        xaxis_title='Cantidad',
        yaxis_title='Causal',
        height=max(ChartHeights.SMALL, len(df_stats) * 40),
        yaxis={'categoryorder': 'total ascending'}
    )
    
    st.plotly_chart(fig, width="stretch", use_container_width=True)
    
    # Show table
    df_table = df_stats[[
        "causal", "cantidad", "culpa_taller", "no_culpa_taller", "porcentaje"
    ]].rename(columns={
        "causal": "Causal",
        "cantidad": "Cantidad",
        "culpa_taller": "Culpa Taller",
        "no_culpa_taller": "No Culpa Taller",
        "porcentaje": "Porcentaje (%)"
    })
    
    df_table["Porcentaje (%)"] = df_table["Porcentaje (%)"].apply(lambda x: f"{x:.1f}%")
    
    # Add fault indicator
    df_table["¿Culpa del Taller?"] = df_table["Causal"].apply(
        lambda x: "❌ Sí" if x in ["Digitación", "No cotizado", "Predesarme", 
                                     "Sin fotos claras", "Sin diagnóstico",
                                     "Error de diagnóstico", "Daño adicional"]
        else "✅ No" if x == "No visible"
        else "⚠️ Pendiente"
    )
    
    st.dataframe(df_table, width="stretch", hide_index=True)


# ============================================================================
# TASA DE IMPREVISTOS POR CAMBIO DE REPUESTO - CULPA DEL TALLER
# ============================================================================

CAUSALES_CULPA_TALLER = {
    "NO COTIZADO",
    "PREDESARME",
    "DIGITACIÓN",
    "DIGITACION",
    "SIN FOTOS CLARAS",
    "SIN DIAGNÓSTICO",
    "SIN DIAGNOSTICO",
}


def _calcular_tasa_culpa_taller_cambio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la tasa mensual de imprevistos con cambio de repuesto que son culpa del taller.

    Reglas:
    1. Filtrar registros donde ACCION contiene "CAMBIO"
    2. No excluir registros por ESTATUS o mano de obra inicial
    3. No deduplicar placas/siniestros: cada registro válido cuenta
    4. Rate = culpa_taller / total_registros_validos * 100
       Culpa del taller: CAUSAL en {no cotizado, predesarme, digitación, sin fotos claras, sin diagnóstico}
    """
    if df is None or df.empty:
        return pd.DataFrame()

    required = {'ACCION', 'AÑO', 'MES', 'PLACA'}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    df_w = df.copy()

    # Step 1: solo registros con CAMBIO
    df_cambio = df_w[df_w['ACCION'].str.contains('CAMBIO', na=False, case=False)].copy()
    if df_cambio.empty:
        return pd.DataFrame()

    # Step 2: no descartar registros por estatus o mano de obra inicial.
    mo_col = 'M._DE_O._INICIAL'
    status_col = 'ESTATUS'
    if mo_col in df_cambio.columns:
        df_cambio['_MO_INICIAL'] = pd.to_numeric(df_cambio[mo_col], errors='coerce').fillna(0)
    else:
        df_cambio['_MO_INICIAL'] = 0

    if status_col in df_cambio.columns:
        df_cambio['_ESTATUS'] = df_cambio[status_col].astype(str).str.upper().str.strip()
    else:
        df_cambio['_ESTATUS'] = ''

    # Normalizar columnas clave
    df_cambio['_PLACA'] = df_cambio['PLACA'].astype(str).str.upper().str.strip()
    df_cambio['_SINIESTRO'] = (
        df_cambio['SINIESTRO'].astype(str).str.upper().str.strip()
        if 'SINIESTRO' in df_cambio.columns
        else ''
    )
    df_cambio['_CAUSAL'] = (
        df_cambio['CAUSAL'].astype(str).str.upper().str.strip()
        if 'CAUSAL' in df_cambio.columns
        else ''
    )
    df_cambio['_AÑO'] = pd.to_numeric(df_cambio['AÑO'], errors='coerce')
    df_cambio['_MES'] = pd.to_numeric(df_cambio['MES'], errors='coerce')

    df_cambio = df_cambio[
        df_cambio['_AÑO'].notna() & df_cambio['_MES'].notna() &
        (df_cambio['_AÑO'] > 2000) &
        (df_cambio['_MES'] >= 1) & (df_cambio['_MES'] <= 12)
    ].copy()

    if df_cambio.empty:
        return pd.DataFrame()

    df_cambio['_AÑO'] = df_cambio['_AÑO'].astype(int)
    df_cambio['_MES'] = df_cambio['_MES'].astype(int)

    # Step 3: no deduplicar. Cada registro válido cuenta en el gráfico.
    df_cambio['_CULPA'] = df_cambio['_CAUSAL'].isin(CAUSALES_CULPA_TALLER)
    
    # Agregar por mes
    resumen = df_cambio.groupby(['_AÑO', '_MES']).agg(
        total=('_PLACA', 'count'),
        culpa_taller=('_CULPA', 'sum')
    ).reset_index()

    resumen['tasa'] = (resumen['culpa_taller'] / resumen['total'] * 100).round(1)
    resumen['FECHA'] = pd.to_datetime(
        resumen['_AÑO'].astype(str) + '-' + resumen['_MES'].astype(str) + '-01',
        format='%Y-%m-%d', errors='coerce'
    )
    resumen = resumen[resumen['FECHA'].notna()].sort_values('FECHA').reset_index(drop=True)
    resumen['mes_label'] = resumen['FECHA'].dt.strftime('%b').str.upper()
    resumen.rename(columns={'_AÑO': 'año', '_MES': 'mes'}, inplace=True)

    return resumen


def render_grafico_culpa_taller_mensual(df=None):
    """
    Gráfico de línea: tasa mensual de imprevistos con cambio de repuesto (culpa del taller).
    Estilo consistente con el resto del dashboard.
    """
    import datetime
    st.subheader("🔧 Imprevistos con Cambio de Repuesto")

    if df is None or df.empty:
        st.info("No hay datos disponibles.")
        return

    resumen = _calcular_tasa_culpa_taller_cambio(df)

    if resumen.empty:
        st.info("No se encontraron imprevistos con ACCION=CAMBIO y mano de obra registrada.")
        return

    años_disponibles = sorted(resumen['año'].unique().tolist(), reverse=True)
    año_actual = datetime.datetime.now().year
    default_idx = años_disponibles.index(año_actual) if año_actual in años_disponibles else 0
    año_sel = st.selectbox(
        "Año",
        options=años_disponibles,
        index=default_idx,
        key="culpa_taller_año"
    )
    resumen = resumen[resumen['año'] == año_sel].copy()

    if resumen.empty:
        st.info(f"No hay datos para el año {año_sel}.")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=resumen['mes_label'],
        y=resumen['culpa_taller'],
        mode='lines+markers+text',
        line=dict(color=BrandColors.PRIMARY, width=3),
        marker=dict(size=10, color=BrandColors.SECONDARY, line=dict(width=2, color='white')),
        text=resumen['culpa_taller'].astype(int).astype(str),
        textposition='top center',
        textfont=dict(size=12, color=BrandColors.PRIMARY),
        hovertemplate='%{x}: %{y} imprevistos<extra></extra>',
        name='Con causal de proceso'
    ))

    fig.update_layout(
        **get_plotly_theme(
            title='🔧 Imprevistos con Cambio de Repuesto',
            height=ChartHeights.MEDIUM,
            show_legend=False
        )
    )
    fig.update_xaxes(title_text='Mes')
    fig.update_yaxes(title_text='Cantidad')
    fig.update_layout(margin=dict(l=50, r=30, t=60, b=50))

    st.plotly_chart(fig, use_container_width=True)

    # Métricas resumidas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total registros cambio", int(resumen['total'].sum()))
    with col2:
        st.metric("Con causal de proceso", int(resumen['culpa_taller'].sum()))
    with col3:
        tasa = (resumen['culpa_taller'].sum() / resumen['total'].sum() * 100) if resumen['total'].sum() > 0 else 0
        st.metric("Tasa con causal", f"{tasa:.1f}%")


# ============================================================================
# DEMORA EN DEFINICIÓN DEL IMPREVISTO POR CIA Y ESTATUS
# ============================================================================

def render_demora_definicion_imprevisto(df=None, año: int = None):
    """
    Gráfico de barras agrupadas: Demora en definición del imprevisto por CIA y Estatus.

    Muestra el promedio de días entre FECHA_INGR y FECHA_AUTO, agrupado por
    compañía de seguros (CIA) y estatus (AUTORIZADO / RECHAZADO).

    Reglas:
    - Deduplicación por PLACA + SINIESTRO (solo se admite 1 registro por combinación)
    - Todos los registros con fechas válidas son considerados
    - Delay = FECHA_AUTO - FECHA_INGR en días
    """
    import datetime

    st.subheader("⏱️ Demora en Definición del Imprevisto")

    if df is None or df.empty:
        st.info("No hay datos disponibles para mostrar.")
        return

    required_cols = {'FECHA_INGR', 'FECHA_AUTO', 'COMPAÑIA_DE_SEGUROS', 'ESTATUS', 'PLACA'}
    if not required_cols.issubset(df.columns):
        faltantes = required_cols - set(df.columns)
        st.warning(f"Faltan columnas necesarias: {', '.join(faltantes)}")
        return

    df_w = df.copy()

    # --- Filtro por año ---
    if año and 'AÑO' in df_w.columns:
        df_w['_AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
        df_w = df_w[df_w['_AÑO'] == año].copy()
    elif año:
        st.warning("Columna AÑO no disponible, se muestran todos los datos.")

    if df_w.empty:
        st.info(f"No hay datos para el año {año}." if año else "No hay datos disponibles.")
        return

    # --- Selector de año interactivo ---
    if 'AÑO' in df.columns:
        años_disponibles = sorted(
            pd.to_numeric(df['AÑO'], errors='coerce').dropna().unique().tolist(),
            reverse=True
        )
        año_actual = datetime.datetime.now().year
        default_idx = años_disponibles.index(año_actual) if año_actual in años_disponibles else 0
        año_sel = st.selectbox(
            "Año",
            options=años_disponibles,
            index=default_idx,
            key="demora_definicion_año"
        )
        df_w = df.copy()
        df_w['_AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
        df_w = df_w[df_w['_AÑO'] == año_sel].copy()
        if df_w.empty:
            st.info(f"No hay datos para el año {año_sel}.")
            return
    else:
        año_sel = año

    # --- Limpiar PLACA y SINIESTRO para deduplicación ---
    df_w['_PLACA'] = df_w['PLACA'].astype(str).str.upper().str.strip()
    df_w['_SINIESTRO'] = (
        df_w['SINIESTRO'].astype(str).str.upper().str.strip()
        if 'SINIESTRO' in df_w.columns
        else ''
    )

    # --- Validación estricta de fechas con diagnóstico ---
    total_registros = len(df_w)
    invalidados = {}

    # 1. Forzar conversión a datetime SIEMPRE (no solo si no es datetime64)
    df_w['FECHA_INGR'] = parse_source_date_column(df_w['FECHA_INGR'], 'FECHA_INGR')
    df_w['FECHA_AUTO'] = parse_source_date_column(df_w['FECHA_AUTO'], 'FECHA_AUTO')

    # 2. Registrar y descartar registros con FECHA_INGR inválida (NaT)
    mask_ingr_na = df_w['FECHA_INGR'].isna()
    invalidados['FECHA_INGR vacía o inválida'] = int(mask_ingr_na.sum())
    df_w_with_ingr = df_w[~mask_ingr_na].copy()

    # 3. Registrar y descartar registros con FECHA_AUTO inválida (NaT)
    mask_auto_na = df_w['FECHA_AUTO'].isna()
    invalidados['FECHA_AUTO vacía o inválida'] = int(mask_auto_na.sum())
    df_w = df_w[~mask_auto_na].copy()

    # 4. Descartar fechas fuera de rango razonable (año < 2000 o > año actual + 1)
    año_limite = datetime.datetime.now().year + 1
    mask_fecha_irreal = (
        (df_w['FECHA_INGR'].dt.year < 2000) | (df_w['FECHA_INGR'].dt.year > año_limite) |
        (df_w['FECHA_AUTO'].dt.year < 2000) | (df_w['FECHA_AUTO'].dt.year > año_limite)
    )
    invalidados['Fechas fuera de rango (año < 2000 o > {})'.format(año_limite)] = int(mask_fecha_irreal.sum())
    df_w = df_w[~mask_fecha_irreal].copy()

    if df_w.empty:
        st.warning("No hay registros con ambas fechas (FECHA_INGR y FECHA_AUTO) válidas.")
        detalles = [f"- {motivo}: {cant}" for motivo, cant in invalidados.items() if cant > 0]
        if detalles:
            st.caption("Registros descartados:\n" + "\n".join(detalles))
        return

    # --- Calcular demora en días ---
    df_w['_DEMORA_DIAS'] = (df_w['FECHA_AUTO'] - df_w['FECHA_INGR']).dt.days

    # --- Filtrar estatus AUTORIZADO y RECHAZADO únicamente ---
    mask_estatus_invalido = ~df_w['ESTATUS'].isin(['AUTORIZADO', 'RECHAZADO'])
    invalidados['Estatus no es AUTORIZADO ni RECHAZADO'] = int(mask_estatus_invalido.sum())
    df_w = df_w[~mask_estatus_invalido].copy()

    if df_w.empty:
        st.warning("No hay registros con estatus AUTORIZADO o RECHAZADO que tengan fechas válidas.")
        return

    # --- Deduplicación por PLACA + SINIESTRO ---
    total_antes = len(df_w)
    df_w = df_w.drop_duplicates(subset=['_PLACA', '_SINIESTRO'], keep='first')
    dup_eliminados = total_antes - len(df_w)
    if dup_eliminados > 0:
        invalidados['Duplicados (misma PLACA + SINIESTRO)'] = dup_eliminados

    registros_validos = len(df_w)

    # --- Diagnóstico visible (siempre mostrado para auditoría) ---
    total_descartados = total_registros - registros_validos
    st.caption(
        f"🔍 **Diagnóstico:** {total_registros} registros entrantes → "
        f"{registros_validos} válidos ({total_descartados} descartados)"
    )
    cols_diag = st.columns(4 if len(invalidados) >= 4 else len(invalidados) or 1)
    col_idx = 0
    for motivo, cant in invalidados.items():
        if cant > 0:
            with cols_diag[col_idx % len(cols_diag)]:
                st.metric(motivo, cant)
            col_idx += 1

    # --- Agrupar por CIA y ESTATUS ---
    df_agrupado = df_w.groupby(['COMPAÑIA_DE_SEGUROS', 'ESTATUS']).agg(
        promedio_demora=('_DEMORA_DIAS', 'mean'),
        conteo=('_DEMORA_DIAS', 'count')
    ).reset_index()

    df_agrupado['promedio_demora'] = df_agrupado['promedio_demora'].round(1)

    if df_agrupado.empty:
        st.info("No hay datos suficientes para mostrar el gráfico.")
        return

    # --- Pivot para tener AUTORIZADO y RECHAZADO como columnas (para el gráfico) ---
    df_pivot = df_agrupado.pivot_table(
        index='COMPAÑIA_DE_SEGUROS',
        columns='ESTATUS',
        values=['promedio_demora', 'conteo'],
        fill_value=0
    )

    # Aplanar columnas del pivot
    df_pivot.columns = [f'{val}_{est}' for val, est in df_pivot.columns]
    df_pivot = df_pivot.reset_index()

    # Asegurar que existan ambas columnas
    for estatus in ['AUTORIZADO', 'RECHAZADO']:
        for metric in ['promedio_demora', 'conteo']:
            col_name = f'{metric}_{estatus}'
            if col_name not in df_pivot.columns:
                df_pivot[col_name] = 0

    # Ordenar por promedio total descendente
    df_pivot['_total_promedio'] = df_pivot['promedio_demora_AUTORIZADO'] + df_pivot['promedio_demora_RECHAZADO']
    df_pivot = df_pivot.sort_values('_total_promedio', ascending=False).reset_index(drop=True)

    if df_pivot.empty:
        st.info("No hay datos suficientes para mostrar el gráfico.")
        return

    # --- Construir gráfico de barras agrupadas ---
    cia_list = df_pivot['COMPAÑIA_DE_SEGUROS'].tolist()

    fig = go.Figure()

    # Barra AUTORIZADO
    fig.add_trace(go.Bar(
        x=cia_list,
        y=df_pivot['promedio_demora_AUTORIZADO'],
        name='AUTORIZADO',
        marker_color=SemanticColors.SUCCESS,
        text=df_pivot.apply(
            lambda r: f"{r['promedio_demora_AUTORIZADO']:.1f}d ({int(r['conteo_AUTORIZADO'])})",
            axis=1
        ),
        textposition='outside',
        textfont=dict(size=11, color='white'),
        hovertemplate=(
            '%{x}<br>'
            'Promedio: %{y:.1f} días<br>'
            'Conteo: %{customdata}<br>'
            'Estatus: AUTORIZADO<extra></extra>'
        ),
        customdata=df_pivot['conteo_AUTORIZADO'].astype(int).tolist(),
    ))

    # Barra RECHAZADO
    fig.add_trace(go.Bar(
        x=cia_list,
        y=df_pivot['promedio_demora_RECHAZADO'],
        name='RECHAZADO',
        marker_color=SemanticColors.ERROR,
        text=df_pivot.apply(
            lambda r: f"{r['promedio_demora_RECHAZADO']:.1f}d ({int(r['conteo_RECHAZADO'])})",
            axis=1
        ),
        textposition='outside',
        textfont=dict(size=11, color='white'),
        hovertemplate=(
            '%{x}<br>'
            'Promedio: %{y:.1f} días<br>'
            'Conteo: %{customdata}<br>'
            'Estatus: RECHAZADO<extra></extra>'
        ),
        customdata=df_pivot['conteo_RECHAZADO'].astype(int).tolist(),
    ))

    fig.update_layout(
        **get_plotly_theme(
            title='⏱️ Demora en Definición del Imprevisto por CIA y Estatus',
            height=ChartHeights.LARGE,
            show_legend=True
        )
    )
    fig.update_xaxes(title_text='Compañía de Seguros (CIA)', tickangle=-30)
    fig.update_yaxes(title_text='Promedio de Días de Demora', tickformat='.0f', ticksuffix='d')

    st.plotly_chart(fig, width="stretch", use_container_width=True)

    # --- Métricas resumen ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total Registros Únicos", len(df_w))
    with col2:
        st.metric("📊 Promedio General (días)", f"{df_w['_DEMORA_DIAS'].mean():.1f}")
    with col3:
        st.metric("✅ Autorizados", int(len(df_w[df_w['ESTATUS'] == 'AUTORIZADO'])))
    with col4:
        st.metric("❌ Rechazados", int(len(df_w[df_w['ESTATUS'] == 'RECHAZADO'])))

    # --- Tabla resumen ---
    with st.expander("📋 Ver Tabla de Detalle"):
        df_tabla = df_pivot[[
            'COMPAÑIA_DE_SEGUROS',
            'promedio_demora_AUTORIZADO',
            'conteo_AUTORIZADO',
            'promedio_demora_RECHAZADO',
            'conteo_RECHAZADO'
        ]].copy()
        df_tabla.columns = [
            'Compañía de Seguros',
            'Promedio Autorizado (días)',
            'Cant. Autorizados',
            'Promedio Rechazado (días)',
            'Cant. Rechazados'
        ]
        df_tabla['Promedio Autorizado (días)'] = df_tabla['Promedio Autorizado (días)'].round(1)
        df_tabla['Promedio Rechazado (días)'] = df_tabla['Promedio Rechazado (días)'].round(1)
        st.dataframe(df_tabla, width="stretch", hide_index=True)


# ============================================================================
# MAIN VISUALIZATION ENTRY POINT
# ============================================================================

def render_imprevistos_visualizations(
    df=None,
    taller_id: str = None,
    año: int = None,
    key_suffix: str = ""
):
    """
    Main entry point for all imprevistos visualizations.
    """
    
    # Combined bar+line chart
    render_grafico_tasa_imprevistos_nuevo(
        df=df,
        taller_id=taller_id,
        año=año,
        key_suffix=key_suffix
    )
    
    st.divider()
    
    # Summary table
    render_tabla_resumen_imprevistos(
        df=df,
        taller_id=taller_id,
        año=año
    )
    
    st.divider()
    
    # Fault classification
    col1, col2 = st.columns(2)
    
    with col1:
        render_grafico_clasificacion_faltas(
            df=df,
            taller_id=taller_id,
            año=año
        )
    
    with col2:
        render_estadisticas_por_tipo(
            df=df,
            taller_id=taller_id,
            año=año
        )
    
    st.divider()
    
    # Statistics by cause
    render_estadisticas_por_causal(
        df=df,
        taller_id=taller_id,
        año=año
    )

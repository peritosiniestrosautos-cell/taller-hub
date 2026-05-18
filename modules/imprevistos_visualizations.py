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

from io import BytesIO
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
from .data_loader import load_tasa_imprevistos_from_excel
from .date_utils import parse_source_date_column
from .theme import (
    BrandColors, SemanticColors, GrayScale, ChartHeights,
    get_plotly_theme, get_chart_color, hex_with_opacity
)


def _format_month_year_label(mes, año) -> str:
    """Return the display label for a month using the record's real year."""
    return datetime(int(año), int(mes), 1).strftime('%B %Y')


# ============================================================================
# HELPER: Cargar datos de vehículos desde TASA DE IMPREVISTOS
# ============================================================================

def _get_vehiculos_por_mes(año: int = None, años: list = None, meses: list = None) -> pd.DataFrame:
    """
    Obtiene el total de vehículos entregados por mes desde la hoja
    'TASA DE IMPREVISTOS'. Primero busca en session_state; si no está,
    carga directamente desde el archivo Excel local.
    
    Args:
        año: Filtrar por un año específico (legacy)
        años: Filtrar por múltiples años
        meses: Filtrar por múltiples meses
    
    Returns:
        DataFrame con columnas: año, mes, total_vehiculos
    """
    df_tasa_sheets = st.session_state.get("tasa_imprevistos_data")
    
    if df_tasa_sheets is None or df_tasa_sheets.empty:
        df_tasa_sheets, error = load_tasa_imprevistos_from_excel()
        if df_tasa_sheets is not None and not df_tasa_sheets.empty:
            st.session_state["tasa_imprevistos_data"] = df_tasa_sheets
    
    if df_tasa_sheets is None or df_tasa_sheets.empty:
        return pd.DataFrame(columns=['año', 'mes', 'total_vehiculos'])
    
    df_tasa_filtered = df_tasa_sheets.copy()
    if años is not None and len(años) > 0:
        df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['AÑO'].isin(años)]
    elif año:
        df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['AÑO'] == año]
    
    if meses is not None and len(meses) > 0:
        df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['MES'].isin(meses)]
    
    df_vehiculos = df_tasa_filtered.groupby(['AÑO', 'MES']).agg(
        total_vehiculos=('TOTAL', 'sum')
    ).reset_index()
    df_vehiculos = df_vehiculos.rename(columns={'AÑO': 'año', 'MES': 'mes'})
    df_vehiculos['año'] = pd.to_numeric(df_vehiculos['año'], errors='coerce').astype(int)
    df_vehiculos['mes'] = pd.to_numeric(df_vehiculos['mes'], errors='coerce').astype(int)
    return df_vehiculos


# ============================================================================
# HELPER: Filtros de Período para Imprevistos
# ============================================================================

def _render_filtros_periodo_imprevistos(df, key_suffix=""):
    """
    Renderiza filtros de período estándar (Año, Trimestre, Mes) como multiselect.
    Retorna: (años_sel, trimestres_sel, meses_sel, meses_filtro)
    """
    df_periodos = df.copy()
    if 'AÑO' in df_periodos.columns:
        df_periodos['_AÑO'] = pd.to_numeric(df_periodos['AÑO'], errors='coerce')
    if 'MES' in df_periodos.columns:
        df_periodos['_MES'] = pd.to_numeric(df_periodos['MES'], errors='coerce')

    años_disponibles = sorted(
        df_periodos['_AÑO'].dropna().astype(int).unique().tolist(),
        reverse=True
    ) if '_AÑO' in df_periodos.columns else []

    trimestres_opciones = ["Q1", "Q2", "Q3", "Q4"]

    meses_disponibles = sorted([
        m for m in df_periodos['_MES'].dropna().astype(int).unique().tolist()
        if 1 <= m <= 12
    ]) if '_MES' in df_periodos.columns else []

    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    col1, col2, col3 = st.columns(3)

    with col1:
        años_sel = st.multiselect(
            "📅 Años",
            options=años_disponibles,
            default=años_disponibles[:min(2, len(años_disponibles))] if años_disponibles else [],
            key=f"imp_filtro_años_{key_suffix}"
        )

    with col2:
        trimestres_sel = st.multiselect(
            "📊 Trimestres",
            options=trimestres_opciones,
            default=[],
            help="Selecciona uno o varios trimestres (ej: Q1 y Q4)",
            key=f"imp_filtro_trimestres_{key_suffix}"
        )

    with col3:
        meses_sel = st.multiselect(
            "📆 Meses",
            options=meses_disponibles,
            format_func=lambda m: meses_nombres.get(m, str(m)),
            default=[],
            help="Selecciona uno o varios meses",
            key=f"imp_filtro_meses_{key_suffix}"
        )

    # Calcular meses a filtrar basado en trimestres + meses individuales
    meses_filtro = list(meses_sel) if meses_sel else []
    trimestre_map = {"Q1": [1, 2, 3], "Q2": [4, 5, 6], "Q3": [7, 8, 9], "Q4": [10, 11, 12]}
    for t in trimestres_sel:
        for m in trimestre_map.get(t, []):
            if m not in meses_filtro:
                meses_filtro.append(m)

    return años_sel, trimestres_sel, meses_sel, meses_filtro


def _generar_excel_simple(df, sheet_name="Datos"):
    """Genera un archivo Excel simple."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


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
    
    title_col, action_col = st.columns([3, 2])
    with title_col:
        st.subheader("📊 Tasa de Imprevistos Mensual")

    if df is None or df.empty:
        st.info("No hay datos disponibles para mostrar.")
        return

    # --- Filtros de período ---
    header_container = st.container()

    años_sel, trimestres_sel, meses_sel, meses_filtro = _render_filtros_periodo_imprevistos(
        df, key_suffix=f"tasa_{key_suffix}"
    )

    from .imprevistos_processor import extraer_imprevistos_from_dataframe

    df_imprevistos = extraer_imprevistos_from_dataframe(df)

    if df_imprevistos.empty:
        st.info("No se encontraron registros de imprevistos en los datos actuales.")
        st.caption("💡 Los imprevistos se detectan cuando ACCION='CAMBIO' o IMPREVISTO no está vacío")
        return

    if 'AÑO' in df.columns and 'MES' in df.columns:
        df_imp_mes = resumir_imprevistos_mensuales(
            df=df,
            años=años_sel if años_sel else None,
            meses=meses_filtro if meses_filtro else None
        )

        df_vehiculos = _get_vehiculos_por_mes(
            años=años_sel if años_sel else None,
            meses=meses_filtro if meses_filtro else None
        )

        if df_vehiculos.empty:
            st.warning("⚠️ No se encontraron datos de la hoja 'TASA DE IMPREVISTOS'. No se puede calcular la tasa sin el total de vehículos.")
            return

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
        with header_container:
            st.subheader("📊 Tasa de Imprevistos Mensual")
        st.info("No hay datos para el período seleccionado.")
        return

    # Botón de exportación
    excel_data = _generar_excel_simple(df_resumen, "Tasa de Imprevistos")
    with header_container:
        title_col, action_col = st.columns([3, 2])
        with title_col:
            st.subheader("📊 Tasa de Imprevistos Mensual")
        with action_col:
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"tasa_imprevistos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

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
    Uses 'TASA DE IMPREVISTOS' sheet for vehicle counts.
    """

    header_container = st.container()

    if df is None or df.empty:
        with header_container:
            st.subheader("📋 Tabla Resumen Mensual")
        st.info("No hay datos disponibles.")
        return

    # --- Filtros de período ---
    años_sel, trimestres_sel, meses_sel, meses_filtro = _render_filtros_periodo_imprevistos(
        df, key_suffix="tabla_resumen"
    )

    from .imprevistos_processor import extraer_imprevistos_from_dataframe

    df_imprevistos = extraer_imprevistos_from_dataframe(df)

    if df_imprevistos.empty:
        st.info("No se encontraron registros de imprevistos.")
        return

    # Get monthly data
    if 'AÑO' in df.columns and 'MES' in df.columns:
        if año and not años_sel:
            df_imprevistos = df_imprevistos[df_imprevistos['año'] == año]

        df_imp_mes = resumir_imprevistos_mensuales(
            df=df,
            años=años_sel if años_sel else ([año] if año else None),
            meses=meses_filtro if meses_filtro else None
        )

        df_vehiculos = _get_vehiculos_por_mes(
            años=años_sel if años_sel else ([año] if año else None),
            meses=meses_filtro if meses_filtro else None
        )

        if df_vehiculos.empty:
            st.warning("⚠️ No se encontraron datos de la hoja 'TASA DE IMPREVISTOS'. No se puede calcular la tasa sin el total de vehículos.")
            return

        df_resumen = df_vehiculos.merge(df_imp_mes, on=['año', 'mes'], how='outer')
        df_resumen['total_vehiculos'] = df_resumen['total_vehiculos'].fillna(0).astype(int)
        df_resumen['total_imprevistos'] = df_resumen['total_imprevistos'].fillna(0).astype(int)
        df_resumen['culpa_taller'] = df_resumen['culpa_taller'].fillna(0).astype(int)
        df_resumen['no_culpa_taller'] = df_resumen['total_imprevistos'] - df_resumen['culpa_taller']
        df_resumen['tasa'] = ((df_resumen['total_imprevistos'] / df_resumen['total_vehiculos'] * 100)).round(1)
        df_resumen['tasa_culpa_taller'] = ((df_resumen['culpa_taller'] / df_resumen['total_vehiculos'] * 100)).round(1)
        df_resumen['tasa_no_culpa_taller'] = ((df_resumen['no_culpa_taller'] / df_resumen['total_vehiculos'] * 100)).round(1)
        df_resumen['mes_nombre'] = df_resumen.apply(
            lambda row: _format_month_year_label(row["mes"], row["año"]),
            axis=1
        )
        df_resumen = df_resumen.sort_values(['año', 'mes'])
    else:
        st.warning("No hay datos de fecha disponibles.")
        return

    if df_resumen.empty:
        with header_container:
            st.subheader("📋 Tabla Resumen Mensual")
        st.info("No hay datos para el período seleccionado.")
        return

    # Botón de exportación
    excel_data = _generar_excel_simple(df_resumen, "Resumen Mensual")
    with header_container:
        title_col, action_col = st.columns([3, 2])
        with title_col:
            st.subheader("📋 Tabla Resumen Mensual")
        with action_col:
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"resumen_imprevistos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

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


def _calcular_tasa_culpa_taller_cambio(df: pd.DataFrame, años=None, meses=None) -> pd.DataFrame:
    """
    Calcula la tasa mensual de imprevistos con cambio de repuesto que son culpa del taller.

    Reglas:
    1. Filtrar registros donde ACCION contiene "CAMBIO"
    2. No excluir registros por ESTATUS o mano de obra inicial
    3. No deduplicar placas/siniestros: cada registro válido cuenta
    4. Rate = culpa_taller / total_registros_validos * 100
       Culpa del taller: CAUSAL en {no cotizado, predesarme, digitación, sin fotos claras, sin diagnóstico}

    Parámetros opcionales:
        años: lista de años a filtrar (ej: [2024, 2025]). Si es None, incluye todos.
        meses: lista de meses a filtrar (ej: [1, 2, 3]). Si es None, incluye todos.
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

    # Aplicar filtros de período si se proporcionan
    if años is not None and len(años) > 0:
        df_cambio = df_cambio[df_cambio['_AÑO'].isin(años)].copy()
    if meses is not None and len(meses) > 0:
        df_cambio = df_cambio[df_cambio['_MES'].isin(meses)].copy()

    if df_cambio.empty:
        return pd.DataFrame()

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

    # Meses en español para el eje X
    MESES_ES = {
        1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR",
        5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO",
        9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"
    }
    resumen['mes_label'] = resumen['_MES'].map(MESES_ES)
    resumen.rename(columns={'_AÑO': 'año', '_MES': 'mes'}, inplace=True)

    return resumen


def _preparar_reporte_cambio_repuesto_mes(df: pd.DataFrame, año=None, mes=None, años=None, meses=None) -> pd.DataFrame:
    """
    Prepara el detalle descargable de imprevistos con cambio para un período.

    Parámetros:
        año: int o None. Año específico (modo legacy).
        mes: int o None. Mes específico (modo legacy).
        años: list o None. Lista de años a filtrar.
        meses: list o None. Lista de meses a filtrar.
    """
    columnas_reporte = ["PLACA", "LINEA", "CIA", "IMPREVISTO", "CAUSAL"]

    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_reporte)

    required = {"PLACA", "ACCION", "AÑO", "MES"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=columnas_reporte)

    df_w = df.copy()
    df_w["_AÑO"] = pd.to_numeric(df_w["AÑO"], errors="coerce")
    df_w["_MES"] = pd.to_numeric(df_w["MES"], errors="coerce")
    df_w["_ACCION"] = df_w["ACCION"].astype(str).str.upper().str.strip()

    mask = df_w["_ACCION"].str.contains("CAMBIO", na=False)

    # Modo legacy: año y mes individuales
    if año is not None:
        mask = mask & (df_w["_AÑO"] == int(año))
    if mes is not None:
        mask = mask & (df_w["_MES"] == int(mes))

    # Modo nuevo: listas de años y meses
    if años is not None and len(años) > 0:
        mask = mask & (df_w["_AÑO"].isin(años))
    if meses is not None and len(meses) > 0:
        mask = mask & (df_w["_MES"].isin(meses))

    df_w = df_w[mask].copy()

    if df_w.empty:
        return pd.DataFrame(columns=columnas_reporte)

    cia_col = (
        "COMPAÑIA_DE_SEGUROS"
        if "COMPAÑIA_DE_SEGUROS" in df_w.columns
        else "COMPAÑÍA_DE_SEGUROS"
        if "COMPAÑÍA_DE_SEGUROS" in df_w.columns
        else None
    )

    reporte = pd.DataFrame({
        "PLACA": df_w["PLACA"].astype(str).str.upper().str.strip(),
        "LINEA": (
            df_w["LINEA"].astype(str).str.upper().str.strip()
            if "LINEA" in df_w.columns
            else ""
        ),
        "CIA": df_w[cia_col].astype(str).str.strip().str.upper() if cia_col else "",
        "IMPREVISTO": (
            df_w["IMPREVISTO"].astype(str).str.strip().str.upper()
            if "IMPREVISTO" in df_w.columns
            else ""
        ),
        "CAUSAL": (
            df_w["CAUSAL"].astype(str).str.strip().str.upper()
            if "CAUSAL" in df_w.columns
            else ""
        ),
    })

    return reporte.sort_values(["PLACA", "CIA", "IMPREVISTO"]).reset_index(drop=True)


def _preparar_reporte_cambio_repuesto_total(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara el detalle de TODOS los imprevistos con cambio de repuestos,
    sin filtrar por mes específico.
    """
    columnas_reporte = ["PLACA", "LINEA", "CIA", "IMPREVISTO", "CAUSAL"]

    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_reporte)

    required = {"PLACA", "ACCION"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=columnas_reporte)

    df_w = df.copy()
    df_w["_ACCION"] = df_w["ACCION"].astype(str).str.upper().str.strip()

    df_w = df_w[
        df_w["_ACCION"].str.contains("CAMBIO", na=False)
    ].copy()

    if df_w.empty:
        return pd.DataFrame(columns=columnas_reporte)

    cia_col = (
        "COMPAÑIA_DE_SEGUROS"
        if "COMPAÑIA_DE_SEGUROS" in df_w.columns
        else "COMPAÑÍA_DE_SEGUROS"
        if "COMPAÑÍA_DE_SEGUROS" in df_w.columns
        else None
    )

    reporte = pd.DataFrame({
        "PLACA": df_w["PLACA"].astype(str).str.upper().str.strip(),
        "LINEA": (
            df_w["LINEA"].astype(str).str.upper().str.strip()
            if "LINEA" in df_w.columns
            else ""
        ),
        "CIA": df_w[cia_col].astype(str).str.strip().str.upper() if cia_col else "",
        "IMPREVISTO": (
            df_w["IMPREVISTO"].astype(str).str.strip().str.upper()
            if "IMPREVISTO" in df_w.columns
            else ""
        ),
        "CAUSAL": (
            df_w["CAUSAL"].astype(str).str.strip().str.upper()
            if "CAUSAL" in df_w.columns
            else ""
        ),
    })

    return reporte.sort_values(["PLACA", "CIA", "IMPREVISTO"]).reset_index(drop=True)


def render_grafico_culpa_taller_mensual(df=None):
    """
    Gráfico de línea: tasa mensual de imprevistos con cambio de repuesto (culpa del taller).
    Soporta filtros por año, trimestre y mes (incluyendo combinaciones de varios períodos).
    Estilo consistente con el resto del dashboard.
    """
    import datetime

    if df is None or df.empty:
        st.subheader("🔧 Imprevistos con Cambio de Repuesto")
        st.info("No hay datos disponibles.")
        return

    header_container = st.container()

    # --- Filtros de período reutilizables ---
    años_sel, trimestres_sel, meses_sel, meses_filtro = _render_filtros_periodo_imprevistos(
        df, key_suffix="culpa_taller"
    )

    # Calcular resumen con filtros aplicados
    resumen = _calcular_tasa_culpa_taller_cambio(
        df,
        años=años_sel if años_sel else None,
        meses=meses_filtro if meses_filtro else None
    )

    if resumen.empty:
        with header_container:
            st.subheader("🔧 Imprevistos con Cambio de Repuesto")
        st.info("No se encontraron imprevistos con ACCION=CAMBIO para el período seleccionado.")
        return

    # Preparar reporte descargable con los mismos filtros
    reporte = _preparar_reporte_cambio_repuesto_mes(
        df,
        años=años_sel if años_sel else None,
        meses=meses_filtro if meses_filtro else None
    )
    csv_reporte = reporte.to_csv(index=False).encode("utf-8-sig")

    # Construir nombre de archivo según el período
    if len(años_sel) == 1:
        if len(meses_filtro) == 1:
            file_name = f"imprevistos_cambio_repuesto_{años_sel[0]}_{meses_filtro[0]:02d}.csv"
        else:
            meses_str = "-".join(f"{m:02d}" for m in sorted(meses_filtro))
            file_name = f"imprevistos_cambio_repuesto_{años_sel[0]}_meses_{meses_str}.csv"
    else:
        años_str = "-".join(str(a) for a in sorted(años_sel))
        meses_str = "-".join(f"{m:02d}" for m in sorted(meses_filtro))
        file_name = f"imprevistos_cambio_repuesto_años_{años_str}_meses_{meses_str}.csv"

    with header_container:
        title_col, action_col = st.columns([3, 2])
        with title_col:
            st.subheader("🔧 Imprevistos con Cambio de Repuesto")
        with action_col:
            st.download_button(
                label="📥 Descargar reporte",
                data=csv_reporte,
                file_name=file_name,
                mime="text/csv",
                disabled=reporte.empty,
                help="Descarga PLACA, CIA, IMPREVISTO y CAUSAL para el período seleccionado.",
                use_container_width=True,
            )

    # Paleta de colores para múltiples años
    AÑO_COLORES = [
        BrandColors.PRIMARY,
        BrandColors.ACCENT,
        BrandColors.SECONDARY,
        BrandColors.TEAL,
        BrandColors.INDIGO,
        BrandColors.CYAN_LIGHT,
    ]

    # Orden cronológico del eje X basado en los meses presentes
    orden_meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
                   "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    meses_presentes = resumen[['mes', 'mes_label']].drop_duplicates().sort_values('mes')
    category_array = meses_presentes['mes_label'].tolist()
    # Asegurar que estén en orden cronológico según el mapeo estándar
    category_array = [m for m in orden_meses if m in category_array]

    fig = go.Figure()

    años_unicos = sorted(resumen['año'].unique().tolist())
    mostrar_leyenda = len(años_unicos) > 1

    for idx, año in enumerate(años_unicos):
        df_año = resumen[resumen['año'] == año].copy()
        color = AÑO_COLORES[idx % len(AÑO_COLORES)]

        fig.add_trace(go.Scatter(
            x=df_año['mes_label'],
            y=df_año['culpa_taller'],
            mode='lines+markers+text',
            line=dict(color=color, width=3),
            marker=dict(size=10, color=color, line=dict(width=2, color='white')),
            text=df_año['culpa_taller'].astype(int).astype(str),
            textposition='top center',
            textfont=dict(size=12, color=color),
            hovertemplate=f'Año {año} - %{{x}}: %{{y}} imprevistos<extra></extra>',
            name=str(año)
        ))

    fig.update_layout(
        **get_plotly_theme(
            title='🔧 Imprevistos con Cambio de Repuesto',
            height=ChartHeights.MEDIUM,
            show_legend=mostrar_leyenda
        )
    )
    fig.update_xaxes(
        title_text='Mes',
        categoryorder='array',
        categoryarray=category_array
    )
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

def _filtrar_demora_definicion_por_periodo_y_cia(
    df: pd.DataFrame,
    cia: str = "Todas",
    año: int = None,
    trimestre: str = "Todos",
    mes: int = None,
) -> pd.DataFrame:
    """Filtra los datos de demora por CIA, año, trimestre y mes."""
    if df is None or df.empty:
        return pd.DataFrame(columns=df.columns if df is not None else None)

    df_w = df.copy()

    if cia and cia not in ("Todas", "Todos"):
        if "COMPAÑIA_DE_SEGUROS" in df_w.columns:
            df_w = df_w[df_w["COMPAÑIA_DE_SEGUROS"] == cia].copy()

    if año is not None and "AÑO" in df_w.columns:
        df_w["_AÑO_FILTRO"] = pd.to_numeric(df_w["AÑO"], errors="coerce")
        df_w = df_w[df_w["_AÑO_FILTRO"] == int(año)].copy()

    if trimestre and trimestre != "Todos" and "MES" in df_w.columns:
        trimestre_map = {
            "Q1": (1, 3),
            "Q2": (4, 6),
            "Q3": (7, 9),
            "Q4": (10, 12),
        }
        if trimestre in trimestre_map:
            mes_inicio, mes_fin = trimestre_map[trimestre]
            df_w["_MES_FILTRO"] = pd.to_numeric(df_w["MES"], errors="coerce")
            df_w = df_w[
                (df_w["_MES_FILTRO"] >= mes_inicio)
                & (df_w["_MES_FILTRO"] <= mes_fin)
            ].copy()

    if mes not in (None, "Todos") and "MES" in df_w.columns:
        df_w["_MES_FILTRO"] = pd.to_numeric(df_w["MES"], errors="coerce")
        df_w = df_w[df_w["_MES_FILTRO"] == int(mes)].copy()

    return df_w.drop(columns=["_AÑO_FILTRO", "_MES_FILTRO"], errors="ignore")


def _preparar_datos_demora_definicion(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza, valida y deduplica registros para demora en definición."""
    columnas = [
        "PLACA", "SINIESTRO", "COMPAÑIA_DE_SEGUROS", "ESTATUS",
        "FECHA_INGR", "FECHA_AUTO", "IMPREVISTO", "ACCION", "CAUSAL",
        "_DEMORA_DIAS",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=columnas)

    required_cols = {"FECHA_INGR", "FECHA_AUTO", "COMPAÑIA_DE_SEGUROS", "ESTATUS", "PLACA"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame(columns=columnas)

    df_w = df.copy()
    df_w["_PLACA"] = df_w["PLACA"].astype(str).str.upper().str.strip()
    df_w["_SINIESTRO"] = (
        df_w["SINIESTRO"].astype(str).str.upper().str.strip()
        if "SINIESTRO" in df_w.columns
        else ""
    )

    df_w["FECHA_INGR"] = parse_source_date_column(df_w["FECHA_INGR"], "FECHA_INGR")
    df_w["FECHA_AUTO"] = parse_source_date_column(df_w["FECHA_AUTO"], "FECHA_AUTO")
    df_w = df_w[df_w["FECHA_INGR"].notna() & df_w["FECHA_AUTO"].notna()].copy()

    if df_w.empty:
        return pd.DataFrame(columns=columnas)

    año_limite = datetime.now().year + 1
    df_w = df_w[
        (df_w["FECHA_INGR"].dt.year >= 2000)
        & (df_w["FECHA_INGR"].dt.year <= año_limite)
        & (df_w["FECHA_AUTO"].dt.year >= 2000)
        & (df_w["FECHA_AUTO"].dt.year <= año_limite)
    ].copy()

    if df_w.empty:
        return pd.DataFrame(columns=columnas)

    df_w["_DEMORA_DIAS"] = (df_w["FECHA_AUTO"] - df_w["FECHA_INGR"]).dt.days
    df_w["ESTATUS"] = df_w["ESTATUS"].astype(str).str.upper().str.strip()
    df_w = df_w[df_w["ESTATUS"].isin(["AUTORIZADO", "RECHAZADO"])].copy()
    df_w = df_w.drop_duplicates(subset=["_PLACA", "_SINIESTRO"], keep="first")

    return df_w


def _preparar_reporte_demora_definicion(df: pd.DataFrame, periodo_label: str):
    """Construye resumen y detalle para el reporte descargable de demora."""
    resumen_cols = ["PERIODO", "CIA", "ESTATUS", "PROMEDIO_DEMORA_DIAS", "CONTEO"]
    detalle_cols = [
        "PERIODO", "PLACA", "SINIESTRO", "CIA", "ESTATUS",
        "FECHA_INGR", "FECHA_AUTO", "DEMORA_DIAS", "IMPREVISTO",
        "ACCION", "CAUSAL",
    ]

    df_w = _preparar_datos_demora_definicion(df)
    if df_w.empty:
        return pd.DataFrame(columns=resumen_cols), pd.DataFrame(columns=detalle_cols)

    resumen = (
        df_w.groupby(["COMPAÑIA_DE_SEGUROS", "ESTATUS"])
        .agg(
            PROMEDIO_DEMORA_DIAS=("_DEMORA_DIAS", "mean"),
            CONTEO=("_DEMORA_DIAS", "count"),
        )
        .reset_index()
        .rename(columns={"COMPAÑIA_DE_SEGUROS": "CIA"})
    )
    resumen["PROMEDIO_DEMORA_DIAS"] = resumen["PROMEDIO_DEMORA_DIAS"].round(1)
    resumen.insert(0, "PERIODO", periodo_label)
    resumen = resumen[resumen_cols].sort_values(["CIA", "ESTATUS"]).reset_index(drop=True)

    detalle = pd.DataFrame({
        "PERIODO": periodo_label,
        "PLACA": df_w["_PLACA"],
        "SINIESTRO": df_w["_SINIESTRO"],
        "CIA": df_w["COMPAÑIA_DE_SEGUROS"].astype(str).str.strip(),
        "ESTATUS": df_w["ESTATUS"],
        "FECHA_INGR": df_w["FECHA_INGR"].dt.strftime("%Y-%m-%d"),
        "FECHA_AUTO": df_w["FECHA_AUTO"].dt.strftime("%Y-%m-%d"),
        "DEMORA_DIAS": df_w["_DEMORA_DIAS"].astype(int),
        "IMPREVISTO": (
            df_w["IMPREVISTO"].astype(str).str.strip()
            if "IMPREVISTO" in df_w.columns
            else ""
        ),
        "ACCION": (
            df_w["ACCION"].astype(str).str.strip()
            if "ACCION" in df_w.columns
            else ""
        ),
        "CAUSAL": (
            df_w["CAUSAL"].astype(str).str.strip()
            if "CAUSAL" in df_w.columns
            else ""
        ),
    })
    detalle = detalle[detalle_cols].sort_values(["CIA", "ESTATUS", "DEMORA_DIAS"], ascending=[True, True, False])
    detalle = detalle.reset_index(drop=True)

    return resumen, detalle


def _generar_excel_reporte_demora_definicion(resumen: pd.DataFrame, detalle: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="RESUMEN", index=False)
        detalle.to_excel(writer, sheet_name="DETALLE", index=False)
    return output.getvalue()


def _periodo_label_demora(año, trimestre, mes, cia):
    partes = []
    if cia and cia not in ("Todas", "Todos"):
        partes.append(f"CIA {cia}")
    else:
        partes.append("Todas las CIA")
    if año is not None:
        partes.append(f"Año {int(año)}")
    if trimestre and trimestre != "Todos":
        partes.append(str(trimestre))
    if mes not in (None, "Todos"):
        partes.append(f"Mes {int(mes):02d}")
    return " - ".join(partes)


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

    if df is None or df.empty:
        st.subheader("⏱️ Demora en Definición del Imprevisto")
        st.info("No hay datos disponibles para mostrar.")
        return

    required_cols = {'FECHA_INGR', 'FECHA_AUTO', 'COMPAÑIA_DE_SEGUROS', 'ESTATUS', 'PLACA'}
    if not required_cols.issubset(df.columns):
        st.subheader("⏱️ Demora en Definición del Imprevisto")
        faltantes = required_cols - set(df.columns)
        st.warning(f"Faltan columnas necesarias: {', '.join(faltantes)}")
        return

    df_filtros = df.copy()
    df_periodos = df_filtros.copy()
    if "AÑO" in df_periodos.columns:
        df_periodos["_AÑO_FILTRO"] = pd.to_numeric(df_periodos["AÑO"], errors="coerce")
    if "MES" in df_periodos.columns:
        df_periodos["_MES_FILTRO"] = pd.to_numeric(df_periodos["MES"], errors="coerce")

    title_col, action_col = st.columns([3, 2])
    with title_col:
        st.subheader("⏱️ Demora en Definición del Imprevisto")

    filtro_cols = st.columns(4)

    cias = sorted(df_filtros["COMPAÑIA_DE_SEGUROS"].dropna().astype(str).str.strip().unique().tolist())
    cias = [cia_item for cia_item in cias if cia_item]
    with filtro_cols[0]:
        cia_sel = st.selectbox(
            "CIA",
            options=["Todas"] + cias,
            key="demora_definicion_cia",
        )

    if "AÑO" in df_periodos.columns:
        años_disponibles = sorted(
            df_periodos["_AÑO_FILTRO"].dropna().astype(int).unique().tolist(),
            reverse=True,
        )
        if años_disponibles:
            año_actual = datetime.datetime.now().year
            default_año = año if año in años_disponibles else año_actual if año_actual in años_disponibles else años_disponibles[0]
            with filtro_cols[1]:
                año_sel = st.selectbox(
                    "Año",
                    options=años_disponibles,
                    index=años_disponibles.index(default_año),
                    key="demora_definicion_año",
                )
        else:
            año_sel = año
            with filtro_cols[1]:
                st.caption("Año no disponible")
    else:
        año_sel = año
        with filtro_cols[1]:
            st.caption("Año no disponible")

    with filtro_cols[2]:
        trimestre_sel = st.selectbox(
            "Trimestre",
            options=["Todos", "Q1", "Q2", "Q3", "Q4"],
            help="Q1: Ene-Mar | Q2: Abr-Jun | Q3: Jul-Sep | Q4: Oct-Dic",
            key="demora_definicion_trimestre",
        )

    meses_disponibles = []
    if "MES" in df_periodos.columns:
        meses_disponibles = sorted(
            df_periodos["_MES_FILTRO"]
            .dropna()
            .astype(int)
            .loc[lambda series: (series >= 1) & (series <= 12)]
            .unique()
            .tolist()
        )
    with filtro_cols[3]:
        mes_sel = st.selectbox(
            "Mes",
            options=["Todos"] + meses_disponibles,
            format_func=lambda value: "Todos" if value == "Todos" else datetime.datetime(2000, int(value), 1).strftime("%B"),
            key="demora_definicion_mes",
        )

    df_w = _filtrar_demora_definicion_por_periodo_y_cia(
        df,
        cia=cia_sel,
        año=año_sel,
        trimestre=trimestre_sel,
        mes=mes_sel,
    )

    periodo_label = _periodo_label_demora(año_sel, trimestre_sel, mes_sel, cia_sel)
    resumen_reporte, detalle_reporte = _preparar_reporte_demora_definicion(df_w, periodo_label)
    excel_reporte = _generar_excel_reporte_demora_definicion(resumen_reporte, detalle_reporte)
    filename_cia = "todas" if cia_sel == "Todas" else str(cia_sel).lower().replace(" ", "_")
    filename_año = str(año_sel) if año_sel is not None else "todos"
    filename_mes = "todos" if mes_sel == "Todos" else f"{int(mes_sel):02d}"

    with action_col:
        st.download_button(
            label="📥 Descargar reporte",
            data=excel_reporte,
            file_name=f"demora_definicion_imprevisto_{filename_cia}_{filename_año}_{trimestre_sel}_{filename_mes}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=resumen_reporte.empty and detalle_reporte.empty,
            help="Descarga el resumen por CIA/Estatus y el detalle filtrado visible.",
            use_container_width=True,
        )

    if df_w.empty:
        st.info(f"No hay datos para los filtros seleccionados: {periodo_label}.")
        return

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

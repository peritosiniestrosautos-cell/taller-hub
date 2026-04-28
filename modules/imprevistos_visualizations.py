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
from plotly.subplots import make_subplots
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
    RF-NEW: Gráfico combinado de barras + línea para tasa de imprevistos.
    
    - Barras: Cantidad de vehículos y cantidad de imprevistos
    - Línea: Tasa de imprevistos (%)
    
    Similar to the reference image provided.
    """
    
    st.subheader("📊 Tasa de Imprevistos Mensual")
    
    # Extract imprevistos from DataFrame
    if df is None or df.empty:
        st.info("No hay datos disponibles para mostrar.")
        return
    
    from .imprevistos_processor import extraer_imprevistos_from_dataframe
    
    df_imprevistos = extraer_imprevistos_from_dataframe(df)
    
    if df_imprevistos.empty:
        st.info("No se encontraron registros de imprevistos en los datos actuales.")
        st.caption("💡 Los imprevistos se detectan cuando ACCION='CAMBIO' o IMPREVISTO no está vacío")
        return
    
    # Get total vehicles per month
    df_all = df.copy()
    if 'AÑO' in df_all.columns and 'MES' in df_all.columns:
        df_all['año'] = pd.to_numeric(df_all['AÑO'], errors='coerce')
        df_all['mes'] = pd.to_numeric(df_all['MES'], errors='coerce')
        
        # Filter by año if specified
        if año:
            df_all = df_all[df_all['año'] == año]
            df_imprevistos = df_imprevistos[df_imprevistos['año'] == año]
        
        # Monthly imprevistos count (deduplicated by placa+siniestro)
        df_imp_mes = resumir_imprevistos_mensuales(df=df, año=año)
        
        # ----------------------------------------------------------------
        # TOTAL VEHÍCULOS: desde hoja "TASA DE IMPREVISTOS" del sheets
        # ----------------------------------------------------------------
        df_tasa_sheets = st.session_state.get("tasa_imprevistos_data")
        if df_tasa_sheets is not None and not df_tasa_sheets.empty:
            df_tasa_filtered = df_tasa_sheets.copy()
            if año:
                df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['AÑO'] == año]
            
            # Sumar totales por año+mes (across all talleres)
            df_vehiculos = df_tasa_filtered.groupby(['AÑO', 'MES']).agg(
                total_vehiculos=('TOTAL', 'sum')
            ).reset_index()
            df_vehiculos = df_vehiculos.rename(columns={'AÑO': 'año', 'MES': 'mes'})
            
            # Asegurar tipos numéricos consistentes
            df_vehiculos['año'] = df_vehiculos['año'].astype(int)
            df_vehiculos['mes'] = df_vehiculos['mes'].astype(int)
        else:
            st.warning("⚠️ No se encontraron datos de la hoja 'TASA DE IMPREVISTOS'. Usando conteo del DataFrame como fallback.")
            df_vehiculos = df_all.groupby(['año', 'mes']).agg(
                total_vehiculos=('PLACA', 'count')
            ).reset_index()
            df_vehiculos['año'] = df_vehiculos['año'].astype(int)
            df_vehiculos['mes'] = df_vehiculos['mes'].astype(int)
        
        # Merge vehículos + imprevistos (outer para no perder meses)
        df_resumen = df_vehiculos.merge(df_imp_mes, on=['año', 'mes'], how='outer')
        df_resumen['total_vehiculos'] = df_resumen['total_vehiculos'].fillna(0).astype(int)
        df_resumen['total_imprevistos'] = df_resumen['total_imprevistos'].fillna(0).astype(int)
        df_resumen['culpa_taller'] = df_resumen['culpa_taller'].fillna(0).astype(int)
        df_resumen['no_culpa_taller'] = df_resumen['total_imprevistos'] - df_resumen['culpa_taller']
        
        # Calcular tasas (evitar división por cero)
        df_resumen['tasa'] = df_resumen.apply(
            lambda r: (r['total_imprevistos'] / r['total_vehiculos'] * 100) if r['total_vehiculos'] > 0 else 0,
            axis=1
        ).round(1)
        
        df_resumen['tasa_culpa_taller'] = df_resumen.apply(
            lambda r: (r['culpa_taller'] / r['total_vehiculos'] * 100) if r['total_vehiculos'] > 0 else 0,
            axis=1
        ).round(1)
        
        df_resumen['tasa_no_culpa_taller'] = df_resumen.apply(
            lambda r: (r['no_culpa_taller'] / r['total_vehiculos'] * 100) if r['total_vehiculos'] > 0 else 0,
            axis=1
        ).round(1)
        
        # Create month labels usando el año real
        df_resumen["mes_nombre"] = df_resumen.apply(
            lambda row: datetime(int(row["año"]), int(row["mes"]), 1).strftime('%b %Y'),
            axis=1
        )
        
        # Sort by month
        df_resumen = df_resumen.sort_values(['año', 'mes'])
    else:
        st.warning("No se encontraron columnas de fecha (AÑO/MES) en los datos.")
        return
    
    if df_resumen.empty:
        st.info("No hay datos para el período seleccionado.")
        return
    
    # =========================================================================
    # DEBUG PANEL
    # =========================================================================
    with st.expander("🐛 Debug - Datos de Tasa de Imprevistos", expanded=False):
        st.markdown("**1. Datos de la hoja 'TASA DE IMPREVISTOS' (session_state):**")
        df_tasa_debug = st.session_state.get("tasa_imprevistos_data")
        if df_tasa_debug is not None and not df_tasa_debug.empty:
            st.dataframe(df_tasa_debug, hide_index=True)
        else:
            st.caption("No hay datos en session_state['tasa_imprevistos_data']")
        
        st.markdown("**2. Imprevistos extraídos del DataFrame (por mes):**")
        if df_imp_mes is not None and not df_imp_mes.empty:
            st.dataframe(df_imp_mes, hide_index=True)
        else:
            st.caption("No se extrajeron imprevistos")
        
        st.markdown("**3. Total de vehículos (de la hoja TASA DE IMPREVISTOS):**")
        if df_vehiculos is not None and not df_vehiculos.empty:
            st.dataframe(df_vehiculos, hide_index=True)
        else:
            st.caption("No hay datos de vehículos")
        
        st.markdown("**4. DataFrame resumen final (merge + tasas):**")
        st.dataframe(df_resumen[['año', 'mes', 'mes_nombre', 'total_vehiculos', 'total_imprevistos', 'culpa_taller', 'tasa']], hide_index=True)
    
    # Create the combined chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bars for vehicles
    fig.add_trace(
        go.Bar(
            x=df_resumen["mes_nombre"],
            y=df_resumen["total_vehiculos"],
            name="Cantidad Vehículos",
            marker_color="#0066CC",
            opacity=0.6,
            offsetgroup=0
        ),
        secondary_y=False
    )
    
    # Add bars for imprevistos
    fig.add_trace(
        go.Bar(
            x=df_resumen["mes_nombre"],
            y=df_resumen["total_imprevistos"],
            name="Cantidad Imprevistos",
            marker_color="#F59E0B",
            opacity=0.7,
            offsetgroup=1
        ),
        secondary_y=False
    )
    
    # Add line for rate (%)
    fig.add_trace(
        go.Scatter(
            x=df_resumen["mes_nombre"],
            y=df_resumen["tasa"],
            mode='lines+markers',
            name='Tasa de Imprevistos (%)',
            line=dict(color='#DC2626', width=3),
            marker=dict(size=8, color='#DC2626', line=dict(width=2, color='white'))
        ),
        secondary_y=True
    )
    
    # Update layout
    fig.update_layout(
        title='📊 Tasa de Imprevistos - Vehículos vs Imprevistos vs Tasa',
        height=450,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        bargap=0.15,
        bargroupgap=0.1
    )
    
    # Update axes
    fig.update_xaxes(title_text="Mes")
    
    fig.update_yaxes(
        title_text="Cantidad",
        secondary_y=False
    )
    
    fig.update_yaxes(
        title_text="Tasa (%)",
        secondary_y=True,
        ticksuffix="%"
    )
    
    # Add annotations for the rate values
    for i, row in df_resumen.iterrows():
        fig.add_annotation(
            x=row["mes_nombre"],
            y=row["tasa"],
            text=f"{row['tasa']:.1f}%",
            showarrow=False,
            yshift=10,
            font=dict(size=10, color="#DC2626")
        )
    
    st.plotly_chart(fig, width="stretch", use_container_width=True)
    
    # Show summary metrics
    total_veh = df_resumen["total_vehiculos"].sum()
    total_imp = df_resumen["total_imprevistos"].sum()
    tasa_prom = df_resumen["tasa"].mean()
    culpa_total = df_resumen["culpa_taller"].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🚗 Total Vehículos", f"{total_veh:,}")
    with col2:
        st.metric("⚠️ Total Imprevistos", f"{total_imp:,}")
    with col3:
        st.metric("📊 Tasa Promedio", f"{tasa_prom:.1f}%")
    with col4:
        st.metric("🏪 Culpa del Taller", f"{int(culpa_total):,}")


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
    colors = ['#DC2626', '#10B981']
    
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
        marker_color=['#0066CC', '#F59E0B'][:len(df_stats)],
        text=df_stats["cantidad"],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Cantidad de Imprevistos por Tipo',
        xaxis_title='Tipo',
        yaxis_title='Cantidad',
        height=350
    )
    
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
        marker_color='#F59E0B',
        text=df_stats["cantidad"],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Cantidad de Imprevistos por Causal',
        xaxis_title='Cantidad',
        yaxis_title='Causal',
        height=max(350, len(df_stats) * 40),
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
    Estilo similar a la imagen de referencia del cliente.
    """
    import datetime
    st.subheader("IMPREVISTOS CON CAMBIO DE REPUESTO")

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
        line=dict(color='#B8D835', width=3),
        marker=dict(size=10, color='#4472C4', line=dict(width=2, color='white')),
        text=resumen['culpa_taller'].astype(int).astype(str),
        textposition='top center',
        textfont=dict(size=12, color='white'),
        hovertemplate='%{x}: %{y} imprevistos<extra></extra>',
        name='Culpa del Taller'
    ))

    fig.update_layout(
        paper_bgcolor='#3D8B8B',
        plot_bgcolor='#3D8B8B',
        font=dict(color='white', family='Arial Black'),
        title=dict(
            text='IMPREVISTOS CON CAMBIO DE REPUESTO',
            font=dict(size=18, color='white'),
            x=0.02
        ),
        xaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=13, color='white'),
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            visible=False,
        ),
        height=380,
        margin=dict(l=30, r=30, t=70, b=40),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Métricas resumidas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total imprevistos cambio", int(resumen['total'].sum()))
    with col2:
        st.metric("Culpa del taller", int(resumen['culpa_taller'].sum()))


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

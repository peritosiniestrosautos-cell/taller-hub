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
from io import BytesIO
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

def _filtrar_df_causales_por_periodo(df, tipo_periodo, periodos):
    """Filtra el DataFrame por Mes, Trimestre o Año usando columnas AÑO/MES.

    periodos puede ser un solo valor o una lista de valores.
    """
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns:
        return pd.DataFrame(columns=df.columns if df is not None else None)

    # Normalizar a lista
    if periodos is None:
        periodos = []
    if not isinstance(periodos, list):
        periodos = [periodos]
    if not periodos:
        return df.copy()

    df_periodo = df.copy()
    df_periodo['_AÑO'] = pd.to_numeric(df_periodo['AÑO'], errors='coerce')
    df_periodo['_MES'] = pd.to_numeric(df_periodo['MES'], errors='coerce')
    df_periodo = df_periodo[
        df_periodo['_AÑO'].notna()
        & df_periodo['_MES'].notna()
        & (df_periodo['_AÑO'] > 2000)
        & (df_periodo['_MES'] >= 1)
        & (df_periodo['_MES'] <= 12)
    ].copy()

    if df_periodo.empty:
        return df_periodo.drop(columns=['_AÑO', '_MES'], errors='ignore')

    df_periodo['_AÑO'] = df_periodo['_AÑO'].astype(int)
    df_periodo['_MES'] = df_periodo['_MES'].astype(int)

    masks = []
    for periodo in periodos:
        if tipo_periodo == "Mes":
            try:
                anio, mes = str(periodo).split("-")
                masks.append(
                    (df_periodo['_AÑO'] == int(anio)) & (df_periodo['_MES'] == int(mes))
                )
            except ValueError:
                masks.append(pd.Series(False, index=df_periodo.index))
        elif tipo_periodo == "Trimestre":
            try:
                anio, trimestre = str(periodo).split("-T")
                trimestre = int(trimestre)
                mes_inicio = (trimestre - 1) * 3 + 1
                meses = {mes_inicio, mes_inicio + 1, mes_inicio + 2}
                masks.append(
                    (df_periodo['_AÑO'] == int(anio)) & (df_periodo['_MES'].isin(meses))
                )
            except ValueError:
                masks.append(pd.Series(False, index=df_periodo.index))
        elif tipo_periodo == "Año":
            masks.append(df_periodo['_AÑO'] == int(periodo))
        else:
            masks.append(pd.Series(True, index=df_periodo.index))

    if masks:
        mask = masks[0]
        for m in masks[1:]:
            mask = mask | m
    else:
        mask = pd.Series(True, index=df_periodo.index)

    return df_periodo[mask].drop(columns=['_AÑO', '_MES'], errors='ignore').copy()


def _preparar_reporte_top_causales_ahorro(df, periodo_label):
    """Construye las hojas de resumen y detalle para el reporte de causales."""
    resumen_cols = ["PERIODO", "CAUSAL", "RECUPERACION", "PORCENTAJE_EQUIVALENTE", "VEHICULOS"]
    detalle_cols = [
        "PERIODO", "PLACA", "CIA", "IMPREVISTO", "ACCION",
        "CAUSAL", "DIFERENCIA", "ESTATUS",
    ]

    if df is None or df.empty or 'CAUSAL' not in df.columns:
        return pd.DataFrame(columns=resumen_cols), pd.DataFrame(columns=detalle_cols)

    df_w = df[df['CAUSAL'].notna() & (df['CAUSAL'].astype(str).str.strip() != '')].copy()
    if df_w.empty:
        return pd.DataFrame(columns=resumen_cols), pd.DataFrame(columns=detalle_cols)

    df_w['DIFERENCIA'] = pd.to_numeric(df_w.get('DIFERENCIA', 0), errors='coerce').fillna(0)
    df_w['_CAUSAL'] = df_w['CAUSAL'].astype(str).str.strip()
    df_w['_PLACA'] = (
        df_w['PLACA'].astype(str).str.upper().str.strip()
        if 'PLACA' in df_w.columns
        else ''
    )

    resumen = (
        df_w.groupby('_CAUSAL')
        .agg(
            RECUPERACION=('DIFERENCIA', 'sum'),
            VEHICULOS=('_PLACA', 'nunique'),
        )
        .reset_index()
        .rename(columns={'_CAUSAL': 'CAUSAL'})
    )
    total_recuperacion = resumen['RECUPERACION'].sum()
    resumen['PORCENTAJE_EQUIVALENTE'] = (
        (resumen['RECUPERACION'] / total_recuperacion * 100).round(2)
        if total_recuperacion else 0
    )
    resumen.insert(0, "PERIODO", periodo_label)
    resumen = resumen[resumen_cols].sort_values('RECUPERACION', ascending=False).reset_index(drop=True)

    cia_col = (
        'COMPAÑIA_DE_SEGUROS'
        if 'COMPAÑIA_DE_SEGUROS' in df_w.columns
        else 'COMPAÑÍA_DE_SEGUROS'
        if 'COMPAÑÍA_DE_SEGUROS' in df_w.columns
        else None
    )

    detalle = pd.DataFrame({
        "PERIODO": periodo_label,
        "PLACA": df_w['_PLACA'],
        "CIA": df_w[cia_col].astype(str).str.strip() if cia_col else "",
        "IMPREVISTO": (
            df_w['IMPREVISTO'].astype(str).str.strip()
            if 'IMPREVISTO' in df_w.columns
            else ""
        ),
        "ACCION": (
            df_w['ACCION'].astype(str).str.strip()
            if 'ACCION' in df_w.columns
            else ""
        ),
        "CAUSAL": df_w['_CAUSAL'],
        "DIFERENCIA": df_w['DIFERENCIA'],
        "ESTATUS": (
            df_w['ESTATUS'].astype(str).str.strip()
            if 'ESTATUS' in df_w.columns
            else ""
        ),
    })
    detalle = detalle[detalle_cols].sort_values('DIFERENCIA', ascending=False).reset_index(drop=True)

    return resumen, detalle


def _generar_excel_reporte_top_causales(resumen, detalle):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        resumen.to_excel(writer, sheet_name='RESUMEN POR CAUSAL', index=False)
        detalle.to_excel(writer, sheet_name='DETALLE', index=False)
    return output.getvalue()


def _period_label_from_key(tipo_periodo, periodos):
    """Genera una etiqueta legible para uno o varios periodos."""
    if periodos is None:
        return "Todos los periodos"
    if not isinstance(periodos, list):
        periodos = [periodos]
    if not periodos:
        return "Todos los periodos"

    labels = []
    for periodo in periodos:
        if tipo_periodo == "Mes":
            anio, mes = str(periodo).split("-")
            labels.append(f"Mes {int(mes):02d}/{int(anio)}")
        elif tipo_periodo == "Trimestre":
            anio, trimestre = str(periodo).split("-T")
            labels.append(f"Trimestre T{trimestre}/{anio}")
        elif tipo_periodo == "Año":
            labels.append(f"Año {periodo}")
        else:
            labels.append(str(periodo))

    if len(labels) == 1:
        return labels[0]
    if len(labels) <= 3:
        return ", ".join(labels)
    return f"{labels[0]}, {labels[1]} y {len(labels) - 2} más"


def render_grafico_causales(df):
    """
    RF-003.5: Gráfico de causales de cambio (barras horizontales)
    """
    if 'CAUSAL' not in df.columns:
        st.warning("No se encontró columna de CAUSAL")
        return

    if 'DIFERENCIA' not in df.columns:
        st.warning("No se encontró columna de DIFERENCIA/AHORRO")
        return

    if 'AÑO' not in df.columns or 'MES' not in df.columns:
        st.warning("No se encontraron columnas AÑO/MES para filtrar causales por periodo.")
        return

    df_periodos = df.copy()
    df_periodos['_AÑO'] = pd.to_numeric(df_periodos['AÑO'], errors='coerce')
    df_periodos['_MES'] = pd.to_numeric(df_periodos['MES'], errors='coerce')
    df_periodos = df_periodos[
        df_periodos['_AÑO'].notna()
        & df_periodos['_MES'].notna()
        & (df_periodos['_AÑO'] > 2000)
        & (df_periodos['_MES'] >= 1)
        & (df_periodos['_MES'] <= 12)
    ].copy()

    if df_periodos.empty:
        st.info("No hay periodos válidos para mostrar causales.")
        return

    df_periodos['_AÑO'] = df_periodos['_AÑO'].astype(int)
    df_periodos['_MES'] = df_periodos['_MES'].astype(int)
    df_periodos['_TRIMESTRE'] = ((df_periodos['_MES'] - 1) // 3 + 1).astype(int)

    filtro_col1, filtro_col2 = st.columns([1, 2])
    with filtro_col1:
        tipo_periodo = st.selectbox(
            "Periodo",
            options=["Mes", "Trimestre", "Año"],
            key="top_causales_tipo_periodo",
        )

    if tipo_periodo == "Mes":
        opciones = (
            df_periodos[['_AÑO', '_MES']]
            .drop_duplicates()
            .sort_values(['_AÑO', '_MES'], ascending=[False, False])
        )
        period_options = [
            f"{row['_AÑO']}-{row['_MES']:02d}"
            for _, row in opciones.iterrows()
        ]
        format_func = lambda value: _period_label_from_key("Mes", value)
    elif tipo_periodo == "Trimestre":
        opciones = (
            df_periodos[['_AÑO', '_TRIMESTRE']]
            .drop_duplicates()
            .sort_values(['_AÑO', '_TRIMESTRE'], ascending=[False, False])
        )
        period_options = [
            f"{row['_AÑO']}-T{row['_TRIMESTRE']}"
            for _, row in opciones.iterrows()
        ]
        format_func = lambda value: _period_label_from_key("Trimestre", value)
    else:
        period_options = [str(anio) for anio in sorted(df_periodos['_AÑO'].unique(), reverse=True)]
        format_func = lambda value: _period_label_from_key("Año", value)

    with filtro_col2:
        periodo_sel = st.multiselect(
            "Seleccionar periodo",
            options=period_options,
            default=period_options[:1] if period_options else [],
            format_func=format_func,
            key=f"top_causales_periodo_{tipo_periodo}",
        )

    df_filtrado_periodo = _filtrar_df_causales_por_periodo(df, tipo_periodo, periodo_sel)
    periodo_label = _period_label_from_key(tipo_periodo, periodo_sel)

    # Filtros adicionales: Causal y Acción
    # Se cargan desde el DataFrame completo para mostrar TODAS las del documento
    filtro_causal_col, filtro_accion_col = st.columns(2)
    with filtro_causal_col:
        causales_disp = sorted(
            df['CAUSAL']
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )
        causales_disp = [c for c in causales_disp if c != '']
        causales_sel = st.multiselect(
            "Causal",
            options=causales_disp,
            default=[],
            key="top_causales_causal",
        )
    with filtro_accion_col:
        acciones_disp = sorted(
            df['ACCION']
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        ) if 'ACCION' in df.columns else []
        acciones_disp = [a for a in acciones_disp if a != '']
        acciones_sel = st.multiselect(
            "Acción",
            options=acciones_disp,
            default=[],
            key="top_causales_accion",
        )

    if causales_sel:
        df_filtrado_periodo = df_filtrado_periodo[
            df_filtrado_periodo['CAUSAL'].isin(causales_sel)
        ]
    if acciones_sel and 'ACCION' in df_filtrado_periodo.columns:
        df_filtrado_periodo = df_filtrado_periodo[
            df_filtrado_periodo['ACCION'].isin(acciones_sel)
        ]

    resumen_reporte, detalle_reporte = _preparar_reporte_top_causales_ahorro(
        df_filtrado_periodo,
        periodo_label,
    )
    excel_reporte = _generar_excel_reporte_top_causales(resumen_reporte, detalle_reporte)

    # Construir nombre de archivo seguro para múltiples periodos
    if isinstance(periodo_sel, list) and len(periodo_sel) > 0:
        archivo_periodo = "_".join(str(p) for p in periodo_sel)
        if len(archivo_periodo) > 50:
            archivo_periodo = f"{periodo_sel[0]}_y_{len(periodo_sel)-1}_mas"
    else:
        archivo_periodo = str(periodo_sel) if periodo_sel else "todos"

    title_col, action_col = st.columns([3, 2])
    with title_col:
        st.subheader("📊 Top Causales de Cambio por Valor de Ahorro")
    with action_col:
        st.download_button(
            label="📥 Descargar reporte",
            data=excel_reporte,
            file_name=f"top_causales_ahorro_{archivo_periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=resumen_reporte.empty and detalle_reporte.empty,
            help="Incluye hojas RESUMEN POR CAUSAL y DETALLE para el periodo seleccionado.",
            use_container_width=True,
        )

    df_causal = df_filtrado_periodo[
        df_filtrado_periodo['CAUSAL'].notna()
        & (df_filtrado_periodo['CAUSAL'].astype(str).str.strip() != '')
    ].groupby('CAUSAL').agg({
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
        title=f'Top 10 - {periodo_label}',
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
# HELPER: Filtros de Período Estándar
# ============================================================================

def _render_filtros_periodo(df, key_suffix="", mostrar_titulo=True):
    """
    Renderiza filtros de período estándar (Año, Trimestre, Mes) como multiselect.
    Permite combinaciones como Q1+Q4 o años múltiples.
    Retorna: (df_filtrado, filtros_aplicados_dict)
    """
    filtros_aplicados = {}

    # Preparar datos de período
    df_periodos = df.copy()
    if 'AÑO' in df_periodos.columns:
        df_periodos['_AÑO'] = pd.to_numeric(df_periodos['AÑO'], errors='coerce')
    if 'MES' in df_periodos.columns:
        df_periodos['_MES'] = pd.to_numeric(df_periodos['MES'], errors='coerce')

    # Año multiselect
    años_disponibles = []
    if '_AÑO' in df_periodos.columns:
        años_disponibles = sorted(
            df_periodos['_AÑO'].dropna().astype(int).unique().tolist(),
            reverse=True
        )

    trimestres_opciones = ["Q1", "Q2", "Q3", "Q4"]

    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    meses_disponibles = []
    if '_MES' in df_periodos.columns:
        meses_disponibles = sorted([
            m for m in df_periodos['_MES'].dropna().astype(int).unique().tolist()
            if 1 <= m <= 12
        ])

    if mostrar_titulo:
        st.caption("🔍 Filtrar por período (combinaciones permitidas: Q1+Q4, 2024+2025, etc.)")

    # Renderizar filtros en 3 columnas
    col1, col2, col3 = st.columns(3)

    with col1:
        años_sel = st.multiselect(
            "📅 Años",
            options=años_disponibles,
            default=años_disponibles[:min(2, len(años_disponibles))] if años_disponibles else [],
            key=f"filtro_años_{key_suffix}"
        )

    with col2:
        trimestres_sel = st.multiselect(
            "📊 Trimestres",
            options=trimestres_opciones,
            default=[],
            help="Selecciona uno o varios trimestres (ej: Q1 y Q4)",
            key=f"filtro_trimestres_{key_suffix}"
        )

    with col3:
        meses_sel = st.multiselect(
            "📆 Meses",
            options=meses_disponibles,
            format_func=lambda m: meses_nombres.get(m, str(m)),
            default=[],
            help="Selecciona uno o varios meses",
            key=f"filtro_meses_{key_suffix}"
        )

    # Aplicar filtros
    df_filtrado = df.copy()

    if años_sel and 'AÑO' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['AÑO'].isin(años_sel)]
        filtros_aplicados['Años'] = ', '.join(map(str, años_sel))

    if trimestres_sel and 'MES' in df_filtrado.columns:
        trimestre_map = {"Q1": [1, 2, 3], "Q2": [4, 5, 6], "Q3": [7, 8, 9], "Q4": [10, 11, 12]}
        meses_trimestre = []
        for t in trimestres_sel:
            meses_trimestre.extend(trimestre_map.get(t, []))
        df_filtrado = df_filtrado[df_filtrado['MES'].isin(meses_trimestre)]
        filtros_aplicados['Trimestres'] = ', '.join(trimestres_sel)

    if meses_sel and 'MES' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['MES'].isin(meses_sel)]
        filtros_aplicados['Meses'] = ', '.join(meses_nombres.get(m, str(m)) for m in meses_sel)

    return df_filtrado, filtros_aplicados


def _generar_excel_simple(df, sheet_name="Datos"):
    """Genera un archivo Excel simple con una o más hojas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


# ============================================================================
# RECUPERACIÓN MENSUAL
# ============================================================================

def render_recuperacion_mensual(df):
    """
    RF-003.7: Tabla de recuperación mensual con % de honorarios (umbral dinámico por taller)
    """
    # Modo presentación: ocultar completamente este gráfico
    fee_config = load_fee_config()
    hide_fees = fee_config.get('hide_fees_presentation', False)
    if hide_fees:
        return

    if df is None or df.empty:
        st.subheader("📊 Recuperación Mensual con % de Honorarios")
        st.info("No hay datos disponibles.")
        return

    if 'AÑO' not in df.columns or 'MES' not in df.columns:
        st.subheader("📊 Recuperación Mensual con % de Honorarios")
        st.warning("No se encontraron columnas de fecha.")
        return

    # --- Filtros de período ---
    header_container = st.container()

    df_valid, filtros = _render_filtros_periodo(df, key_suffix="recuperacion")

    # Filtrar solo registros con AÑO y MES válidos
    df_valid = df_valid[(df_valid['AÑO'].notna()) & (df_valid['MES'].notna()) &
                  (df_valid['AÑO'] > 2000) & (df_valid['MES'] >= 1) & (df_valid['MES'] <= 12)]

    if df_valid.empty:
        with header_container:
            st.subheader("📊 Recuperación Mensual con % de Honorarios")
        st.warning("No hay datos con fechas válidas para los filtros seleccionados.")
        return

    # Botón de exportación
    excel_data = _generar_excel_simple(df_valid, "Recuperación Mensual")
    with header_container:
        title_col, action_col = st.columns([3, 2])
        with title_col:
            st.subheader("📊 Recuperación Mensual con % de Honorarios")
        with action_col:
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"recuperacion_mensual_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

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
    if df is None or df.empty:
        st.subheader("📐 Efectividad en la Valoración")
        st.warning("No hay datos disponibles para calcular la efectividad de valoración.")
        return

    required_cols = {'AÑO', 'MES', 'PLACA'}
    if not required_cols.issubset(df.columns):
        st.subheader("📐 Efectividad en la Valoración")
        st.warning("Faltan columnas requeridas (AÑO, MES, PLACA) para calcular la efectividad.")
        return

    # --- Filtros de período ---
    header_container = st.container()

    df_filtros, filtros_info = _render_filtros_periodo(df, key_suffix="efectividad")

    # ------------------------------------------------------------------
    # 1. Obtener imprevistos mensuales (misma lógica que tasa de imprevistos)
    # ------------------------------------------------------------------
    df_imp_mes = resumir_imprevistos_mensuales(df=df_filtros)

    if df_imp_mes.empty:
        with header_container:
            st.subheader("📐 Efectividad en la Valoración")
        st.info("No se encontraron registros de imprevistos para los filtros seleccionados.")
        return

    # ------------------------------------------------------------------
    # 2. Total vehículos desde la hoja "TASA DE IMPREVISTOS"
    # ------------------------------------------------------------------
    df_all = df_filtros.copy()
    df_all['año'] = pd.to_numeric(df_all['AÑO'], errors='coerce')
    df_all['mes'] = pd.to_numeric(df_all['MES'], errors='coerce')

    df_tasa_sheets = st.session_state.get("tasa_imprevistos_data")
    if df_tasa_sheets is not None and not df_tasa_sheets.empty:
        df_tasa_filtered = df_tasa_sheets.copy()
        # Aplicar mismos filtros de año/mes a los vehículos
        if 'AÑO' in df_tasa_filtered.columns and filtros_info.get('Años'):
            años_sel = [int(a) for a in filtros_info['Años'].split(', ')]
            df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['AÑO'].isin(años_sel)]
        if 'MES' in df_tasa_filtered.columns:
            meses_filtro = []
            if filtros_info.get('Trimestres'):
                trimestre_map = {"Q1": [1,2,3], "Q2": [4,5,6], "Q3": [7,8,9], "Q4": [10,11,12]}
                for t in filtros_info['Trimestres'].split(', '):
                    meses_filtro.extend(trimestre_map.get(t, []))
            if filtros_info.get('Meses'):
                meses_nombres_rev = {v: k for k, v in {
                    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                }.items()}
                for nombre_mes in filtros_info['Meses'].split(', '):
                    m_num = meses_nombres_rev.get(nombre_mes)
                    if m_num and m_num not in meses_filtro:
                        meses_filtro.append(m_num)
            if meses_filtro:
                df_tasa_filtered = df_tasa_filtered[df_tasa_filtered['MES'].isin(meses_filtro)]

        df_vehiculos = df_tasa_filtered.groupby(['AÑO', 'MES']).agg(
            total_vehiculos=('TOTAL', 'sum')
        ).reset_index()
        df_vehiculos = df_vehiculos.rename(columns={'AÑO': 'año', 'MES': 'mes'})
        df_vehiculos['año'] = df_vehiculos['año'].astype(int)
        df_vehiculos['mes'] = df_vehiculos['mes'].astype(int)
    else:
        with header_container:
            st.subheader("📐 Efectividad en la Valoración")
        st.warning("⚠️ No se encontraron datos de la hoja 'TASA DE IMPREVISTOS'. No se puede calcular la efectividad sin el total de vehículos.")
        return

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
        with header_container:
            st.subheader("📐 Efectividad en la Valoración")
        st.warning("No se pudo construir la serie mensual de efectividad para los filtros seleccionados.")
        return

    # Botón de exportación
    excel_data = _generar_excel_simple(df_resumen, "Efectividad")
    with header_container:
        title_col, action_col = st.columns([3, 2])
        with title_col:
            st.subheader("📐 Efectividad en la Valoración")
        with action_col:
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"efectividad_valoracion_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

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
        st.subheader("🏢 Distribución de Ahorros por Compañía de Seguros")
        st.info("No hay datos para mostrar distribución por compañía de seguros.")
        return

    if 'COMPAÑIA_DE_SEGUROS' not in df.columns:
        st.subheader("🏢 Distribución de Ahorros por Compañía de Seguros")
        st.warning("No se encontró la columna 'COMPAÑIA_DE_SEGUROS' en los datos.")
        return

    # --- Filtros de período ---
    header_container = st.container()

    df_filtros, _ = _render_filtros_periodo(df, key_suffix="compania")

    # Filtrar solo registros autorizados para métricas de ahorro
    df = filter_authorized_savings_records(df_filtros)
    if df is None or df.empty:
        with header_container:
            st.subheader("🏢 Distribución de Ahorros por Compañía de Seguros")
        st.info("No hay registros AUTORIZADO para mostrar distribución por compañía con los filtros seleccionados.")
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
        with header_container:
            st.subheader("🏢 Distribución de Ahorros por Compañía de Seguros")
        st.info("No hay datos de ahorro por compañía de seguros.")
        return

    total_ahorro = resumen['DIFERENCIA'].sum()

    # Calcular porcentaje
    resumen['PORCENTAJE'] = (resumen['DIFERENCIA'] / total_ahorro) * 100

    # Replicar colores si hay más compañías que colores
    color_list = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(resumen))]

    # Botón de exportación
    excel_data = _generar_excel_simple(resumen, "Ahorro por Compañía")
    with header_container:
        title_col, action_col = st.columns([3, 2])
        with title_col:
            st.subheader("🏢 Distribución de Ahorros por Compañía de Seguros")
        with action_col:
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"ahorro_por_compania_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

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

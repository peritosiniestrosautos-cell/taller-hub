"""
================================================================================
VISUALIZACIONES MULTITALLER - Taller Hub
================================================================================
Funciones específicas para visualizaciones comparativas entre talleres.
RF-MT: Análisis multitaller
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import PORCENTAJE_HONORARIOS
from .taller_config import get_taller_config, get_talleres_disponibles
from .fee_config import load_fee_config, calculate_fees_per_month
from .data_processor import filter_authorized_savings_records
from .theme import (
    BrandColors, SemanticColors, GrayScale, ChartHeights, TALLER_COLORS,
    get_plotly_theme, get_chart_color, hex_with_opacity
)


def _get_taller_color(taller_name: str) -> str:
    """Busca el color de un taller por nombre"""
    talleres = get_talleres_disponibles()
    for tid, tconf in talleres.items():
        if tconf.get("nombre") == taller_name and "color" in tconf:
            return tconf["color"]
    return BrandColors.PRIMARY


# ============================================================================
# KPIs MULTITALLER
# ============================================================================

def render_kpis_multitaller(df):
    """
    Muestra KPIs comparativos cuando hay múltiples talleres.
    """
    if df is None or df.empty:
        return
    
    if "TALLER_ORIGEN" not in df.columns:
        # Fallback: usar KPIs normales
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        st.info("No hay registros AUTORIZADO para comparar ahorro entre talleres.")
        return

    # RF-005.3: Deduplicar por PLACA + SINIESTRO — misma placa con mismo
    # siniestro solo cuenta una vez. Placas con siniestros distintos sí cuentan.
    if 'PLACA' in df.columns and 'SINIESTRO' in df.columns:
        df = df.drop_duplicates(subset=['PLACA', 'SINIESTRO'], keep='first')

    talleres = df["TALLER_ORIGEN"].unique()
    
    if len(talleres) <= 1:
        # Solo hay un taller, no mostrar comparativas
        return
    
    st.subheader("🏪 Comparativa de Talleres")

    # Calcular métricas por taller
    resumen = df.groupby("TALLER_ORIGEN").agg({
        "DIFERENCIA": ["sum", "mean", "count"],
        "PLACA": "nunique"
    }).reset_index()

    resumen.columns = ["TALLER", "AHORRO_TOTAL", "AHORRO_PROMEDIO", "TOTAL_REPARACIONES", "VEHICULOS_UNICOS"]
    
    # Apply per-taller per-month fee calculation
    fee_config = load_fee_config()
    fee_info = calculate_fees_per_month(df, fee_config)
    
    # Update resumen with per-taller fees (sum of per-month)
    for idx, row in resumen.iterrows():
        taller = row["TALLER"]
        if taller in fee_info['by_taller']:
            resumen.loc[idx, "HONORARIOS"] = fee_info['by_taller'][taller]['total_honorarios']
            resumen.loc[idx, "UTILIDAD"] = row["AHORRO_TOTAL"] - fee_info['by_taller'][taller]['total_honorarios']
        else:
            # Fallback to default calculation
            resumen.loc[idx, "HONORARIOS"] = row["AHORRO_TOTAL"] * fee_config['global_defaults']['base_percentage']
            resumen.loc[idx, "UTILIDAD"] = row["AHORRO_TOTAL"] - resumen.loc[idx, "HONORARIOS"]
    
    # Ordenar por ahorro total descendente
    resumen = resumen.sort_values("AHORRO_TOTAL", ascending=False)
    
    # Mostrar KPIs en cards (2 por fila)
    for i in range(0, len(resumen), 2):
        cols = st.columns(2, gap="medium")
        for j in range(2):
            idx = i + j
            if idx < len(resumen):
                with cols[j]:
                    taller = resumen.iloc[idx]["TALLER"]
                    row = resumen.iloc[idx]
                    color = _get_taller_color(taller)

                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {hex_with_opacity(color, 34)} 0%, {hex_with_opacity(color, 17)} 100%); 
                                border-left: 4px solid {color}; 
                                border-radius: 12px; padding: 1rem; min-height: 140px;
                                display: flex; flex-direction: column; justify-content: center;">
                        <div style="font-size: 1rem; font-weight: 700; color: {color}; margin-bottom: 0.5rem;">
                            {taller}
                        </div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: {GrayScale.SLATE_800};">
                            ${row["AHORRO_TOTAL"]:,.0f}
                        </div>
                        <div style="font-size: 0.8rem; color: {GrayScale.SLATE_500}; margin-top: 0.25rem;">
                            💰 Ahorro Total
                        </div>
                        <div style="margin-top: 0.75rem; border-top: 1px solid {GrayScale.SLATE_200}; padding-top: 0.5rem;">
                            <div style="font-size: 0.8rem; color: {GrayScale.SLATE_600};">
                                📊 {int(row["TOTAL_REPARACIONES"])} reparaciones<br>
                                🚗 {int(row["VEHICULOS_UNICOS"])} vehículos<br>
                                💵 ${row["UTILIDAD"]:,.0f} utilidad
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


def render_ranking_talleres(df):
    """
    Muestra un ranking visual de talleres por diferentes métricas.
    """
    if df is None or df.empty or "TALLER_ORIGEN" not in df.columns:
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    st.divider()
    st.subheader("🏆 Ranking de Talleres")
    
    # Calcular métricas
    resumen = df.groupby("TALLER_ORIGEN").agg({
        "DIFERENCIA": ["sum", "mean"],
        "PLACA": "count"
    }).reset_index()
    
    resumen.columns = ["TALLER", "AHORRO_TOTAL", "AHORRO_PROMEDIO", "REPARACIONES"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**💰 Por Ahorro Total**")
        top_ahorro = resumen.nlargest(3, "AHORRO_TOTAL")
        for i, (_, row) in enumerate(top_ahorro.iterrows(), 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            st.markdown(f"{emoji} **{row['TALLER']}**<br>${row['AHORRO_TOTAL']:,.0f}", unsafe_allow_html=True)
    
    with col2:
        st.markdown("**📊 Por Reparaciones**")
        top_rep = resumen.nlargest(3, "REPARACIONES")
        for i, (_, row) in enumerate(top_rep.iterrows(), 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            st.markdown(f"{emoji} **{row['TALLER']}**<br>{row['REPARACIONES']} reparaciones", unsafe_allow_html=True)
    
    with col3:
        st.markdown("**📈 Por Promedio**")
        top_prom = resumen.nlargest(3, "AHORRO_PROMEDIO")
        for i, (_, row) in enumerate(top_prom.iterrows(), 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            st.markdown(f"{emoji} **{row['TALLER']}**<br>${row['AHORRO_PROMEDIO']:,.0f}/rep", unsafe_allow_html=True)


# ============================================================================
# GRÁFICOS COMPARATIVOS MULTITALLER
# ============================================================================

def render_comparativo_anual(df):
    """
    Gráfico comparativo año vs año: muestra ahorro mensual agrupado por año.
    Una línea/barra por año. Eje X: meses (1-12), Eje Y: ahorro (DIFERENCIA).
    Incluye filtros independientes: años (multiselect), trimestre y mes.
    """
    if df is None or df.empty:
        return

    if "AÑO" not in df.columns or "MES" not in df.columns or "DIFERENCIA" not in df.columns:
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        st.info("No hay registros AUTORIZADO para construir el comparativo anual.")
        return

    # --- Filtros independientes del comparativo anual ---
    col1, col2, col3 = st.columns(3)

    años_en_datos = sorted(df['AÑO'].dropna().unique(), reverse=True)
    años_en_datos = [int(a) for a in años_en_datos if a > 2000]

    with col1:
        años_seleccionados = st.multiselect(
            "📅 Años a comparar",
            options=años_en_datos,
            default=años_en_datos,
            help="Selecciona los años que deseas comparar",
            key="comp_anual_años"
        )

    with col2:
        trimestre = st.selectbox(
            "📊 Trimestre",
            options=["Todos", "Q1", "Q2", "Q3", "Q4"],
            help="Q1: Ene-Mar | Q2: Abr-Jun | Q3: Jul-Sep | Q4: Oct-Dic",
            key="comp_anual_trimestre"
        )

    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    with col3:
        meses_en_datos = sorted(df['MES'].dropna().unique())
        meses_en_datos = [m for m in meses_en_datos if 1 <= m <= 12]
        meses_opciones = ["Todos"] + [meses_nombres[m] for m in meses_en_datos]
        mes_seleccionado = st.selectbox(
            "📆 Mes",
            options=meses_opciones,
            help="Filtra por un mes específico",
            key="comp_anual_mes"
        )

    # Aplicar filtros independientes
    df_filtrado = df.copy()

    if años_seleccionados:
        df_filtrado = df_filtrado[df_filtrado['AÑO'].isin(años_seleccionados)]

    trimestre_map = {"Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12)}
    if trimestre != "Todos":
        inicio, fin = trimestre_map[trimestre]
        df_filtrado = df_filtrado[(df_filtrado['MES'] >= inicio) & (df_filtrado['MES'] <= fin)]

    if mes_seleccionado != "Todos":
        mes_num = [k for k, v in meses_nombres.items() if v == mes_seleccionado][0]
        df_filtrado = df_filtrado[df_filtrado['MES'] == mes_num]

    # Filtrar datos válidos
    df_valid = df_filtrado[
        (df_filtrado['AÑO'].notna()) & (df_filtrado['MES'].notna()) &
        (df_filtrado['AÑO'] > 2000) & (df_filtrado['MES'] >= 1) & (df_filtrado['MES'] <= 12)
    ]

    if df_valid.empty:
        st.info("No hay datos para los filtros seleccionados del comparativo anual.")
        return

    # Años únicos en los datos (puede ser 1 o más)
    años_unicos = sorted(df_valid['AÑO'].unique())

    # Agrupar por año y mes
    df_grupo = df_valid.groupby(["AÑO", "MES"]).agg({
        "DIFERENCIA": "sum"
    }).reset_index()

    # Nombres de meses para el eje X
    month_names = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    # Obtener los meses presentes en los datos (para respetar filtro de trimestre)
    meses_presentes = sorted(df_valid['MES'].unique())

    # Crear gráfico
    fig = go.Figure()

    # Colores para cada año (usar paleta centralizada)
    for i, año in enumerate(años_unicos):
        color = get_chart_color(i)
        df_año = df_grupo[df_grupo["AÑO"] == año]

        # Preparar datos para el gráfico
        x_meses = []
        y_valores = []

        for mes in meses_presentes:
            row = df_año[df_año["MES"] == mes]
            if not row.empty:
                x_meses.append(month_names.get(mes, str(mes)))
                y_valores.append(row["DIFERENCIA"].values[0])
            else:
                # Mes sin datos
                x_meses.append(month_names.get(mes, str(mes)))
                y_valores.append(0)

        # Preparar textos abreviados para cada barra
        textos = []
        for v in y_valores:
            if pd.isna(v) or v == 0:
                textos.append('')
            elif abs(v) >= 1000000:
                textos.append(f'{v/1000000:.1f}M')
            else:
                textos.append(f'{v/1000:.1f}k')

        fig.add_trace(go.Bar(
            x=x_meses,
            y=y_valores,
            name=str(int(año)),
            marker_color=color,
            text=textos,
            textposition='outside',
            textfont=dict(size=11, color='white'),
            hovertemplate=f"<b>Año {int(año)}</b><br>Mes: %{{x}}<br>Ahorro: $%{{y:,.0f}}<extra></extra>"
        ))

    theme = get_plotly_theme(
        title="📅 Comparativo Anual: Ahorro Mensual por Año",
        height=ChartHeights.XLARGE,
    )
    theme["margin"] = {"l": 60, "r": 20, "t": 80, "b": 60}
    fig.update_layout(**theme)
    fig.update_xaxes(title_text="Mes")
    fig.update_yaxes(title_text="Ahorro ($)", tickformat="$,.0f")
    fig.update_layout(barmode="group")

    st.plotly_chart(fig, width='stretch')


def render_grafico_comparativo_ahorro(df):
    """
    Gráfico de barras comparando ahorro por taller.
    """
    if df is None or df.empty or "TALLER_ORIGEN" not in df.columns:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    # Preparar datos
    resumen = df.groupby("TALLER_ORIGEN").agg({
        "DIFERENCIA": "sum",
        "PLACA": "count"
    }).reset_index()
    resumen.columns = ["TALLER", "AHORRO", "REPARACIONES"]
    
    # Crear gráfico
    fig = px.bar(
        resumen,
        x="TALLER",
        y="AHORRO",
        color="TALLER",
        text=resumen["AHORRO"].apply(lambda x: f"${x:,.0f}"),
        title="💰 Comparativa de Ahorro por Taller",
        labels={"AHORRO": "Ahorro Total ($)", "TALLER": ""}
    )
    
    fig.update_traces(textposition="outside")
    fig.update_layout(
        **get_plotly_theme(
            title="💰 Comparativa de Ahorro por Taller",
            height=ChartHeights.LARGE,
            show_legend=False
        )
    )
    fig.update_yaxes(tickformat="$,.0f")
    
    st.plotly_chart(fig, width='stretch')


def render_grafico_tendencia_por_taller(df):
    """
    Gráfico de líneas mostrando la tendencia de ahorro por taller a lo largo del tiempo.
    """
    if df is None or df.empty:
        return
    
    if "TALLER_ORIGEN" not in df.columns or "AÑO" not in df.columns or "MES" not in df.columns:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    # Filtrar datos válidos
    df_valid = df[(df['AÑO'].notna()) & (df['MES'].notna()) & 
                  (df['AÑO'] > 2000) & (df['MES'] >= 1) & (df['MES'] <= 12)]
    
    if df_valid.empty:
        return
    
    # Agrupar por taller, año y mes
    df_mes = df_valid.groupby(["TALLER_ORIGEN", "AÑO", "MES"]).agg({
        "DIFERENCIA": "sum"
    }).reset_index()
    
    # Crear fecha
    df_mes["FECHA"] = pd.to_datetime(
        df_mes["AÑO"].astype(str) + "-" + df_mes["MES"].astype(str) + "-01",
        errors="coerce"
    )
    df_mes = df_mes[df_mes["FECHA"].notna()]
    df_mes = df_mes.sort_values("FECHA")
    df_mes["TEXTO_FECHA"] = df_mes["FECHA"].dt.strftime("%b %Y")
    
    # Crear gráfico
    fig = go.Figure()
    
    for taller in talleres:
        df_taller = df_mes[df_mes["TALLER_ORIGEN"] == taller]
        if not df_taller.empty:
            color = _get_taller_color(taller)

            fig.add_trace(go.Scatter(
                x=df_taller["TEXTO_FECHA"],
                y=df_taller["DIFERENCIA"],
                mode="lines+markers",
                name=taller,
                line=dict(color=color, width=2),
                marker=dict(size=6)
            ))

    fig.update_layout(
        **get_plotly_theme(
            title="📈 Evolución de Ahorros por Taller",
            height=ChartHeights.XLARGE,
        )
    )
    fig.update_xaxes(title_text="Mes")
    fig.update_yaxes(title_text="Ahorro ($)", tickformat="$,.0f")
    
    st.plotly_chart(fig, width='stretch')


def render_heatmap_talleres_meses(df):
    """
    Heatmap de ahorro por taller y mes.
    """
    if df is None or df.empty:
        return
    
    if "TALLER_ORIGEN" not in df.columns or "AÑO" not in df.columns or "MES" not in df.columns:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    # Preparar datos
    df_valid = df[(df['AÑO'].notna()) & (df['MES'].notna())]
    
    if df_valid.empty:
        return
    
    pivot = df_valid.pivot_table(
        values="DIFERENCIA",
        index="TALLER_ORIGEN",
        columns=["AÑO", "MES"],
        aggfunc="sum",
        fill_value=0
    )
    
    # Formatear nombres de columnas
    pivot.columns = [f"{int(año)}-{int(mes):02d}" for año, mes in pivot.columns]
    
    # Crear heatmap
    fig = px.imshow(
        pivot,
        labels=dict(x="Período", y="Taller", color="Ahorro ($)"),
        title="🔥 Mapa de Calor: Ahorro por Taller y Mes",
        color_continuous_scale="Blues",
        aspect="auto"
    )
    
    fig.update_layout(
        **get_plotly_theme(
            title="🔥 Mapa de Calor: Ahorro por Taller y Mes",
            height=ChartHeights.LARGE,
            show_legend=True
        )
    )
    
    st.plotly_chart(fig, width='stretch')


def render_distribucion_por_taller(df):
    """
    Gráfico de pastel/torta mostrando la distribución del ahorro entre talleres.
    """
    if df is None or df.empty or "TALLER_ORIGEN" not in df.columns:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    # Calcular totales por taller
    resumen = df.groupby("TALLER_ORIGEN")["DIFERENCIA"].sum().reset_index()
    resumen = resumen.sort_values("DIFERENCIA", ascending=False)
    
    # Colores personalizados por taller
    colors = [_get_taller_color(taller) for taller in resumen["TALLER_ORIGEN"]]
    
    # Crear gráfico de dona
    fig = go.Figure(data=[go.Pie(
        labels=resumen["TALLER_ORIGEN"],
        values=resumen["DIFERENCIA"],
        hole=0.5,
        marker_colors=colors,
        textinfo="label+percent",
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>Ahorro: $%{value:,.0f}<br>Porcentaje: %{percent}<extra></extra>"
    )])
    
    # Agregar total en el centro
    total = resumen["DIFERENCIA"].sum()
    fig.add_annotation(
        text=f"<b>Total</b><br>${total:,.0f}",
        showarrow=False,
        font=dict(size=16)
    )
    
    fig.update_layout(
        **get_plotly_theme(
            title="📊 Distribución del Ahorro entre Talleres",
            height=ChartHeights.XLARGE,
        )
    )
    
    st.plotly_chart(fig, width='stretch')


# ============================================================================
# TABLA RESUMEN MULTITALLER
# ============================================================================

def render_tabla_resumen_talleres(df):
    """
    Tabla detallada con métricas por taller.
    """
    if df is None or df.empty or "TALLER_ORIGEN" not in df.columns:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    st.subheader("📋 Resumen Detallado por Taller")

    # Calcular métricas
    resumen = df.groupby("TALLER_ORIGEN").agg({
        "DIFERENCIA": ["sum", "mean", "count"],
        "PLACA": "nunique",
        "M._DE_O._INICIAL": "sum",
        "M._DE_O._FINAL": "sum"
    }).reset_index()

    resumen.columns = ["TALLER", "AHORRO_TOTAL", "AHORRO_PROMEDIO", "REPARACIONES",
                       "VEHICULOS", "MO_INICIAL", "MO_FINAL"]

    # Calcular derivados con regla de umbral por taller (mes a mes)
    fee_config = load_fee_config()
    hide_fees = fee_config.get('hide_fees_presentation', False)
    
    # Use per-taller per-month fee calculations
    fee_info = calculate_fees_per_month(df, fee_config)
    
    # Update resumen with per-taller fees (sum of per-month)
    for idx, row in resumen.iterrows():
        taller = row["TALLER"]
        if taller in fee_info['by_taller']:
            resumen.loc[idx, "HONORARIOS"] = fee_info['by_taller'][taller]['total_honorarios']
            resumen.loc[idx, "UTILIDAD"] = row["AHORRO_TOTAL"] - fee_info['by_taller'][taller]['total_honorarios']
        else:
            # Fallback
            resumen.loc[idx, "HONORARIOS"] = row["AHORRO_TOTAL"] * fee_config['global_defaults']['base_percentage']
            resumen.loc[idx, "UTILIDAD"] = row["AHORRO_TOTAL"] - resumen.loc[idx, "HONORARIOS"]
    
    resumen["EFICIENCIA"] = ((resumen["MO_INICIAL"] - resumen["MO_FINAL"]) / resumen["MO_INICIAL"] * 100).round(1)

    # Formatear para display
    display = resumen.copy()
    cols_moneda = ["AHORRO_TOTAL", "AHORRO_PROMEDIO", "MO_INICIAL", "MO_FINAL", "HONORARIOS", "UTILIDAD"]
    for col in cols_moneda:
        display[col] = display[col].apply(lambda x: f"${x:,.0f}")

    display["EFICIENCIA"] = display["EFICIENCIA"].apply(lambda x: f"{x}%")

    # Reordenar columnas
    if hide_fees:
        display = display[["TALLER", "REPARACIONES", "VEHICULOS", "AHORRO_TOTAL",
                           "AHORRO_PROMEDIO", "UTILIDAD", "EFICIENCIA"]]
        display.columns = ["Taller", "Reparaciones", "Vehículos", "Ahorro Total",
                           "Promedio", "Utilidad", "Eficiencia"]
        st.info("🔒 Modo presentación activo - Columnas de honorarios ocultas")
    else:
        display = display[["TALLER", "REPARACIONES", "VEHICULOS", "AHORRO_TOTAL",
                           "AHORRO_PROMEDIO", "HONORARIOS", "UTILIDAD", "EFICIENCIA"]]
        display.columns = ["Taller", "Reparaciones", "Vehículos", "Ahorro Total",
                           "Promedio", "Honorarios", "Utilidad", "Eficiencia"]

    st.dataframe(display, width='stretch', hide_index=True)
    
    # Botón de exportación
    col1, col2 = st.columns([1, 4])
    with col1:
        csv = resumen.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="resumen_talleres.csv",
            mime="text/csv"
        )


# ============================================================================
# PESTAÑAS DE VISTA MULTITALLER
# ============================================================================

def render_vista_multitaller(df, key_suffix=""):
    """
    Renderiza la vista completa de análisis multitaller con pestañas.
    
    Args:
        df: DataFrame consolidado con columna TALLER_ORIGEN
        key_suffix: Sufijo para keys únicos de Streamlit
    """
    if df is None or df.empty or "TALLER_ORIGEN" not in df.columns:
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        return
    
    talleres = df["TALLER_ORIGEN"].unique()
    if len(talleres) <= 1:
        return
    
    # Crear pestañas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Comparativa", 
        "📈 Tendencias", 
        "🔥 Heatmap",
        "📋 Detalle"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            render_grafico_comparativo_ahorro(df)
        with col2:
            render_distribucion_por_taller(df)
    
    with tab2:
        render_grafico_tendencia_por_taller(df)
    
    with tab3:
        render_heatmap_talleres_meses(df)
    
    with tab4:
        render_tabla_resumen_talleres(df)

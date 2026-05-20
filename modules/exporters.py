"""
================================================================================
EXPORTACIÓN - Taller Hub
================================================================================
Funciones para exportar reportes en diferentes formatos.
RF-004: Exportación de datos
"""

import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, KeepTogether, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
from .fee_config import load_fee_config, calculate_fees_per_month, format_currency
from .imprevistos_processor import resumir_imprevistos_mensuales, extraer_imprevistos_from_dataframe
from .data_loader import load_tasa_imprevistos_from_excel
from .imprevistos_visualizations import CAUSALES_CULPA_TALLER
from .date_utils import parse_source_date_column
from .data_processor import filter_authorized_savings_records
from .pdf_styles import CONTENT_WIDTH
from .pdf_executive_helpers import (
    build_kpi_row, build_executive_table, build_section_title,
    build_body_paragraph, build_bullet_list, build_hallazgo_box,
    build_conclusion_paragraph, build_sub_section_title,
)
from .pdf_charts import (
    generar_grafico_imprevistos_ejecutivo,
    generar_grafico_tasa_ejecutivo,
    generar_grafico_ahorro_comparativo_historico_ejecutivo,
)
from .pdf_narrative import (
    narrativa_corte_y_saludo, narrativa_introduccion,
    narrativa_ahorros_generados, narrativa_gestion_imprevistos,
    narrativa_imprevistos_cambio_detalle, narrativa_tasa_imprevistos,
    narrativa_ahorro_por_mes, narrativa_comparativo_anual,
    narrativa_ahorro_trimestre, narrativa_causales,
)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PDF_KPI_FONT_SIZE = 10


def _format_honorarios_kpi_value(honorarios, fee_percentage=None):
    """Return the honorarios KPI text shown in the PDF summary."""
    return format_currency(honorarios)


def _get_vehiculos_por_mes_pdf():
    """
    Obtiene datos de vehículos por mes para el PDF.
    Intenta session_state primero, luego carga desde Excel.
    """
    try:
        import streamlit as st
        df_tasa = st.session_state.get("tasa_imprevistos_data")
    except Exception:
        df_tasa = None

    if df_tasa is None or df_tasa.empty:
        df_tasa, _ = load_tasa_imprevistos_from_excel()

    if df_tasa is None or df_tasa.empty:
        return pd.DataFrame(columns=['año', 'mes', 'total_vehiculos'])

    df_vehiculos = df_tasa.groupby(['AÑO', 'MES']).agg(
        total_vehiculos=('TOTAL', 'sum')
    ).reset_index()
    df_vehiculos = df_vehiculos.rename(columns={'AÑO': 'año', 'MES': 'mes'})
    df_vehiculos['año'] = pd.to_numeric(df_vehiculos['año'], errors='coerce').astype(int)
    df_vehiculos['mes'] = pd.to_numeric(df_vehiculos['mes'], errors='coerce').astype(int)
    return df_vehiculos


def _calcular_tasa_imprevistos_pdf(df):
    """Calcula la tasa de imprevistos mensual para el PDF."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_imp_mes = resumir_imprevistos_mensuales(df=df)
    if df_imp_mes.empty:
        return pd.DataFrame()

    df_vehiculos = _get_vehiculos_por_mes_pdf()
    if df_vehiculos.empty:
        return pd.DataFrame()

    df_resumen = df_vehiculos.merge(df_imp_mes, on=['año', 'mes'], how='outer')
    df_resumen['total_vehiculos'] = df_resumen['total_vehiculos'].fillna(0).astype(int)
    df_resumen['total_imprevistos'] = df_resumen['total_imprevistos'].fillna(0).astype(int)
    df_resumen['responsabilidad_taller'] = df_resumen['culpa_taller'].fillna(0).astype(int)
    df_resumen['no_responsabilidad_taller'] = df_resumen['total_imprevistos'] - df_resumen['responsabilidad_taller']
    df_resumen['tasa'] = ((df_resumen['total_imprevistos'] / df_resumen['total_vehiculos'] * 100)).round(1)
    df_resumen['tasa_responsabilidad_taller'] = ((df_resumen['responsabilidad_taller'] / df_resumen['total_vehiculos'] * 100)).round(1)
    df_resumen['tasa_no_responsabilidad_taller'] = ((df_resumen['no_responsabilidad_taller'] / df_resumen['total_vehiculos'] * 100)).round(1)

    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    df_resumen['mes_nombre'] = df_resumen.apply(
        lambda row: f"{MESES_ES.get(int(row['mes']), str(int(row['mes'])))} {int(row['año'])}",
        axis=1
    )
    df_resumen = df_resumen.sort_values(['año', 'mes'])
    return df_resumen


def _generar_grafico_ahorro_mes(df):
    """Genera un gráfico de barras con el ahorro por mes."""
    try:
        if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'DIFERENCIA' not in df.columns:
            return None

        # Asegurar que DIFERENCIA sea numérico
        df_work = df.copy()
        df_work['DIFERENCIA'] = pd.to_numeric(df_work['DIFERENCIA'], errors='coerce').fillna(0)

        # Filtrar filas con AÑO/MES válidos (igual que la tabla del PDF)
        df_work = df_work[df_work['AÑO'].notna() & df_work['MES'].notna()].copy()
        if df_work.empty:
            return None

        # Agrupar (igual que la tabla del PDF)
        df_mes = df_work.groupby(['AÑO', 'MES'])['DIFERENCIA'].sum().reset_index()
        if df_mes.empty:
            return None

        # Ordenar
        df_mes = df_mes.sort_values(['AÑO', 'MES'])

        meses_es = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }

        def _fmt_label(r):
            try:
                m = int(float(r['MES']))
                a = int(float(r['AÑO']))
                return f"{meses_es.get(m, str(m))} {a}"
            except (ValueError, TypeError):
                return f"{r['MES']} {r['AÑO']}"

        df_mes['mes_label'] = df_mes.apply(_fmt_label, axis=1)

        fig, ax = plt.subplots(figsize=(6.5, 3))
        bars = ax.bar(df_mes['mes_label'], df_mes['DIFERENCIA'], color='#3B82F6', edgecolor='white', linewidth=1.2)

        # Etiquetas encima de cada barra (en millones como el comparativo anual)
        for bar in bars:
            height = bar.get_height()
            if abs(height) >= 1000000:
                label = f'${height/1000000:.1f}M'
            elif abs(height) >= 1000:
                label = f'${height/1000:.0f}k'
            else:
                label = f'${height:,.0f}'
            ax.annotate(label,
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=7, color='#1E40AF', fontweight='bold')

        ax.set_title('Ahorro por Mes', fontsize=12, fontweight='bold', color='#1E293B', pad=15)
        ax.set_ylabel('Ahorro (millones $)', fontsize=9, color='#64748B')
        ax.tick_params(axis='x', rotation=45, labelsize=8, colors='#64748B')
        ax.tick_params(axis='y', labelsize=8, colors='#64748B')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E2E8F0')
        ax.spines['bottom'].set_color('#E2E8F0')
        ax.grid(axis='y', linestyle='--', alpha=0.4, color='#CBD5E1')
        ax.set_axisbelow(True)
        # Formatear eje Y en millones
        import matplotlib.ticker as mticker
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x/1000000:.1f}M'))
        fig.tight_layout()

        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        img_buffer.seek(0)
        plt.close(fig)
        return img_buffer
    except Exception as e:
        print(f"[PDF] Error generando gráfico de ahorro por mes: {e}")
        import traceback
        traceback.print_exc()
        return None


def _generar_grafico_tasa_imprevistos(df_tasa):
    """Genera un gráfico de línea con la tasa de imprevistos mensual."""
    if df_tasa is None or df_tasa.empty:
        return None

    fig, ax = plt.subplots(figsize=(6.5, 3))
    ax.plot(df_tasa['mes_nombre'], df_tasa['tasa'], marker='o', linewidth=2.5,
            color='#1E40AF', markersize=8, markerfacecolor='#3B82F6', markeredgecolor='white', markeredgewidth=1.5)

    for i, row in df_tasa.iterrows():
        ax.annotate(f"{row['tasa']:.1f}%", (i, row['tasa']),
                    textcoords="offset points", xytext=(0, 10), ha='center',
                    fontsize=8, color='#1E40AF', fontweight='bold')

    ax.set_title('Tasa de Imprevistos Mensual', fontsize=12, fontweight='bold', color='#1E293B', pad=15)
    ax.set_ylabel('Tasa (%)', fontsize=9, color='#64748B')
    ax.tick_params(axis='x', rotation=45, labelsize=8, colors='#64748B')
    ax.tick_params(axis='y', labelsize=8, colors='#64748B')
    ax.set_ylim(bottom=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#E2E8F0')
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#CBD5E1')
    ax.set_axisbelow(True)
    fig.tight_layout()

    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    img_buffer.seek(0)
    plt.close(fig)
    return img_buffer


def _preparar_cambio_repuestos_pdf(df, año=None, mes=None):
    """Prepara el detalle de imprevistos con cambio de repuestos (culpa del taller) para el PDF.

    Filtra por ACCION=CAMBIO y CAUSAL en CAUSALES_CULPA_TALLER para mantener
    consistencia con el gráfico histórico del mismo reporte.
    """
    columnas_reporte = ["PLACA", "LINEA", "CIA", "IMPREVISTO", "CAUSAL"]

    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_reporte)

    required = {"PLACA", "ACCION"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=columnas_reporte)

    df_w = df.copy()
    df_w["_ACCION"] = df_w["ACCION"].astype(str).str.upper().str.strip()
    df_w = df_w[df_w["_ACCION"].str.contains("CAMBIO", na=False)].copy()

    if df_w.empty:
        return pd.DataFrame(columns=columnas_reporte)

    # Filtrar por mes en curso si se especifica
    if año is not None and mes is not None and "AÑO" in df_w.columns and "MES" in df_w.columns:
        df_w["_AÑO"] = pd.to_numeric(df_w["AÑO"], errors="coerce")
        df_w["_MES"] = pd.to_numeric(df_w["MES"], errors="coerce")
        df_w = df_w[(df_w["_AÑO"] == int(año)) & (df_w["_MES"] == int(mes))].copy()

    if df_w.empty:
        return pd.DataFrame(columns=columnas_reporte)

    # Solo incluir registros cuyo CAUSAL indica culpa del taller (igual que el gráfico)
    df_w["_CAUSAL"] = (
        df_w["CAUSAL"].astype(str).str.upper().str.strip()
        if "CAUSAL" in df_w.columns
        else ""
    )
    df_w = df_w[df_w["_CAUSAL"].isin(CAUSALES_CULPA_TALLER)].copy()

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
        "CAUSAL": df_w["_CAUSAL"],
    })

    return reporte.sort_values(["PLACA", "CIA", "IMPREVISTO"]).reset_index(drop=True)


def _preparar_demora_definicion_pdf(df):
    """Prepara datos de demora en definición del imprevisto para el PDF.

    Filtra, valida fechas, deduplica por PLACA+SINIESTRO y agrupa
    por COMPAÑIA_DE_SEGUROS y ESTATUS devolviendo promedio de días.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    required_cols = {"FECHA_INGR", "FECHA_AUTO", "COMPAÑIA_DE_SEGUROS", "ESTATUS", "PLACA"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

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
        return pd.DataFrame()

    año_limite = datetime.now().year + 1
    df_w = df_w[
        (df_w["FECHA_INGR"].dt.year >= 2000)
        & (df_w["FECHA_INGR"].dt.year <= año_limite)
        & (df_w["FECHA_AUTO"].dt.year >= 2000)
        & (df_w["FECHA_AUTO"].dt.year <= año_limite)
    ].copy()

    if df_w.empty:
        return pd.DataFrame()

    df_w["_DEMORA_DIAS"] = (df_w["FECHA_AUTO"] - df_w["FECHA_INGR"]).dt.days
    df_w["ESTATUS"] = df_w["ESTATUS"].astype(str).str.upper().str.strip()
    df_w = df_w[df_w["ESTATUS"].isin(["AUTORIZADO", "RECHAZADO"])].copy()
    df_w = df_w.drop_duplicates(subset=["_PLACA", "_SINIESTRO"], keep="first")

    if df_w.empty:
        return pd.DataFrame()

    agrupado = (
        df_w.groupby(["COMPAÑIA_DE_SEGUROS", "ESTATUS"])
        .agg(promedio_demora=("_DEMORA_DIAS", "mean"), conteo=("_DEMORA_DIAS", "count"))
        .reset_index()
    )
    agrupado["promedio_demora"] = agrupado["promedio_demora"].round(1)

    # Pivot para tener AUTORIZADO y RECHAZADO como columnas
    pivot = agrupado.pivot_table(
        index="COMPAÑIA_DE_SEGUROS",
        columns="ESTATUS",
        values=["promedio_demora", "conteo"],
        fill_value=0,
    )
    pivot.columns = [f"{val}_{est}" for val, est in pivot.columns]
    pivot = pivot.reset_index()

    for estatus in ["AUTORIZADO", "RECHAZADO"]:
        for metric in ["promedio_demora", "conteo"]:
            col_name = f"{metric}_{estatus}"
            if col_name not in pivot.columns:
                pivot[col_name] = 0

    pivot["_total_promedio"] = pivot["promedio_demora_AUTORIZADO"] + pivot["promedio_demora_RECHAZADO"]
    pivot = pivot.sort_values("_total_promedio", ascending=False).reset_index(drop=True)
    return pivot


def _generar_grafico_demora_definicion(df_pivot):
    """Genera gráfico de barras agrupadas de demora en definición por CIA y Estatus."""
    if df_pivot is None or df_pivot.empty:
        return None

    cias = df_pivot["COMPAÑIA_DE_SEGUROS"].tolist()
    if not cias:
        return None

    autorizado_vals = df_pivot["promedio_demora_AUTORIZADO"].tolist()
    rechazado_vals = df_pivot["promedio_demora_RECHAZADO"].tolist()
    autorizado_cnt = df_pivot["conteo_AUTORIZADO"].tolist()
    rechazado_cnt = df_pivot["conteo_RECHAZADO"].tolist()

    x = range(len(cias))
    width = 0.35

    fig, ax = plt.subplots(figsize=(6.5, 3))

    bars1 = ax.bar(
        [i - width / 2 for i in x],
        autorizado_vals,
        width,
        label="AUTORIZADO",
        color="#22C55E",
        edgecolor="white",
        linewidth=0.5,
    )
    bars2 = ax.bar(
        [i + width / 2 for i in x],
        rechazado_vals,
        width,
        label="RECHAZADO",
        color="#EF4444",
        edgecolor="white",
        linewidth=0.5,
    )

    # Anotaciones
    for bar, cnt in zip(bars1, autorizado_cnt):
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f"{height:.1f}d ({int(cnt)})",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                fontweight="bold",
                color="#15803D",
            )

    for bar, cnt in zip(bars2, rechazado_cnt):
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f"{height:.1f}d ({int(cnt)})",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                fontweight="bold",
                color="#B91C1C",
            )

    ax.set_title(
        "Demora en Definición del Imprevisto por CIA y Estatus",
        fontsize=12,
        fontweight="bold",
        color="#1E293B",
        pad=15,
    )
    ax.set_ylabel("Promedio de Días de Demora", fontsize=9, color="#64748B")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cias, rotation=30, ha="right", fontsize=8, color="#64748B")
    ax.tick_params(axis="y", labelsize=8, colors="#64748B")
    ax.set_ylim(bottom=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#E2E8F0")
    ax.spines["bottom"].set_color("#E2E8F0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    fig.tight_layout()

    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    img_buffer.seek(0)
    plt.close(fig)
    return img_buffer


def _generar_grafico_cambio_repuestos(df):
    """Genera un gráfico de barras con imprevistos con cambio de repuestos (culpa del taller) por mes.

    Muestra la misma métrica que el gráfico '🔧 Imprevistos con Cambio de Repuesto'
    del dashboard: cantidad de registros con ACCION=CAMBIO cuyo CAUSAL indica
    culpa del taller (CAUSALES_CULPA_TALLER).
    """
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'ACCION' not in df.columns:
        return None

    df_w = df.copy()
    df_w["_ACCION"] = df_w["ACCION"].astype(str).str.upper().str.strip()
    df_w = df_w[df_w["_ACCION"].str.contains("CAMBIO", na=False)]

    if df_w.empty:
        return None

    df_w['_AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
    df_w['_MES'] = pd.to_numeric(df_w['MES'], errors='coerce')
    df_w = df_w[(df_w['_AÑO'].notna()) & (df_w['_MES'].notna()) &
                (df_w['_AÑO'] > 2000) & (df_w['_MES'] >= 1) & (df_w['_MES'] <= 12)]

    if df_w.empty:
        return None

    # Normalizar CAUSAL y calcular culpa del taller (misma lógica que el dashboard)
    df_w['_CAUSAL'] = (
        df_w['CAUSAL'].astype(str).str.upper().str.strip()
        if 'CAUSAL' in df_w.columns
        else ''
    )
    df_w['_CULPA'] = df_w['_CAUSAL'].isin(CAUSALES_CULPA_TALLER)

    resumen = df_w.groupby(['_AÑO', '_MES']).agg(
        cantidad=('_CULPA', 'sum')
    ).reset_index()
    resumen = resumen.sort_values(['_AÑO', '_MES'])

    MESES_ES = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
    resumen['periodo'] = resumen.apply(
        lambda r: f"{MESES_ES.get(int(r['_MES']), str(int(r['_MES'])))} {int(r['_AÑO'])}", axis=1
    )

    fig, ax = plt.subplots(figsize=(6.5, 3))
    bars = ax.bar(resumen['periodo'], resumen['cantidad'], color='#3B82F6', edgecolor='white', linewidth=0.5)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{int(height)}", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                    fontsize=8, fontweight='bold', color='#1E40AF')

    ax.set_title('Imprevistos con Cambio de Repuestos por Mes', fontsize=12, fontweight='bold',
                 color='#1E293B', pad=15)
    ax.set_ylabel('Cantidad', fontsize=9, color='#64748B')
    ax.tick_params(axis='x', rotation=45, labelsize=8, colors='#64748B')
    ax.tick_params(axis='y', labelsize=8, colors='#64748B')
    ax.set_ylim(bottom=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#E2E8F0')
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#CBD5E1')
    ax.set_axisbelow(True)
    fig.tight_layout()

    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    img_buffer.seek(0)
    plt.close(fig)
    return img_buffer


def _calcular_comparativo_ahorro_pdf(df):
    """Calcula comparativo de ahorros por mes con % desviación."""
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'DIFERENCIA' not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    df_valid = df[(df['AÑO'].notna()) & (df['MES'].notna()) &
                  (df['AÑO'] > 2000) & (df['MES'] >= 1) & (df['MES'] <= 12)]

    if df_valid.empty:
        return pd.DataFrame(), pd.DataFrame()

    resumen = df_valid.groupby(['AÑO', 'MES'])['DIFERENCIA'].sum().reset_index()
    resumen['AÑO'] = resumen['AÑO'].astype(int)
    resumen['MES'] = resumen['MES'].astype(int)
    resumen = resumen.sort_values(['AÑO', 'MES']).reset_index(drop=True)

    if len(resumen) < 2:
        return pd.DataFrame(), pd.DataFrame()

    # Comparativo mes a mes
    resumen['ahorro_anterior'] = resumen['DIFERENCIA'].shift(1)
    resumen['desviacion_pct'] = resumen.apply(
        lambda r: ((r['DIFERENCIA'] - r['ahorro_anterior']) / r['ahorro_anterior'] * 100)
        if pd.notna(r['ahorro_anterior']) and r['ahorro_anterior'] != 0 else 0,
        axis=1
    ).round(1)

    MESES_ES = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    resumen['periodo'] = resumen.apply(
        lambda r: f"{MESES_ES.get(int(r['MES']), str(int(r['MES'])))} {int(r['AÑO'])}", axis=1
    )
    resumen['periodo_anterior'] = resumen['periodo'].shift(1)
    resumen['indicador'] = resumen['desviacion_pct'].apply(
        lambda x: "▲ Aumentó" if x > 0 else ("▼ Disminuyó" if x < 0 else "● Sin cambio")
    )

    # Comparativo trimestral — Comparación homóloga (mismo trimestre, año anterior)
    df_trim = df_valid.copy()
    df_trim['TRIMESTRE'] = ((df_trim['MES'].astype(int) - 1) // 3 + 1)
    trimestral = df_trim.groupby(['AÑO', 'TRIMESTRE'])['DIFERENCIA'].sum().reset_index()
    trimestral['AÑO'] = trimestral['AÑO'].astype(int)
    trimestral['TRIMESTRE'] = trimestral['TRIMESTRE'].astype(int)
    trimestral = trimestral.sort_values(['AÑO', 'TRIMESTRE']).reset_index(drop=True)

    # Solo incluir trimestres con datos reales (> 0) para evitar falsos "disminuyó"
    trimestral = trimestral[trimestral['DIFERENCIA'] > 0].reset_index(drop=True)

    if len(trimestral) < 2:
        return resumen, pd.DataFrame()

    # Para cada trimestre, buscar el mismo trimestre del año anterior
    def _comparar_trimestre_homologo(row):
        año_actual = row['AÑO']
        trimestre = row['TRIMESTRE']
        año_anterior = año_actual - 1

        prev = trimestral[(trimestral['AÑO'] == año_anterior) & (trimestral['TRIMESTRE'] == trimestre)]
        if prev.empty:
            return pd.Series({
                'ahorro_anterior': None,
                'desviacion_pct': 0.0,
                'periodo_anterior': None,
                'tiene_comparativo': False
            })

        ahorro_ant = prev['DIFERENCIA'].values[0]
        desv = ((row['DIFERENCIA'] - ahorro_ant) / ahorro_ant * 100) if ahorro_ant != 0 else 0.0
        return pd.Series({
            'ahorro_anterior': ahorro_ant,
            'desviacion_pct': round(desv, 1),
            'periodo_anterior': f"Q{trimestre} {año_anterior}",
            'tiene_comparativo': True
        })

    trimestral[['ahorro_anterior', 'desviacion_pct', 'periodo_anterior', 'tiene_comparativo']] = (
        trimestral.apply(_comparar_trimestre_homologo, axis=1)
    )

    # Filtrar solo trimestres que tengan un año anterior comparable
    trimestral = trimestral[trimestral['tiene_comparativo']].copy()
    trimestral['periodo'] = trimestral.apply(lambda r: f"Q{int(r['TRIMESTRE'])} {int(r['AÑO'])}", axis=1)
    trimestral['indicador'] = trimestral['desviacion_pct'].apply(
        lambda x: "▲ Aumentó" if x > 0 else ("▼ Disminuyó" if x < 0 else "● Sin cambio")
    )

    return resumen, trimestral


def _calcular_causales_imprevistos_pdf(df):
    """Calcula causales de imprevistos con cantidad total para el PDF."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_imp = extraer_imprevistos_from_dataframe(df)
    if df_imp.empty or 'causal' not in df_imp.columns:
        return pd.DataFrame()

    df_causal = df_imp[df_imp['causal'].notna() & (df_imp['causal'].astype(str).str.strip() != '')].copy()
    if df_causal.empty:
        return pd.DataFrame()

    resumen = df_causal.groupby('causal').size().reset_index(name='cantidad')
    total = resumen['cantidad'].sum()
    resumen['porcentaje'] = ((resumen['cantidad'] / total * 100) if total > 0 else 0).round(1)
    resumen = resumen.sort_values('cantidad', ascending=False).reset_index(drop=True)
    return resumen


def generate_pdf_report(df, filtros_aplicados, include_honorarios=True, taller_nombre="Taller Hub", filtros_graficos=None, año=None, mes=None):
    """
    Generar reporte PDF del dashboard actual
    
    Args:
        df: DataFrame con los datos filtrados
        filtros_aplicados: Diccionario con los filtros aplicados
        include_honorarios: Boolean para incluir/excluir honorarios
        taller_nombre: Nombre del taller para el footer
        filtros_graficos: Diccionario con filtros aplicados a gráficos específicos
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    buffer = io.BytesIO()
    
    # Crear documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Contenedor para elementos del documento
    elements = []
    
    # Definir estilos
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Estilo para encabezados de sección
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1E40AF'),
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subencabezados
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#3B82F6'),
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para texto normal
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    # Estilo para métricas KPI
    kpi_style = ParagraphStyle(
        'KPI',
        parent=styles['Normal'],
        fontSize=PDF_KPI_FONT_SIZE,
        textColor=colors.HexColor('#1E40AF'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo para labels de KPI
    kpi_label_style = ParagraphStyle(
        'KPILabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        fontName='Helvetica'
    )
    
    # Mapa de número de mes a nombre en español
    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    # =========================================================================
    # HEADER DEL DOCUMENTO
    # =========================================================================
    elements.append(Paragraph(f"🚗 {taller_nombre.upper()}", title_style))
    elements.append(
        Paragraph("Sistema de Gestión de recuperación de mano de obra e imprevistos", subtitle_style)
    )
    
    # Línea separadora
    elements.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#3B82F6'),
            spaceAfter=20
        )
    )
    
    # =========================================================================
    # METADATA DEL REPORTE
    # =========================================================================
    elements.append(Paragraph("📋 Información del Reporte", heading_style))
    
    metadata_data = [
        [Paragraph("<b>Campo</b>", body_style), Paragraph("<b>Valor</b>", body_style)],
        [Paragraph("Fecha de generación", body_style), 
         Paragraph(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), body_style)],
        [Paragraph("Total de registros", body_style), 
         Paragraph(f"{len(df):,}", body_style)],
        [Paragraph("Talleres incluidos", body_style), 
         Paragraph(
             f"{df['TALLER_ORIGEN'].nunique()}" if 'TALLER_ORIGEN' in df.columns else "1",
             body_style
         )]
    ]
    
    # Agregar filtros aplicados
    if filtros_aplicados:
        filtros_str = ", ".join([f"{k}: {v}" for k, v in filtros_aplicados.items() if v])
        if filtros_str:
            metadata_data.append([
                Paragraph("Filtros aplicados", body_style),
                Paragraph(filtros_str, body_style)
            ])
    
    metadata_table = Table(metadata_data, colWidths=[2.5*inch, 4*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1E293B')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(metadata_table)
    
    # =========================================================================
    # KPIs PRINCIPALES
    # =========================================================================
    elements.append(Paragraph("📊 Métricas Principales", heading_style))
    
    if 'DIFERENCIA' in df.columns:
        total_ahorro = df['DIFERENCIA'].sum()
        
        # Calcular honorarios si se incluyen
        fee_info = None
        utilidad = total_ahorro
        fee_percentage = 0
        
        if include_honorarios:
            fee_config = load_fee_config()
            fee_info = calculate_fees_per_month(df, fee_config)
            honorarios = fee_info['total_honorarios']
            fee_percentage = (honorarios / total_ahorro * 100) if total_ahorro > 0 else 0
            utilidad = total_ahorro - honorarios
        
        # Crear tabla de KPIs
        kpi_data = [
            [
                Paragraph("<b>💰 Ahorro Total</b>", kpi_label_style),
            ]
        ]
        
        kpi_values = [
            [
                Paragraph(format_currency(total_ahorro), kpi_style),
            ]
        ]
        
        if include_honorarios and fee_info:
            kpi_data[0].extend([
                Paragraph("<b>📊 Honorarios</b>", kpi_label_style),
                Paragraph("<b>✅ Utilidad Neta</b>", kpi_label_style),
            ])
            kpi_values[0].extend([
                Paragraph(_format_honorarios_kpi_value(honorarios, fee_percentage), kpi_style),
                Paragraph(format_currency(utilidad), kpi_style),
            ])
        
        kpi_table_data = kpi_data + kpi_values
        
        # Determinar anchos de columna dinámicos
        if include_honorarios and fee_info:
            col_widths = [2.2*inch, 2.2*inch, 2.2*inch]
        else:
            col_widths = [6.5*inch]
        
        kpi_table = Table(kpi_table_data, colWidths=col_widths)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#3B82F6')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#3B82F6')),
        ]))
        
        elements.append(kpi_table)
        elements.append(Spacer(1, 20))
        
        # =========================================================================
        # RESUMEN POR TALLER (si es multitaller)
        # =========================================================================
        if 'TALLER_ORIGEN' in df.columns and df['TALLER_ORIGEN'].nunique() > 1:
            elements.append(Paragraph("🏪 Resumen por Taller", heading_style))
            
            talleres_resumen = []
            for taller_id in df['TALLER_ORIGEN'].unique():
                df_taller = df[df['TALLER_ORIGEN'] == taller_id]
                ahorro_taller = df_taller['DIFERENCIA'].sum()
                row_data = [
                    Paragraph(taller_id, body_style),
                    Paragraph(format_currency(ahorro_taller), body_style),
                ]
                
                if include_honorarios and fee_info and taller_id in fee_info['by_taller']:
                    taller_fee = fee_info['by_taller'][taller_id]
                    row_data.append(
                        Paragraph(format_currency(taller_fee['total_honorarios']), body_style)
                    )
                
                talleres_resumen.append(row_data)
            
            # Encabezados de tabla
            taller_headers = [
                Paragraph("<b>Taller</b>", body_style),
                Paragraph("<b>Ahorro</b>", body_style),
            ]
            
            if include_honorarios and fee_info:
                taller_headers.append(Paragraph("<b>Honorarios</b>", body_style))
            
            taller_table_data = [taller_headers] + talleres_resumen
            
            # Anchuras de columna
            if include_honorarios and fee_info:
                taller_col_widths = [2.5*inch, 2*inch, 2*inch]
            else:
                taller_col_widths = [3.25*inch, 3.25*inch]
            
            taller_table = Table(taller_table_data, colWidths=taller_col_widths)
            taller_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(taller_table)
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # TASA DE IMPREVISTOS (Gráfico + Tabla)
        # =========================================================================
        df_tasa_imp = _calcular_tasa_imprevistos_pdf(df)
        if not df_tasa_imp.empty:
            elements.append(Paragraph("📊 Tasa de Imprevistos", heading_style))
            
            # Gráfico
            grafico_tasa_buf = _generar_grafico_tasa_imprevistos(df_tasa_imp)
            if grafico_tasa_buf:
                elements.append(Image(grafico_tasa_buf, width=6.5*inch, height=3*inch))
                elements.append(Spacer(1, 10))
            
            # Tabla
            tasa_table_data = [[
                Paragraph("<b>Mes</b>", body_style),
                Paragraph("<b>Vehículos</b>", body_style),
                Paragraph("<b>Imprevistos</b>", body_style),
                Paragraph("<b>Resp. Taller</b>", body_style),
                Paragraph("<b>No Resp. Taller</b>", body_style),
                Paragraph("<b>Tasa Total</b>", body_style),
            ]]
            
            for _, row in df_tasa_imp.iterrows():
                tasa_table_data.append([
                    Paragraph(str(row['mes_nombre']), body_style),
                    Paragraph(f"{int(row['total_vehiculos']):,}", body_style),
                    Paragraph(f"{int(row['total_imprevistos']):,}", body_style),
                    Paragraph(f"{int(row['responsabilidad_taller']):,}", body_style),
                    Paragraph(f"{int(row['no_responsabilidad_taller']):,}", body_style),
                    Paragraph(f"{row['tasa']:.1f}%", body_style),
                ])
            
            tasa_table = Table(tasa_table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
            tasa_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(tasa_table)
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # IMPREVISTOS CON CAMBIO DE REPUESTOS (Gráfico + Tabla del período)
        # =========================================================================
        año_cambio = int(año) if año is not None else datetime.now().year
        mes_cambio = int(mes) if mes is not None else None
        df_cambio_rep = _preparar_cambio_repuestos_pdf(df, año=año_cambio, mes=mes_cambio)

        # Gráfico histórico (siempre mostrar si hay datos de cambio)
        grafico_cambio_buf = _generar_grafico_cambio_repuestos(df)
        if grafico_cambio_buf:
            elements.append(Paragraph("🔧 Imprevistos con Cambio de Repuestos", heading_style))
            elements.append(Image(grafico_cambio_buf, width=6.5*inch, height=3*inch))
            elements.append(Spacer(1, 10))

        if not df_cambio_rep.empty:
            if mes_cambio is not None:
                mes_nombre_cambio = MESES_ES.get(mes_cambio, str(mes_cambio))
                elements.append(Paragraph(f"Detalle del Período ({mes_nombre_cambio} {año_cambio})", subheading_style))
            else:
                elements.append(Paragraph(f"Detalle del Período Seleccionado ({año_cambio})", subheading_style))
            
            cambio_table_data = [[
                Paragraph("<b>PLACA</b>", body_style),
                Paragraph("<b>LÍNEA</b>", body_style),
                Paragraph("<b>CIA</b>", body_style),
                Paragraph("<b>IMPREVISTO</b>", body_style),
                Paragraph("<b>CAUSAL</b>", body_style),
            ]]
            
            for _, row in df_cambio_rep.iterrows():
                cambio_table_data.append([
                    Paragraph(str(row['PLACA']), body_style),
                    Paragraph(str(row['LINEA']), body_style),
                    Paragraph(str(row['CIA']), body_style),
                    Paragraph(str(row['IMPREVISTO']), body_style),
                    Paragraph(str(row['CAUSAL']), body_style),
                ])
            
            cambio_table = Table(cambio_table_data, colWidths=[1*inch, 1.1*inch, 1*inch, 1.7*inch, 1.7*inch])
            cambio_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(cambio_table)
            elements.append(Spacer(1, 15))
        elif grafico_cambio_buf:
            # Si hay gráfico pero no hay datos para el período seleccionado, mostrar mensaje
            if mes_cambio is not None:
                mes_nombre_cambio = MESES_ES.get(mes_cambio, str(mes_cambio))
                elements.append(Paragraph(f"No hay imprevistos con cambio de repuestos para {mes_nombre_cambio} {año_cambio}.", body_style))
            else:
                elements.append(Paragraph(f"No hay imprevistos con cambio de repuestos para el período seleccionado ({año_cambio}).", body_style))
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # DEMORA EN DEFINICIÓN DEL IMPREVISTO (Gráfico + Tabla)
        # =========================================================================
        df_demora = _preparar_demora_definicion_pdf(df)
        if not df_demora.empty:
            elements.append(Paragraph("⏱️ Demora en Definición del Imprevisto", heading_style))

            grafico_demora_buf = _generar_grafico_demora_definicion(df_demora)
            if grafico_demora_buf:
                elements.append(Image(grafico_demora_buf, width=6.5*inch, height=3*inch))
                elements.append(Spacer(1, 10))

            # Tabla resumen
            demora_table_data = [[
                Paragraph("<b>Compañía de Seguros</b>", body_style),
                Paragraph("<b>Promedio Autorizado (días)</b>", body_style),
                Paragraph("<b>Cant. Autorizados</b>", body_style),
                Paragraph("<b>Promedio Rechazado (días)</b>", body_style),
                Paragraph("<b>Cant. Rechazados</b>", body_style),
            ]]

            for _, row in df_demora.iterrows():
                demora_table_data.append([
                    Paragraph(str(row["COMPAÑIA_DE_SEGUROS"]), body_style),
                    Paragraph(f"{row['promedio_demora_AUTORIZADO']:.1f}", body_style),
                    Paragraph(f"{int(row['conteo_AUTORIZADO']):,}", body_style),
                    Paragraph(f"{row['promedio_demora_RECHAZADO']:.1f}", body_style),
                    Paragraph(f"{int(row['conteo_RECHAZADO']):,}", body_style),
                ])

            demora_table = Table(demora_table_data, colWidths=[2*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch])
            demora_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

            elements.append(demora_table)
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # RESUMEN MENSUAL (Ahorro por Mes)
        # =========================================================================
        if 'AÑO' in df.columns and 'MES' in df.columns:
            elements.append(Paragraph("📅 Ahorro por Mes", heading_style))

            # Gráfico
            grafico_ahorro_buf = _generar_grafico_ahorro_mes(df)
            if grafico_ahorro_buf:
                elements.append(Image(grafico_ahorro_buf, width=6.5*inch, height=3*inch))
                elements.append(Spacer(1, 10))
            
            resumen_mes = df.groupby(['AÑO', 'MES']).agg({
                'DIFERENCIA': ['sum', 'mean', 'count']
            }).round(0)
            resumen_mes.columns = ['Ahorro Total', 'Promedio', 'Reparaciones']
            resumen_mes = resumen_mes.reset_index()
            
            # Crear tabla mensual
            mes_table_data = [[
                Paragraph("<b>Año</b>", body_style),
                Paragraph("<b>Mes</b>", body_style),
                Paragraph("<b>Ahorro Total</b>", body_style),
                Paragraph("<b>Promedio</b>", body_style),
                Paragraph("<b>Reparaciones</b>", body_style),
            ]]
            
            for _, row in resumen_mes.iterrows():
                mes_num = int(row['MES']) if pd.notna(row['MES']) else None
                mes_nombre = MESES_ES.get(mes_num, str(row['MES'])) if mes_num else str(row['MES'])
                mes_table_data.append([
                    Paragraph(str(int(row['AÑO'])), body_style),
                    Paragraph(mes_nombre, body_style),
                    Paragraph(format_currency(row['Ahorro Total']), body_style),
                    Paragraph(format_currency(row['Promedio']), body_style),
                    Paragraph(f"{int(row['Reparaciones']):,}", body_style),
                ])
            
            mes_table = Table(mes_table_data, colWidths=[0.9*inch, 1.2*inch, 1.6*inch, 1.6*inch, 1.2*inch])
            mes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(mes_table)
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # COMPARATIVO DE AHORROS (Mensual y Trimestral con % Desviación)
        # =========================================================================
        comparativo_mes, comparativo_trim = _calcular_comparativo_ahorro_pdf(df)
        if not comparativo_mes.empty:
            elements.append(Paragraph("📈 Ahorros Generales - Comparativo con Desviación", heading_style))
            
            # Tabla mensual
            elements.append(Paragraph("Comparativo Mensual", subheading_style))
            comp_mes_data = [[
                Paragraph("<b>Período</b>", body_style),
                Paragraph("<b>Ahorro</b>", body_style),
                Paragraph("<b>Período Anterior</b>", body_style),
                Paragraph("<b>% Desviación</b>", body_style),
                Paragraph("<b>Tendencia</b>", body_style),
            ]]
            
            for _, row in comparativo_mes.iterrows():
                desv_color = colors.HexColor('#16A34A') if row['desviacion_pct'] > 0 else (
                    colors.HexColor('#DC2626') if row['desviacion_pct'] < 0 else colors.HexColor('#64748B')
                )
                comp_mes_data.append([
                    Paragraph(str(row['periodo']), body_style),
                    Paragraph(format_currency(row['DIFERENCIA']), body_style),
                    Paragraph(str(row['periodo_anterior']) if pd.notna(row['periodo_anterior']) else "-", body_style),
                    Paragraph(f"{row['desviacion_pct']:.1f}%", body_style),
                    Paragraph(str(row['indicador']), ParagraphStyle(
                        'Tendencia', parent=body_style, textColor=desv_color, fontName='Helvetica-Bold'
                    )),
                ])
            
            comp_mes_table = Table(comp_mes_data, colWidths=[1.2*inch, 1.4*inch, 1.4*inch, 1.2*inch, 1.3*inch])
            comp_mes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(comp_mes_table)
            elements.append(Spacer(1, 10))

            # Tabla trimestral — comparación homóloga (mismo trimestre, año anterior)
            if not comparativo_trim.empty and len(comparativo_trim) >= 1:
                elements.append(Paragraph("Comparativo Trimestral (Homólogo)", subheading_style))
                comp_trim_data = [[
                    Paragraph("<b>Período</b>", body_style),
                    Paragraph("<b>Ahorro</b>", body_style),
                    Paragraph("<b>Período Anterior</b>", body_style),
                    Paragraph("<b>% Desviación</b>", body_style),
                    Paragraph("<b>Tendencia</b>", body_style),
                ]]

                for _, row in comparativo_trim.iterrows():
                    desv_color = colors.HexColor('#16A34A') if row['desviacion_pct'] > 0 else (
                        colors.HexColor('#DC2626') if row['desviacion_pct'] < 0 else colors.HexColor('#64748B')
                    )
                    comp_trim_data.append([
                        Paragraph(str(row['periodo']), body_style),
                        Paragraph(format_currency(row['DIFERENCIA']), body_style),
                        Paragraph(str(row['periodo_anterior']) if pd.notna(row['periodo_anterior']) else "-", body_style),
                        Paragraph(f"{row['desviacion_pct']:.1f}%", body_style),
                        Paragraph(str(row['indicador']), ParagraphStyle(
                            'Tendencia', parent=body_style, textColor=desv_color, fontName='Helvetica-Bold'
                        )),
                    ])

                comp_trim_table = Table(comp_trim_data, colWidths=[1.2*inch, 1.4*inch, 1.4*inch, 1.2*inch, 1.3*inch])
                comp_trim_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))

                elements.append(comp_trim_table)
                elements.append(Spacer(1, 15))
        
        # =========================================================================
        # CAUSALES DE IMPREVISTOS (Barras - Total de Datos)
        # =========================================================================
        df_causales_imp = _calcular_causales_imprevistos_pdf(df)
        if not df_causales_imp.empty:
            elements.append(Paragraph("🔍 Causales de Imprevistos", heading_style))
            
            causal_imp_data = [[
                Paragraph("<b>Causal</b>", body_style),
                Paragraph("<b>Cantidad</b>", body_style),
                Paragraph("<b>% del Total</b>", body_style),
            ]]
            
            for _, row in df_causales_imp.iterrows():
                causal_imp_data.append([
                    Paragraph(str(row['causal']), body_style),
                    Paragraph(f"{int(row['cantidad']):,}", body_style),
                    Paragraph(f"{row['porcentaje']:.1f}%", body_style),
                ])
            
            causal_imp_table = Table(causal_imp_data, colWidths=[4*inch, 1.2*inch, 1.2*inch])
            causal_imp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(causal_imp_table)
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # TOP CAUSALES DE AHORRO
        # =========================================================================
        if 'CAUSAL' in df.columns:
            elements.append(Paragraph("🔍 Top 10 Causales de Ahorro", heading_style))
            
            resumen_causal = df.groupby('CAUSAL').agg({
                'DIFERENCIA': ['sum', 'count']
            }).round(0)
            resumen_causal.columns = ['Ahorro Total', 'Frecuencia']
            resumen_causal = resumen_causal.sort_values('Ahorro Total', ascending=False).head(10)
            resumen_causal = resumen_causal.reset_index()
            
            causal_table_data = [[
                Paragraph("<b>Causal</b>", body_style),
                Paragraph("<b>Ahorro Total</b>", body_style),
                Paragraph("<b>Frecuencia</b>", body_style),
            ]]
            
            for _, row in resumen_causal.iterrows():
                causal_table_data.append([
                    Paragraph(str(row['CAUSAL']), body_style),
                    Paragraph(format_currency(row['Ahorro Total']), body_style),
                    Paragraph(f"{int(row['Frecuencia']):,}", body_style),
                ])
            
            causal_table = Table(causal_table_data, colWidths=[3.5*inch, 1.8*inch, 1.2*inch])
            causal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(causal_table)
            elements.append(Spacer(1, 15))
    
    # =========================================================================
    # FOOTER
    # =========================================================================
    elements.append(Spacer(1, 30))
    elements.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#CBD5E1'),
            spaceAfter=10
        )
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#94A3B8'),
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    elements.append(Paragraph(
        f"Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", 
        footer_style
    ))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def generate_excel_report(df, filtros_aplicados, taller_nombre="Taller Hub"):
    """
    RF-004.1: Generar informe mensual automático en Excel
    Incluye múltiples hojas: Datos, Resumen, Gráficos
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja 1: Datos filtrados
        df_export = df.copy()
        # Formatear monedas para Excel
        for col in ['M._DE_O._INICIAL', 'M._DE_O._FINAL', 'DIFERENCIA']:
            if col in df_export.columns:
                df_export[col] = df_export[col].apply(lambda x: f"${x:,.0f}" if x != 0 else "")

        df_export.to_excel(writer, sheet_name='Datos Detallados', index=False)

        # Hoja 2: Resumen por mes
        if 'AÑO' in df.columns and 'MES' in df.columns:
            resumen_mes = df.groupby(['AÑO', 'MES']).agg({
                'DIFERENCIA': ['sum', 'mean', 'count'],
                'PLACA': 'nunique'
            }).round(0)
            resumen_mes.columns = ['Ahorro Total', 'Promedio', 'Cantidad Reparaciones', 'Vehículos Únicos']
            resumen_mes.to_excel(writer, sheet_name='Resumen Mensual')

        # Hoja 3: Resumen por compañía
        if 'COMPAÑIA_DE_SEGUROS' in df.columns:
            resumen_cia = df.groupby('COMPAÑIA_DE_SEGUROS').agg({
                'DIFERENCIA': ['sum', 'count'],
                'PLACA': 'nunique'
            }).round(0)
            resumen_cia.columns = ['Ahorro Total', 'Reparaciones', 'Vehículos']
            resumen_cia.to_excel(writer, sheet_name='Por Compañía')

        # Hoja 4: Causales
        if 'CAUSAL' in df.columns:
            resumen_causal = df.groupby('CAUSAL').agg({
                'DIFERENCIA': ['sum', 'count']
            }).round(0)
            resumen_causal.columns = ['Ahorro Total', 'Frecuencia']
            resumen_causal.to_excel(writer, sheet_name='Por Causal')

        # Hoja 5: Metadata del reporte
        metadata = pd.DataFrame({
            'Campo': ['Fecha de generación', 'Filtros aplicados', 'Total registros',
                     'Ahorro total', 'Usuario'],
            'Valor': [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                str(filtros_aplicados),
                len(df),
                f"${df['DIFERENCIA'].sum():,.0f}" if 'DIFERENCIA' in df.columns else 'N/A',
                taller_nombre
            ]
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)

    output.seek(0)
    return output


# =============================================================================
# HELPERS PRIVADOS — INFORME EJECUTIVO
# =============================================================================


def _exec_get_month_name(mes):
    """Retorna el nombre del mes en español."""
    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    return MESES_ES.get(int(mes), str(mes))


def _exec_add_narrative(elements, narrative_result):
    """Extiende elements con el resultado de una función narrativa."""
    if narrative_result is None:
        return
    if isinstance(narrative_result, list):
        elements.extend(narrative_result)
    else:
        elements.append(narrative_result)


def _exec_prepare_df_historico_cambio(df):
    """Prepara DataFrame con historial completo de imprevistos con cambio de repuestos.

    Usa la MISMA lógica que _generar_grafico_cambio_repuestos y el dashboard:
    cuenta registros con ACCION=CAMBIO cuyo CAUSAL indica culpa del taller
    (CAUSALES_CULPA_TALLER).
    """
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'ACCION' not in df.columns:
        return pd.DataFrame()
    df_w = df.copy()
    df_w['_ACCION'] = df_w['ACCION'].astype(str).str.upper().str.strip()
    df_w = df_w[df_w['_ACCION'].str.contains('CAMBIO', na=False)]
    if df_w.empty:
        return pd.DataFrame()
    df_w['_AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
    df_w['_MES'] = pd.to_numeric(df_w['MES'], errors='coerce')
    df_w = df_w[(df_w['_AÑO'].notna()) & (df_w['_MES'].notna()) &
                (df_w['_AÑO'] > 2000) & (df_w['_MES'] >= 1) & (df_w['_MES'] <= 12)]
    if df_w.empty:
        return pd.DataFrame()

    # Filtrar solo causales de culpa del taller (igual que el dashboard)
    df_w['_CAUSAL'] = (
        df_w['CAUSAL'].astype(str).str.upper().str.strip()
        if 'CAUSAL' in df_w.columns
        else ''
    )
    df_w['_CULPA'] = df_w['_CAUSAL'].isin(CAUSALES_CULPA_TALLER)

    resumen = df_w.groupby(['_AÑO', '_MES']).agg(
        cantidad=('_CULPA', 'sum')
    ).reset_index()
    resumen = resumen.sort_values(['_AÑO', '_MES'])
    MESES_ES = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    resumen['periodo'] = resumen.apply(
        lambda r: f"{MESES_ES.get(int(r['_MES']), str(int(r['_MES'])))} {int(r['_AÑO'])}", axis=1
    )
    resumen['año'] = resumen['_AÑO'].astype(int)
    resumen['mes'] = resumen['_MES'].astype(int)
    return resumen[['año', 'mes', 'periodo', 'cantidad']]


def _exec_get_cambio_counts_for_period(df_historico_cambio, año, mes):
    """Retorna conteos de cambio del mes seleccionado y del mes calendario anterior."""
    if (
        df_historico_cambio is None
        or df_historico_cambio.empty
        or not {'año', 'mes', 'cantidad'}.issubset(df_historico_cambio.columns)
    ):
        return 0, 0

    año = int(año)
    mes = int(mes)
    prev_año = año - 1 if mes == 1 else año
    prev_mes = 12 if mes == 1 else mes - 1

    df_w = df_historico_cambio.copy()
    df_w['año'] = pd.to_numeric(df_w['año'], errors='coerce')
    df_w['mes'] = pd.to_numeric(df_w['mes'], errors='coerce')
    df_w['cantidad'] = pd.to_numeric(df_w['cantidad'], errors='coerce').fillna(0)

    actual = df_w[(df_w['año'] == año) & (df_w['mes'] == mes)]['cantidad'].sum()
    anterior = df_w[(df_w['año'] == prev_año) & (df_w['mes'] == prev_mes)]['cantidad'].sum()
    return int(actual), int(anterior)


def _exec_prepare_df_mensual_ahorro(df):
    """Prepara DataFrame de ahorro por mes para narrativa y gráficos."""
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'DIFERENCIA' not in df.columns:
        return pd.DataFrame()
    df_w = df.copy()
    df_w['DIFERENCIA'] = pd.to_numeric(df_w['DIFERENCIA'], errors='coerce').fillna(0)
    df_w['AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
    df_w['MES'] = pd.to_numeric(df_w['MES'], errors='coerce')
    df_w = df_w[(df_w['AÑO'].notna()) & (df_w['MES'].notna()) &
                (df_w['AÑO'] > 2000) & (df_w['MES'] >= 1) & (df_w['MES'] <= 12)]
    if df_w.empty:
        return pd.DataFrame()
    resumen = df_w.groupby(['AÑO', 'MES'])['DIFERENCIA'].sum().reset_index()
    resumen = resumen.sort_values(['AÑO', 'MES'])
    MESES_ES = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    resumen['periodo'] = resumen.apply(
        lambda r: f"{MESES_ES.get(int(r['MES']), str(int(r['MES'])))} {int(r['AÑO'])}", axis=1
    )
    return resumen


def _exec_filter_df_mensual_until_period(df_mensual, año, mes):
    """Filtra el ahorro mensual desde el inicio de los datos hasta el período seleccionado."""
    if df_mensual is None or df_mensual.empty or not {'AÑO', 'MES'}.issubset(df_mensual.columns):
        return pd.DataFrame()

    df_w = df_mensual.copy()
    df_w['AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
    df_w['MES'] = pd.to_numeric(df_w['MES'], errors='coerce')
    df_w = df_w[
        df_w['AÑO'].notna()
        & df_w['MES'].notna()
        & (
            (df_w['AÑO'] < int(año))
            | ((df_w['AÑO'] == int(año)) & (df_w['MES'] <= int(mes)))
        )
    ].copy()
    return df_w.sort_values(['AÑO', 'MES']).reset_index(drop=True)


def _exec_prepare_comparativo_anual_2025_2026(df):
    """Prepara comparativo anual 2025 vs 2026 por mes."""
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'DIFERENCIA' not in df.columns:
        return pd.DataFrame()
    df_w = df.copy()
    df_w['DIFERENCIA'] = pd.to_numeric(df_w['DIFERENCIA'], errors='coerce').fillna(0)
    df_w['AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
    df_w['MES'] = pd.to_numeric(df_w['MES'], errors='coerce')
    df_w = df_w[(df_w['AÑO'].isin([2025, 2026])) & (df_w['MES'] >= 1) & (df_w['MES'] <= 12)]
    if df_w.empty:
        return pd.DataFrame()
    pivot = df_w.pivot_table(index='MES', columns='AÑO', values='DIFERENCIA', aggfunc='sum', fill_value=0).reset_index()
    if 2025 not in pivot.columns:
        pivot[2025] = 0
    if 2026 not in pivot.columns:
        pivot[2026] = 0
    total_2025 = pivot[2025].sum()
    total_2026 = pivot[2026].sum()
    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    pivot['MES_NOMBRE'] = pivot['MES'].apply(lambda m: MESES_ES.get(int(m), str(int(m))))
    pivot['PCT_2025'] = pivot[2025].apply(lambda x: round((x / total_2025 * 100), 1) if total_2025 > 0 else 0.0)
    pivot['PCT_2026'] = pivot[2026].apply(lambda x: round((x / total_2026 * 100), 1) if total_2026 > 0 else 0.0)
    pivot['TOTAL'] = pivot[2025] + pivot[2026]
    pivot['VARIACION'] = pivot.apply(
        lambda r: round(((r[2026] - r[2025]) / r[2025] * 100), 1) if r[2025] != 0 else 0.0, axis=1
    )
    return pivot[['MES_NOMBRE', 2025, 'PCT_2025', 2026, 'PCT_2026', 'TOTAL', 'VARIACION']]


def _exec_prepare_trimestral_2025_2026(df, año, mes):
    """Prepara tabla trimestral comparando 2025 vs 2026 para el trimestre del mes dado."""
    if df is None or df.empty or 'AÑO' not in df.columns or 'MES' not in df.columns or 'DIFERENCIA' not in df.columns:
        return pd.DataFrame(), 0.0
    trimestre = ((int(mes) - 1) // 3) + 1
    meses_trim = list(range((trimestre - 1) * 3 + 1, trimestre * 3 + 1))
    df_w = df.copy()
    df_w['DIFERENCIA'] = pd.to_numeric(df_w['DIFERENCIA'], errors='coerce').fillna(0)
    df_w['AÑO'] = pd.to_numeric(df_w['AÑO'], errors='coerce')
    df_w['MES'] = pd.to_numeric(df_w['MES'], errors='coerce')
    df_w = df_w[(df_w['AÑO'].isin([2025, 2026])) & (df_w['MES'].isin(meses_trim))]
    if df_w.empty:
        return pd.DataFrame(), 0.0
    resumen = df_w.groupby(['AÑO', 'MES'])['DIFERENCIA'].sum().reset_index()
    pivot = resumen.pivot_table(index='MES', columns='AÑO', values='DIFERENCIA', fill_value=0).reset_index()
    if 2025 not in pivot.columns:
        pivot[2025] = 0
    if 2026 not in pivot.columns:
        pivot[2026] = 0
    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    pivot['MES_NOMBRE'] = pivot['MES'].apply(lambda m: MESES_ES.get(int(m), str(int(m))))
    pivot['TOTAL'] = pivot[2025] + pivot[2026]
    pivot['VARIACION'] = pivot.apply(
        lambda r: round(((r[2026] - r[2025]) / r[2025] * 100), 1) if r[2025] != 0 else 0.0, axis=1
    )
    total_2025 = pivot[2025].sum()
    total_2026 = pivot[2026].sum()
    variacion = round(((total_2026 - total_2025) / total_2025 * 100), 1) if total_2025 != 0 else 0.0
    return pivot, variacion


def _exec_prepare_causales_dinero(df):
    """Prepara causales con recuperación de dinero."""
    if df is None or df.empty or 'CAUSAL' not in df.columns or 'DIFERENCIA' not in df.columns:
        return pd.DataFrame()
    df_w = df.copy()
    df_w['DIFERENCIA'] = pd.to_numeric(df_w['DIFERENCIA'], errors='coerce').fillna(0)
    df_w = df_w[df_w['CAUSAL'].notna() & (df_w['CAUSAL'].astype(str).str.strip() != '')]
    if df_w.empty:
        return pd.DataFrame()
    resumen = df_w.groupby('CAUSAL')['DIFERENCIA'].sum().reset_index()
    resumen.columns = ['CAUSAL', 'RECUPERACION']
    total = resumen['RECUPERACION'].sum()
    resumen['PCT'] = resumen['RECUPERACION'].apply(lambda x: round((x / total * 100), 1) if total > 0 else 0.0)
    resumen = resumen.sort_values('RECUPERACION', ascending=False).reset_index(drop=True)
    return resumen


# =============================================================================
# GENERAR INFORME EJECUTIVO PDF
# =============================================================================

def generate_executive_pdf_report(df, mes, año, include_honorarios=True, taller_nombre="Distrikia"):
    """
    Genera un PDF ejecutivo tipo informe mensual (similar al PDF de referencia del cliente).

    Args:
        df: DataFrame con todos los datos (puede ser acumulado hasta el mes).
        mes: int (1-12)
        año: int
        include_honorarios: bool
        taller_nombre: str

    Returns:
        io.BytesIO con el PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )
    elements = []

    mes_nombre = _exec_get_month_name(mes)

    # ------------------------------------------------------------------
    # Preparación de datos comunes
    # ------------------------------------------------------------------
    df_ahorro = filter_authorized_savings_records(df) if 'ESTATUS' in df.columns else df
    total_ahorro = df_ahorro['DIFERENCIA'].sum() if 'DIFERENCIA' in df_ahorro.columns else 0

    honorarios = 0
    if include_honorarios and 'DIFERENCIA' in df_ahorro.columns:
        try:
            fee_config = load_fee_config()
            fee_info = calculate_fees_per_month(df_ahorro, fee_config)
            honorarios = fee_info.get('total_honorarios', 0) if fee_info else 0
        except Exception:
            honorarios = 0

    utilidad = total_ahorro - honorarios

    # Cambio de repuestos del mes (culpa del taller)
    df_cambio_mes = _preparar_cambio_repuestos_pdf(df, año, mes)

    # Historial de imprevistos con cambio de repuestos, usado por el gráfico y la narrativa.
    df_historico_cambio = _exec_prepare_df_historico_cambio(df)
    cambios_count, cambios_count_anterior = _exec_get_cambio_counts_for_period(
        df_historico_cambio, año, mes
    )

    # Tasa histórica
    df_tasa_historico = _calcular_tasa_imprevistos_pdf(df)
    tasa_actual = 0.0
    tasa_anterior = 0.0
    vehiculos_entregados = 0
    total_imprevistos_tasa = 0
    if not df_tasa_historico.empty:
        df_tasa_historico = df_tasa_historico.sort_values(['año', 'mes']).reset_index(drop=True)
        df_tasa_actual = df_tasa_historico[
            (df_tasa_historico['año'] == int(año)) & (df_tasa_historico['mes'] == int(mes))
        ]
        if not df_tasa_actual.empty:
            tasa_actual = df_tasa_actual['tasa'].values[0]
            vehiculos_entregados = int(df_tasa_actual['total_vehiculos'].values[0])
            total_imprevistos_tasa = int(df_tasa_actual['total_imprevistos'].values[0])
            idx = df_tasa_actual.index[0]
            if idx > 0:
                tasa_anterior = df_tasa_historico.loc[idx - 1, 'tasa']

    # Ahorro mensual
    df_mensual = _exec_prepare_df_mensual_ahorro(df)

    # Comparativo anual 2025 vs 2026
    comparativo_df = _exec_prepare_comparativo_anual_2025_2026(df)

    # Trimestral 2025 vs 2026
    trimestral_df, variacion_trimestral_pct = _exec_prepare_trimestral_2025_2026(df, año, mes)

    # Causales con dinero
    df_causales_dinero = _exec_prepare_causales_dinero(df)

    # ======================================================================
    # PÁGINA 1 — Portada + Introducción + KPIs + Gestión Imprevistos
    # ======================================================================
    _exec_add_narrative(elements, narrativa_corte_y_saludo(mes_nombre, año))
    elements.append(Spacer(1, 12))
    _exec_add_narrative(elements, narrativa_introduccion(mes_nombre, año, total_ahorro, honorarios, utilidad))
    elements.append(Spacer(1, 12))

    # KPIs
    kpi_cards = [
        {"label": "Ahorro Acumulado", "value": format_currency(total_ahorro), "icon": "💰"},
    ]
    if include_honorarios:
        kpi_cards.append({"label": "Valor Honorarios", "value": format_currency(honorarios), "icon": "📊"})
    kpi_cards.append({"label": "Utilidad Taller", "value": format_currency(utilidad), "icon": "✅"})
    elements.append(build_kpi_row(kpi_cards))
    elements.append(Spacer(1, 16))

    _exec_add_narrative(elements, narrativa_ahorros_generados(total_ahorro, honorarios, utilidad))
    elements.append(Spacer(1, 8))
    _exec_add_narrative(elements, narrativa_gestion_imprevistos(cambios_count, cambios_count_anterior))
    elements.append(Spacer(1, 12))

    # Gráfico imprevistos histórico
    if not df_historico_cambio.empty:
        buf_imp = generar_grafico_imprevistos_ejecutivo(df_historico_cambio)
        if buf_imp:
            elements.append(Image(buf_imp, width=6.5 * inch, height=3.25 * inch))
    else:
        elements.append(build_body_paragraph("No hay datos históricos de imprevistos con cambio de repuestos."))

    # No forzar salto de página; dejar que el contenido fluya naturalmente
    elements.append(Spacer(1, 16))

    # ======================================================================
    # PÁGINA 2 — Detalle Imprevistos + Tasa
    # ======================================================================
    _exec_add_narrative(elements, narrativa_imprevistos_cambio_detalle(df_cambio_mes))
    elements.append(Spacer(1, 10))

    # Tabla imprevistos del mes
    if not df_cambio_mes.empty and all(c in df_cambio_mes.columns for c in ['PLACA', 'CIA', 'IMPREVISTO', 'CAUSAL']):
        tabla_data = df_cambio_mes[['PLACA', 'CIA', 'IMPREVISTO', 'CAUSAL']].astype(str).values.tolist()
        elements.append(build_executive_table(
            tabla_data,
            ['PLACA', 'CIA', 'IMPREVISTO', 'CAUSAL']
        ))
    else:
        elements.append(build_body_paragraph("No hay imprevistos con cambio de repuestos para el mes en curso."))

    elements.append(Spacer(1, 12))
    _exec_add_narrative(elements, narrativa_tasa_imprevistos(tasa_actual, tasa_anterior, vehiculos_entregados, total_imprevistos_tasa))
    elements.append(Spacer(1, 10))

    # Gráfico tasa
    if not df_tasa_historico.empty:
        buf_tasa = generar_grafico_tasa_ejecutivo(df_tasa_historico)
        if buf_tasa:
            elements.append(Image(buf_tasa, width=6.5 * inch, height=3.25 * inch))
    else:
        elements.append(build_body_paragraph("No hay datos históricos de tasa de imprevistos."))

    elements.append(PageBreak())

    # ======================================================================
    # PÁGINA 3 — Narrativa + Ahorro por Mes
    # ======================================================================
    elements.append(build_body_paragraph(
        "A continuación se presenta el desglose del ahorro por mes, "
        "comparando el desempeño del taller a lo largo del tiempo."
    ))
    elements.append(Spacer(1, 10))
    _exec_add_narrative(elements, narrativa_ahorro_por_mes(df_mensual, año=año, mes=mes))
    elements.append(Spacer(1, 12))

    df_ahorro_mes_grafico = _exec_filter_df_mensual_until_period(df_mensual, año, mes)
    if not df_ahorro_mes_grafico.empty:
        buf_ahorro_mes = generar_grafico_ahorro_comparativo_historico_ejecutivo(df_ahorro_mes_grafico)
        if buf_ahorro_mes:
            elements.append(Image(buf_ahorro_mes, width=6.5 * inch, height=3.25 * inch))
    else:
        elements.append(build_body_paragraph("No hay datos mensuales de ahorro hasta el período seleccionado."))

    elements.append(PageBreak())

    # ======================================================================
    # PÁGINA 4 — Tabla Comparativa Anual + Trimestre
    # ======================================================================
    elements.append(build_section_title("AHORROS GENERALES DEL PROYECTO"))
    elements.append(Spacer(1, 8))

    if not comparativo_df.empty:
        # Filtrar meses futuros: mapear nombre de mes a número y filtrar
        MES_A_NUM = {
            'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
            'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
        }
        comp_data = []
        for _, row in comparativo_df.iterrows():
            mes_num = MES_A_NUM.get(str(row['MES_NOMBRE']), 0)
            # Para 2026, no mostrar meses después del mes seleccionado
            if mes_num > int(mes):
                continue
            comp_data.append([
                str(row['MES_NOMBRE']),
                format_currency(row[2025]),
                f"{row['PCT_2025']:.1f}%",
                format_currency(row[2026]),
                f"{row['PCT_2026']:.1f}%",
                format_currency(row['TOTAL']),
                f"{row['VARIACION']:.1f}%",
            ])
        # Fila total (solo con los meses filtrados)
        df_filtrado = comparativo_df[
            comparativo_df['MES_NOMBRE'].apply(lambda x: MES_A_NUM.get(str(x), 0) <= int(mes))
        ].copy()
        total_2025_sum = df_filtrado[2025].sum()
        total_2026_sum = df_filtrado[2026].sum()
        total_sum = df_filtrado['TOTAL'].sum()
        total_var = round(((total_2026_sum - total_2025_sum) / total_2025_sum * 100), 1) if total_2025_sum != 0 else 0.0
        comp_data.append([
            "TOTAL",
            format_currency(total_2025_sum),
            "100.0%",
            format_currency(total_2026_sum),
            "100.0%",
            format_currency(total_sum),
            f"{total_var:.1f}%",
        ])
        col_w = [CONTENT_WIDTH / 7] * 7
        elements.append(build_executive_table(
            comp_data,
            ['MES', 'AHORRO 2025', '%', 'AHORRO 2026', '%', 'TOTAL AHORRADO', 'VARIACIÓN'],
            col_widths=col_w,
            has_total_row=True
        ))
    else:
        elements.append(build_body_paragraph("No hay datos suficientes para el comparativo anual."))

    elements.append(Spacer(1, 12))
    _exec_add_narrative(elements, narrativa_comparativo_anual(comparativo_df, año=año, mes=mes))
    elements.append(Spacer(1, 8))
    _exec_add_narrative(elements, narrativa_ahorro_trimestre(variacion_trimestral_pct))

    elements.append(PageBreak())

    # ======================================================================
    # PÁGINA 5 — Tabla Trimestral + Causales
    # ======================================================================
    elements.append(build_section_title("COMPARATIVO TRIMESTRAL"))
    elements.append(Spacer(1, 8))

    if not trimestral_df.empty:
        trim_data = []
        for _, row in trimestral_df.iterrows():
            trim_data.append([
                str(row['MES_NOMBRE']),
                format_currency(row[2025]),
                format_currency(row[2026]),
                format_currency(row['TOTAL']),
                f"{row['VARIACION']:.1f}%",
            ])
        col_w = [CONTENT_WIDTH / 5] * 5
        elements.append(build_executive_table(
            trim_data,
            ['MES', '2025', '2026', 'Total', 'Variación'],
            col_widths=col_w
        ))
    else:
        elements.append(build_body_paragraph("No hay datos suficientes para el comparativo trimestral."))

    elements.append(Spacer(1, 12))

    df_causales = _calcular_causales_imprevistos_pdf(df)
    _exec_add_narrative(elements, narrativa_causales(df_causales))
    elements.append(Spacer(1, 8))

    # Tabla causales por imprevisto (con dinero)
    if not df_causales_dinero.empty:
        caus_data = []
        for _, row in df_causales_dinero.iterrows():
            caus_data.append([
                str(row['CAUSAL']),
                format_currency(row['RECUPERACION']),
                f"{row['PCT']:.1f}%",
            ])
        col_w = [CONTENT_WIDTH * 0.5, CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.25]
        elements.append(build_executive_table(
            caus_data,
            ['CAUSAS', 'RECUPERACIÓN $', '% RELATIVO'],
            col_widths=col_w
        ))
    else:
        elements.append(build_body_paragraph("No hay datos de causales con recuperación de dinero."))

    # Nota: secciones omitidas a solicitud del cliente (2026-05-19):
    # - Página 6: No Cotizados + Cambio Piezas
    # - Página 7: Tabla Cambio Piezas + cierre ejecutivo

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_csv_export(df):
    """RF-004.3, RF-004.4: Exportar datos filtrados"""
    return df.to_csv(index=False).encode('utf-8')

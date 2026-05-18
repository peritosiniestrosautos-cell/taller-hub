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
        return resumen, trimestral

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


def generate_pdf_report(df, filtros_aplicados, include_honorarios=True, taller_nombre="Taller Hub", filtros_graficos=None):
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
        # IMPREVISTOS CON CAMBIO DE REPUESTOS (Gráfico + Tabla del mes en curso)
        # =========================================================================
        ahora = datetime.now()
        año_actual = ahora.year
        mes_actual = ahora.month
        df_cambio_rep = _preparar_cambio_repuestos_pdf(df, año=año_actual, mes=mes_actual)
        
        # Gráfico histórico (siempre mostrar si hay datos de cambio)
        grafico_cambio_buf = _generar_grafico_cambio_repuestos(df)
        if grafico_cambio_buf:
            elements.append(Paragraph("🔧 Imprevistos con Cambio de Repuestos", heading_style))
            elements.append(Image(grafico_cambio_buf, width=6.5*inch, height=3*inch))
            elements.append(Spacer(1, 10))
        
        if not df_cambio_rep.empty:
            mes_nombre_actual = MESES_ES.get(mes_actual, str(mes_actual))
            elements.append(Paragraph(f"Detalle del Mes en Curso ({mes_nombre_actual} {año_actual})", subheading_style))
            
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
            # Si hay gráfico pero no hay datos para el mes actual, mostrar mensaje
            mes_nombre_actual = MESES_ES.get(mes_actual, str(mes_actual))
            elements.append(Paragraph(f"No hay imprevistos con cambio de repuestos para {mes_nombre_actual} {año_actual}.", body_style))
            elements.append(Spacer(1, 15))
        
        # =========================================================================
        # RESUMEN MENSUAL (Ahorro por Mes)
        # =========================================================================
        if 'AÑO' in df.columns and 'MES' in df.columns:
            elements.append(Paragraph("📅 Ahorro por Mes", heading_style))
            
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
    # FILTROS APLICADOS A GRÁFICOS
    # =========================================================================
    if filtros_graficos and any(v for v in filtros_graficos.values()):
        elements.append(Paragraph("⚙️ Filtros Aplicados a Gráficos", heading_style))
        
        filtros_graf_data = [[
            Paragraph("<b>Gráfico</b>", body_style),
            Paragraph("<b>Filtros</b>", body_style),
        ]]
        
        for grafico, filtros in filtros_graficos.items():
            if filtros:
                filtros_str = ", ".join([f"{k}: {v}" for k, v in filtros.items() if v])
                if filtros_str:
                    filtros_graf_data.append([
                        Paragraph(str(grafico), body_style),
                        Paragraph(filtros_str, body_style),
                    ])
        
        if len(filtros_graf_data) > 1:
            filtros_graf_table = Table(filtros_graf_data, colWidths=[2*inch, 4.5*inch])
            filtros_graf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(filtros_graf_table)
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


def generate_csv_export(df):
    """RF-004.3, RF-004.4: Exportar datos filtrados"""
    return df.to_csv(index=False).encode('utf-8')

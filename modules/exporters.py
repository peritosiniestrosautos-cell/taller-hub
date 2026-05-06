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
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
from .fee_config import load_fee_config, calculate_fees_per_month, format_currency

PDF_KPI_FONT_SIZE = 10


def _format_honorarios_kpi_value(honorarios, fee_percentage=None):
    """Return the honorarios KPI text shown in the PDF summary."""
    return format_currency(honorarios)


def generate_pdf_report(df, filtros_aplicados, include_honorarios=True, taller_nombre="Taller Hub"):
    """
    Generar reporte PDF del dashboard actual
    
    Args:
        df: DataFrame con los datos filtrados
        filtros_aplicados: Diccionario con los filtros aplicados
        include_honorarios: Boolean para incluir/excluir honorarios
    
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
    
    # =========================================================================
    # HEADER DEL DOCUMENTO
    # =========================================================================
    elements.append(Paragraph("🚗 TALLER HUB", title_style))
    elements.append(
        Paragraph("Sistema de Gestión de Ahorros y Análisis de Talleres Automotrices", subtitle_style)
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
        vehiculos_unicos = df['PLACA'].nunique() if 'PLACA' in df.columns else 0
        total_reparaciones = len(df)
        
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
                Paragraph("<b>🚗 Vehículos</b>", kpi_label_style),
                Paragraph("<b>🔧 Reparaciones</b>", kpi_label_style),
            ]
        ]
        
        kpi_values = [
            [
                Paragraph(format_currency(total_ahorro), kpi_style),
                Paragraph(f"{vehiculos_unicos:,}", kpi_style),
                Paragraph(f"{total_reparaciones:,}", kpi_style),
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
            col_widths = [1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch]
        else:
            col_widths = [2*inch, 2*inch, 2*inch]
        
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
                vehiculos_taller = df_taller['PLACA'].nunique() if 'PLACA' in df_taller.columns else 0
                reparaciones_taller = len(df_taller)
                
                row_data = [
                    Paragraph(taller_id, body_style),
                    Paragraph(format_currency(ahorro_taller), body_style),
                    Paragraph(f"{vehiculos_taller:,}", body_style),
                    Paragraph(f"{reparaciones_taller:,}", body_style),
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
                Paragraph("<b>Vehículos</b>", body_style),
                Paragraph("<b>Reparaciones</b>", body_style),
            ]
            
            if include_honorarios and fee_info:
                taller_headers.append(Paragraph("<b>Honorarios</b>", body_style))
            
            taller_table_data = [taller_headers] + talleres_resumen
            
            # Anchuras de columna
            if include_honorarios and fee_info:
                taller_col_widths = [1.5*inch, 1.3*inch, 1.1*inch, 1.1*inch, 1.5*inch]
            else:
                taller_col_widths = [2*inch, 1.5*inch, 1.3*inch, 1.7*inch]
            
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
        # RESUMEN MENSUAL
        # =========================================================================
        if 'AÑO' in df.columns and 'MES' in df.columns:
            elements.append(Paragraph("📅 Resumen Mensual", heading_style))
            
            resumen_mes = df.groupby(['AÑO', 'MES']).agg({
                'DIFERENCIA': ['sum', 'mean', 'count'],
                'PLACA': 'nunique' if 'PLACA' in df.columns else 'count'
            }).round(0)
            resumen_mes.columns = ['Ahorro Total', 'Promedio', 'Reparaciones', 'Vehículos']
            resumen_mes = resumen_mes.reset_index()
            
            # Crear tabla mensual
            mes_table_data = [[
                Paragraph("<b>Año</b>", body_style),
                Paragraph("<b>Mes</b>", body_style),
                Paragraph("<b>Ahorro Total</b>", body_style),
                Paragraph("<b>Promedio</b>", body_style),
                Paragraph("<b>Reparaciones</b>", body_style),
                Paragraph("<b>Vehículos</b>", body_style),
            ]]
            
            for _, row in resumen_mes.iterrows():
                mes_table_data.append([
                    Paragraph(str(int(row['AÑO'])), body_style),
                    Paragraph(str(row['MES']), body_style),
                    Paragraph(format_currency(row['Ahorro Total']), body_style),
                    Paragraph(format_currency(row['Promedio']), body_style),
                    Paragraph(f"{int(row['Reparaciones']):,}", body_style),
                    Paragraph(f"{int(row['Vehículos']):,}", body_style),
                ])
            
            mes_table = Table(mes_table_data, colWidths=[0.7*inch, 0.9*inch, 1.3*inch, 1.3*inch, 1.1*inch, 1.2*inch])
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
        # TOP CAUSALES
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
    
    elements.append(Paragraph(f"{taller_nombre} v2.0 | Desarrollado para RENOMOTRIZ", footer_style))
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

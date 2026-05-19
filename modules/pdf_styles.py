"""
================================================================================
PDF STYLES — Tema Ejecutivo para Informes Distrikia
================================================================================
Constantes de color, fuentes y estilos ParagraphStyle para generar PDFs
tipo informe ejecutivo (similar al PDF de referencia entregado por el cliente).

Uso:
    from modules.pdf_styles import EXEC_COLORS, get_executive_styles
    styles = get_executive_styles()
    elements.append(Paragraph("Título", styles['EXEC_TITLE']))
"""

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import inch

# =============================================================================
# PALETA DE COLORES EJECUTIVA (extraída del PDF de referencia)
# =============================================================================
EXEC_COLORS = {
    # Fondos principales
    "teal_dark":       HexColor("#1B4D4D"),   # Tarjetas KPI principales
    "teal_medium":     HexColor("#2A7A7A"),   # Tarjetas KPI secundarias / acentos
    "teal_chart":      HexColor("#2A9D8F"),   # Fondo de gráficos (verde agua)
    "teal_chart_dark": HexColor("#1F7A6F"),   # Variante oscura para gráficos
    "teal_light":      HexColor("#4ECDC4"),   # Líneas / puntos en gráficos

    # Tablas
    "gray_header":     HexColor("#666666"),   # Header de tablas (gris oscuro)
    "gray_header_text":HexColor("#FFFFFF"),   # Texto en header de tablas
    "gray_light":      HexColor("#F5F5F5"),   # Filas alternadas
    "gray_border":     HexColor("#CCCCCC"),   # Bordes de tablas

    # Texto
    "black":           HexColor("#1E293B"),   # Texto principal (casi negro)
    "white":           HexColor("#FFFFFF"),   # Texto sobre fondos oscuros
    "gray_body":       HexColor("#4B5563"),   # Texto secundario

    # Variaciones / indicadores
    "yellow_accent":   HexColor("#FFD700"),   # Positivo / variación favorable
    "red_accent":      HexColor("#E74C3C"),   # Negativo / variación desfavorable
    "green_total":     HexColor("#27AE60"),   # Totales / resaltado verde
}

# =============================================================================
# CONFIGURACIÓN DE FUENTES
# =============================================================================
FONT_BOLD = "Helvetica-Bold"
FONT_NORMAL = "Helvetica"
FONT_OBLIQUE = "Helvetica-Oblique"

# =============================================================================
# DIMENSIONES Y LAYOUT
# =============================================================================
PAGE_WIDTH = 8.5 * inch
PAGE_HEIGHT = 11 * inch
MARGIN = 0.75 * inch
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)  # ~7.0 pulgadas

# =============================================================================
# ESTILOS PARAGRAPH PRE-CONFIGURADOS
# =============================================================================

def get_executive_styles():
    """
    Retorna un diccionario con todos los ParagraphStyle del tema ejecutivo.
    """
    return {
        # ------------------------------------------------------------------
        # Encabezados del documento
        # ------------------------------------------------------------------
        "EXEC_CORTE": ParagraphStyle(
            "ExecCorte",
            fontName=FONT_BOLD,
            fontSize=14,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=18,
        ),
        "EXEC_GREETING": ParagraphStyle(
            "ExecGreeting",
            fontName=FONT_BOLD,
            fontSize=12,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            spaceAfter=12,
            leading=16,
        ),
        "EXEC_SECTION_HEAD": ParagraphStyle(
            "ExecSectionHead",
            fontName=FONT_BOLD,
            fontSize=11,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            spaceBefore=18,
            spaceAfter=8,
            leading=14,
        ),
        "EXEC_SUB_HEAD": ParagraphStyle(
            "ExecSubHead",
            fontName=FONT_BOLD,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            spaceBefore=12,
            spaceAfter=6,
            leading=13,
        ),

        # ------------------------------------------------------------------
        # Cuerpo de texto
        # ------------------------------------------------------------------
        "EXEC_BODY": ParagraphStyle(
            "ExecBody",
            fontName=FONT_NORMAL,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14,
        ),
        "EXEC_BODY_BOLD": ParagraphStyle(
            "ExecBodyBold",
            fontName=FONT_BOLD,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=14,
        ),
        "EXEC_BULLET": ParagraphStyle(
            "ExecBullet",
            fontName=FONT_NORMAL,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            leftIndent=18,
            bulletIndent=8,
            spaceAfter=4,
            leading=14,
            bulletFontName=FONT_NORMAL,
            bulletFontSize=10,
        ),
        "EXEC_BULLET_BOLD": ParagraphStyle(
            "ExecBulletBold",
            fontName=FONT_BOLD,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            leftIndent=18,
            bulletIndent=8,
            spaceAfter=4,
            leading=14,
            bulletFontName=FONT_BOLD,
            bulletFontSize=10,
        ),
        "EXEC_BULLET_INDENT2": ParagraphStyle(
            "ExecBulletIndent2",
            fontName=FONT_NORMAL,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            leftIndent=36,
            bulletIndent=26,
            spaceAfter=4,
            leading=14,
            bulletFontName=FONT_NORMAL,
            bulletFontSize=10,
        ),

        # ------------------------------------------------------------------
        # KPIs — Tarjetas
        # ------------------------------------------------------------------
        "EXEC_KPI_LABEL": ParagraphStyle(
            "ExecKPILabel",
            fontName=FONT_BOLD,
            fontSize=8,
            textColor=EXEC_COLORS["white"],
            alignment=TA_CENTER,
            spaceAfter=4,
            leading=10,
        ),
        "EXEC_KPI_VALUE": ParagraphStyle(
            "ExecKPIValue",
            fontName=FONT_BOLD,
            fontSize=12,
            textColor=EXEC_COLORS["white"],
            alignment=TA_CENTER,
            spaceAfter=2,
            leading=16,
        ),
        "EXEC_KPI_ICON": ParagraphStyle(
            "ExecKPIIcon",
            fontName=FONT_NORMAL,
            fontSize=14,
            textColor=EXEC_COLORS["white"],
            alignment=TA_CENTER,
            spaceAfter=2,
            leading=18,
        ),

        # ------------------------------------------------------------------
        # Tablas
        # ------------------------------------------------------------------
        "EXEC_TABLE_HEADER": ParagraphStyle(
            "ExecTableHeader",
            fontName=FONT_BOLD,
            fontSize=9,
            textColor=EXEC_COLORS["gray_header_text"],
            alignment=TA_CENTER,
            leading=12,
        ),
        "EXEC_TABLE_BODY": ParagraphStyle(
            "ExecTableBody",
            fontName=FONT_NORMAL,
            fontSize=9,
            textColor=EXEC_COLORS["black"],
            alignment=TA_CENTER,
            leading=12,
        ),
        "EXEC_TABLE_BODY_LEFT": ParagraphStyle(
            "ExecTableBodyLeft",
            fontName=FONT_NORMAL,
            fontSize=9,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            leading=12,
        ),
        "EXEC_TABLE_TOTAL": ParagraphStyle(
            "ExecTableTotal",
            fontName=FONT_BOLD,
            fontSize=9,
            textColor=EXEC_COLORS["white"],
            alignment=TA_CENTER,
            leading=12,
        ),
        "EXEC_TABLE_TOTAL_LEFT": ParagraphStyle(
            "ExecTableTotalLeft",
            fontName=FONT_BOLD,
            fontSize=9,
            textColor=EXEC_COLORS["white"],
            alignment=TA_LEFT,
            leading=12,
        ),

        # ------------------------------------------------------------------
        # Conclusión / cierre
        # ------------------------------------------------------------------
        "EXEC_CONCLUSION_TITLE": ParagraphStyle(
            "ExecConclusionTitle",
            fontName=FONT_BOLD,
            fontSize=11,
            textColor=EXEC_COLORS["black"],
            alignment=TA_LEFT,
            spaceBefore=18,
            spaceAfter=8,
            leading=14,
        ),
        "EXEC_CONCLUSION_BODY": ParagraphStyle(
            "ExecConclusionBody",
            fontName=FONT_NORMAL,
            fontSize=10,
            textColor=EXEC_COLORS["black"],
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14,
        ),
    }

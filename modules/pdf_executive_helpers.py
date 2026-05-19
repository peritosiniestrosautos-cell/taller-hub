"""
================================================================================
PDF EXECUTIVE HELPERS — Constructores visuales para informes ejecutivos
================================================================================
Funciones helper para construir tarjetas KPI, tablas, títulos, párrafos y
listas con el estilo ejecutivo definido en pdf_styles.py.
"""

from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.colors import HexColor

from .pdf_styles import (
    EXEC_COLORS,
    FONT_BOLD,
    FONT_NORMAL,
    CONTENT_WIDTH,
    get_executive_styles,
)


def _get_style(name):
    """Obtiene un ParagraphStyle del diccionario de estilos ejecutivos."""
    return get_executive_styles()[name]


def _escape_xml(text):
    """Escapa caracteres XML para uso seguro en reportlab Paragraph."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------------------
# 1. Tarjeta KPI
# ------------------------------------------------------------------------------
def build_kpi_card(label, value, icon_text, width, bg_color=None):
    """
    Construye una tarjeta KPI como ``reportlab.platypus.Table``.

    Parámetros
    ----------
    label : str
        Etiqueta descriptiva (se muestra en mayúsculas).
    value : str
        Valor monetario / numérico.
    icon_text : str
        Emoji o carácter de icono (ej: "💰"). Ignorado; se mantiene para compatibilidad.
    width : float
        Ancho de la tarjeta en puntos.
    bg_color : reportlab.lib.colors.Color, optional
        Color de fondo. Por defecto ``EXEC_COLORS["teal_dark"]``.

    Retorna
    -------
    reportlab.platypus.Table
    """
    bg = bg_color or EXEC_COLORS["teal_dark"]

    label_para = Paragraph(str(label).upper(), _get_style("EXEC_KPI_LABEL"))
    value_para = Paragraph(str(value), _get_style("EXEC_KPI_VALUE"))

    data = [[label_para], [value_para]]
    table = Table(data, colWidths=[width])

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


# ------------------------------------------------------------------------------
# 2. Fila de tarjetas KPI
# ------------------------------------------------------------------------------
def build_kpi_row(cards_data):
    """
    Construye una fila horizontal de tarjetas KPI.

    Parámetros
    ----------
    cards_data : list[dict]
        Cada dict debe tener las claves: ``label``, ``value``, ``icon`` y
        opcionalmente ``bg`` (color de fondo).

    Retorna
    -------
    reportlab.platypus.Table
    """
    if not cards_data:
        return Table([[]], colWidths=[CONTENT_WIDTH])

    n = len(cards_data)
    gap = 8
    card_width = (CONTENT_WIDTH - (gap * (n - 1))) / n

    cells = []
    widths = []
    for i, card in enumerate(cards_data):
        cells.append(
            build_kpi_card(
                label=card.get("label", ""),
                value=card.get("value", ""),
                icon_text=card.get("icon", ""),
                width=card_width,
                bg_color=card.get("bg"),
            )
        )
        widths.append(card_width)
        if i < n - 1:
            cells.append("")
            widths.append(gap)

    row = Table([cells], colWidths=widths, hAlign="LEFT")
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return row


# ------------------------------------------------------------------------------
# 3. Tabla ejecutiva
# ------------------------------------------------------------------------------
def build_executive_table(data, headers, col_widths=None, has_total_row=False):
    """
    Construye una tabla estilo ejecutivo con header, filas alternadas y
    opcional fila de totales.

    Parámetros
    ----------
    data : list[list[str]]
        Filas de datos. Cada celda debe ser un string.
    headers : list[str]
        Lista de encabezados para la primera fila.
    col_widths : list[float], optional
        Anchos de columna. Si es ``None`` se distribuye ``CONTENT_WIDTH``
        equitativamente.
    has_total_row : bool
        Si ``True``, la última fila de *data* se pinta con fondo oscuro y
        texto blanco como fila de totales.

    Retorna
    -------
    reportlab.platypus.Table | None
    """
    styles = get_executive_styles()
    n_cols = len(headers)

    if col_widths is None:
        col_widths = [CONTENT_WIDTH / n_cols] * n_cols

    # Caso vacío: devolver tabla mínima con headers o None
    if not data:
        if headers:
            header_paras = [Paragraph(str(h), styles["EXEC_TABLE_HEADER"]) for h in headers]
            t = Table([header_paras], colWidths=col_widths)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), EXEC_COLORS["gray_header"]),
                        ("TEXTCOLOR", (0, 0), (-1, 0), EXEC_COLORS["white"]),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 0.5, EXEC_COLORS["gray_border"]),
                    ]
                )
            )
            return t
        return None

    all_rows = []
    header_paras = [Paragraph(str(h), styles["EXEC_TABLE_HEADER"]) for h in headers]
    all_rows.append(header_paras)

    for r_idx, row in enumerate(data):
        row_paras = []
        for c_idx, cell in enumerate(row):
            if has_total_row and r_idx == len(data) - 1:
                style_name = (
                    "EXEC_TABLE_TOTAL_LEFT"
                    if c_idx == 0
                    else "EXEC_TABLE_TOTAL"
                )
            else:
                style_name = (
                    "EXEC_TABLE_BODY_LEFT"
                    if c_idx == 0
                    else "EXEC_TABLE_BODY"
                )
            row_paras.append(Paragraph(str(cell), styles[style_name]))
        all_rows.append(row_paras)

    t = Table(all_rows, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), EXEC_COLORS["gray_header"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), EXEC_COLORS["white"]),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, EXEC_COLORS["gray_border"]),
    ]

    for r_idx in range(1, len(all_rows)):
        if has_total_row and r_idx == len(all_rows) - 1:
            style_cmds.append(
                ("BACKGROUND", (0, r_idx), (-1, r_idx), EXEC_COLORS["teal_dark"])
            )
            style_cmds.append(
                ("TEXTCOLOR", (0, r_idx), (-1, r_idx), EXEC_COLORS["white"])
            )
            style_cmds.append(
                ("FONTNAME", (0, r_idx), (-1, r_idx), FONT_BOLD)
            )
        else:
            if r_idx % 2 == 0:
                style_cmds.append(
                    ("BACKGROUND", (0, r_idx), (-1, r_idx), EXEC_COLORS["gray_light"])
                )

    t.setStyle(TableStyle(style_cmds))
    return t


# ------------------------------------------------------------------------------
# 4. Título de sección
# ------------------------------------------------------------------------------
def build_section_title(text):
    """
    Retorna un ``Paragraph`` con estilo ``EXEC_SECTION_HEAD`` en mayúsculas.
    """
    return Paragraph(str(text).upper(), _get_style("EXEC_SECTION_HEAD"))


# ------------------------------------------------------------------------------
# 5. Sub-título de sección
# ------------------------------------------------------------------------------
def build_sub_section_title(text):
    """
    Retorna un ``Paragraph`` con estilo ``EXEC_SUB_HEAD``.
    """
    return Paragraph(str(text), _get_style("EXEC_SUB_HEAD"))


# ------------------------------------------------------------------------------
# 6. Párrafo de cuerpo con frases en negrita opcionales
# ------------------------------------------------------------------------------
def build_body_paragraph(text, bold_phrases=None):
    """
    Retorna un ``Paragraph`` con estilo ``EXEC_BODY``.

    Parámetros
    ----------
    text : str
        Texto del párrafo.
    bold_phrases : list[str], optional
        Frases que se envolverán en ``<b>...</b>`` dentro del texto.
    """
    safe_text = _escape_xml(str(text))

    if bold_phrases:
        # Ordenar de más larga a más corta para evitar reemplazos parciales
        for phrase in sorted(bold_phrases, key=len, reverse=True):
            safe_phrase = _escape_xml(phrase)
            safe_text = safe_text.replace(safe_phrase, f"<b>{safe_phrase}</b>")

    return Paragraph(safe_text, _get_style("EXEC_BODY"))


# ------------------------------------------------------------------------------
# 7. Lista de bullets
# ------------------------------------------------------------------------------
def build_bullet_list(items, bold_prefix=False):
    """
    Retorna una lista de ``Paragraph`` con estilo ``EXEC_BULLET``.

    Parámetros
    ----------
    items : list[str]
        Elementos de la lista.
    bold_prefix : bool
        Si ``True``, pone en negrita el texto antes del primer ``":"``.

    Retorna
    -------
    list[Paragraph]
    """
    style = _get_style("EXEC_BULLET")
    paragraphs = []

    for item in items:
        raw = str(item)
        if bold_prefix and ":" in raw:
            prefix, rest = raw.split(":", 1)
            safe_prefix = _escape_xml(prefix)
            safe_rest = _escape_xml(rest)
            text = f"<b>{safe_prefix}:</b>{safe_rest}"
        else:
            text = _escape_xml(raw)
        paragraphs.append(Paragraph(f"• {text}", style))

    return paragraphs


# ------------------------------------------------------------------------------
# 8. Caja de hallazgo
# ------------------------------------------------------------------------------
def build_hallazgo_box(title, description):
    """
    Retorna una mini tabla que destaca un hallazgo.

    Parámetros
    ----------
    title : str
        Título del hallazgo (en negrita).
    description : str
        Descripción del hallazgo.

    Retorna
    -------
    reportlab.platypus.Table
    """
    styles = get_executive_styles()
    title_para = Paragraph(f"<b>{_escape_xml(title)}</b>", styles["EXEC_BODY_BOLD"])
    desc_para = Paragraph(_escape_xml(description), styles["EXEC_BODY"])

    data = [[title_para], [desc_para]]
    t = Table(data, colWidths=[CONTENT_WIDTH])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), EXEC_COLORS["gray_light"]),
                ("BOX", (0, 0), (-1, -1), 0.5, EXEC_COLORS["gray_border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


# ------------------------------------------------------------------------------
# 9. Párrafo de conclusión
# ------------------------------------------------------------------------------
def build_conclusion_paragraph(text):
    """
    Retorna un ``Paragraph`` con estilo ``EXEC_CONCLUSION_BODY``.
    """
    return Paragraph(str(text), _get_style("EXEC_CONCLUSION_BODY"))

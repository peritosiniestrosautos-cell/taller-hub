"""
================================================================================
DESIGN TOKENS - Taller Hub
================================================================================
Sistema centralizado de colores, tipografía, espaciado y temas para Plotly.
Todos los valores visuales del dashboard deben importarse desde aquí.
"""

# ============================================================================
# PALETA CORPORATIVA
# ============================================================================

class BrandColors:
    """Colores principales de marca"""
    PRIMARY = "#0066CC"       # Azul corporativo
    SECONDARY = "#00A8E8"     # Cyan
    ACCENT = "#00CC66"        # Verde
    TEAL = "#0891B2"          # Teal para promedio
    INDIGO = "#6366F1"        # Indigo para variaciones
    CYAN_LIGHT = "#06B6D4"    # Cyan claro


# ============================================================================
# COLORES SEMÁNTICOS
# ============================================================================

class SemanticColors:
    """Colores para estados y feedback"""
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#DC2626"
    INFO = "#0066CC"

    # Backgrounds para alertas
    SUCCESS_BG = "#D1FAE5"
    WARNING_BG = "#FEF3C7"
    ERROR_BG = "#FEE2E2"

    # Textos para badges
    SUCCESS_TEXT = "#065F46"
    WARNING_TEXT = "#92400E"
    ERROR_TEXT = "#991B1B"


# ============================================================================
# ESCALA DE GRAYS (Slate)
# ============================================================================

class GrayScale:
    """Escala de grises para textos y fondos"""
    SLATE_50 = "#F8FAFC"
    SLATE_100 = "#F1F5F9"
    SLATE_200 = "#E2E8F0"
    SLATE_300 = "#CBD5E1"
    SLATE_400 = "#94A3B8"
    SLATE_500 = "#64748B"
    SLATE_600 = "#475569"
    SLATE_700 = "#334155"
    SLATE_800 = "#1E293B"
    SLATE_900 = "#0F172A"


# ============================================================================
# COLORES POR TALLER
# ============================================================================

TALLER_COLORS = [
    "#0066CC",  # Azul
    "#00A8E8",  # Cyan
    "#00CC66",  # Verde
    "#F59E0B",  # Amarillo
    "#DC2626",  # Rojo
    "#8B5CF6",  # Púrpura
    "#EC4899",  # Rosa
    "#14B8A6",  # Turquesa
    "#F97316",  # Naranja
    "#84CC16",  # Lima
]

TALLER_COLOR_NAMES = {
    "#0066CC": "Azul",
    "#00A8E8": "Cyan",
    "#00CC66": "Verde",
    "#F59E0B": "Amarillo",
    "#DC2626": "Rojo",
    "#8B5CF6": "Púrpura",
    "#EC4899": "Rosa",
    "#14B8A6": "Turquesa",
    "#F97316": "Naranja",
    "#84CC16": "Lima",
}


# ============================================================================
# PALETA EXTENDIDA PARA GRÁFICOS
# ============================================================================

CHART_COLORS = [
    BrandColors.PRIMARY,
    BrandColors.SECONDARY,
    BrandColors.ACCENT,
    SemanticColors.WARNING,
    SemanticColors.ERROR,
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F97316",
    BrandColors.INDIGO,
    "#84CC16",
    GrayScale.SLATE_500,
]


# ============================================================================
# TIPOGRAFÍA
# ============================================================================

class Typography:
    """Escala tipográfica"""
    FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

    # Tamaños
    HEADER_SIZE = "2.8rem"
    HEADER_WEIGHT = "800"

    SUBHEADER_SIZE = "1.1rem"
    SUBHEADER_WEIGHT = "400"

    KPI_VALUE_SIZE = "1.9rem"
    KPI_VALUE_WEIGHT = "700"

    KPI_LABEL_SIZE = "0.85rem"
    KPI_LABEL_WEIGHT = "500"

    KPI_DELTA_SIZE = "0.8rem"
    KPI_DELTA_WEIGHT = "600"

    BODY_SIZE = "0.9rem"
    BODY_WEIGHT = "400"

    CAPTION_SIZE = "0.75rem"
    CAPTION_WEIGHT = "400"

    BADGE_SIZE = "0.75rem"
    BADGE_WEIGHT = "600"


# ============================================================================
# ESPACIADO (sistema 8px)
# ============================================================================

class Spacing:
    """Sistema de espaciado basado en 8px (valores en rem para CSS)"""
    XS = "0.25"    # 4px
    SM = "0.5"     # 8px
    MD = "1.5"     # 24px
    LG = "2"       # 32px
    XL = "2"       # 32px
    XXL = "3"      # 48px
    XXXL = "4"     # 64px


# ============================================================================
# BORDER RADIUS
# ============================================================================

class BorderRadius:
    """Escala de redondeo"""
    SM = "8px"
    MD = "12px"
    LG = "16px"
    XL = "24px"
    FULL = "9999px"


# ============================================================================
# CHART HEIGHTS
# ============================================================================

class ChartHeights:
    """Alturas estándar para gráficos"""
    SMALL = 300
    MEDIUM = 380
    LARGE = 450
    XLARGE = 500


# ============================================================================
# PLOTLY CHART THEME
# ============================================================================

def get_plotly_theme(title: str = "", height: int = ChartHeights.MEDIUM, show_legend: bool = True):
    """
    Retorna configuración base de layout para gráficos Plotly.
    Uso: fig.update_layout(**get_plotly_theme("Mi Título"))
    """
    return {
        "title": title,
        "height": height,
        "hovermode": "x unified",
        "showlegend": show_legend,
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": Typography.FONT_FAMILY,
            "size": 12,
            "color": GrayScale.SLATE_800,
        },
        "xaxis": {
            "gridcolor": GrayScale.SLATE_200,
            "gridwidth": 1,
        },
        "yaxis": {
            "gridcolor": GrayScale.SLATE_200,
            "gridwidth": 1,
            "tickformat": "$,.0f",
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        "margin": {"l": 60, "r": 30, "t": 60, "b": 50},
    }


def get_chart_color(index: int) -> str:
    """Retorna un color de la paleta de gráficos por índice"""
    return CHART_COLORS[index % len(CHART_COLORS)]


def get_taller_color(index: int) -> str:
    """Retorna un color de taller por índice"""
    return TALLER_COLORS[index % len(TALLER_COLORS)]


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convierte hex a rgba para uso en Plotly"""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def hex_with_opacity(hex_color: str, opacity: int = 20) -> str:
    """
    Agrega opacidad a un color hex para usar en gradientes CSS.
    opacity: 0-255 (20 = ~8%, 11 = ~4%)
    """
    hex_color = hex_color.lstrip("#")
    opacity_hex = format(opacity, "02x")
    return f"#{hex_color}{opacity_hex}"


def hex_to_plotly_fill(hex_color: str, alpha: float = 0.1) -> str:
    """Convierte hex a rgba para fillcolor en Plotly"""
    return hex_to_rgba(hex_color, alpha)

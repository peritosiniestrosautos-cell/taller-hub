"""
================================================================================
CONFIGURACIÓN Y CONSTANTES - Taller Hub
================================================================================
Configuración de página, estilos CSS y constantes del sistema.
"""

import streamlit as st
from .theme import (
    BrandColors, SemanticColors, GrayScale,
    Typography, BorderRadius, Spacing,
    hex_with_opacity
)


# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

def setup_page_config():
    """Configura la página de Streamlit con los colores corporativos"""
    st.set_page_config(
        page_title="Dashboard de Ahorros | Talleres Automotrices",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )


# ============================================================================
# CSS PERSONALIZADO - Usa design tokens centralizados
# ============================================================================

CUSTOM_CSS = f"""
<style>
    /* Header principal */
    .main-header {{
        font-size: {Typography.HEADER_SIZE};
        font-weight: {Typography.HEADER_WEIGHT};
        background: linear-gradient(90deg, {BrandColors.PRIMARY} 0%, {BrandColors.SECONDARY} 50%, {BrandColors.ACCENT} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: {Spacing.XS}rem;
        letter-spacing: -1px;
    }}
    
    /* Subheader */
    .sub-header {{
        font-size: {Typography.SUBHEADER_SIZE};
        color: {GrayScale.SLATE_500};
        text-align: center;
        margin-bottom: {Spacing.LG}rem;
        font-weight: {Typography.SUBHEADER_WEIGHT};
    }}
    
    /* Cards de KPI */
    .kpi-container {{
        background: white;
        border-radius: {BorderRadius.LG};
        padding: {Spacing.MD}rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 4px solid;
        transition: transform 0.2s;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin: 0.5rem 0;
    }}
    
    .kpi-container:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }}
    
    .kpi-ahorro {{ border-left-color: {BrandColors.PRIMARY}; }}
    .kpi-honorarios {{ border-left-color: {BrandColors.SECONDARY}; }}
    .kpi-utilidad {{ border-left-color: {BrandColors.ACCENT}; }}
    .kpi-promedio {{ border-left-color: {BrandColors.TEAL}; }}
    
    .kpi-value {{
        font-size: {Typography.KPI_VALUE_SIZE};
        font-weight: {Typography.KPI_VALUE_WEIGHT};
        color: {GrayScale.SLATE_800};
        margin-bottom: 0.25rem;
    }}
    
    .kpi-label {{
        font-size: {Typography.KPI_LABEL_SIZE};
        color: {GrayScale.SLATE_500};
        font-weight: {Typography.KPI_LABEL_WEIGHT};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .kpi-delta {{
        font-size: {Typography.KPI_DELTA_SIZE};
        color: {BrandColors.ACCENT};
        font-weight: {Typography.KPI_DELTA_WEIGHT};
        margin-top: 0.5rem;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {GrayScale.SLATE_800} 0%, {GrayScale.SLATE_900} 100%) !important;
        border-right: 1px solid {GrayScale.SLATE_700};
    }}
    
    [data-testid="stSidebar"] * {{
        color: {GrayScale.SLATE_100} !important;
    }}
    
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stCaption {{
        color: {GrayScale.SLATE_100} !important;
    }}
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] select {{
        color: {GrayScale.SLATE_800} !important;
        background-color: #FFFFFF !important;
    }}
    
    /* Botones */
    .stButton>button {{
        border-radius: {BorderRadius.SM};
        font-weight: 600;
        transition: all 0.2s;
    }}
    
    .stButton>button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {hex_with_opacity(BrandColors.PRIMARY, 76)};
    }}
    
    /* Tablas */
    .stDataFrame {{
        border-radius: {BorderRadius.MD};
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    
    /* Alertas de validación */
    .validation-error {{
        background: {SemanticColors.ERROR_BG};
        border-left: 4px solid {SemanticColors.ERROR};
        padding: 1rem;
        border-radius: {BorderRadius.SM};
        margin: 0.5rem 0;
    }}
    
    .validation-warning {{
        background: {SemanticColors.WARNING_BG};
        border-left: 4px solid {SemanticColors.WARNING};
        padding: 1rem;
        border-radius: {BorderRadius.SM};
        margin: 0.5rem 0;
    }}
    
    .validation-success {{
        background: {SemanticColors.SUCCESS_BG};
        border-left: 4px solid {SemanticColors.SUCCESS};
        padding: 1rem;
        border-radius: {BorderRadius.SM};
        margin: 0.5rem 0;
    }}
    
    /* Status badges */
    .badge-autorizado {{
        background: {SemanticColors.SUCCESS_BG};
        color: {SemanticColors.SUCCESS_TEXT};
        padding: 2px 8px;
        border-radius: {BorderRadius.FULL};
        font-size: {Typography.BADGE_SIZE};
        font-weight: {Typography.BADGE_WEIGHT};
    }}
    
    .badge-rechazado {{
        background: {SemanticColors.ERROR_BG};
        color: {SemanticColors.ERROR_TEXT};
        padding: 2px 8px;
        border-radius: {BorderRadius.FULL};
        font-size: {Typography.BADGE_SIZE};
        font-weight: {Typography.BADGE_WEIGHT};
    }}
    
    .badge-pendiente {{
        background: {SemanticColors.WARNING_BG};
        color: {SemanticColors.WARNING_TEXT};
        padding: 2px 8px;
        border-radius: {BorderRadius.FULL};
        font-size: {Typography.BADGE_SIZE};
        font-weight: {Typography.BADGE_WEIGHT};
    }}
</style>
"""


def apply_custom_css():
    """Aplica el CSS personalizado al dashboard"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
# MAPEO DE COLUMNAS
# ============================================================================

COLUMN_MAPPING = {
    'PLACA': ['PLACA'],
    'MARCA': ['MARCA'],
    'LINEA': ['LINEA'],
    'COMPAÑIA_DE_SEGUROS': ['COMPAÑIA', 'SEGURO', 'ASEGURADORA'],
    'SINIESTRO': ['SINIESTRO'],
    'IMPREVISTO': ['IMPREVISTO'],
    'ACCION': ['ACCION'],
    'CAUSAL': ['CAUSAL'],
    'ESTATUS': ['ESTATUS', 'ESTADO'],
    'OBSERVACION': ['OBSERVACION', 'OBSERVACIÓN', 'OBS'],
    'M._DE_O._INICIAL': ['INICIAL', 'M.O.INICIAL', 'MANO_OBRA_INICIAL', 'VALOR_INICIAL'],
    'M._DE_O._FINAL': ['FINAL', 'M.O.FINAL', 'MANO_OBRA_FINAL', 'VALOR_FINAL'],
    'DIFERENCIA': ['DIFERENCIA', 'AHORRO', 'RECUPERACION', 'RECUPERADO'],
    'FECHA_INGR': ['FECHA_INGR', 'FECHA_INGRESO', 'FECHA', 'INGRESO'],
    'FECHA_AUTO': ['FECHA_AUTO', 'FECHA_AUTORIZACION'],
    'AÑO': ['AÑO', 'ANIO', 'YEAR', 'S'],
    'MES': ['MES', 'MONTH', 'R'],
    'DIA': ['DIA', 'DAY', 'Q']
}


# ============================================================================
# CONSTANTES DE NEGOCIO
# ============================================================================

PORCENTAJE_HONORARIOS = 0.18  # 18% del ahorro
EXCEL_FILENAME = "ENSAYO DISTRIKIA INFORME PARA FEBRERO 2026.xlsx"
SHEET_NAME = "BASE DE DATOS"

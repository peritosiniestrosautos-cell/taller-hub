"""
================================================================================
CARGA DE DATOS - Taller Hub
================================================================================
Funciones para cargar datos desde Google Sheets y archivos Excel locales.
Soporte multitaller - RF-MT: Múltiples fuentes de datos
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .data_processor import procesar_dataframe
from .config import EXCEL_FILENAME, SHEET_NAME
from .taller_config import (
    get_taller_config, 
    get_url_taller, 
    consolidar_dataframes,
    get_nombre_taller
)


# ============================================================================
# CONEXIÓN A GOOGLE SHEETS
# ============================================================================

@st.cache_resource(ttl=3600)
def get_google_sheets_client():
    """
    RF-001: Conexión a Google Sheets API
    Soporta tanto desarrollo local (archivo JSON) como producción (secrets)
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    try:
        # Intentar cargar desde secrets de Streamlit Cloud
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        st.sidebar.success("✅ Conectado via Streamlit Secrets")
    except Exception:
        try:
            # Fallback: archivo local credentials.json
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            st.sidebar.success("✅ Conectado via archivo local")
        except Exception:
            try:
                # Segundo fallback: archivo en .streamlit/credentials.json
                creds = Credentials.from_service_account_file(".streamlit/credentials.json", scopes=scopes)
                st.sidebar.success("✅ Conectado via archivo local (.streamlit)")
            except Exception as e3:
                st.sidebar.error(f"❌ Error de conexión: {e3}")
                return None
    
    return gspread.authorize(creds)


# ============================================================================
# CARGA DESDE EXCEL (Fallback)
# ============================================================================

@st.cache_data(ttl=30)
def load_data_from_excel(excel_path=None, taller_id: str = "default") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga datos desde archivo Excel local
    Útil para pruebas o cuando Google Sheets no está disponible
    
    Args:
        excel_path: Ruta al archivo Excel
        taller_id: ID del taller para taggear los datos
    """
    if excel_path is None:
        excel_path = EXCEL_FILENAME
        
    try:
        if not Path(excel_path).exists():
            return None, f"Archivo no encontrado: {excel_path}"
        
        df = pd.read_excel(excel_path, sheet_name=SHEET_NAME)
        
        # Aplicar procesamiento de datos
        df = procesar_dataframe(df, fuente="Excel")
        
        # Agregar metadatos de taller
        df["TALLER_ORIGEN"] = get_nombre_taller(taller_id) if taller_id != "default" else "Taller Excel"
        df["TALLER_ID"] = taller_id
        
        return df, None
    except Exception as e:
        return None, f"Error cargando Excel: {str(e)}"


# ============================================================================
# CARGA DESDE GOOGLE SHEETS (Single Taller)
# ============================================================================

@st.cache_data(ttl=30)
def load_data_from_sheets_single(sheet_url: str, taller_id: str = "default") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga datos desde un solo Google Sheet.
    Versión base usada por la función multitaller.
    
    Args:
        sheet_url: URL del Google Sheet
        taller_id: ID del taller para identificación
    
    Returns:
        Tuple (DataFrame, error_message)
    """
    try:
        client = get_google_sheets_client()
        if not client:
            # Fallback a Excel si hay error de autenticación
            return load_data_from_excel(taller_id=taller_id)
        
        # Abrir spreadsheet
        spreadsheet = client.open_by_url(sheet_url)
        
        # Cargar hoja BASE DE DATOS
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
        except:
            # Intentar con nombre alternativo
            try:
                worksheet = spreadsheet.worksheet("Hoja1")
            except:
                # Usar la primera hoja disponible
                available_sheets = [ws.title for ws in spreadsheet.worksheets()]
                if available_sheets:
                    worksheet = spreadsheet.worksheet(available_sheets[0])
                else:
                    return None, f"No se encontraron hojas en el spreadsheet"
        
        data = worksheet.get_all_records()
        
        if not data:
            return None, "La hoja no tiene datos (solo encabezados o vacía)"
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return None, "La hoja está vacía"
        
        # Aplicar procesamiento de datos
        df = procesar_dataframe(df, fuente="Google Sheets")
        
        return df, None
        
    except Exception as e:
        return None, f"Error cargando datos: {str(e)}"


# ============================================================================
# CARGA DE HOJA "TASA DE IMPREVISTOS"
# ============================================================================

def _normalize_column_name(col: str) -> str:
    """Normaliza nombres de columnas para manejar variaciones."""
    col_upper = str(col).upper().strip()
    mapping = {
        'AÑO': ['AÑO', 'ANO', 'ANIO', 'YEAR'],
        'MES': ['MES', 'MONTH'],
        'SURA': ['SURA'],
        'BOLIVAR': ['BOLIVAR', 'BOLÍVAR'],
        'ALLIANZ': ['ALLIANZ'],
        'MAPFRE': ['MAPFRE', 'MAPRE'],
        'TOTAL': ['TOTAL'],
    }
    for canonical, variants in mapping.items():
        if col_upper in variants:
            return canonical
    return col_upper


# Mapeo de nombres de meses en español a números
_MES_NOMBRE_A_NUMERO = {
    'ENE': 1, 'ENERO': 1,
    'FEB': 2, 'FEBRERO': 2,
    'MAR': 3, 'MARZO': 3,
    'ABR': 4, 'ABRIL': 4,
    'MAY': 5, 'MAYO': 5,
    'JUN': 6, 'JUNIO': 6,
    'JUL': 7, 'JULIO': 7,
    'AGO': 8, 'AGOS': 8, 'AGOSTO': 8,
    'SEP': 9, 'SEPT': 9, 'SEPTIEMBRE': 9,
    'OCT': 10, 'OCTUBRE': 10,
    'NOV': 11, 'NOVIEMBRE': 11,
    'DIC': 12, 'DICIEMBRE': 12,
}


def _parse_mes(valor) -> Optional[int]:
    """Convierte un valor de mes (número o nombre) a entero 1-12."""
    if pd.isna(valor):
        return None
    # Intentar como número
    try:
        return int(float(valor))
    except (ValueError, TypeError):
        pass
    # Intentar como nombre de mes
    val_str = str(valor).upper().strip()
    return _MES_NOMBRE_A_NUMERO.get(val_str)


@st.cache_data(ttl=30)
def load_tasa_imprevistos_sheet(sheet_url: str, taller_id: str = "default") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga la hoja 'TASA DE IMPREVISTOS' de un Google Sheet.
    
    Nota: La hoja tiene una fila de título en la fila 1 y los encabezados
    reales (AÑO, MES, SURA, BOLÍVAR, ALLIANZ, MAPFRE, TOTAL) en la fila 2.
    
    Args:
        sheet_url: URL del Google Sheet
        taller_id: ID del taller para identificación
    
    Returns:
        Tuple (DataFrame, error_message)
    """
    try:
        client = get_google_sheets_client()
        if not client:
            return None, "No se pudo conectar a Google Sheets"
        
        spreadsheet = client.open_by_url(sheet_url)
        
        # Buscar la hoja con variaciones de nombre
        target_names = ["TASA DE IMPREVISTOS", "Tasa de Imprevistos", "tasa de imprevistos"]
        worksheet = None
        available_sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        for name in target_names:
            if name in available_sheets:
                worksheet = spreadsheet.worksheet(name)
                break
        
        if worksheet is None:
            # Intentar búsqueda case-insensitive
            for ws in spreadsheet.worksheets():
                if "TASA" in ws.title.upper() and "IMPREVISTO" in ws.title.upper():
                    worksheet = ws
                    break
        
        if worksheet is None:
            return None, f"No se encontró la hoja 'TASA DE IMPREVISTOS'. Hojas disponibles: {available_sheets}"
        
        # Usar get_all_values() para poder saltar la fila de título
        values = worksheet.get_all_values()
        
        if len(values) < 2:
            return None, "La hoja 'TASA DE IMPREVISTOS' no tiene suficientes filas"
        
        # Fila 0 = título, Fila 1 = encabezados reales, Fila 2+ = datos
        headers = values[1]
        data_rows = values[2:]
        
        if not data_rows:
            return None, "La hoja 'TASA DE IMPREVISTOS' no tiene datos"
        
        df = pd.DataFrame(data_rows, columns=headers)
        
        if df.empty:
            return None, "La hoja 'TASA DE IMPREVISTOS' está vacía"
        
        # Normalizar nombres de columnas
        df.columns = [_normalize_column_name(c) for c in df.columns]
        
        # Asegurar que existan las columnas mínimas necesarias
        if 'TOTAL' not in df.columns:
            return None, f"La hoja no tiene columna 'total'. Columnas encontradas: {list(df.columns)}"
        
        if 'AÑO' not in df.columns or 'MES' not in df.columns:
            return None, f"La hoja no tiene columnas 'año' y/o 'mes'. Columnas encontradas: {list(df.columns)}"
        
        # Convertir a numérico (MES puede ser nombre o número)
        df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
        df['MES'] = df['MES'].apply(_parse_mes)
        df['TOTAL'] = pd.to_numeric(df['TOTAL'], errors='coerce')
        
        # Eliminar filas sin año, mes o total válidos
        df = df[df['AÑO'].notna() & df['MES'].notna() & df['TOTAL'].notna()].copy()
        
        if df.empty:
            return None, "No hay filas válidas después de la limpieza"
        
        # Agregar metadatos de taller
        df["TALLER_ORIGEN"] = get_nombre_taller(taller_id) if taller_id != "default" else "Default"
        df["TALLER_ID"] = taller_id
        
        return df, None
        
    except Exception as e:
        return None, f"Error cargando TASA DE IMPREVISTOS: {str(e)}"


# ============================================================================
# CARGA DE HOJA "TASA DE IMPREVISTOS" DESDE EXCEL (Fallback local)
# ============================================================================

@st.cache_data(ttl=30)
def load_tasa_imprevistos_from_excel(excel_path=None, taller_id: str = "default") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga la hoja 'TASA DE IMPREVISTOS' desde un archivo Excel local.
    
    La tabla tiene una fila de título en la fila 1 y los encabezados reales
    (AÑO, MES, SURA, BOLÍVAR, ALLIANZ, MAPFRE, TOTAL) en la fila 2.
    
    Args:
        excel_path: Ruta al archivo Excel. Si es None, usa EXCEL_FILENAME.
        taller_id: ID del taller para identificación.
    
    Returns:
        Tuple (DataFrame, error_message)
    """
    if excel_path is None:
        excel_path = EXCEL_FILENAME
    
    try:
        if not Path(excel_path).exists():
            # Intentar buscar cualquier archivo .xlsx en el directorio
            import glob
            xlsx_files = glob.glob("*.xlsx")
            if xlsx_files:
                excel_path = xlsx_files[0]
            else:
                return None, f"Archivo no encontrado: {excel_path}"
        
        xl = pd.ExcelFile(excel_path)
        
        # Buscar la hoja con variaciones de nombre
        target_names = ["TASA DE IMPREVISTOS", "Tasa de Imprevistos", "tasa de imprevistos"]
        sheet_name = None
        for name in target_names:
            if name in xl.sheet_names:
                sheet_name = name
                break
        
        if sheet_name is None:
            # Búsqueda case-insensitive
            for sn in xl.sheet_names:
                if "TASA" in sn.upper() and "IMPREVISTO" in sn.upper():
                    sheet_name = sn
                    break
        
        if sheet_name is None:
            return None, f"No se encontró la hoja 'TASA DE IMPREVISTOS'. Hojas: {xl.sheet_names}"
        
        # header=1 para saltar la fila de título y usar la segunda fila como encabezados
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=1)
        
        if df.empty:
            return None, "La hoja 'TASA DE IMPREVISTOS' está vacía"
        
        # Normalizar nombres de columnas
        df.columns = [_normalize_column_name(c) for c in df.columns]
        
        if 'TOTAL' not in df.columns:
            return None, f"La hoja no tiene columna 'total'. Columnas: {list(df.columns)}"
        
        if 'AÑO' not in df.columns or 'MES' not in df.columns:
            return None, f"La hoja no tiene columnas 'año' y/o 'mes'. Columnas: {list(df.columns)}"
        
        # Convertir a numérico (MES puede ser nombre o número)
        df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
        df['MES'] = df['MES'].apply(_parse_mes)
        df['TOTAL'] = pd.to_numeric(df['TOTAL'], errors='coerce')
        
        df = df[df['AÑO'].notna() & df['MES'].notna() & df['TOTAL'].notna()].copy()
        
        if df.empty:
            return None, "No hay filas válidas"
        
        # Agregar metadatos
        df["TALLER_ORIGEN"] = get_nombre_taller(taller_id) if taller_id != "default" else "Taller Excel"
        df["TALLER_ID"] = taller_id
        
        return df, None
        
    except Exception as e:
        return None, f"Error cargando TASA DE IMPREVISTOS desde Excel: {str(e)}"


# ============================================================================
# CARGA MULTITALLER (Nueva funcionalidad)
# ============================================================================

def load_data_multitaller(
    talleres_ids: List[str],
    progress_bar=None
) -> Tuple[Optional[pd.DataFrame], Dict[str, str]]:
    """
    RF-MT: Carga datos de múltiples talleres y los consolida.
    
    Args:
        talleres_ids: Lista de IDs de talleres a cargar
        progress_bar: Opcional - st.progress() para mostrar avance
    
    Returns:
        Tuple (DataFrame_consolidado, dict_errores)
        - DataFrame_consolidado: DataFrame con todos los datos + columna TALLER_ORIGEN
        - dict_errores: {taller_id: mensaje_error} para los talleres con problemas
    """
    if not talleres_ids:
        return None, {"general": "No se seleccionaron talleres"}
    
    dfs_por_taller = {}
    tasa_dfs = []
    errores = {}
    total = len(talleres_ids)
    
    for idx, taller_id in enumerate(talleres_ids):
        # Actualizar progreso si se proporcionó barra
        if progress_bar is not None:
            progress = (idx + 1) / total
            progress_bar.progress(progress, text=f"Cargando {get_nombre_taller(taller_id)}...")
        
        # Obtener configuración del taller
        config = get_taller_config(taller_id)
        if not config:
            errores[taller_id] = "Taller no encontrado en configuración"
            continue
        
        if not config.get("activo", False):
            errores[taller_id] = "Taller desactivado"
            continue
        
        sheet_url = config.get("sheet_url")
        if not sheet_url:
            errores[taller_id] = "URL no configurada"
            continue
        
        # Cargar datos principales del taller
        df, error = load_data_from_sheets_single(sheet_url, taller_id)
        
        if error:
            errores[taller_id] = error
            continue
        
        if df is not None and not df.empty:
            dfs_por_taller[taller_id] = df
        else:
            errores[taller_id] = "No se encontraron datos"
            continue
        
        # Cargar hoja TASA DE IMPREVISTOS desde Sheets
        df_tasa, tasa_error = load_tasa_imprevistos_sheet(sheet_url, taller_id)
        if df_tasa is not None and not df_tasa.empty:
            tasa_dfs.append(df_tasa)
        else:
            # Fallback: intentar cargar desde Excel local
            df_tasa_excel, tasa_excel_error = load_tasa_imprevistos_from_excel(taller_id=taller_id)
            if df_tasa_excel is not None and not df_tasa_excel.empty:
                tasa_dfs.append(df_tasa_excel)
            else:
                # Guardar warning pero no error crítico
                st.session_state.setdefault("tasa_imprevistos_warnings", {})
                st.session_state["tasa_imprevistos_warnings"][taller_id] = tasa_error or tasa_excel_error or "Sin datos"
    
    # Consolidar DataFrames principales
    if dfs_por_taller:
        df_consolidado = consolidar_dataframes(dfs_por_taller)
        
        # Guardar info de debug en session state
        st.session_state["talleres_cargados"] = list(dfs_por_taller.keys())
        st.session_state["talleres_con_error"] = errores
        
        # Consolidar y guardar datos de TASA DE IMPREVISTOS
        if tasa_dfs:
            df_tasa_consolidado = pd.concat(tasa_dfs, ignore_index=True)
            st.session_state["tasa_imprevistos_data"] = df_tasa_consolidado
        else:
            st.session_state["tasa_imprevistos_data"] = pd.DataFrame()
        
        return df_consolidado, errores
    
    return None, errores


# ============================================================================
# CARGA DESDE GOOGLE SHEETS (Compatibilidad hacia atrás)
# ============================================================================

@st.cache_data(ttl=30)
def load_data_from_sheets(sheet_url: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    RF-001: Carga y limpieza de datos desde Google Sheets
    Mantiene compatibilidad con versión anterior (monotaller).
    
    Nota: Para multitaller, usar load_data_multitaller()
    """
    return load_data_from_sheets_single(sheet_url, taller_id="single")


# ============================================================================
# FUNCIONES DE RESUMEN Y ESTADÍSTICAS
# ============================================================================

def get_estadisticas_carga(errores: Dict[str, str], total_talleres: int) -> dict:
    """
    Genera estadísticas del proceso de carga multitaller.
    
    Returns:
        Dict con estadísticas
    """
    exitosos = total_talleres - len(errores)
    
    return {
        "total_talleres": total_talleres,
        "exitosos": exitosos,
        "con_error": len(errores),
        "porcentaje_exito": (exitosos / total_talleres * 100) if total_talleres > 0 else 0,
        "detalle_errores": errores,
    }


def render_resumen_carga(stats: dict):
    """Renderiza un resumen visual del estado de carga"""
    if stats["con_error"] == 0:
        st.sidebar.success(f"✅ Todos los talleres cargados ({stats['exitosos']})")
    else:
        st.sidebar.warning(
            f"⚠️ Carga parcial: {stats['exitosos']} exitosos, "
            f"{stats['con_error']} con errores"
        )
        
        with st.sidebar.expander("Ver detalle de errores"):
            for taller_id, error in stats["detalle_errores"].items():
                st.caption(f"**{get_nombre_taller(taller_id)}:** {error}")

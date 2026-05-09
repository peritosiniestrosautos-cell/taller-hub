"""
================================================================================
PROCESAMIENTO DE DATOS - Taller Hub
================================================================================
Funciones para limpiar, transformar y procesar los datos.
RF-002: Limpieza y transformación de datos
"""

import pandas as pd
from datetime import datetime
from .config import COLUMN_MAPPING
from .date_utils import parse_source_date_column


# Variable global para logs de debug
debug_logs = []


def add_log(msg):
    """Agrega un mensaje al log de debug"""
    debug_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")


def get_debug_logs():
    """Retorna los logs de debug acumulados"""
    return debug_logs.copy()


def clear_debug_logs():
    """Limpia los logs de debug"""
    global debug_logs
    debug_logs = []


def normalize_estatus_value(value):
    """
    Normaliza ESTATUS a un conjunto canónico en mayúsculas.
    La regla de negocio de ahorro cuenta únicamente registros AUTORIZADO.
    """
    if pd.isna(value):
        return ""

    status = str(value).strip().upper()

    if not status or status in {"NAN", "NONE", "NAT"}:
        return ""
    if "AUTORIZ" in status:
        return "AUTORIZADO"
    if "RECHAZ" in status:
        return "RECHAZADO"
    if "PEND" in status:
        return "PENDIENTE"

    return status


def filter_authorized_savings_records(df):
    """
    Retorna solo registros autorizados para métricas de ahorro.
    Si no existe ESTATUS, devuelve el DataFrame original por compatibilidad.
    """
    if df is None or df.empty or 'ESTATUS' not in df.columns:
        return df

    estatus_normalizado = df['ESTATUS'].apply(normalize_estatus_value)
    return df[estatus_normalizado == "AUTORIZADO"].copy()


def drop_non_data_rows(df):
    """
    Elimina filas vacías o filas-resumen sin identidad de reparación.
    Caso observado en Google Sheets: una fila final con solo RECUPERADO total.
    """
    if df is None or df.empty:
        return df

    text_identity_cols = [
        col for col in ['PLACA', 'SINIESTRO', 'IMPREVISTO', 'ACCION', 'CAUSAL', 'ESTATUS']
        if col in df.columns
    ]
    numeric_identity_cols = [col for col in ['DIA', 'MES', 'AÑO'] if col in df.columns]

    if not text_identity_cols and not numeric_identity_cols:
        return df

    text_has_data = pd.Series(False, index=df.index)
    for col in text_identity_cols:
        text_has_data = text_has_data | df[col].fillna('').astype(str).str.strip().ne('')

    numeric_has_data = pd.Series(False, index=df.index)
    for col in numeric_identity_cols:
        numeric_has_data = numeric_has_data | df[col].notna()

    valid_rows = text_has_data | numeric_has_data
    return df[valid_rows].copy()


def procesar_dataframe(df, fuente="Google Sheets"):
    """
    Procesa y limpia el DataFrame con las transformaciones necesarias
    """
    global debug_logs
    debug_logs = []  # Limpiar logs anteriores
    
    add_log(f"Iniciando procesamiento desde: {fuente}")
    add_log(f"Filas originales: {len(df)}")
    add_log(f"Columnas originales: {list(df.columns)}")
    
    # =========================================================================
    # LIMPIEZA Y TRANSFORMACIÓN DE DATOS (RF-001, RF-002)
    # =========================================================================
    
    # Normalizar nombres de columnas (quitar espacios, mayúsculas, tildes)
    df.columns = df.columns.str.strip().str.upper().str.replace(' ', '_')
    # Quitar tildes de nombres de columnas
    df.columns = df.columns.str.replace('Í', 'I').str.replace('Ó', 'O').str.replace('Á', 'A').str.replace('É', 'E').str.replace('Ú', 'U')
    
    add_log(f"Columnas normalizadas: {list(df.columns)}")
    
    # Encontrar columnas reales y renombrar
    actual_columns = {}
    for standard_name, possible_names in COLUMN_MAPPING.items():
        for col in df.columns:
            # Match exacto para nombres de 1 carácter (Q, R, S)
            exact_short = any(len(p) == 1 and p == col for p in possible_names)
            # Substring para nombres de más de 1 carácter
            substring = any(len(p) > 1 and p in col for p in possible_names)
            if exact_short or substring:
                actual_columns[standard_name] = col
                break

    add_log(f"Columnas mapeadas: {actual_columns}")

    # Renombrar columnas encontradas (evitar crear duplicados)
    rename_map = {}
    for standard_name, actual_col in actual_columns.items():
        if actual_col in df.columns:
            # Si el nombre destino ya existe como otra columna, no renombrar
            if standard_name in df.columns and actual_col != standard_name:
                continue
            rename_map[actual_col] = standard_name
    df = df.rename(columns=rename_map)
    
    add_log(f"Columnas finales: {list(df.columns)}")
    
    # =========================================================================
    # CONVERSIÓN DE TIPOS DE DATOS (RF-002)
    # =========================================================================
    
    # Campos numéricos - limpiar formato de moneda ($, comas, espacios)
    numeric_cols = ['M._DE_O._INICIAL', 'M._DE_O._FINAL', 'DIFERENCIA']
    for col in numeric_cols:
        if col in df.columns:
            add_log(f"Procesando columna numérica: {col}")
            # Limpiar: quitar $, comas, espacios, y convertir a número
            df[col] = df[col].astype(str).str.replace(r'[\$,\s]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            add_log(f"  {col} suma: {df[col].sum()}")
    
    # Fechas auxiliares: se mantienen solo como referencia visual/debug.
    # La lógica de negocio debe usar únicamente DIA/MES/AÑO.
    date_cols = ['FECHA_INGR', 'FECHA_AUTO']
    for col in date_cols:
        if col in df.columns:
            df[col] = parse_source_date_column(df[col], col)
            add_log(f"Columna auxiliar de fecha procesada: {col}")

    # Componentes de fecha: usar DIA/MES/AÑO como fuente primaria.
    for col in ['DIA', 'MES', 'AÑO']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            add_log(f"Columna componente de fecha normalizada: {col}")

    if all(col in df.columns for col in ['DIA', 'MES', 'AÑO']):
        fecha_desde_componentes = pd.to_datetime(
            df[['AÑO', 'MES', 'DIA']].rename(
                columns={'AÑO': 'year', 'MES': 'month', 'DIA': 'day'}
            ),
            errors='coerce'
        )
        add_log("Fecha base construida exclusivamente desde DIA/MES/AÑO")
    else:
        fecha_desde_componentes = pd.Series(pd.NaT, index=df.index)
        add_log("No fue posible construir fecha base desde DIA/MES/AÑO")

    # Calcular DIFERENCIA si no existe o es cero
    if 'DIFERENCIA' not in df.columns or df['DIFERENCIA'].sum() == 0:
        if 'M._DE_O._INICIAL' in df.columns and 'M._DE_O._FINAL' in df.columns:
            df['DIFERENCIA'] = df['M._DE_O._FINAL'] - df['M._DE_O._INICIAL']
            add_log("DIFERENCIA calculada de INICIAL/FINAL")

    add_log(f"render_kpis: DIFERENCIA existe={('DIFERENCIA' in df.columns)}, suma={df.get('DIFERENCIA', pd.Series([0])).sum()}")

    # FECHA_COMPLETA se deriva solo de DIA/MES/AÑO.
    df['FECHA_COMPLETA'] = fecha_desde_componentes
    add_log("FECHA_COMPLETA asignada desde DIA/MES/AÑO sin usar fallbacks")

    # Campos de texto - limpiar
    text_cols = ['PLACA', 'MARCA', 'LINEA', 'COMPAÑIA_DE_SEGUROS', 
                 'SINIESTRO', 'IMPREVISTO', 'ACCION', 'CAUSAL', 'ESTATUS']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df[col] = df[col].replace('NAN', '').replace('NONE', '').replace('NAT', '')

    if 'ESTATUS' in df.columns:
        df['ESTATUS'] = df['ESTATUS'].apply(normalize_estatus_value)
        add_log("ESTATUS normalizado a valores canónicos")

    original_len = len(df)
    df = drop_non_data_rows(df)
    removed_rows = original_len - len(df)
    if removed_rows:
        add_log(f"Filas vacías/resumen descartadas: {removed_rows}")
    
    add_log(f"Procesamiento completado. Filas: {len(df)}, Columnas: {len(df.columns)}")
    return df

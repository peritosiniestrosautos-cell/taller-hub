"""
================================================================================
CONFIGURACIÓN DE TALLERES - Taller Hub
================================================================================
Configuración de múltiples talleres para arquitectura multitaller.
Versión 2.0 - Usa taller_manager.py para persistencia JSON.

Este módulo mantiene compatibilidad hacia atrás con el código existente,
pero ahora delega las operaciones CRUD a taller_manager.py.
"""

import streamlit as st
from typing import Dict, List, Optional

# Importar el nuevo gestor de talleres
from .taller_manager import (
    cargar_talleres,
    guardar_talleres,
    get_talleres_activos as _get_talleres_activos,
    get_talleres_disponibles as _get_talleres_disponibles,
    get_taller_config as _get_taller_config,
    get_url_taller as _get_url_taller,
    get_nombre_taller as _get_nombre_taller,
    get_color_taller as _get_color_taller,
    COLORES_PREDEFINIDOS,
)

# ============================================================================
# COMPATIBILIDAD: Exportar COLORES_TALLERES (nombre anterior)
# ============================================================================
COLORES_TALLERES = COLORES_PREDEFINIDOS

# ============================================================================
# CONFIGURACIÓN DE TALLERES (Compatibilidad hacia atrás)
# ============================================================================

# TALLERES_CONFIG se carga dinámicamente desde el JSON
# Para mantener compatibilidad, usamos una property-like approach
def _get_talleres_config():
    """Retorna la configuración actual de talleres desde persistencia"""
    return cargar_talleres()


# Variable de compatibilidad - acceder a través de función
TALLERES_CONFIG = property(_get_talleres_config)


# ============================================================================
# FUNCIONES DE ACCESO (Delegadas a taller_manager)
# ============================================================================

def get_talleres_activos() -> Dict[str, dict]:
    """Retorna solo los talleres marcados como activos"""
    return _get_talleres_activos()


def get_talleres_disponibles() -> Dict[str, dict]:
    """Retorna todos los talleres configurados"""
    return _get_talleres_disponibles()


def get_taller_config(taller_id: str) -> Optional[dict]:
    """Retorna la configuración de un taller específico"""
    return _get_taller_config(taller_id)


def get_url_taller(taller_id: str) -> Optional[str]:
    """Retorna la URL del sheet de un taller"""
    return _get_url_taller(taller_id)


def get_nombre_taller(taller_id: str) -> str:
    """Retorna el nombre legible de un taller"""
    return _get_nombre_taller(taller_id)


def get_color_taller(taller_id: str) -> str:
    """Retorna el color asignado a un taller"""
    return _get_color_taller(taller_id)


# ============================================================================
# FUNCIONES DE MODIFICACIÓN (Legacy - mantener compatibilidad)
# ============================================================================

def agregar_taller(
    taller_id: str,
    nombre: str,
    sheet_url: str,
    activo: bool = True,
    descripcion: str = "",
) -> bool:
    """
    Agrega un nuevo taller a la configuración (LEGACY).
    Ahora delega a taller_manager.crear_taller.
    
    Nota: El taller_id es ignorado - se genera automáticamente.
    """
    from .taller_manager import crear_taller
    result = crear_taller(nombre, sheet_url)
    return result is not None


def toggle_taller_activo(taller_id: str, activo: bool):
    """Activa o desactiva un taller (LEGACY)"""
    from .taller_manager import actualizar_taller
    return actualizar_taller(taller_id, activo=activo)


# ============================================================================
# FUNCIONES DE UI PARA TALLERES (Actualizadas)
# ============================================================================

def render_selector_talleres_sidebar() -> List[str]:
    """
    Renderiza el selector de talleres en el sidebar.
    Retorna la lista de IDs de talleres seleccionados.
    """
    st.sidebar.header("🏪 Selección de Talleres")
    
    talleres = get_talleres_disponibles()
    
    if not talleres:
        st.sidebar.warning("⚠️ No hay talleres configurados")
        return []
    
    # Checkbox para ver todos
    ver_todos = st.sidebar.checkbox("📊 Ver todos los talleres", value=True)
    
    seleccionados = []
    
    if ver_todos:
        # Seleccionar todos los activos por defecto
        seleccionados = [tid for tid, tconfig in talleres.items() if tconfig.get("activo", False)]
        st.sidebar.info(f"✅ {len(seleccionados)} taller(es) seleccionado(s)")
    else:
        # Mostrar checkboxes individuales
        st.sidebar.markdown("**Selecciona los talleres:**")
        for taller_id, config in talleres.items():
            if not config.get("activo", False):
                continue
            
            col1, col2 = st.sidebar.columns([0.1, 0.9])
            with col1:
                color = config.get("color", "#0066CC")
                st.markdown(f"<div style='width:12px;height:12px;background:{color};border-radius:50%;margin-top:8px;'></div>", unsafe_allow_html=True)
            with col2:
                if st.checkbox(config["nombre"], value=True, key=f"chk_{taller_id}"):
                    seleccionados.append(taller_id)
    
    # Mostrar resumen
    if seleccionados:
        st.sidebar.caption(f"**Talleres activos:** {len(seleccionados)}")
        for tid in seleccionados:
            nombre = get_nombre_taller(tid)
            st.sidebar.caption(f"  • {nombre}")
    else:
        st.sidebar.warning("⚠️ Selecciona al menos un taller")
    
    st.sidebar.divider()
    
    return seleccionados


def render_gestion_talleres():
    """
    Renderiza panel de gestión de talleres (para modo admin).
    Muestra una tabla con los talleres configurados.
    """
    import pandas as pd
    
    st.subheader("🔧 Gestión de Talleres")
    
    talleres = get_talleres_disponibles()
    
    # Tabla de talleres
    data = []
    for tid, config in talleres.items():
        url_corta = config["sheet_url"][:50] + "..." if len(config["sheet_url"]) > 50 else config["sheet_url"]
        data.append({
            "ID": tid,
            "Nombre": config["nombre"],
            "URL": url_corta,
            "Activo": "✅" if config.get("activo", False) else "❌",
            "Color": config.get("color", "#0066CC"),
        })
    
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info("No hay talleres configurados. Agrega uno nuevo desde el sidebar.")
    
    # Instrucciones
    with st.expander("ℹ️ Información"):
        st.markdown("""
        **Gestión de Talleres:**
        
        Usa el panel **"Gestión de Talleres"** en el sidebar (izquierda) para:
        - ➕ Agregar nuevos talleres
        - ✏️ Editar talleres existentes
        - 🗑️ Eliminar talleres
        
        Los datos se guardan automáticamente en el archivo `data/talleres.json`.
        """)


# ============================================================================
# FUNCIONES DE PROCESAMIENTO MULTITALLER (Sin cambios)
# ============================================================================

def consolidar_dataframes(dfs_por_taller: dict) -> Optional:
    """
    Consolida múltiples DataFrames de diferentes talleres en uno solo.
    Agrega la columna TALLER_ORIGEN a cada DataFrame.
    
    Args:
        dfs_por_taller: Dict {taller_id: DataFrame}
    
    Returns:
        DataFrame consolidado o None si no hay datos
    """
    import pandas as pd
    
    if not dfs_por_taller:
        return None
    
    dfs_procesados = []
    
    for taller_id, df in dfs_por_taller.items():
        if df is None or df.empty:
            continue
        
        df_copy = df.copy()
        config = get_taller_config(taller_id)
        
        # Agregar columna de taller
        df_copy["TALLER_ORIGEN"] = config["nombre"] if config else taller_id
        df_copy["TALLER_ID"] = taller_id
        df_copy["TALLER_COLOR"] = get_color_taller(taller_id)
        
        dfs_procesados.append(df_copy)
    
    if not dfs_procesados:
        return None
    
    # Consolidar todos los DataFrames
    df_consolidado = pd.concat(dfs_procesados, ignore_index=True)
    
    return df_consolidado


def get_resumen_por_taller(df_consolidado) -> Optional:
    """
    Genera un resumen de métricas por taller.

    Returns:
        DataFrame con resumen por taller
    """
    import pandas as pd
    from .fee_config import calculate_fees_per_month, load_fee_config
    from .data_processor import filter_authorized_savings_records

    if df_consolidado is None or df_consolidado.empty:
        return None

    if "TALLER_ORIGEN" not in df_consolidado.columns:
        return None

    df_consolidado = filter_authorized_savings_records(df_consolidado)
    if df_consolidado is None or df_consolidado.empty:
        return None

    resumen = df_consolidado.groupby("TALLER_ORIGEN").agg({
        "DIFERENCIA": ["sum", "mean", "count"],
        "PLACA": "nunique",
    }).reset_index()

    # Aplanar columnas multi-index
    resumen.columns = ["TALLER", "AHORRO_TOTAL", "AHORRO_PROMEDIO", "TOTAL_REPARACIONES", "VEHICULOS_UNICOS"]

    # Calcular honorarios por mes (regla de umbral evaluada mes a mes, no acumulado)
    fee_config = load_fee_config()
    fee_info = calculate_fees_per_month(df_consolidado, fee_config)
    
    # Update resumen with per-taller fees (sum of per-month calculations)
    for idx, row in resumen.iterrows():
        taller = row["TALLER"]
        if taller in fee_info['by_taller']:
            resumen.loc[idx, "HONORARIOS"] = fee_info['by_taller'][taller]['total_honorarios']
            resumen.loc[idx, "UTILIDAD"] = row["AHORRO_TOTAL"] - fee_info['by_taller'][taller]['total_honorarios']
        else:
            # Fallback to default
            resumen.loc[idx, "HONORARIOS"] = row["AHORRO_TOTAL"] * fee_config['global_defaults']['base_percentage']
            resumen.loc[idx, "UTILIDAD"] = row["AHORRO_TOTAL"] - resumen.loc[idx, "HONORARIOS"]

    return resumen

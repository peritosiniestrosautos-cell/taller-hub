"""
================================================================================
GESTOR DE TALLERES - Taller Hub
================================================================================
Sistema CRUD para gestión dinámica de talleres con persistencia en JSON.
Permite agregar, editar, eliminar y activar/desactivar talleres desde la UI.
"""

import json
import os
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime

from .fee_config import update_taller_fee_config, load_fee_config
from .theme import TALLER_COLORS, TALLER_COLOR_NAMES, BrandColors, GrayScale

# ============================================================================
# CONFIGURACIÓN DE PERSISTENCIA
# ============================================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TALLERES_FILE = os.path.join(DATA_DIR, "talleres.json")

# Re-export from theme for backwards compatibility
COLORES_PREDEFINIDOS = TALLER_COLORS
NOMBRES_COLORES = {f"#{'🔵🩵🟢🟡🔴🟣🩷🩲🟠🫒'[i]} {name}" for i, (hex_code, name) in enumerate(TALLER_COLOR_NAMES.items())}

NOMBRES_COLORES = {
    "#0066CC": "🔵 Azul",
    "#00A8E8": "🩵 Cyan",
    "#00CC66": "🟢 Verde",
    "#F59E0B": "🟡 Amarillo",
    "#DC2626": "🔴 Rojo",
    "#8B5CF6": "🟣 Púrpura",
    "#EC4899": "🩷 Rosa",
    "#14B8A6": "🩲 Turquesa",
    "#F97316": "🟠 Naranja",
    "#84CC16": "🫒 Lima",
}


def _ensure_data_dir():
    """Asegura que el directorio de datos exista"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def _get_default_talleres() -> Dict[str, dict]:
    """Retorna la configuración por defecto de talleres"""
    return {
        "autozen": {
            "id": "autozen",
            "nombre": "Autozen",
            "sheet_url": "https://docs.google.com/spreadsheets/d/1IJetXo3teQCw1iTVGR1ky-GDMMRoUd-D/edit?gid=1340033279#gid=1340033279",
            "activo": False,
            "color": BrandColors.PRIMARY,
        },
        "taller_1": {
            "id": "taller_1",
            "nombre": "Distrikia",
            "sheet_url": "https://docs.google.com/spreadsheets/d/1WgrIeUkrmvgecDP5hKaOtXjrmxsGdjSzMrari4LbvAI/edit?gid=0#gid=0",
            "activo": True,
            "color": BrandColors.SECONDARY,
        },
        "renomotriz": {
            "id": "renomotriz",
            "nombre": "Renomotriz",
            "sheet_url": "https://docs.google.com/spreadsheets/d/1PvdZBQCFBBFSgKhjfFkHFXs1jO5nJIUvXBSlX0pXUZg/edit?gid=0#gid=0",
            "activo": False,
            "color": BrandColors.ACCENT,
        },
        "colision_express": {
            "id": "colision_express",
            "nombre": "Colisión Express",
            "sheet_url": "https://docs.google.com/spreadsheets/d/1ScPJ0hsqdwS2Lwo2KujfzCKJKsrwRxvbkdVghk4sVS0/edit?gid=0#gid=0",
            "activo": False,
            "color": "#F59E0B",
        },
    }


def cargar_talleres() -> Dict[str, dict]:
    """
    Carga la configuración de talleres desde el archivo JSON.
    Si no existe, crea el archivo con valores por defecto.
    
    Returns:
        Dict con la configuración de talleres
    """
    _ensure_data_dir()
    
    if not os.path.exists(TALLERES_FILE):
        # Crear archivo con valores por defecto
        talleres = _get_default_talleres()
        guardar_talleres(talleres)
        return talleres
    
    try:
        with open(TALLERES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        st.error(f"Error al cargar talleres: {e}")
        return _get_default_talleres()


def guardar_talleres(talleres: Dict[str, dict]) -> bool:
    """
    Guarda la configuración de talleres en el archivo JSON.
    
    Args:
        talleres: Dict con la configuración de talleres
        
    Returns:
        True si se guardó correctamente
    """
    _ensure_data_dir()
    
    try:
        with open(TALLERES_FILE, 'w', encoding='utf-8') as f:
            json.dump(talleres, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        st.error(f"Error al guardar talleres: {e}")
        return False


# ============================================================================
# OPERACIONES CRUD
# ============================================================================

def crear_taller(nombre: str, sheet_url: str, color: Optional[str] = None) -> Optional[str]:
    """
    Crea un nuevo taller.
    
    Args:
        nombre: Nombre del taller
        sheet_url: URL del Google Sheet
        color: Color opcional (si no se especifica, se asigna automáticamente)
        
    Returns:
        ID del taller creado o None si falló
    """
    talleres = cargar_talleres()
    
    # Generar ID único
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    taller_id = f"taller_{timestamp}"
    
    # Asignar color automáticamente si no se especifica
    if color is None:
        idx = len(talleres) % len(COLORES_PREDEFINIDOS)
        color = COLORES_PREDEFINIDOS[idx]
    
    talleres[taller_id] = {
        "id": taller_id,
        "nombre": nombre.strip(),
        "sheet_url": sheet_url.strip(),
        "activo": True,
        "color": color,
    }
    
    if guardar_talleres(talleres):
        return taller_id
    return None


def actualizar_taller(taller_id: str, nombre: Optional[str] = None, 
                      sheet_url: Optional[str] = None, 
                      color: Optional[str] = None,
                      activo: Optional[bool] = None) -> bool:
    """
    Actualiza los datos de un taller existente.
    
    Args:
        taller_id: ID del taller a actualizar
        nombre: Nuevo nombre (opcional)
        sheet_url: Nueva URL (opcional)
        color: Nuevo color (opcional)
        activo: Nuevo estado (opcional)
        
    Returns:
        True si se actualizó correctamente
    """
    talleres = cargar_talleres()
    
    if taller_id not in talleres:
        return False
    
    if nombre is not None:
        talleres[taller_id]["nombre"] = nombre.strip()
    
    if sheet_url is not None:
        talleres[taller_id]["sheet_url"] = sheet_url.strip()
    
    if color is not None:
        talleres[taller_id]["color"] = color
    
    if activo is not None:
        talleres[taller_id]["activo"] = activo
    
    return guardar_talleres(talleres)


def eliminar_taller(taller_id: str) -> bool:
    """
    Elimina un taller permanentemente.
    
    Args:
        taller_id: ID del taller a eliminar
        
    Returns:
        True si se eliminó correctamente
    """
    talleres = cargar_talleres()
    
    if taller_id not in talleres:
        return False
    
    del talleres[taller_id]
    return guardar_talleres(talleres)


def toggle_taller_estado(taller_id: str) -> bool:
    """
    Activa o desactiva un taller (toggle).
    
    Args:
        taller_id: ID del taller
        
    Returns:
        True si se cambió el estado correctamente
    """
    talleres = cargar_talleres()
    
    if taller_id not in talleres:
        return False
    
    talleres[taller_id]["activo"] = not talleres[taller_id].get("activo", True)
    return guardar_talleres(talleres)


# ============================================================================
# FUNCIONES DE CONSULTA
# ============================================================================

def get_talleres_activos() -> Dict[str, dict]:
    """Retorna solo los talleres marcados como activos"""
    talleres = cargar_talleres()
    return {k: v for k, v in talleres.items() if v.get("activo", False)}


def get_talleres_disponibles() -> Dict[str, dict]:
    """Retorna todos los talleres configurados"""
    return cargar_talleres()


def get_taller_config(taller_id: str) -> Optional[dict]:
    """Retorna la configuración de un taller específico"""
    talleres = cargar_talleres()
    return talleres.get(taller_id)


def get_url_taller(taller_id: str) -> Optional[str]:
    """Retorna la URL del sheet de un taller"""
    config = get_taller_config(taller_id)
    return config["sheet_url"] if config else None


def get_nombre_taller(taller_id: str) -> str:
    """Retorna el nombre legible de un taller"""
    config = get_taller_config(taller_id)
    return config["nombre"] if config else taller_id


def get_color_taller(taller_id: str) -> str:
    """Retorna el color asignado a un taller"""
    config = get_taller_config(taller_id)
    if config and "color" in config:
        return config["color"]

    # Asignar color basado en índice si no tiene definido
    talleres = list(cargar_talleres().keys())
    idx = talleres.index(taller_id) if taller_id in talleres else 0
    return TALLER_COLORS[idx % len(TALLER_COLORS)]


# ============================================================================
# COMPONENTES UI PARA CRUD
# ============================================================================

def render_crud_talleres_sidebar():
    """
    Renderiza el panel completo de CRUD de talleres en el sidebar.
    Incluye: lista de talleres, agregar, editar y eliminar.
    """
    st.sidebar.header("🔧 Gestión de Talleres")
    
    talleres = cargar_talleres()
    
    # ================================================================
    # SECCIÓN: LISTA DE TALLERES ACTUALES
    # ================================================================
    st.sidebar.markdown("**📋 Talleres Configurados**")
    
    if not talleres:
        st.sidebar.info("No hay talleres configurados. Agrega uno nuevo.")
    else:
        for taller_id, config in talleres.items():
            col1, col2, col3 = st.sidebar.columns([0.15, 0.55, 0.3])
            
            with col1:
                # Indicador de color
                color = config.get("color", BrandColors.PRIMARY)
                estado_icon = "🟢" if config.get("activo", True) else "⚪"
                st.markdown(
                    f"<div style='width:14px;height:14px;background:{color};"
                    f"border-radius:50%;margin-top:4px;'></div>",
                    unsafe_allow_html=True
                )
            
            with col2:
                nombre = config["nombre"]
                if len(nombre) > 15:
                    nombre = nombre[:12] + "..."
                st.caption(f"{estado_icon} {nombre}")
            
            with col3:
                # Botón eliminar (pequeño)
                if st.button("🗑️", key=f"del_{taller_id}", help="Eliminar taller"):
                    if eliminar_taller(taller_id):
                        st.sidebar.success("✅ Eliminado")
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Error")
    
    st.sidebar.divider()
    
    # ================================================================
    # SECCIÓN: AGREGAR NUEVO TALLER
    # ================================================================
    with st.sidebar.expander("➕ Agregar Nuevo Taller", expanded=False):
        # CSS específico para inputs (sin !important para no romper focus)
        st.markdown(f"""
        <style>
        section[data-testid="stSidebar"] .stTextInput input {{
            color: {GrayScale.SLATE_700};
        }}
        section[data-testid="stSidebar"] .stTextInput input::placeholder {{
            color: {GrayScale.SLATE_400};
        }}
        </style>
        """, unsafe_allow_html=True)

        with st.form("form_nuevo_taller"):
            st.markdown("**Nuevo Taller**")

            nuevo_nombre = st.text_input(
                "Nombre del Taller",
                placeholder="Ej: Taller Norte",
                max_chars=50,
                key="new_nombre"
            )

            nuevo_url = st.text_input(
                "URL de Google Sheets",
                placeholder="https://docs.google.com/spreadsheets/d/...",
                help="Pega la URL completa del Google Sheet",
                key="new_url"
            )

            # Selector de color con nombres en español
            color_idx_default = len(talleres) % len(COLORES_PREDEFINIDOS)

            nuevo_color = st.selectbox(
                "Color del taller",
                options=COLORES_PREDEFINIDOS,
                index=color_idx_default,
                format_func=lambda x: NOMBRES_COLORES.get(x, x)
            )
            
            # Configuración de honorarios
            st.divider()
            st.markdown("**💰 Configuración de Honorarios**")
            
            # Load global defaults
            fee_config = load_fee_config()
            defaults = fee_config.get('global_defaults', {})
            
            col_fee1, col_fee2 = st.columns(2)
            
            with col_fee1:
                fee_threshold = st.number_input(
                    "💰 Umbral ($)",
                    min_value=1000000,
                    max_value=100000000,
                    value=int(defaults.get('threshold', 15000000)),
                    step=500000,
                    format="%d",
                    help="Si el ahorro supera este valor, se aplica tasa premium",
                    key="new_fee_threshold"
                )
                
                fee_base = st.number_input(
                    "📊 Tasa Base (%)",
                    min_value=1.0,
                    max_value=50.0,
                    value=defaults.get('base_percentage', 0.18) * 100,
                    step=0.5,
                    help="Porcentaje cuando el ahorro está por debajo del umbral",
                    key="new_fee_base"
                )
            
            with col_fee2:
                fee_premium = st.number_input(
                    "🚀 Tasa Premium (%)",
                    min_value=1.0,
                    max_value=50.0,
                    value=defaults.get('premium_percentage', 0.20) * 100,
                    step=0.5,
                    help="Porcentaje cuando el ahorro supera el umbral",
                    key="new_fee_premium"
                )
                
                # Preview
                st.markdown(f"""
                <div style="background: {GrayScale.SLATE_800}; padding: 0.5rem; border-radius: 6px; margin-top: 1.5rem;">
                <p style="color: {GrayScale.SLATE_400}; margin: 0; font-size: 0.75rem;">
                💡 > ${fee_threshold:,.0f} → {fee_premium:.0f}%<br>
                📌 ≤ ${fee_threshold:,.0f} → {fee_base:.0f}%
                </p>
                </div>
                """, unsafe_allow_html=True)

            submitted = st.form_submit_button("💾 Guardar Taller", use_container_width=True)

            if submitted:
                if not nuevo_nombre.strip():
                    st.error("⚠️ El nombre es obligatorio")
                elif not nuevo_url.strip():
                    st.error("⚠️ La URL es obligatoria")
                elif "docs.google.com/spreadsheets" not in nuevo_url:
                    st.error("⚠️ URL inválida. Debe ser un Google Sheets")
                else:
                    taller_id = crear_taller(nuevo_nombre, nuevo_url, nuevo_color)
                    if taller_id:
                        # Save fee configuration for this taller
                        update_taller_fee_config(
                            taller_id,
                            fee_threshold,
                            fee_base / 100,
                            fee_premium / 100
                        )
                        st.success(f"✅ Taller creado!")
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar")
    
    # ================================================================
    # SECCIÓN: EDITAR TALLER EXISTENTE
    # ================================================================
    if talleres:
        with st.sidebar.expander("✏️ Editar Taller", expanded=False):
            # CSS específico para inputs
            st.markdown(f"""
            <style>
            section[data-testid="stSidebar"] .stTextInput input {{
                color: {GrayScale.SLATE_700};
            }}
            </style>
            """, unsafe_allow_html=True)

            # Selector de taller a editar
            taller_options = {f"{v['nombre']} ({k})": k for k, v in talleres.items()}
            taller_seleccionado = st.selectbox(
                "Seleccionar taller",
                options=list(taller_options.keys()),
                key="edit_select"
            )

            if taller_seleccionado:
                taller_id = taller_options[taller_seleccionado]
                config = talleres[taller_id]
                
                # Load fee config for this taller
                from .fee_config import get_taller_fee_config
                fee_config_taller = get_taller_fee_config(taller_id)

                with st.form("form_editar_taller"):
                    edit_nombre = st.text_input(
                        "Nombre",
                        value=config["nombre"]
                    )

                    edit_url = st.text_input(
                        "URL",
                        value=config["sheet_url"]
                    )

                    # Estado activo/inactivo
                    edit_activo = st.toggle(
                        "Taller activo",
                        value=config.get("activo", True)
                    )

                    # Color actual
                    colores_con_seleccion = COLORES_PREDEFINIDOS.copy()
                    if config["color"] not in colores_con_seleccion:
                        colores_con_seleccion.insert(0, config["color"])

                    try:
                        color_idx = colores_con_seleccion.index(config["color"])
                    except ValueError:
                        color_idx = 0

                    # Selector de color con nombres en español
                    edit_color = st.selectbox(
                        "Color",
                        options=colores_con_seleccion,
                        index=color_idx,
                        format_func=lambda x: NOMBRES_COLORES.get(x, x)
                    )
                    
                    # Configuración de honorarios
                    st.divider()
                    st.markdown("**💰 Configuración de Honorarios**")
                    
                    col_fee1, col_fee2 = st.columns(2)
                    
                    with col_fee1:
                        edit_fee_threshold = st.number_input(
                            "💰 Umbral ($)",
                            min_value=1000000,
                            max_value=100000000,
                            value=int(fee_config_taller.get('threshold', 15000000)),
                            step=500000,
                            format="%d",
                            help="Si el ahorro supera este valor, se aplica tasa premium",
                            key=f"edit_fee_threshold_{taller_id}"
                        )
                        
                        edit_fee_base = st.number_input(
                            "📊 Tasa Base (%)",
                            min_value=1.0,
                            max_value=50.0,
                            value=fee_config_taller.get('base_percentage', 0.18) * 100,
                            step=0.5,
                            help="Porcentaje cuando el ahorro está por debajo del umbral",
                            key=f"edit_fee_base_{taller_id}"
                        )
                    
                    with col_fee2:
                        edit_fee_premium = st.number_input(
                            "🚀 Tasa Premium (%)",
                            min_value=1.0,
                            max_value=50.0,
                            value=fee_config_taller.get('premium_percentage', 0.20) * 100,
                            step=0.5,
                            help="Porcentaje cuando el ahorro supera el umbral",
                            key=f"edit_fee_premium_{taller_id}"
                        )
                        
                        # Preview
                        st.markdown(f"""
                        <div style="background: {GrayScale.SLATE_800}; padding: 0.5rem; border-radius: 6px; margin-top: 1.5rem;">
                        <p style="color: {GrayScale.SLATE_400}; margin: 0; font-size: 0.75rem;">
                        💡 > ${edit_fee_threshold:,.0f} → {edit_fee_premium:.0f}%<br>
                        📌 ≤ ${edit_fee_threshold:,.0f} → {edit_fee_base:.0f}%
                        </p>
                        </div>
                        """, unsafe_allow_html=True)

                    submitted = st.form_submit_button("💾 Actualizar", use_container_width=True)

                    if submitted:
                        if actualizar_taller(
                            taller_id,
                            nombre=edit_nombre,
                            sheet_url=edit_url,
                            color=edit_color,
                            activo=edit_activo
                        ):
                            # Update fee configuration
                            update_taller_fee_config(
                                taller_id,
                                edit_fee_threshold,
                                edit_fee_base / 100,
                                edit_fee_premium / 100
                            )
                            st.success("✅ Actualizado!")
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar")


def render_selector_talleres_simple() -> List[str]:
    """
    Renderiza un selector simple de talleres activos.
    Retorna la lista de IDs de talleres seleccionados.
    """
    talleres = get_talleres_activos()
    
    if not talleres:
        st.sidebar.warning("⚠️ No hay talleres activos")
        return []
    
    st.sidebar.markdown("**🏪 Talleres Activos**")
    
    seleccionados = []
    
    for taller_id, config in talleres.items():
        col1, col2 = st.sidebar.columns([0.15, 0.85])
        
        with col1:
            color = config.get("color", BrandColors.PRIMARY)
            st.markdown(
                f"<div style='width:12px;height:12px;background:{color};"
                f"border-radius:50%;margin-top:8px;'></div>",
                unsafe_allow_html=True
            )
        
        with col2:
            if st.checkbox(config["nombre"], value=True, key=f"chk_{taller_id}"):
                seleccionados.append(taller_id)
    
    if not seleccionados:
        st.sidebar.warning("⚠️ Selecciona al menos un taller")
    
    return seleccionados

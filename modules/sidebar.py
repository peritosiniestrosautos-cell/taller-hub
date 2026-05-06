"""
================================================================================
SIDEBAR - Taller Hub
================================================================================
Funciones para el panel lateral: configuración, filtros y auto-refresh.
Soporte multitaller con selector de talleres y CRUD integrado.
"""

import streamlit as st
import time
from datetime import datetime
from typing import List, Dict, Optional
from .data_processor import filter_authorized_savings_records

from .taller_config import (
    render_selector_talleres_sidebar as _render_selector_legacy,
    get_taller_config,
    get_nombre_taller,
    get_color_taller,
    get_talleres_disponibles,
)

from .taller_manager import (
    render_crud_talleres_sidebar,
    get_talleres_activos,
    cargar_talleres,
)

from .fee_config import render_presentation_toggle
from .chart_config import render_chart_type_selector
from .theme import BrandColors, GrayScale


# ============================================================================
# CONFIGURACIÓN DEL SIDEBAR
# ============================================================================

def render_sidebar():
    """
    Configuración y filtros en sidebar.
    Versión multitaller con CRUD de talleres integrado.
    """
    
    st.sidebar.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: {BrandColors.PRIMARY}; margin-bottom: 0.5rem;">🚗 TALLERES</h2>
        <p style="color: {GrayScale.SLATE_500}; font-size: 0.9rem;">Sistema de Gestión de Ahorros</p>
        <p style="color: {BrandColors.ACCENT}; font-size: 0.75rem;">🏪 Modo Multitaller</p>
    </div>
    """, unsafe_allow_html=True)
    
    # =========================================================================
    # SECCIÓN: CRUD DE TALLERES (Nuevo)
    # =========================================================================
    render_crud_talleres_sidebar()
    
    st.sidebar.divider()
    
    # =========================================================================
    # SECCIÓN: SELECCIÓN DE TALLERES ACTIVOS
    # =========================================================================
    talleres_seleccionados = _render_selector_talleres_moderno()
    
    # Guardar en session state
    st.session_state['talleres_seleccionados'] = talleres_seleccionados
    
    # =========================================================================
    # CONFIGURACIÓN DE CONEXIÓN (Legacy - para compatibilidad)
    # =========================================================================
    with st.sidebar.expander("🔗 Configuración Avanzada", expanded=False):
        st.caption("Conexión manual a un sheet específico:")
        
        # URL de Google Sheets (para uso manual/debug)
        default_url = ""
        try:
            default_url = st.secrets.get("SHEET_URL", "")
        except:
            pass
        
        if not default_url:
            default_url = "https://docs.google.com/spreadsheets/d/TU_ID/edit"
        
        sheet_url = st.text_input(
            "URL de Google Sheets (manual)",
            value=default_url,
            type="password",
            help="Solo usar para debug o conexión directa a un taller"
        )
        
        st.session_state['sheet_url_manual'] = sheet_url
    
    st.sidebar.divider()

    # =========================================================================
    # CONFIGURACIÓN DE HONORARIOS
    # =========================================================================
    presentation_mode = render_presentation_toggle()

    st.sidebar.divider()

    # =========================================================================
    # CONFIGURACIÓN DE TIPOS DE GRÁFICOS
    # =========================================================================
    render_chart_type_selector()

    st.sidebar.divider()

    # =========================================================================
    # AUTO-REFRESH
    # =========================================================================
    st.sidebar.header("⏱️ Actualización Automática")
    auto_refresh = st.sidebar.toggle("Auto-refresh activado", value=False)

    if auto_refresh:
        refresh_interval = st.sidebar.slider("Intervalo (segundos)", 10, 300, 60, step=10)
        st.sidebar.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

        # Trigger refresh
        time.sleep(refresh_interval)
        st.rerun()

    st.sidebar.divider()

    # Retornar talleres seleccionados y auto_refresh
    return talleres_seleccionados, auto_refresh


def _render_selector_talleres_moderno() -> List[str]:
    """
    Renderiza el selector moderno de talleres activos.
    Retorna la lista de IDs de talleres seleccionados.
    """
    st.sidebar.header("🏪 Talleres a Visualizar")
    
    talleres = get_talleres_activos()
    
    if not talleres:
        st.sidebar.warning("⚠️ No hay talleres activos. Agrega uno en 'Gestión de Talleres'.")
        return []
    
    # Checkbox para seleccionar todos
    seleccionar_todos = st.sidebar.checkbox("✅ Seleccionar todos", value=True, key="sel_todos")
    
    seleccionados = []
    
    if seleccionar_todos:
        # Seleccionar todos los activos
        seleccionados = list(talleres.keys())
        st.sidebar.info(f"📊 {len(seleccionados)} taller(es) seleccionado(s)")
        
        # Mostrar lista compacta
        for tid, config in talleres.items():
            color = config.get("color", BrandColors.PRIMARY)
            st.sidebar.markdown(
                f"<div style='display:flex;align-items:center;margin:2px 0;'>"
                f"<div style='width:10px;height:10px;background:{color};border-radius:50%;margin-right:8px;'></div>"
                f"<span style='font-size:0.8rem;'>{config['nombre']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        # Mostrar checkboxes individuales
        st.sidebar.markdown("**Selecciona los talleres:**")
        for taller_id, config in talleres.items():
            col1, col2 = st.sidebar.columns([0.12, 0.88])
            
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


# ============================================================================
# FILTROS DE DATOS (Actualizado para multitaller)
# ============================================================================

def render_filtros(df):
    """
    Filtros dinámicos basados en los datos.
    Incluye filtro por taller si hay múltiples talleres.
    """
    
    st.sidebar.header("🔍 Filtros de Datos")
    
    # =========================================================================
    # BOTÓN LIMPIAR FILTROS (Debe ir ANTES de los widgets)
    # =========================================================================
    if st.sidebar.button("🧹 Limpiar Filtros", type="secondary", key="clear_filters_btn"):
        st.session_state["filtro_año"] = "Todos"
        st.session_state["filtro_trimestre"] = "Todos"
        st.session_state["filtro_mes"] = "Todos"
        st.session_state["filtro_compañia"] = []
        st.session_state["filtro_estado"] = []
        st.session_state["filtro_accion"] = []
        if "filtro_talleres" in st.session_state:
            del st.session_state["filtro_talleres"]
        st.rerun()
    
    filtros = {}
    
    # =========================================================================
    # FILTRO POR TALLER (Nuevo - solo si hay múltiples talleres)
    # =========================================================================
    if df is not None and "TALLER_ORIGEN" in df.columns:
        talleres_en_datos = sorted(df["TALLER_ORIGEN"].unique())
        
        if len(talleres_en_datos) > 1:
            st.sidebar.subheader("🏪 Filtrar por Taller")
            
            # Mostrar talleres con sus colores
            cols_talleres = st.sidebar.columns(len(talleres_en_datos))
            for idx, taller in enumerate(talleres_en_datos):
                with cols_talleres[idx]:
                    # Buscar color del taller
                    color = BrandColors.PRIMARY
                    all_talleres = cargar_talleres()
                    for tid, tconf in all_talleres.items():
                        if tconf["nombre"] == taller and "color" in tconf:
                            color = tconf["color"]
                            break
                    
                    st.markdown(
                        f"<div style='width:12px;height:12px;background:{color};"
                        f"border-radius:50%;display:inline-block;margin-right:5px;'></div>",
                        unsafe_allow_html=True
                    )
            
            filtros["talleres"] = st.sidebar.multiselect(
                "Selecciona talleres:",
                options=talleres_en_datos,
                default=talleres_en_datos,
                help="Filtra los datos por taller(es) específico(s)",
                key="filtro_talleres"
            )
        else:
            filtros["talleres"] = talleres_en_datos
    
    # =========================================================================
    # FILTROS EXISTENTES
    # =========================================================================
    
    # Filtro de Año
    if df is not None and 'AÑO' in df.columns:
        años = sorted(df['AÑO'].dropna().unique(), reverse=True)
        años_options = ["Todos"] + [str(int(a)) for a in años if a > 0]
        filtros['año'] = st.sidebar.selectbox("📅 Año", años_options, key="filtro_año")

    # Filtro de Trimestre (Q1/Q2/Q3/Q4/Todos)
    filtros['trimestre'] = st.sidebar.selectbox(
        "📊 Trimestre",
        options=["Todos", "Q1", "Q2", "Q3", "Q4"],
        help="Q1: Ene-Mar | Q2: Abr-Jun | Q3: Jul-Sep | Q4: Oct-Dic",
        key="filtro_trimestre"
    )

    # Filtro de Mes
    if df is not None and 'MES' in df.columns:
        meses = sorted(df['MES'].dropna().unique())
        meses_names = ["Todos"] + [datetime(2000, int(m), 1).strftime('%B') for m in meses if m > 0]
        mes_sel = st.sidebar.selectbox("📆 Mes", meses_names, key="filtro_mes")
        filtros['mes'] = mes_sel if mes_sel == "Todos" else meses_names.index(mes_sel)
    
    # Filtro de Compañía
    if df is not None and 'COMPAÑIA_DE_SEGUROS' in df.columns:
        cias = sorted(df['COMPAÑIA_DE_SEGUROS'].dropna().unique())
        cias = [c for c in cias if c != '']
        filtros['compañia'] = st.sidebar.multiselect(
            "🏢 Compañía de Seguros",
            options=cias,
            default=[],
            key="filtro_compañia"
        )
    
    # Filtro de Estado
    if df is not None and 'ESTATUS' in df.columns:
        estados = sorted(df['ESTATUS'].dropna().unique())
        estados = [e for e in estados if e != '']
        filtros['estado'] = st.sidebar.multiselect(
            "📋 Estado Autorización",
            options=estados,
            default=[],
            key="filtro_estado"
        )
    
    # Filtro de Acción
    if df is not None and 'ACCION' in df.columns:
        acciones = sorted(df['ACCION'].dropna().unique())
        acciones = [a for a in acciones if a != '']
        filtros['accion'] = st.sidebar.multiselect(
            "🔧 Tipo de Acción",
            options=acciones,
            default=[],
            key="filtro_accion"
        )
    
    return filtros


def aplicar_filtros(df, filtros):
    """
    Aplicar filtros seleccionados al dataframe.
    Incluye soporte para filtro por taller.
    """
    
    if df is None or df.empty:
        return df
    
    df_filtered = df.copy()
    
    # =========================================================================
    # FILTRO POR TALLER
    # =========================================================================
    if filtros.get('talleres') and len(filtros['talleres']) > 0:
        if 'TALLER_ORIGEN' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['TALLER_ORIGEN'].isin(filtros['talleres'])]
    
    # =========================================================================
    # FILTROS EXISTENTES
    # =========================================================================
    
    # Filtro de año
    if filtros.get('año') and filtros['año'] != "Todos":
        df_filtered = df_filtered[df_filtered['AÑO'] == int(filtros['año'])]

    # Filtro de trimestre
    # Mapeo: Q1=meses 1-3, Q2=4-6, Q3=7-9, Q4=10-12
    trimestre_map = {
        "Q1": (1, 3),
        "Q2": (4, 6),
        "Q3": (7, 9),
        "Q4": (10, 12)
    }
    if filtros.get('trimestre') and filtros['trimestre'] != "Todos":
        mes_inicio, mes_fin = trimestre_map[filtros['trimestre']]
        if 'MES' in df_filtered.columns:
            df_filtered = df_filtered[
                (df_filtered['MES'] >= mes_inicio) & (df_filtered['MES'] <= mes_fin)
            ]

    # Filtro de mes
    if filtros.get('mes') and filtros['mes'] != "Todos":
        df_filtered = df_filtered[df_filtered['MES'] == int(filtros['mes'])]
    
    # Filtro de compañía
    if filtros.get('compañia') and len(filtros['compañia']) > 0:
        df_filtered = df_filtered[df_filtered['COMPAÑIA_DE_SEGUROS'].isin(filtros['compañia'])]
    
    # Filtro de estado
    if filtros.get('estado') and len(filtros['estado']) > 0:
        df_filtered = df_filtered[df_filtered['ESTATUS'].isin(filtros['estado'])]
    
    # Filtro de acción
    if filtros.get('accion') and len(filtros['accion']) > 0:
        df_filtered = df_filtered[df_filtered['ACCION'].isin(filtros['accion'])]
    
    return df_filtered


# ============================================================================
# RESUMEN DE TALLERES EN SIDEBAR
# ============================================================================

def render_resumen_talleres_sidebar(df):
    """
    Muestra un resumen rápido de los datos por taller en el sidebar.
    """
    if df is None or df.empty or "TALLER_ORIGEN" not in df.columns:
        return

    df = filter_authorized_savings_records(df)
    if df is None or df.empty:
        return
    
    st.sidebar.divider()
    st.sidebar.header("📊 Resumen por Taller")
    
    resumen = df.groupby("TALLER_ORIGEN").agg({
        "DIFERENCIA": "sum",
        "PLACA": "count"
    }).reset_index()
    
    for _, row in resumen.iterrows():
        taller = row["TALLER_ORIGEN"]
        ahorro = row["DIFERENCIA"]
        cantidad = row["PLACA"]
        
        st.sidebar.markdown(f"""
        <div style="margin-bottom: 0.5rem;">
            <div style="font-size: 0.85rem; font-weight: 600;">{taller}</div>
            <div style="font-size: 0.75rem; color: {GrayScale.SLATE_500};">
                💰 ${ahorro:,.0f} | 🚗 {cantidad} reparaciones
            </div>
        </div>
        """, unsafe_allow_html=True)

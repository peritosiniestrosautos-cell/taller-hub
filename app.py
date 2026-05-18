"""
================================================================================
TALLER HUB - Sistema de Gestión de Ahorros y Análisis de Talleres Automotrices
Dashboard Ejecutivo con Auto-refresh - VERSIÓN MULTITALLER
Versión: 2.0.0 | Fecha: Abril 2026
Stakeholders: Alexander Cano (Analista/Gerente), Sergio Romero (Operativo)
================================================================================

ARCHIVO PRINCIPAL - Entry Point (Multitaller)
Soporta múltiples fuentes de datos (varios Google Sheets de diferentes talleres)
"""

# Importar configuración
from modules.config import setup_page_config, apply_custom_css

# Importar carga de datos (multitaller)
from modules.data_loader import (
    load_data_multitaller,
    get_estadisticas_carga,
    render_resumen_carga
)

# Importar validaciones
from modules.validators import run_validations

# Importar visualizaciones
from modules.visualizations import (
    render_kpis,
    render_grafico_causales,
    render_tabla_detalle,
    render_recuperacion_mensual,
    render_efectividad_valoracion,
    render_grafico_ahorro_por_compania,
    render_grafico_ahorro_mes_nuevo
)

# Importar visualizaciones de imprevistos
from modules.imprevistos_visualizations import (
    render_grafico_tasa_imprevistos_nuevo,
    render_grafico_culpa_taller_mensual,
    render_demora_definicion_imprevisto,
    render_tabla_resumen_imprevistos,
)

# Importar visualizaciones multitaller
from modules.visualizations_multitaller import (
    render_kpis_multitaller,
    render_ranking_talleres,
    render_vista_multitaller,
    render_comparativo_anual
)

# Importar sidebar y filtros
from modules.sidebar import (
    render_sidebar, 
    render_filtros, 
    aplicar_filtros,
    render_resumen_talleres_sidebar
)
from modules.data_processor import filter_authorized_savings_records

# Importar componentes UI
from modules.components import (
    render_header,
    render_footer,
    render_alerts,
    render_data_info,
    render_export_section,
    render_error_state,
    render_empty_state
)

# Importar configuración de talleres
from modules.taller_config import get_talleres_activos

import streamlit as st


# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================

setup_page_config()
apply_custom_css()


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del dashboard - Versión Multitaller"""
    
    # =========================================================================
    # SIDEBAR - Selección de talleres y configuración
    # =========================================================================
    talleres_seleccionados, auto_refresh = render_sidebar()
    
    # Header (con nombre del taller activo)
    render_header(talleres_seleccionados)
    
    # Verificar si hay talleres configurados
    if not talleres_seleccionados:
        st.warning("⚠️ No hay talleres seleccionados. Activa al menos un taller en la configuración.")
        
        # Mostrar ayuda para configurar talleres
        with st.expander("ℹ️ ¿Cómo configurar talleres?", expanded=True):
            st.markdown("""
            ### Configuración de Talleres
            
            Para agregar más talleres, edita el archivo `modules/taller_config.py`:
            
            1. Copia el template de `taller_2` dentro de `TALLERES_CONFIG`
            2. Cambia el ID (ej: `taller_5`)
            3. Actualiza el nombre y la URL del Google Sheet
            4. Cambia `"activo": True` para habilitarlo
            5. Reinicia la aplicación
            
            **Nota:** Cada taller debe tener su propio Google Sheet con la misma estructura de columnas.
            """)
        
        render_footer(talleres_seleccionados)
        return
    
    # =========================================================================
    # CARGA DE DATOS MULTITALLER
    # =========================================================================
    
    # Barra de progreso para carga
    progress_bar = st.progress(0, text="Iniciando carga de talleres...")
    
    with st.spinner(f"🔄 Cargando datos de {len(talleres_seleccionados)} taller(es)..."):
        df, errores = load_data_multitaller(
            talleres_ids=talleres_seleccionados,
            progress_bar=progress_bar
        )
    
    # Limpiar barra de progreso
    progress_bar.empty()
    
    # Mostrar resumen de carga en sidebar
    stats = get_estadisticas_carga(errores, len(talleres_seleccionados))
    render_resumen_carga(stats)
    
    # =========================================================================
    # MANEJO DE ERRORES
    # =========================================================================
    
    # Si no se cargó ningún dato
    if df is None or df.empty:
        error_msg = "No se pudieron cargar datos de ningún taller."
        if errores:
            error_msg += "\n\n**Errores por taller:**"
            for tid, err in errores.items():
                from modules.taller_config import get_nombre_taller
                error_msg += f"\n- **{get_nombre_taller(tid)}:** {err}"
        
        render_error_state(error_msg)
        
        # Mostrar ayuda
        with st.expander("🔧 Ayuda para resolver el problema"):
            st.markdown("""
            ### Posibles soluciones:
            
            1. **Verifica las URLs** de los Google Sheets en `modules/taller_config.py`
            2. **Confirma los permisos** de acceso a los spreadsheets
            3. **Verifica que las hojas** tengan la estructura correcta (columna 'BASE DE DATOS')
            4. **Revisa las credenciales** de Google Sheets API
            
            Para debug, puedes usar el modo manual en "Configuración Avanzada" en el sidebar.
            """)
        
        render_footer(talleres_seleccionados)
        return
    
    # Si se cargaron datos parcialmente (algunos talleres fallaron)
    if errores and len(errores) < len(talleres_seleccionados):
        st.warning(f"⚠️ Se cargaron datos de {stats['exitosos']} taller(es), pero {stats['con_error']} fallaron.")
    
    # =========================================================================
    # DATOS CARGADOS - CONTINUAR CON DASHBOARD
    # =========================================================================
    
    # Verificar si es multitaller
    es_multitaller = "TALLER_ORIGEN" in df.columns and df["TALLER_ORIGEN"].nunique() > 1
    
    # Mostrar badge de multitaller
    if es_multitaller:
        st.success(f"🏪 **Modo Multitaller Activo** - {df['TALLER_ORIGEN'].nunique()} talleres cargados con {len(df)} registros totales")
    
    # Información de datos cargados
    render_data_info(df, df)
    
    # Mostrar resumen de talleres en sidebar
    render_resumen_talleres_sidebar(df)
    
    # =========================================================================
    # VALIDACIONES
    # =========================================================================
    alerts = run_validations(df)
    render_alerts(alerts)
    
    # =========================================================================
    # FILTROS
    # =========================================================================
    filtros = render_filtros(df)
    df_filtered = aplicar_filtros(df, filtros)
    
    # Información de filtros aplicados
    if len(df_filtered) != len(df):
        st.info(f"📊 Filtros aplicados: mostrando {len(df_filtered)} de {len(df)} registros")
    
    # =========================================================================
    # SECCIÓN: KPIs COMPARATIVOS MULTITALLER
    # =========================================================================
    if es_multitaller:
        render_kpis_multitaller(df_filtered)
        
        st.divider()
        
        render_ranking_talleres(df_filtered)
        
        st.divider()
        
        # Vista detallada multitaller con pestañas
        render_vista_multitaller(df_filtered, key_suffix="main")
        
        st.divider()
    
    # =========================================================================
    # SECCIÓN: KPIs PRINCIPALES (Consolidados)
    # =========================================================================
    st.subheader("📊 Métricas Consolidadas" if es_multitaller else "📊 Métricas Principales")
    render_kpis(df_filtered)

    st.divider()

    # =========================================================================
    # SECCIÓN: COMPARATIVO ANUAL (Año vs Año)
    # =========================================================================
    # Usar la data filtrada por el usuario para que el comparativo respete
    # los filtros aplicados en el sidebar
    df_ahorro_autorizado = filter_authorized_savings_records(df_filtered)
    if df_ahorro_autorizado is not None and not df_ahorro_autorizado.empty and 'AÑO' in df_ahorro_autorizado.columns:
        años_unicos = df_ahorro_autorizado['AÑO'].dropna().unique()
        if len(años_unicos) >= 1:
            st.subheader("📅 Comparativo Anual")
            render_comparativo_anual(df_filtered)

            st.divider()

    # =========================================================================
    # SECCIÓN: AHORRO POR MES
    # =========================================================================
    render_grafico_ahorro_mes_nuevo(df_filtered)

    st.divider()

    # =========================================================================
    # SECCIÓN: GRÁFICOS
    # =========================================================================
    render_grafico_causales(df_filtered)
    
    # =========================================================================
    # SECCIÓN: DISTRIBUCIÓN DE AHORROS POR COMPAÑÍA DE SEGUROS
    # =========================================================================
    render_grafico_ahorro_por_compania(df_filtered)
    
    st.divider()
    
    # =========================================================================
    # SECCIÓN: RECUPERACIÓN MENSUAL + EFECTIVIDAD
    # =========================================================================
    render_recuperacion_mensual(df_filtered)

    st.divider()

    render_efectividad_valoracion(df_filtered)

    st.divider()

    # =========================================================================
    # SECCIÓN: TASA DE IMPREVISTOS
    # =========================================================================
    render_grafico_tasa_imprevistos_nuevo(
        df=df_filtered,
        taller_id=None,
        año=None
    )

    st.divider()

    render_grafico_culpa_taller_mensual(df=df_filtered)

    st.divider()

    # Tabla resumen mensual de imprevistos
    render_tabla_resumen_imprevistos(df=df_filtered, año=None)

    st.divider()

    # Gráfico: Demora en Definición del Imprevisto por CIA y Estatus
    render_demora_definicion_imprevisto(df=df_filtered)

    st.divider()
    
    # =========================================================================
    # SECCIÓN: TABLA DETALLADA
    # =========================================================================
    render_tabla_detalle(df_filtered)
    
    st.divider()
    
    # =========================================================================
    # SECCIÓN: EXPORTACIÓN
    # =========================================================================
    render_export_section(df_filtered, filtros, talleres_seleccionados)
    
    # =========================================================================
    # FOOTER
    # =========================================================================
    render_footer(talleres_seleccionados)


if __name__ == "__main__":
    main()

"""
================================================================================
COMPONENTES UI - Taller Hub
================================================================================
Componentes reutilizables para el dashboard.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List
from .data_processor import filter_authorized_savings_records
from .theme import GrayScale
from .taller_config import get_nombre_taller


def _get_taller_display_name(talleres_seleccionados: List[str]) -> str:
    """Obtiene el nombre para mostrar según los talleres seleccionados"""
    if not talleres_seleccionados:
        return "Taller Hub"
    nombres = [get_nombre_taller(tid) for tid in talleres_seleccionados]
    return " | ".join(nombres)


def render_header(talleres_seleccionados: List[str] = None):
    """Renderiza el header principal del dashboard"""
    taller_nombre = _get_taller_display_name(talleres_seleccionados or [])

    col_logo, col_title = st.columns([1, 5])

    with col_logo:
        st.image("logo.png", width=100)

    with col_title:
        st.markdown(f'<div class="main-header">🚗 {taller_nombre.upper()}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sub-header">Sistema de Gestión de Ahorros y Análisis de Talleres Automotrices</div>',
            unsafe_allow_html=True
        )


def render_footer(talleres_seleccionados: List[str] = None):
    """Renderiza el footer del dashboard"""
    taller_nombre = _get_taller_display_name(talleres_seleccionados or [])

    st.divider()
    st.markdown(f"""
    <div style="text-align: center; color: {GrayScale.SLATE_400}; font-size: 0.8rem; padding: 2rem 0;">
        <p>{taller_nombre} v2.0 | Desarrollado para RENOMOTRIZ</p>
        <p>Stakeholders: Alexander Cano (Analista) | Sergio Romero (Operativo)</p>
    </div>
    """, unsafe_allow_html=True)


def render_debug_panel(df, error, debug_logs):
    """
    Panel de debug para diagnosticar problemas con los datos
    Soporte multitaller
    """
    with st.expander("🔧 Panel de Debug (Diagnóstico)", expanded=False):
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Limpiar Caché y Recargar", type="primary"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.rerun()
        
        st.write(f"**df is None:** {df is None}")
        st.write(f"**error:** {error}")
        
        if df is not None:
            st.write(f"**df.shape:** {df.shape}")
            st.write(f"**df.empty:** {df.empty}")
            st.write(f"**Columnas:** {list(df.columns)}")
            
            # Información de multitaller
            if "TALLER_ORIGEN" in df.columns:
                st.write("**Información Multitaller:**")
                st.write(f"  - Talleres únicos: {df['TALLER_ORIGEN'].nunique()}")
                st.write(f"  - Lista de talleres: {df['TALLER_ORIGEN'].unique().tolist()}")
                
                # Desglose por taller
                st.write("  - Registros por taller:")
                for taller, count in df.groupby("TALLER_ORIGEN").size().items():
                    st.write(f"    - {taller}: {count}")
            
            # Verificar columnas críticas para gráficas
            cols_criticas = ['AÑO', 'MES', 'DIFERENCIA', 'CAUSAL', 'ACCION', 'IMPREVISTO']
            st.write("**Columnas críticas para gráficas:**")
            for col in cols_criticas:
                existe = col in df.columns
                st.write(f"  - {col}: {'✅' if existe else '❌'}")
                if existe and col == 'DIFERENCIA':
                    st.write(f"    - Suma DIFERENCIA: ${df[col].sum():,.0f}")
                    st.write(f"    - Valores > 0: {len(df[df[col] > 0])}")
                    st.write(f"    - Valores nulos: {df[col].isna().sum()}")
            
            # Mostrar logs de procesamiento
            if debug_logs:
                st.write("**Logs de procesamiento:**")
                for log in debug_logs:
                    st.text(log)
                
        else:
            st.error("❌ DataFrame es None - No se pudieron cargar los datos")


def render_alerts(alerts):
    """Muestra las alertas de validación"""
    for severity, message in alerts:
        if severity == "error":
            st.error(f"🚨 {message}")
        elif severity == "warning":
            st.warning(f"⚠️ {message}")
        elif severity == "success":
            st.success(f"✅ {message}")


def render_data_info(df, df_filtered):
    """Muestra información sobre los datos cargados y filtros aplicados"""
    
    # Información básica
    mensaje = f"✅ Datos cargados: **{len(df)}** registros | Última actualización: {datetime.now().strftime('%H:%M:%S')}"
    
    # Si es multitaller, mostrar desglose por taller
    if "TALLER_ORIGEN" in df.columns:
        talleres = df["TALLER_ORIGEN"].unique()
        if len(talleres) > 1:
            # Crear desglose por taller
            desglose = df.groupby("TALLER_ORIGEN").size().to_dict()
            detalle = " | ".join([f"**{t}**: {c} regs" for t, c in desglose.items()])
            mensaje += f"\n\n🏪 **Desglose por taller:** {detalle}"
    
    st.success(mensaje)
    
    # Información de filtros aplicados
    if len(df_filtered) != len(df):
        st.info(f"📊 Mostrando {len(df_filtered)} de {len(df)} registros (filtros aplicados)")


def render_export_section(df_filtered, filtros, talleres_seleccionados=None):
    """Sección de exportación de datos"""
    from .exporters import generate_excel_report, generate_csv_export, generate_pdf_report
    from .fee_config import load_fee_config

    st.divider()
    st.header("📥 Exportación de Datos")

    taller_nombre = _get_taller_display_name(talleres_seleccionados or [])
    taller_slug = taller_nombre.lower().replace(" ", "_").replace("|", "_")

    # Toggle para incluir honorarios en PDF
    fee_config = load_fee_config()
    include_honorarios = st.toggle(
        "📊 Incluir honorarios en el reporte PDF",
        value=not fee_config.get('hide_fees_presentation', False),
        help="Activa/desactiva la inclusión de datos de honorarios en el PDF exportado"
    )

    col_exp1, col_exp2, col_exp3 = st.columns(3)

    # Exportar Excel
    with col_exp1:
        excel_buffer = generate_excel_report(df_filtered, filtros, taller_nombre)
        st.download_button(
            label="📊 Descargar Excel (Múltiples hojas)",
            data=excel_buffer,
            file_name=f"{taller_slug}_reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch'
        )

    # Exportar CSV
    with col_exp2:
        csv_data = generate_csv_export(df_filtered)
        st.download_button(
            label="📄 Descargar CSV",
            data=csv_data,
            file_name=f"{taller_slug}_datos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            width='stretch'
        )

    # Generar PDF
    with col_exp3:
        pdf_buffer = generate_pdf_report(df_filtered, filtros, include_honorarios=include_honorarios, taller_nombre=taller_nombre)
        honorarios_text = "con" if include_honorarios else "sin"
        st.download_button(
            label=f"📑 Descargar PDF ({honorarios_text} honorarios)",
            data=pdf_buffer,
            file_name=f"{taller_slug}_dashboard_{honorarios_text}_honorarios_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            width='stretch'
        )


def render_error_state(error):
    """Muestra el estado de error cuando no se pueden cargar los datos"""
    st.error(f"❌ {error}")
    st.info("""💡 Verifica:
1. La URL de Google Sheets es correcta
2. La hoja 'BASE DE DATOS' existe
3. Las credenciales de Google Cloud están configuradas""")


def render_empty_state():
    """Muestra el estado cuando no hay datos"""
    st.warning("⚠️ No se encontraron datos en la hoja")


def render_savings_debug_panel(df):
    """
    Panel de diagnóstico para ahorro mensual.
    Valida la agregación mensual usando únicamente DIA/MES/AÑO.
    FECHA_INGR y FECHA_AUTO quedan como referencia auxiliar.
    """
    with st.expander("🧪 Debug Ahorro Mensual", expanded=False):
        if df is None or df.empty:
            st.info("No hay datos para depurar.")
            return

        if not {'AÑO', 'MES', 'DIFERENCIA'}.issubset(df.columns):
            st.warning("Faltan columnas AÑO, MES o DIFERENCIA para depurar el ahorro mensual.")
            return

        df_debug = filter_authorized_savings_records(df)
        if df_debug is None or df_debug.empty:
            st.info("No hay registros AUTORIZADO para depurar.")
            return

        df_debug = df_debug[df_debug['DIFERENCIA'].fillna(0) != 0].copy()
        if df_debug.empty:
            st.info("No hay registros AUTORIZADO con ahorro distinto de cero.")
            return

        df_debug['FECHA_AUTO_DT'] = pd.to_datetime(df_debug.get('FECHA_AUTO'), errors='coerce', dayfirst=True)
        df_debug['FECHA_INGR_DT'] = pd.to_datetime(df_debug.get('FECHA_INGR'), errors='coerce', dayfirst=True)
        df_debug['AUTO_AÑO'] = df_debug['FECHA_AUTO_DT'].dt.year
        df_debug['AUTO_MES'] = df_debug['FECHA_AUTO_DT'].dt.month
        df_debug['INGR_AÑO'] = df_debug['FECHA_INGR_DT'].dt.year
        df_debug['INGR_MES'] = df_debug['FECHA_INGR_DT'].dt.month

        resumen_actual = (
            df_debug.groupby(['AÑO', 'MES'])['DIFERENCIA']
            .sum()
            .reset_index()
            .rename(columns={'DIFERENCIA': 'AHORRO_DIA_MES_ANO'})
        )

        resumen_ingr = (
            df_debug[df_debug['INGR_AÑO'].notna() & df_debug['INGR_MES'].notna()]
            .groupby(['INGR_AÑO', 'INGR_MES'])['DIFERENCIA']
            .sum()
            .reset_index()
            .rename(columns={'INGR_AÑO': 'AÑO', 'INGR_MES': 'MES', 'DIFERENCIA': 'REF_FECHA_INGR'})
        )

        comparativo = (
            resumen_actual.merge(resumen_ingr, on=['AÑO', 'MES'], how='outer')
            .fillna(0)
            .sort_values(['AÑO', 'MES'])
        )
        comparativo['DELTA_INGR_VS_COMPONENTES'] = comparativo['REF_FECHA_INGR'] - comparativo['AHORRO_DIA_MES_ANO']
        comparativo['PERIODO'] = comparativo['MES'].astype(int).astype(str).str.zfill(2) + '/' + comparativo['AÑO'].astype(int).astype(str)

        mismatch_ingr = df_debug[
            df_debug['INGR_AÑO'].notna() &
            ((df_debug['AÑO'] != df_debug['INGR_AÑO']) | (df_debug['MES'] != df_debug['INGR_MES']))
        ].copy()

        c1, c2, c3 = st.columns(3)
        c1.metric("Regs autorizados con ahorro", f"{len(df_debug):,}")
        c2.metric("Con DIA/MES/AÑO válidos", f"{len(df_debug[df_debug['FECHA_COMPLETA'].notna()]):,}")
        c3.metric("Difieren vs FECHA_INGR", f"{len(mismatch_ingr):,}", f"${mismatch_ingr['DIFERENCIA'].sum():,.0f}")

        st.caption("La lógica oficial usa solo DIA/MES/AÑO. La comparación con FECHA_INGR es solo para detectar incongruencias en la fuente.")

        st.dataframe(
            comparativo[['PERIODO', 'AHORRO_DIA_MES_ANO', 'REF_FECHA_INGR', 'DELTA_INGR_VS_COMPONENTES']],
            width='stretch',
            hide_index=True,
        )

        if not mismatch_ingr.empty:
            movement = (
                mismatch_ingr.groupby(['AÑO', 'MES', 'INGR_AÑO', 'INGR_MES'])['DIFERENCIA']
                .sum()
                .reset_index()
                .sort_values('DIFERENCIA', ascending=False)
            )
            movement['DE'] = movement['MES'].astype(int).astype(str).str.zfill(2) + '/' + movement['AÑO'].astype(int).astype(str)
            movement['HACIA'] = movement['INGR_MES'].astype(int).astype(str).str.zfill(2) + '/' + movement['INGR_AÑO'].astype(int).astype(str)

            st.markdown("**Incongruencias detectadas vs FECHA_INGR**")
            st.dataframe(
                movement[['DE', 'HACIA', 'DIFERENCIA']],
                width='stretch',
                hide_index=True,
            )

            detalle_cols = [
                col for col in ['PLACA', 'SINIESTRO', 'DIFERENCIA', 'DIA', 'MES', 'AÑO', 'FECHA_INGR', 'FECHA_AUTO', 'ESTATUS', 'TALLER_ORIGEN']
                if col in mismatch_ingr.columns
            ]
            st.markdown("**Filas con conflicto entre componentes y FECHA_INGR**")
            st.dataframe(
                mismatch_ingr[detalle_cols].sort_values('DIFERENCIA', ascending=False),
                width='stretch',
                hide_index=True,
            )

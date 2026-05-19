"""
================================================================================
PDF NARRATIVE — Texto narrativo dinámico para informes ejecutivos
================================================================================
Cada función retorna una lista de elementos reportlab (Paragraph, Spacer, etc.)
listos para agregar al PDF.

Uso:
    from modules.pdf_narrative import narrativa_introduccion
    elements.extend(narrativa_introduccion(...))
"""

import pandas as pd
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import mm

from .pdf_styles import get_executive_styles
from .pdf_executive_helpers import (
    build_body_paragraph,
    build_bullet_list,
    build_section_title,
    build_sub_section_title,
    build_hallazgo_box,
    build_conclusion_paragraph,
)

styles = get_executive_styles()


# ------------------------------------------------------------------------------
# Helpers de formato
# ------------------------------------------------------------------------------
def _fmt_money(value):
    """Formatea valores monetarios en español: $142.643.006"""
    try:
        return f"${float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _fmt_pct(value):
    """Formatea porcentaje: 78,3% (con coma decimal típica en español)."""
    try:
        return f"{float(value):.1f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "0,0%"


def _safe_len(df):
    """Retorna la longitud segura de un DataFrame."""
    if df is None or getattr(df, "empty", True):
        return 0
    return len(df)


def _get_ahorro_col(df):
    """Intenta identificar la columna de ahorro/monto en un DataFrame mensual."""
    if df is None or df.empty:
        return None
    for col in ("DIFERENCIA", "ahorro", "total", "valor", "monto"):
        if col in df.columns:
            return col
    # Último recurso: primera columna numérica
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            return col
    return None


# ------------------------------------------------------------------------------
# 1. Corte y saludo
# ------------------------------------------------------------------------------
def narrativa_corte_y_saludo(mes_nombre: str, año: int) -> list:
    """Retorna [Paragraph('Corte: Mes Año'), Paragraph('Compañeros de Distrikia:'), Spacer, Paragraph(intro)]"""
    elements = []
    elements.append(Paragraph(f"Corte: {mes_nombre} {año}", styles["EXEC_CORTE"]))
    elements.append(Paragraph("Compañeros de Distrikia:", styles["EXEC_GREETING"]))
    elements.append(Spacer(1, 6))
    intro = (
        f"El presente informe corresponde al cierre de {mes_nombre} de {año}. "
        "A continuación presentamos un análisis detallado de los resultados obtenidos "
        "en el programa de intermediación y gestión de imprevistos."
    )
    elements.append(build_body_paragraph(intro))
    return elements


# ------------------------------------------------------------------------------
# 2. Introducción
# ------------------------------------------------------------------------------
def narrativa_introduccion(mes_nombre: str, año: int, total_ahorro: float, honorarios: float, utilidad: float) -> list:
    """Párrafo introductorio con las cifras clave del período."""
    elements = []
    texto = (
        f"El presente informe tiene como objetivo mostrar los resultados operativos y financieros "
        f"del programa de intermediación al cierre de {mes_nombre} de {año}. "
        f"Durante este período, el programa generó un ahorro acumulado de {_fmt_money(total_ahorro)}, "
        f"de los cuales {_fmt_money(honorarios)} corresponden al valor de la intermediación "
        f"y {_fmt_money(utilidad)} representan la utilidad neta para el taller. "
        "Los números reflejan una gestión activa y una valoración cada vez más precisa de los procesos."
    )
    elements.append(build_body_paragraph(texto))
    return elements


# ------------------------------------------------------------------------------
# 3. Ahorros generados
# ------------------------------------------------------------------------------
def narrativa_ahorros_generados(total_ahorro: float, honorarios: float, utilidad: float) -> list:
    """Sección AHORROS GENERADOS con bullets resumen."""
    elements = []
    elements.append(build_section_title("AHORROS GENERADOS"))
    elements.append(
        build_body_paragraph(
            "Al cierre del período analizado, el programa de intermediación se consolida como una línea clave de rentabilidad:"
        )
    )
    bullets = [
        f"Ahorro acumulado: {_fmt_money(total_ahorro)}",
        f"Valor de la intermediación: {_fmt_money(honorarios)}",
        f"Utilidad para el taller: {_fmt_money(utilidad)}",
    ]
    elements.extend(build_bullet_list(bullets, bold_prefix=True))
    return elements


# ------------------------------------------------------------------------------
# 4. Gestión de imprevistos
# ------------------------------------------------------------------------------
def narrativa_gestion_imprevistos(cantidad_mes_actual: int, cantidad_mes_anterior: int) -> list:
    """Sección GESTIÓN DE IMPREVISTOS con texto comparativo y bullets interpretativos."""
    elements = []
    elements.append(build_section_title("GESTIÓN DE IMPREVISTOS"))

    variacion = cantidad_mes_actual - cantidad_mes_anterior
    if cantidad_mes_anterior and cantidad_mes_anterior != 0:
        variacion_pct = (variacion / cantidad_mes_anterior) * 100
    else:
        variacion_pct = 0.0

    if variacion > 0:
        texto = (
            f"En el mes en curso se observa un alza de {abs(variacion)} imprevistos "
            f"({_fmt_pct(variacion_pct)}) respecto al mes anterior. "
            "Esto no necesariamente indica un problema operativo, sino que puede reflejar:"
        )
    elif variacion < 0:
        texto = (
            f"En el mes en curso se observa una reducción de {abs(variacion)} imprevistos "
            f"({_fmt_pct(abs(variacion_pct))}) respecto al mes anterior. "
            "Esta disminución puede deberse a:"
        )
    else:
        texto = (
            "La cantidad de imprevistos se mantiene estable respecto al mes anterior. "
            "Esto sugiere una gestión consistente, aunque conviene analizar en detalle los factores subyacentes:"
        )

    elements.append(build_body_paragraph(texto))

    bullets = [
        "Mayor profundidad en los procesos de inspección y diagnóstico.",
        "Incremento en el volumen de vehículos valorados durante el período.",
        "Mejora en la trazabilidad y registro de cada evento identificado.",
    ]
    elements.extend(build_bullet_list(bullets))
    return elements


# ------------------------------------------------------------------------------
# 5. Detalle de imprevistos con cambio (antes de tabla)
# ------------------------------------------------------------------------------
def narrativa_imprevistos_cambio_detalle(df_cambio_mes) -> list:
    """Texto introductorio antes de la tabla de imprevistos del mes con cambio de repuestos."""
    elements = []
    n = _safe_len(df_cambio_mes)

    if n == 0:
        elements.append(Spacer(1, 6))
        return elements

    texto = (
        "En cuanto a la severidad de los imprevistos que requieren sustitución de componentes, "
        "se identificaron aquellos casos donde la causa está directamente ligada a la operación del taller. "
        f"Frecuencia de sustitución: durante el período se registraron {n} casos con acción de cambio "
        "que ameritan revisión técnica y administrativa."
    )
    elements.append(build_body_paragraph(texto))
    return elements


# ------------------------------------------------------------------------------
# 6. Tasa de imprevistos
# ------------------------------------------------------------------------------
def narrativa_tasa_imprevistos(tasa_actual: float, tasa_anterior: float, vehiculos_entregados: int, total_imprevistos: int) -> list:
    """TASA DE IMPREVISTOS: explicación, comportamiento reciente y hallazgo."""
    elements = []
    elements.append(build_section_title("TASA DE IMPREVISTOS"))

    explicacion = (
        "Este indicador mide la precisión de la valoración inicial comparando la cantidad de imprevistos "
        "identificados contra el total de vehículos entregados. Una tasa menor refleja mayor rigor en la inspección previa."
    )
    elements.append(build_body_paragraph(explicacion))

    variacion = tasa_actual - tasa_anterior
    if variacion > 0:
        comportamiento = (
            f"Comportamiento reciente: se observa un incremento de {_fmt_pct(abs(variacion))} en la tasa "
            f"respecto al período anterior, pasando de {_fmt_pct(tasa_anterior)} a {_fmt_pct(tasa_actual)}. "
            "Es recomendable revisar los protocolos de valoración para identificar oportunidades de mejora."
        )
    elif variacion < 0:
        comportamiento = (
            f"Comportamiento reciente: se observa una reducción de {_fmt_pct(abs(variacion))} en la tasa "
            f"respecto al período anterior, pasando de {_fmt_pct(tasa_anterior)} a {_fmt_pct(tasa_actual)}. "
            "Esta tendencia favorable sugiere que los ajustes implementados en el proceso de inspección están dando resultados."
        )
    else:
        comportamiento = (
            f"Comportamiento reciente: la tasa se mantiene en {_fmt_pct(tasa_actual)}, "
            "sin variación respecto al período anterior. La estabilidad es positiva, pero siempre existe margen de mejora."
        )
    elements.append(build_body_paragraph(comportamiento))

    hallazgo = (
        f"La entrega de {vehiculos_entregados} vehículos por compañías de seguros, "
        f"con un total de {total_imprevistos} imprevistos detectados, arroja una tasa de {_fmt_pct(tasa_actual)}. "
        "Este valor debe contextualizarse con el tipo de siniestros atendidos y la complejidad promedio de las reparaciones."
    )
    elements.append(build_hallazgo_box("Hallazgo", hallazgo))
    return elements


# ------------------------------------------------------------------------------
# 7. Ahorro por mes
# ------------------------------------------------------------------------------
def narrativa_ahorro_por_mes(df_mensual) -> list:
    """AHORROS POR MES: texto descriptivo de tres momentos clave según los datos mensuales."""
    elements = []
    elements.append(build_section_title("AHORROS POR MES"))

    if _safe_len(df_mensual) == 0:
        elements.append(Spacer(1, 6))
        return elements

    col = _get_ahorro_col(df_mensual)
    if col is None:
        elements.append(Spacer(1, 6))
        return elements

    df = df_mensual.copy()
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df[df[col] != 0].reset_index(drop=True)

    if df.empty:
        elements.append(
            build_body_paragraph(
                "No se registraron ahorros significativos en el período analizado para describir tendencias."
            )
        )
        return elements

    # Detectar momentos: inicio, pico, disminución
    inicio_val = df[col].iloc[0]
    pico_idx = df[col].idxmax()
    pico_val = df[col].max()
    pico_label = df.iloc[pico_idx].get("periodo", df.iloc[pico_idx].get("mes_label", f"mes {pico_idx + 1}"))

    # Buscar momento de disminución significativa después del pico
    disminucion_texto = None
    post_pico = df.iloc[pico_idx + 1 :]
    if not post_pico.empty:
        min_idx = post_pico[col].idxmin()
        min_val = post_pico[col].min()
        min_label = df.iloc[min_idx].get("periodo", df.iloc[min_idx].get("mes_label", f"mes {min_idx + 1}"))
        disminucion_texto = (
            f"un momento de ajuste en {min_label} con {_fmt_money(min_val)}, "
            "lo cual puede asociarse a menor volumen de vehículos o a valoraciones más precisas desde el inicio."
        )
    else:
        # Si no hay post-pico, buscar el último valor como referencia
        ult_val = df[col].iloc[-1]
        ult_label = df.iloc[-1].get("periodo", df.iloc[-1].get("mes_label", "el último mes"))
        if ult_val < pico_val:
            disminucion_texto = (
                f"una moderación hacia {ult_label} con {_fmt_money(ult_val)}, "
                "sugiriendo estabilización en los montos recuperados."
            )
        else:
            disminucion_texto = (
                f"una consolidación en {ult_label} con {_fmt_money(ult_val)}, "
                "manteniendo niveles elevados de recuperación."
            )

    inicio_label = df.iloc[0].get("periodo", df.iloc[0].get("mes_label", "el primer mes"))

    texto_intro = (
        "El comportamiento mensual muestra tres momentos claros que caracterizan la dinámica de recuperación:"
    )
    elements.append(build_body_paragraph(texto_intro))

    bullets = [
        (
            f"Inicio: en {inicio_label} el ahorro fue de {_fmt_money(inicio_val)}, "
            "estableciendo la línea base del período analizado."
        ),
        (
            f"Pico: el máximo ahorro se alcanzó en {pico_label} con {_fmt_money(pico_val)}, "
            "evidenciando el potencial del programa cuando coinciden volumen y oportunidad."
        ),
        f"Disminución: {disminucion_texto}",
    ]
    elements.extend(build_bullet_list(bullets))

    elementos_clave = (
        "El sistema funciona, pero no es lineal; depende directamente de:"
    )
    elements.append(build_body_paragraph(elementos_clave))

    bullets_deps = [
        "Volumen de vehículos valorados y entregados por las compañías de seguros.",
        "Calidad de la valoración inicial y exhaustividad del diagnóstico.",
        "Gestión activa de imprevistos, incluyendo negociación documentada y seguimiento de estatus.",
    ]
    elements.extend(build_bullet_list(bullets_deps))
    return elements


# ------------------------------------------------------------------------------
# 8. Comparativo anual
# ------------------------------------------------------------------------------
def narrativa_comparativo_anual(comparativo_df) -> list:
    """Texto después de la tabla comparativa anual con bullets dinámicos de variación mes a mes."""
    elements = []

    if _safe_len(comparativo_df) == 0:
        elements.append(Spacer(1, 6))
        return elements

    df = comparativo_df.copy()
    texto_intro = "Los datos muestran una dinámica muy interesante en la evolución mensual del ahorro:"
    elements.append(build_body_paragraph(texto_intro))

    bullets = []
    for _, row in df.iterrows():
        periodo = row.get("periodo", "Período")
        desviacion = row.get("desviacion_pct", 0)
        indicador = row.get("indicador", "")
        ahorro = row.get("DIFERENCIA", row.get("ahorro", 0))
        try:
            ahorro_num = float(ahorro)
        except (TypeError, ValueError):
            ahorro_num = 0
        if ahorro_num <= 0:
            continue
        if desviacion is not None and desviacion != 0:
            bullets.append(
                f"{periodo}: {_fmt_money(ahorro)} — variación del {_fmt_pct(desviacion)} respecto al mes anterior {indicador}."
            )
        else:
            bullets.append(f"{periodo}: {_fmt_money(ahorro)} — primer período de referencia.")

    if not bullets:
        bullets.append("El período analizado muestra una evolución inicial en la recuperación de mano de obra.")

    elements.extend(build_bullet_list(bullets))

    cierre = (
        "El crecimiento no es constante, pero sí significativo. Cada pico de recuperación coincide "
        "con períodos de alta actividad y gestión disciplinada, lo que reafirma que el modelo es escalable."
    )
    elements.append(build_body_paragraph(cierre))
    return elements


# ------------------------------------------------------------------------------
# 9. Ahorro por trimestre
# ------------------------------------------------------------------------------
def narrativa_ahorro_trimestre(variacion_pct: float) -> list:
    """AHORROS POR TRIMESTRE: interpretación ejecutiva de la variación trimestral."""
    elements = []
    elements.append(build_section_title("AHORROS POR TRIMESTRE"))

    if variacion_pct is None:
        variacion_pct = 0.0

    if variacion_pct > 0:
        texto_principal = (
            f"El taller prácticamente duplicó su capacidad de recuperación, con un crecimiento trimestral "
            f"de {_fmt_pct(variacion_pct)}. Este salto refleja no solo más vehículos, sino una valoración "
            "más agresiva y una gestión de imprevistos más oportuna."
        )
    elif variacion_pct < 0:
        texto_principal = (
            f"El trimestre cerró con una contracción de {_fmt_pct(abs(variacion_pct))} en la recuperación. "
            "Si bien la cifra es menor, es importante analizar si obedece a una mejora en la calidad de la valoración inicial "
            "o a factores externos como menor volumen de siniestros."
        )
    else:
        texto_principal = (
            "El trimestre se mantuvo estable en términos de recuperación. La consistencia es un indicador positivo, "
            "aunque siempre existe potencial de crecimiento optimizando los procesos de inspección y negociación."
        )

    elements.append(build_body_paragraph(texto_principal))
    elements.append(build_sub_section_title("¿Qué significa esto realmente?"))

    bullets = [
        "Cada peso recuperado es margen que antes se perdía por valoraciones incompletas.",
        "La intermediación ya no es un experimento; es una línea de negocio predecible.",
        "El siguiente paso es estandarizar los protocolos que generaron los mejores resultados.",
    ]
    elements.extend(build_bullet_list(bullets))

    cierre = (
        "Un lenguaje simple: antes el dinero se quedaba en el camino, hoy lo estamos recogiendo."
    )
    elements.append(build_conclusion_paragraph(cierre))
    return elements


# ------------------------------------------------------------------------------
# 10. Causales de imprevistos
# ------------------------------------------------------------------------------
def narrativa_causales(df_causales) -> list:
    """CAUSAL DE LOS IMPREVISTOS: análisis dinámico del concentración de causas."""
    elements = []
    elements.append(build_section_title("CAUSAL DE LOS IMPREVISTOS"))

    if _safe_len(df_causales) == 0:
        elements.append(Spacer(1, 6))
        return elements

    df = df_causales.copy()
    # Normalizar nombres de columnas
    df.columns = [c.lower().strip() for c in df.columns]

    col_causal = "causal" if "causal" in df.columns else df.columns[0]
    col_pct = "porcentaje" if "porcentaje" in df.columns else None
    col_cant = "cantidad" if "cantidad" in df.columns else None

    if col_pct is None and col_cant is not None:
        total = pd.to_numeric(df[col_cant], errors="coerce").fillna(0).sum()
        df["porcentaje"] = df[col_cant].apply(lambda x: (float(x) / total * 100) if total > 0 else 0)
        col_pct = "porcentaje"

    # Ordenar por porcentaje descendente
    if col_pct:
        df = df.sort_values(by=col_pct, ascending=False).reset_index(drop=True)

    # Calcular % de las dos principales causas
    top2_pct = 0.0
    top2_nombres = []
    if col_pct and len(df) >= 2:
        top2_pct = pd.to_numeric(df[col_pct].head(2), errors="coerce").fillna(0).sum()
        top2_nombres = [str(v) for v in df[col_causal].head(2).tolist()]
    elif col_pct and len(df) == 1:
        top2_pct = float(df[col_pct].iloc[0])
        top2_nombres = [str(df[col_causal].iloc[0])]

    nombres_txt = " y ".join(top2_nombres) if len(top2_nombres) <= 2 else ", ".join(top2_nombres[:-1]) + f" y {top2_nombres[-1]}"

    texto = (
        f"El {_fmt_pct(top2_pct)} de las causas de imprevistos corresponden a {nombres_txt}. "
        "La mayoría de los imprevistos no son aleatorios; responden a patrones identificables en la operación:"
    )
    elements.append(build_body_paragraph(texto))

    bullets = [
        "Ajustes de mano de obra que no se contemplaron en la valoración inicial.",
        "Ítems no cotizados por falta de fotos claras o diagnóstico incompleto.",
        "Predesarme insuficiente que deja al descubierto daños adicionales.",
    ]
    elements.extend(build_bullet_list(bullets))
    return elements


# ------------------------------------------------------------------------------
# 11. No cotizados
# ------------------------------------------------------------------------------
def narrativa_no_cotizados(df_no_cotizado) -> list:
    """ANALIZANDO LA CAUSA NO COTIZADOS: análisis dinámico de acciones asociadas."""
    elements = []
    elements.append(build_section_title("ANALIZANDO LA CAUSA NO COTIZADOS"))

    n = _safe_len(df_no_cotizado)
    if n == 0:
        elements.append(Spacer(1, 6))
        return elements

    # Si viene df con acciones, calcular distribución
    accion_col = None
    if df_no_cotizado is not None and not df_no_cotizado.empty:
        for c in df_no_cotizado.columns:
            if str(c).upper() in ("ACCION", "ACTION", "ACCIONES"):
                accion_col = c
                break

    if accion_col:
        acc_counts = df_no_cotizado[accion_col].astype(str).str.upper().str.strip().value_counts()
        total = acc_counts.sum()
        # Buscar acciones relevantes
        cambio = acc_counts.get("CAMBIO", 0)
        reparacion = sum(v for k, v in acc_counts.items() if "REPARA" in k)
        bitec = sum(v for k, v in acc_counts.items() if "BITEC" in k or "AJUSTE" in k)
        otros = total - cambio - reparacion - bitec

        pct_cambio = (cambio / total * 100) if total else 0
        pct_repara = (reparacion / total * 100) if total else 0
        pct_bitec = (bitec / total * 100) if total else 0

        texto = (
            f"El {_fmt_pct(pct_cambio + pct_repara + pct_bitec)} de los imprevistos no cotizados "
            f"se asocia con acciones atribuidas a cambio ({_fmt_pct(pct_cambio)}), "
            f"reparaciones ({_fmt_pct(pct_repara)}) y ajustes por bitec ({_fmt_pct(pct_bitec)}). "
            "Esto indica que la falta de cotización inicial está fuertemente ligada a la complejidad técnica del siniestro."
        )
    else:
        texto = (
            f"Se identificaron {n} imprevistos clasificados como no cotizados. "
            "Estos casos representan una oportunidad de mejora en la inspección inicial, "
            "ya que una valoración más exhaustiva podría prevenir gran parte de estos eventos."
        )

    elements.append(build_body_paragraph(texto))
    return elements


# ------------------------------------------------------------------------------
# 12. Cambio de piezas
# ------------------------------------------------------------------------------
def narrativa_cambio_piezas(df_cambio) -> list:
    """ANALIZANDO LAS CAUSAS DESDE LAS ACCIONES DE CAMBIO DE PIEZAS: resumen y concentración."""
    elements = []
    elements.append(build_section_title("ANALIZANDO LAS CAUSAS DESDE LAS ACCIONES DE CAMBIO DE PIEZAS"))

    n = _safe_len(df_cambio)
    if n == 0:
        elements.append(Spacer(1, 6))
        return elements

    elements.append(build_sub_section_title(f"Total casos: {n}"))

    # Si tiene columna CAUSAL, resumir top causas
    causal_col = None
    if df_cambio is not None and not df_cambio.empty:
        for c in df_cambio.columns:
            if str(c).upper() in ("CAUSAL", "CAUSA", "CAUSALES"):
                causal_col = c
                break

    if causal_col:
        causales = df_cambio[causal_col].astype(str).str.upper().str.strip().value_counts().head(5)
        bullets_causas = [f"{k}: {v} casos" for k, v in causales.items()]
        elements.extend(build_bullet_list(bullets_causas, bold_prefix=True))

        total = _safe_len(df_cambio)
        top3 = causales.head(3).sum()
        pct_top3 = (top3 / total * 100) if total else 0

        lectura = (
            f"Lectura técnica: el {_fmt_pct(pct_top3)} de los cambios está concentrado en 3 causas clave."
        )
        elements.append(build_body_paragraph(lectura))
    else:
        elements.append(
            build_body_paragraph(
                "Los casos de cambio de piezas reflejan la complejidad inherente a ciertos siniestros "
                "y la necesidad de una valoración técnica más profunda desde el primer diagnóstico."
            )
        )

    confirmacion = "Esto confirma:"
    elements.append(build_body_paragraph(confirmacion))

    bullets_conf = [
        "Que los imprevistos de cambio no son eventos aislados, sino repetitivos en ciertos tipos de daño.",
        "Que existe espacio para estandarizar el protocolo de inspección en los siniestros más frecuentes.",
        "Que capacitar al equipo en la identificación temprana de estas causas reduce paradas y reclamaciones.",
    ]
    elements.extend(build_bullet_list(bullets_conf))
    return elements


# ------------------------------------------------------------------------------
# 13. Conclusión
# ------------------------------------------------------------------------------
def narrativa_conclusion(variacion_trimestral_pct: float) -> list:
    """CONCLUSIÓN: párrafos finales ejecutivos."""
    elements = []
    elements.append(build_section_title("CONCLUSIÓN"))

    if variacion_trimestral_pct is None:
        variacion_trimestral_pct = 0.0

    p1 = (
        "El proceso funciona cuando se ejecuta con disciplina. Los meses con mayores recuperaciones "
        "no son producto de la suerte, sino de una secuencia clara: inspección exhaustiva, "
        "documentación oportuna, negociación activa y seguimiento de estatus."
    )
    elements.append(build_conclusion_paragraph(p1))

    p2 = (
        f"El crecimiento del {_fmt_pct(variacion_trimestral_pct)} trimestral demuestra que hay potencial real "
        "en el modelo de intermediación. Lo importante ahora es convertir esos picos en una línea base "
        "sostenible para todos los períodos."
    )
    elements.append(build_conclusion_paragraph(p2))

    p3 = (
        "No es falta de capacidad, es oportunidad de estandarizar lo que ya funciona. "
        "Con los protocolos adecuados, cada taller puede replicar estos resultados de manera predecible."
    )
    elements.append(build_conclusion_paragraph(p3))
    return elements

# Workflow: Implementación de PDF Ejecutivo tipo Informe

> Análisis de gaps entre el PDF actual del sistema y el PDF de referencia entregado por el cliente.

---

## 1. ANÁLISIS COMPARATIVO: REFERENCIA vs ACTUAL

### 1.1 Estructura del Documento

| Aspecto | PDF Referencia (Cliente) | PDF Actual (Sistema) |
|---------|-------------------------|----------------------|
| **Tono** | Ejecutivo / Narrativo | Dashboard / Técnico |
| **Destinatario** | Directivos / Compañeros de Distrikia | Operadores / Analistas |
| **Páginas** | ~7 páginas con flujo narrativo | Variable, secciones apiladas |
| **Header** | "Corte: Marzo 2026" + saludo personalizado | 🚗 TALLER HUB + subtítulo técnico |
| **Footer** | Ninguno | Fecha de generación técnica |
| **Metadata** | Implícita en el texto | Tabla explícita (fecha, filtros, registros) |

### 1.2 Elementos Visuales

| Elemento | PDF Referencia | PDF Actual |
|----------|---------------|------------|
| **KPIs principales** | 3 tarjetas horizontales con fondo **verde oscuro / teal** y iconos | Tabla simple con borde azul |
| **Headers de tablas** | Fondo **gris neutro** (#808080 aprox) | Fondo **azul brillante** (#3B82F6) |
| **Gráficos** | Fondo **verde oscuro** (#2a9d8f / teal), líneas brillantes | Fondo blanco, estilo matplotlib default |
| **Tipografía** | Sans-serif, tamaños variados por jerarquía | Helvetica uniforme |
| **Colores corporativos** | Verde teal + gris + blanco | Azul + slate + blanco |
| **Iconos/emojis** | Iconos planos (💰 ⭐ 🏦) en tarjetas KPI | Emojis en títulos de sección |

### 1.3 Contenido y Secciones

| Sección | PDF Referencia | PDF Actual |
|---------|---------------|------------|
| **Introducción** | ✅ Párrafo narrativo: "El presente informe tiene como objetivo..." | ❌ No existe |
| **KPIs ejecutivos** | ✅ Tarjetas: Ahorro Acumulado / Honorarios / Utilidad Taller | ✅ Tabla técnica |
| **Ahorros Generados** | ✅ Bullets narrativos con cifras | ❌ No existe como sección |
| **Gestión de Imprevistos** | ✅ Texto + tabla de detalle del mes | ✅ Solo tabla/gráfico |
| **Tasa de Imprevistos** | ✅ Texto explicativo + hallazgo destacado | ✅ Solo tabla/gráfico |
| **Ahorro por Mes** | ✅ Texto con 3 momentos + gráfico comparativo 2025 vs 2026 | ✅ Solo tabla + gráfico de barras |
| **Tabla comparativa anual** | ✅ Tabla 2025 vs 2026 con % y variación | ✅ Comparativo mensual/trimestral (diferente formato) |
| **Causales de imprevistos** | ✅ Tabla con dinero ($) y % relativo | ✅ Solo cantidad y % |
| **No Cotizados por acción** | ✅ Sub-sección especial con tabla propia | ❌ No existe |
| **Cambio de Piezas** | ✅ Tabla con cantidad + % + dinero | ✅ Solo tabla de detalle |
| **Conclusión** | ✅ Párrafo final ejecutivo | ❌ No existe |

---

## 2. GAPS IDENTIFICADOS (Priorizados)

### 🔴 CRÍTICO — Cambio de paradigma del PDF
1. **No existe modo "Informe Ejecutivo"**: El sistema solo genera un "reporte técnico del dashboard". Se necesita una función nueva `generate_executive_pdf_report()` o un modo alternativo.
2. **Falta narrativa ejecutiva**: El PDF de referencia explica el *porqué* y el *qué significa* de los números. El actual solo los muestra.
3. **Paleta de colores completamente diferente**: El cliente espera verde teal oscuro, no azul dashboard.

### 🟡 ALTO — Estilo visual
4. **KPIs sin tarjetas estilo PowerPoint**: Necesitan fondo oscuro, iconos, tipografía blanca.
5. **Gráficos sin fondo oscuro**: Los 3 gráficos del informe (imprevistos, tasa, ahorro comparativo) usan fondo verde.
6. **Headers de tabla grises**: Las tablas del referente usan fondo gris oscuro con letras blancas, no azul.
7. **Falta gráfico comparativo año vs año**: El referente muestra líneas de 2025 y 2026 superpuestas.

### 🟢 MEDIO — Contenido faltante
8. **Falta sección "Conclusión"** con texto ejecutivo.
9. **Falta sub-sección "No Cotizados por Acción"**.
10. **Las tablas de causales no muestran dinero ($)**: Solo cantidad y %.
11. **Falta tabla "Acciones de Cambio de Piezas"** con cantidad + % + dinero.

### 🔵 BAJO — Refinamientos
12. **Emoji en títulos**: El referente no usa emojis en headers; usa texto plano mayúsculas.
13. **Fuente**: El referente parece usar Calibri/Arial; el sistema usa Helvetica.

---

## 3. WORKFLOW DE IMPLEMENTACIÓN

### Fase 1: Infraestructura de Estilos Ejecutivos
**Archivo objetivo:** `modules/pdf_styles.py` (nuevo)

- [ ] Definir constantes de color del tema ejecutivo:
  - `TEAL_DARK = '#1B4D4D'` (fondo tarjetas KPI)
  - `TEAL_CARD = '#2A7A7A'` (fondo tarjetas secundarias)
  - `TEAL_CHART_BG = '#2A9D8F'` (fondo gráficos)
  - `GRAY_HEADER = '#666666'` (headers de tabla)
  - `TEXT_DARK = '#1E293B'` (texto principal)
- [ ] Crear `ParagraphStyle` para cada jerarquía del informe:
  - `EXEC_TITLE` — "Corte: Marzo 2026"
  - `EXEC_GREETING` — "Compañeros de Distrikia:"
  - `EXEC_BODY` — párrafos narrativos
  - `EXEC_BULLET` — bullets con viñetas
  - `EXEC_SECTION_HEAD` — "AHORROS GENERADOS."
  - `EXEC_SUB_HEAD` — "Tasa de Imprevistos:"
  - `EXEC_KPI_LABEL` — "AHORRO ACUMULADO"
  - `EXEC_KPI_VALUE` — "$142,643,006"
  - `EXEC_TABLE_HEADER` — headers grises
  - `EXEC_TABLE_BODY` — celdas de tabla
  - `EXEC_CONCLUSION` — texto de cierre

### Fase 2: Helpers Visuales Ejecutivos
**Archivo objetivo:** `modules/pdf_executive_helpers.py` (nuevo)

- [ ] `build_kpi_card(label, value, icon, width)` → retorna `Table` con fondo teal oscuro, texto blanco, icono.
- [ ] `build_kpi_row(cards_data)` → organiza 3 tarjetas en fila horizontal.
- [ ] `build_executive_table(data, headers, col_widths)` → tabla con headers grises, filas alternadas blanco/gris claro.
- [ ] `build_section_title(text)` → texto en negrita, mayúsculas, sin emoji, con espaciado.
- [ ] `build_body_paragraph(text)` → texto justificado, tamaño 10-11pt.
- [ ] `build_bullet_list(items)` → lista con viñetas.

### Fase 3: Gráficos con Fondo Oscuro (Tema Ejecutivo)
**Archivo objetivo:** Modificar/crear funciones en `modules/exporters.py` o `modules/pdf_charts.py`

- [ ] `_generar_grafico_imprevistos_ejecutivo(df)` — Línea con fondo teal (#2A9D8F), ejes blancos, puntos resaltados.
- [ ] `_generar_grafico_tasa_ejecutivo(df)` — Línea con fondo teal, mismos datos que `_generar_grafico_tasa_imprevistos` pero estilo ejecutivo.
- [ ] `_generar_grafico_ahorro_comparativo_ejecutivo(df)` — **NUEVO** Gráfico de líneas con dos series (año anterior vs año actual), fondo teal, leyenda.

> Nota: Para matplotlib con fondo oscuro se usa `fig.patch.set_facecolor('#2A9D8F')` y `ax.set_facecolor('#2A9D8F')`.

### Fase 4: Motor de Texto Narrativo
**Archivo objetivo:** `modules/pdf_narrative.py` (nuevo)

Crear funciones que generen texto dinámico basado en los datos:

- [ ] `narrativa_introduccion(mes, año, total_ahorro, honorarios, utilidad)` → párrafo introductorio.
- [ ] `narrativa_ahorros_generados(df_resumen)` → bullets con cifras y tendencias.
- [ ] `narrativa_gestion_imprevistos(df_imprevistos_mes, mes_anterior, mes_actual)` → texto + hallazgos.
- [ ] `narrativa_tasa_imprevistos(tasa_actual, tasa_anterior, vehiculos_entregados, imprevistos)` → explicación del indicador.
- [ ] `narrativa_ahorro_por_mes(df_mensual)` → 3 momentos (inicio/pico/disminución).
- [ ] `narrativa_comparativo_anual(variaciones)` → bullets dinámicos (Febrero +94%, Marzo -18%).
- [ ] `narrativa_causales(df_causales)` → concentración 78.3% en 2 atributos.
- [ ] `narrativa_no_cotizados(df_no_cotizado)` → análisis por acción.
- [ ] `narrativa_cambio_piezas(df_cambio)` → causales principales.
- [ ] `narrativa_conclusion(variacion_trimestral)` → texto de cierre.

### Fase 5: Generador PDF Ejecutivo Principal
**Archivo objetivo:** `modules/exporters.py` (nueva función)

- [ ] Crear `generate_executive_pdf_report(df, mes, año, taller_nombre, ...)`:
  1. Página 1: Corte + Saludo + Introducción + KPIs tarjetas + Ahorros Generados + Gestión Imprevistos + Gráfico Imprevistos.
  2. Página 2: Imprevistos del mes (tabla) + Tasa de Imprevistos (texto + hallazgo + gráfico).
  3. Página 3: Narrativa simple + Ahorro por Mes (texto + gráfico comparativo).
  4. Página 4: Tabla comparativa anual 2025 vs 2026 + Narrativa + Ahorro por Trimestre.
  5. Página 5: Tabla trimestral + Causales (tabla con $ y %).
  6. Página 6: Continuación causales + No Cotizados por acción.
  7. Página 7: Cambio de Piezas (tabla cantidad/%/$) + Conclusión.

### Fase 6: Tablas de Datos Específicas

- [ ] Tabla "Ahorros Generales del Proyecto" (2025 vs 2026): MES | AHORRO 2025 | % | AHORRO 2026 | % | TOTAL | VARIACIÓN.
- [ ] Tabla "Ahorro General por Trimestre": MES | 2025 | 2026 | Total | Variación.
- [ ] Tabla "Causales por Imprevisto" (con dinero): CAUSAS | RECUPERACIÓN $ | % RELATIVO.
- [ ] Tabla "Acciones de los Imprevistos — No Cotizado": ACCIONES | RECUPERACIÓN $ | % RELATIVO.
- [ ] Tabla "Acciones de Cambio de Piezas": CAUSALES | CANTIDAD | % | DINERO $.

### Fase 7: Integración con Streamlit
**Archivo objetivo:** `modules/components.py`

- [ ] En `render_export_section`, agregar selector:
  - "📊 PDF Técnico (Dashboard)" → `generate_pdf_report()`
  - "📑 PDF Ejecutivo (Informe Mensual)" → `generate_executive_pdf_report()`
- [ ] Para PDF Ejecutivo, solicitar mes y año obligatoriamente.
- [ ] Ajustar nombre de archivo: `distrikia_informe_marzo_2026_ejecutivo.pdf`

### Fase 8: Pruebas y Validación

- [ ] Generar PDF con datos de prueba y comparar visualmente con referencia.
- [ ] Verificar que todas las tablas calculen % correctamente.
- [ ] Verificar que los gráficos tengan fondo oscuro correcto.
- [ ] Verificar que el texto narrativo no tenga errores ortográficos.
- [ ] Revisar saltos de página (PageBreak) para que cada sección quede bien ubicada.
- [ ] Test con datos reales del taller.

---

## 4. ESPECIFICACIONES TÉCNICAS

### 4.1 Paleta de Colores Ejecutiva

```python
EXEC_COLORS = {
    'teal_dark':     '#1B4D4D',   # Fondo tarjetas KPI
    'teal_medium':   '#2A7A7A',   # Fondo tarjetas secundarias
    'teal_chart':    '#2A9D8F',   # Fondo gráficos
    'teal_light':    '#4ECDC4',   # Acentos
    'gray_header':   '#666666',   # Header tablas
    'gray_light':    '#F5F5F5',   # Filas alternadas
    'white':         '#FFFFFF',
    'black':         '#1E293B',
    'yellow_accent': '#FFD700',   # Variación positiva
    'red_accent':    '#E74C3C',   # Variación negativa
}
```

### 4.2 Jerarquía Tipográfica

| Elemento | Fuente | Tamaño | Color | Peso |
|----------|--------|--------|-------|------|
| Corte | Helvetica-Bold | 14pt | Negro | Bold |
| Saludo | Helvetica-Bold | 12pt | Negro | Bold |
| Sección | Helvetica-Bold | 11pt | Negro | Bold |
| Body | Helvetica | 10pt | Negro | Normal |
| KPI Label | Helvetica-Bold | 8pt | Blanco | Bold |
| KPI Value | Helvetica-Bold | 12pt | Blanco | Bold |
| Tabla Header | Helvetica-Bold | 9pt | Blanco | Bold |
| Tabla Body | Helvetica | 9pt | Negro | Normal |
| Total Row | Helvetica-Bold | 9pt | Blanco/Verde | Bold |

### 4.3 Dimensiones y Layout

- Página: Letter (8.5 x 11 pulgadas)
- Márgenes: 1 pulgada todos lados
- Ancho útil: ~6.5 pulgadas
- Tarjetas KPI: 3 en fila, ~2.1 pulgadas cada una
- Tablas: ancho completo ajustado por columna

---

## 5. ARCHIVOS A CREAR / MODIFICAR

| Acción | Archivo |
|--------|---------|
| **Crear** | `modules/pdf_styles.py` |
| **Crear** | `modules/pdf_executive_helpers.py` |
| **Crear** | `modules/pdf_narrative.py` |
| **Modificar** | `modules/exporters.py` — agregar `generate_executive_pdf_report()` y gráficos ejecutivos |
| **Modificar** | `modules/components.py` — agregar selector de tipo PDF |
| **Modificar** | `tests/test_pdf_exporters.py` — agregar tests del PDF ejecutivo |

---

## 6. ESTIMACIÓN DE ESFUERZO

| Fase | Complejidad | Tiempo Est. |
|------|-------------|-------------|
| Fase 1: Estilos | Media | 1-2h |
| Fase 2: Helpers visuales | Media | 2-3h |
| Fase 3: Gráficos oscuros | Alta | 3-4h |
| Fase 4: Narrativa | Alta | 3-4h |
| Fase 5: Generador principal | Alta | 4-5h |
| Fase 6: Tablas específicas | Media | 2-3h |
| Fase 7: Integración Streamlit | Baja | 1h |
| Fase 8: Pruebas y ajustes | Media | 2-3h |
| **Total** | | **~18-25h** |

---

*Documento generado el 2026-05-19*

#!/usr/bin/env python3
"""
Análisis exhaustivo de Tasa de Imprevistos Mensual.
Compara los porcentajes del cliente contra todas las combinaciones posibles
de filtros en el Excel local para identificar la metodología usada.
"""

import pandas as pd
import numpy as np
from itertools import combinations
from collections import defaultdict

# =============================================================================
# CONFIGURACIÓN DE DATOS
# =============================================================================

# Leer Excel
EXCEL_PATH = 'DISTRIKIA COPIA.xlsx'
df_base = pd.read_excel(EXCEL_PATH, sheet_name='BASE DE DATOS')

# Mapeo mes número -> nombre
MES_NOMBRE = {1:'ENE', 2:'FEB', 3:'MAR', 4:'ABR', 5:'MAY', 6:'JUN',
              7:'JUL', 8:'AGOS', 9:'SEPT', 10:'OCT', 11:'NOV', 12:'DIC'}
MES_NUMERO = {v:k for k,v in MES_NOMBRE.items()}

# Totales de vehículos entregados por mes (de hoja TASA DE IMPREVISTOS)
TOTALES = {
    (2025, 'FEB'): 58, (2025, 'MAR'): 51, (2025, 'ABR'): 48, (2025, 'MAY'): 65,
    (2025, 'JUN'): 40, (2025, 'JUL'): 54, (2025, 'AGOS'): 46, (2025, 'SEPT'): 58,
    (2025, 'OCT'): 55, (2025, 'NOV'): 37, (2025, 'DIC'): 41, (2026, 'ENE'): 48,
    (2026, 'FEB'): 54, (2026, 'MAR'): 60
}

# Porcentajes nuevos del cliente
PCT_NUEVOS = {
    (2025, 'FEB'): 39.7, (2025, 'MAR'): 47.1, (2025, 'ABR'): 60.4, (2025, 'MAY'): 41.5,
    (2025, 'JUN'): 32.5, (2025, 'JUL'): 44.4, (2025, 'AGOS'): 41.3, (2025, 'SEPT'): 50.0,
    (2025, 'OCT'): 43.6, (2025, 'NOV'): 35.1, (2025, 'DIC'): 24.4, (2026, 'ENE'): 43.8,
    (2026, 'FEB'): 53.7, (2026, 'MAR'): 72.0
}

# Porcentajes antiguos del cliente
PCT_ANTIGUOS = {
    (2025, 'FEB'): 40.0, (2025, 'MAR'): 47.0, (2025, 'ABR'): 60.0, (2025, 'MAY'): 42.0,
    (2025, 'JUN'): 33.0, (2025, 'JUL'): 44.0, (2025, 'AGOS'): 41.0, (2025, 'SEPT'): 50.0,
    (2025, 'OCT'): 44.0, (2025, 'NOV'): 35.0, (2025, 'DIC'): 24.0, (2026, 'ENE'): 44.0,
    (2026, 'FEB'): 54.0, (2026, 'MAR'): 60.0
}

# Calcular imprevistos que reporta el cliente (redondeo estándar)
IMP_NUEVOS = {k: round(v * PCT_NUEVOS[k] / 100) for k, v in TOTALES.items()}
IMP_ANTIGUOS = {k: round(v * PCT_ANTIGUOS[k] / 100) for k, v in TOTALES.items()}

# Orden de meses
MESES_ORDEN = list(TOTALES.keys())

print("=" * 100)
print("ANÁLISIS DE TASA DE IMPREVISTOS MENSUAL")
print("=" * 100)

# =============================================================================
# PASO 1: Tabla de imprevistos del cliente
# =============================================================================
print("\n" + "=" * 100)
print("PASO 1: IMPREVISTOS CALCULADOS DE LOS PORCENTAJES DEL CLIENTE")
print("=" * 100)

tabla1 = pd.DataFrame({
    'AÑO': [k[0] for k in MESES_ORDEN],
    'MES': [k[1] for k in MESES_ORDEN],
    'TOTAL': [TOTALES[k] for k in MESES_ORDEN],
    '% NUEVO': [PCT_NUEVOS[k] for k in MESES_ORDEN],
    'IMP. NUEVO': [IMP_NUEVOS[k] for k in MESES_ORDEN],
    '% ANTIGUO': [PCT_ANTIGUOS[k] for k in MESES_ORDEN],
    'IMP. ANTIGUO': [IMP_ANTIGUOS[k] for k in MESES_ORDEN],
    'DIF. IMPREVISTOS': [IMP_NUEVOS[k] - IMP_ANTIGUOS[k] for k in MESES_ORDEN]
})
print(tabla1.to_string(index=False))

# =============================================================================
# PASO 2: Explorar combinaciones de filtros
# =============================================================================
print("\n" + "=" * 100)
print("PASO 2: EXPLORACIÓN DE COMBINACIONES DE FILTROS EN EL EXCEL LOCAL")
print("=" * 100)

# Valores únicos de columnas relevantes
estatus_vals = ['AUTORIZADO', 'RECHAZADO', 'EN PROCESO']
causales_vals = sorted([c for c in df_base['CAUSAL'].dropna().unique() if str(c) != 'nan'])
print(f"\nCausales en BASE DE DATOS ({len(causales_vals)}):")
for i, c in enumerate(causales_vals, 1):
    print(f"  {i}. {c}")

# Precalcular conteos por mes para acelerar
# Agregar columna de mes-año como clave
df_base['AÑO_MES'] = df_base['AÑO'].astype(str) + '-' + df_base['MES'].map(MES_NOMBRE)

# Función para contar vehículos únicos con una combinación de filtros
def contar_imprevistos(df, dedup_cols, filtros):
    """
    df: DataFrame completo
    dedup_cols: lista de columnas para deduplicar
    filtros: dict con filtros adicionales
    """
    df_f = df.copy()
    for col, vals in filtros.items():
        if vals is not None:
            if isinstance(vals, list):
                df_f = df_f[df_f[col].isin(vals)]
            elif isinstance(vals, str) and vals.startswith('exclude_'):
                excluir = vals.replace('exclude_', '').split(',')
                df_f = df_f[~df_f[col].isin(excluir)]
    return df_f.groupby('AÑO_MES')[dedup_cols].apply(lambda x: x.drop_duplicates().shape[0]).to_dict()

# Combinaciones de ESTATUS
estatus_combos = [
    ("Sin filtro ESTATUS", {}),
    ("Solo AUTORIZADO", {'ESTATUS': ['AUTORIZADO']}),
    ("Excluir EN PROCESO", {'ESTATUS': 'exclude_EN PROCESO'}),
    ("Excluir RECHAZADO", {'ESTATUS': 'exclude_RECHAZADO'}),
    ("Excluir EN PROCESO+RECHAZADO", {'ESTATUS': 'exclude_EN PROCESO,RECHAZADO'}),
    ("Solo AUTORIZADO+EN PROCESO", {'ESTATUS': ['AUTORIZADO', 'EN PROCESO']}),
]

# Combinaciones de PROPIO
propio_combos = [
    ("Sin filtro PROPIO", {}),
    ("Solo PROPIO=SI", {'PROPIO': ['SI']}),
    ("Solo PROPIO=NO", {'PROPIO': ['NO']}),
]

# Combinaciones de COBRADO
cobrado_combos = [
    ("Sin filtro COBRADO", {}),
    ("Solo COBRADO=en taller", {'COBRADO': ['en taller']}),
    ("Excluir COBRADO=fuera", {'COBRADO': 'exclude_fuera'}),
]

# Deduplicación
dedup_combos = [
    ("PLACA", ['PLACA ']),
    ("PLACA+SINIESTRO", ['PLACA ', 'SINIESTRO']),
]

# Generar combinaciones de causales a excluir (limitado a 0, 1, y algunas combinaciones lógicas)
def generar_filtros_causales():
    filtros = []
    # Sin filtro de causal
    filtros.append(("Sin filtro causal", {}))
    # Excluir cada causal individual
    for c in causales_vals:
        filtros.append((f"Excluir: {c}", {'CAUSAL': f'exclude_{c}'}))
    # Solo ciertas causales (1 causal)
    for c in causales_vals:
        filtros.append((f"Solo: {c}", {'CAUSAL': [c]}))
    # Combinaciones específicas comunes
    filtros.append(("Excluir: AJUSTE MANO DE OBRA, NO COTIZADO", {'CAUSAL': 'exclude_AJUSTE MANO DE OBRA,NO COTIZADO'}))
    filtros.append(("Excluir: AJUSTE MANO DE OBRA, ELIMINACIÓN CIA.", {'CAUSAL': 'exclude_AJUSTE MANO DE OBRA,ELIMINACIÓN CIA.'}))
    filtros.append(("Excluir: NO COTIZADO, ELIMINACIÓN CIA.", {'CAUSAL': 'exclude_NO COTIZADO,ELIMINACIÓN CIA.'}))
    filtros.append(("Solo: NO COTIZADO, AJUSTE MANO DE OBRA", {'CAUSAL': ['NO COTIZADO', 'AJUSTE MANO DE OBRA']}))
    filtros.append(("Solo: NO COTIZADO, ELIMINACIÓN CIA.", {'CAUSAL': ['NO COTIZADO', 'ELIMINACIÓN CIA.']}))
    return filtros

causales_filtros = generar_filtros_causales()

print(f"\nTotal de combinaciones a probar:")
print(f"  ESTATUS: {len(estatus_combos)}")
print(f"  CAUSALES: {len(causales_filtros)}")
print(f"  PROPIO: {len(propio_combos)}")
print(f"  COBRADO: {len(cobrado_combos)}")
print(f"  DEDUP: {len(dedup_combos)}")
print(f"  TOTAL: {len(estatus_combos) * len(causales_filtros) * len(propio_combos) * len(cobrado_combos) * len(dedup_combos):,}")

# =============================================================================
# PASO 3: Probar TODAS las combinaciones (optimizado)
# =============================================================================
print("\n" + "=" * 100)
print("PASO 3: PROBANDO TODAS LAS COMBINACIONES")
print("=" * 100)

mejores_combinaciones = []
contador = 0

for dedup_nombre, dedup_cols in dedup_combos:
    for estatus_nombre, estatus_filtro in estatus_combos:
        for causal_nombre, causal_filtro in causales_filtros:
            for propio_nombre, propio_filtro in propio_combos:
                for cobrado_nombre, cobrado_filtro in cobrado_combos:
                    filtros = {**estatus_filtro, **causal_filtro, **propio_filtro, **cobrado_filtro}
                    nombre_combo = f"[{dedup_nombre}] + [{estatus_nombre}] + [{causal_nombre}] + [{propio_nombre}] + [{cobrado_nombre}]"
                    
                    # Calcular conteos para todos los meses de una vez
                    conteos_dict = contar_imprevistos(df_base, dedup_cols, filtros)
                    
                    resultados = {}
                    errores = 0
                    errores_abs = 0
                    
                    for key in MESES_ORDEN:
                        año, mes_nombre = key
                        clave = f"{año}-{mes_nombre}"
                        imp_local = conteos_dict.get(clave, 0)
                        imp_cliente = IMP_NUEVOS[key]
                        
                        resultados[key] = imp_local
                        errores += abs(imp_local - imp_cliente)
                        errores_abs += (imp_local - imp_cliente)
                    
                    coincide = all(resultados[k] == IMP_NUEVOS[k] for k in MESES_ORDEN)
                    
                    mejores_combinaciones.append({
                        'nombre': nombre_combo,
                        'dedup': dedup_nombre,
                        'filtros': filtros,
                        'resultados': resultados,
                        'error_total': errores,
                        'error_medio': errores / len(MESES_ORDEN),
                        'sesgo': errores_abs,
                        'coincide_exacto': coincide
                    })
                    
                    contador += 1
                    if contador % 500 == 0:
                        print(f"  Probadas {contador} combinaciones...")

# Ordenar por error total
mejores_combinaciones.sort(key=lambda x: x['error_total'])

print(f"\n{'='*100}")
print("TOP 20 COMBINACIONES CON MENOR ERROR TOTAL")
print(f"{'='*100}")
print(f"{'Rank':>5} {'Error Total':>12} {'Error Medio':>12} {'Sesgo':>8} {'Exacto':>8} {'Combinación':<80}")
for i, combo in enumerate(mejores_combinaciones[:20], 1):
    exacto = "SÍ" if combo['coincide_exacto'] else "NO"
    nombre_corto = combo['nombre'][:75] + "..." if len(combo['nombre']) > 75 else combo['nombre']
    print(f"{i:>5} {combo['error_total']:>12} {combo['error_medio']:>12.2f} {combo['sesgo']:>8} {exacto:>8} {nombre_corto:<80}")

# =============================================================================
# PASO 4: Detalle de las mejores combinaciones
# =============================================================================
print("\n" + "=" * 100)
print("PASO 4: DETALLE DE LAS 5 MEJORES COMBINACIONES")
print("=" * 100)

for rank, combo in enumerate(mejores_combinaciones[:5], 1):
    print(f"\n{'─'*100}")
    print(f"RANK #{rank}: {combo['nombre']}")
    print(f"Error total: {combo['error_total']} | Error medio: {combo['error_medio']:.2f} | Sesgo: {combo['sesgo']}")
    print(f"{'─'*100}")
    
    tabla = pd.DataFrame({
        'AÑO': [k[0] for k in MESES_ORDEN],
        'MES': [k[1] for k in MESES_ORDEN],
        'TOTAL': [TOTALES[k] for k in MESES_ORDEN],
        'Cliente': [IMP_NUEVOS[k] for k in MESES_ORDEN],
        'Excel': [combo['resultados'][k] for k in MESES_ORDEN],
        'Dif': [combo['resultados'][k] - IMP_NUEVOS[k] for k in MESES_ORDEN]
    })
    print(tabla.to_string(index=False))

# =============================================================================
# PASO 5: ¿Alguna coincide exactamente?
# =============================================================================
print("\n" + "=" * 100)
print("PASO 5: COMBINACIONES QUE COINCIDEN EXACTAMENTE CON EL CLIENTE")
print("=" * 100)

exactas = [c for c in mejores_combinaciones if c['coincide_exacto']]
if exactas:
    print(f"\n¡SE ENCONTRARON {len(exactas)} COMBINACIONES CON COINCIDENCIA EXACTA!")
    for combo in exactas:
        print(f"\n  ✓ {combo['nombre']}")
else:
    print("\n✗ NO SE ENCONTRÓ NINGUNA COMBINACIÓN QUE COINCIDA EXACTAMENTE CON TODOS LOS MESES.")

# =============================================================================
# PASO 6: Análisis de meses individuales
# =============================================================================
print("\n" + "=" * 100)
print("PASO 6: ANÁLISIS MES A MES - ¿QUÉ FILTROS COINCIDEN POR MES?")
print("=" * 100)

# Para cada mes, encontrar qué combinaciones dan exactamente el valor del cliente
for key in MESES_ORDEN:
    año, mes_nombre = key
    imp_cliente = IMP_NUEVOS[key]
    total = TOTALES[key]
    
    print(f"\n{'─'*80}")
    print(f"{año} {mes_nombre}: Cliente reporta {imp_cliente} imprevistos (de {total} vehículos, {PCT_NUEVOS[key]}%)")
    print(f"{'─'*80}")
    
    coinciden_mes = [c for c in mejores_combinaciones if c['resultados'][key] == imp_cliente]
    
    if coinciden_mes:
        print(f"  Combinaciones que coinciden exactamente para este mes: {len(coinciden_mes)}")
        for combo in coinciden_mes[:5]:
            print(f"    - {combo['nombre']}")
    else:
        print(f"  Ninguna combinación coincide exactamente. Más cercanas:")
        cercanas = sorted(mejores_combinaciones, key=lambda x: abs(x['resultados'][key] - imp_cliente))
        for combo in cercanas[:5]:
            diff = combo['resultados'][key] - imp_cliente
            print(f"    - {combo['resultados'][key]} (dif: {diff:+d}) | {combo['nombre'][:60]}")

# =============================================================================
# PASO 7: Comparación nueva vs antigua
# =============================================================================
print("\n" + "=" * 100)
print("PASO 7: COMPARACIÓN NUEVOS PORCENTAJES VS ANTIGUOS")
print("=" * 100)

tabla_cmp = pd.DataFrame({
    'AÑO': [k[0] for k in MESES_ORDEN],
    'MES': [k[1] for k in MESES_ORDEN],
    'TOTAL': [TOTALES[k] for k in MESES_ORDEN],
    '% ANTIGUO': [PCT_ANTIGUOS[k] for k in MESES_ORDEN],
    'IMP. ANTIGUO': [IMP_ANTIGUOS[k] for k in MESES_ORDEN],
    '% NUEVO': [PCT_NUEVOS[k] for k in MESES_ORDEN],
    'IMP. NUEVO': [IMP_NUEVOS[k] for k in MESES_ORDEN],
    'DIF. %': [PCT_NUEVOS[k] - PCT_ANTIGUOS[k] for k in MESES_ORDEN],
    'DIF. IMP.': [IMP_NUEVOS[k] - IMP_ANTIGUOS[k] for k in MESES_ORDEN]
})
print(tabla_cmp.to_string(index=False))

# =============================================================================
# PASO 8: Conclusiones
# =============================================================================
print("\n" + "=" * 100)
print("PASO 8: CONCLUSIONES Y RECOMENDACIONES")
print("=" * 100)

mejor = mejores_combinaciones[0]
print(f"\n1. MEJOR COMBINACIÓN ENCONTRADA:")
print(f"   {mejor['nombre']}")
print(f"   Error total acumulado: {mejor['error_total']} imprevistos")
print(f"   Error medio por mes: {mejor['error_medio']:.2f} imprevistos")

meses_exactos = sum(1 for k in MESES_ORDEN if mejor['resultados'][k] == IMP_NUEVOS[k])
print(f"   Meses que coinciden exactamente: {meses_exactos} de {len(MESES_ORDEN)}")

print(f"\n2. MESES CON DISCREPANCIAS (usando la mejor combinación):")
for key in MESES_ORDEN:
    local = mejor['resultados'][key]
    cliente = IMP_NUEVOS[key]
    if local != cliente:
        diff = local - cliente
        print(f"   {key[0]} {key[1]}: Excel={local}, Cliente={cliente}, Diferencia={diff:+d}")

diffs = [mejor['resultados'][k] - IMP_NUEVOS[k] for k in MESES_ORDEN]
print(f"\n3. PATRÓN DE DIFERENCIAS:")
print(f"   Meses donde Excel > Cliente: {sum(1 for d in diffs if d > 0)}")
print(f"   Meses donde Excel < Cliente: {sum(1 for d in diffs if d < 0)}")
print(f"   Meses donde Excel = Cliente: {sum(1 for d in diffs if d == 0)}")

sin_filtro = next((c for c in mejores_combinaciones if c['dedup'] == 'PLACA' and not any(k in c['filtros'] for k in ['ESTATUS', 'CAUSAL', 'PROPIO', 'COBRADO'])), None)
if sin_filtro:
    print(f"\n4. SIN NINGÚN FILTRO (solo PLACA única):")
    print(f"   Error total: {sin_filtro['error_total']}")
    print(f"   Error medio: {sin_filtro['error_medio']:.2f}")

print("\n" + "=" * 100)

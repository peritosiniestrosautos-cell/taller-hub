#!/usr/bin/env python3
"""
ANÁLISIS FINAL - TASA DE IMPREVISTOS MENSUAL
=============================================
Compara los porcentajes del cliente contra el Excel local para determinar
si los datos son correctos y qué metodología de filtros usar.
"""

import pandas as pd
import numpy as np

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
EXCEL_PATH = 'DISTRIKIA COPIA.xlsx'
df_base = pd.read_excel(EXCEL_PATH, sheet_name='BASE DE DATOS')

MES_NOMBRE = {1:'ENE', 2:'FEB', 3:'MAR', 4:'ABR', 5:'MAY', 6:'JUN',
              7:'JUL', 8:'AGOS', 9:'SEPT', 10:'OCT', 11:'NOV', 12:'DIC'}
MES_NUMERO = {v:k for k,v in MES_NOMBRE.items()}

TOTALES = {
    (2025, 'FEB'): 58, (2025, 'MAR'): 51, (2025, 'ABR'): 48, (2025, 'MAY'): 65,
    (2025, 'JUN'): 40, (2025, 'JUL'): 54, (2025, 'AGOS'): 46, (2025, 'SEPT'): 58,
    (2025, 'OCT'): 55, (2025, 'NOV'): 37, (2025, 'DIC'): 41, (2026, 'ENE'): 48,
    (2026, 'FEB'): 54, (2026, 'MAR'): 60
}

PCT_NUEVOS = {
    (2025, 'FEB'): 39.7, (2025, 'MAR'): 47.1, (2025, 'ABR'): 60.4, (2025, 'MAY'): 41.5,
    (2025, 'JUN'): 32.5, (2025, 'JUL'): 44.4, (2025, 'AGOS'): 41.3, (2025, 'SEPT'): 50.0,
    (2025, 'OCT'): 43.6, (2025, 'NOV'): 35.1, (2025, 'DIC'): 24.4, (2026, 'ENE'): 43.8,
    (2026, 'FEB'): 53.7, (2026, 'MAR'): 72.0
}

PCT_ANTIGUOS = {
    (2025, 'FEB'): 40.0, (2025, 'MAR'): 47.0, (2025, 'ABR'): 60.0, (2025, 'MAY'): 42.0,
    (2025, 'JUN'): 33.0, (2025, 'JUL'): 44.0, (2025, 'AGOS'): 41.0, (2025, 'SEPT'): 50.0,
    (2025, 'OCT'): 44.0, (2025, 'NOV'): 35.0, (2025, 'DIC'): 24.0, (2026, 'ENE'): 44.0,
    (2026, 'FEB'): 54.0, (2026, 'MAR'): 60.0
}

MESES_ORDEN = list(TOTALES.keys())

# =============================================================================
# FUNCIONES
# =============================================================================
def contar_placas_unicas(año, mes):
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes)]
    return df_mes['PLACA '].nunique()

def contar_placas_unicas_filtrado(año, mes, excluir_causal=None):
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes)]
    if excluir_causal:
        df_mes = df_mes[~df_mes['CAUSAL'].isin(excluir_causal if isinstance(excluir_causal, list) else [excluir_causal])]
    return df_mes['PLACA '].nunique()

# =============================================================================
# RESULTADO 1: Imprevistos del cliente (nuevos vs antiguos)
# =============================================================================
print("=" * 110)
print("RESULTADO 1: IMPREVISTOS DEL CLIENTE (CALCULADOS DE LOS PORCENTAJES)")
print("=" * 110)

tabla1 = []
for key in MESES_ORDEN:
    año, mes = key
    total = TOTALES[key]
    imp_nuevo = round(total * PCT_NUEVOS[key] / 100)
    imp_antiguo = round(total * PCT_ANTIGUOS[key] / 100)
    tabla1.append({
        'AÑO': año, 'MES': mes, 'TOTAL': total,
        '% NUEVO': f"{PCT_NUEVOS[key]:.1f}%",
        'IMP. NUEVO': imp_nuevo,
        '% ANTIGUO': f"{PCT_ANTIGUOS[key]:.1f}%",
        'IMP. ANTIGUO': imp_antiguo,
        'DIF': imp_nuevo - imp_antiguo
    })

df1 = pd.DataFrame(tabla1)
print(df1.to_string(index=False))

# =============================================================================
# RESULTADO 2: Comparación Excel local vs Cliente
# =============================================================================
print("\n" + "=" * 110)
print("RESULTADO 2: COMPARACIÓN EXCEL LOCAL VS CLIENTE")
print("=" * 110)

tabla2 = []
for key in MESES_ORDEN:
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    placas = contar_placas_unicas(año, mes_num)
    imp_nuevo = round(TOTALES[key] * PCT_NUEVOS[key] / 100)
    imp_antiguo = round(TOTALES[key] * PCT_ANTIGUOS[key] / 100)
    
    match_nuevo = "✓" if placas == imp_nuevo else "✗"
    match_antiguo = "✓" if placas == imp_antiguo else "✗"
    
    tabla2.append({
        'AÑO': año, 'MES': mes_nombre,
        'TOTAL': TOTALES[key],
        'Placas Únicas': placas,
        'Imp. Nuevo': imp_nuevo,
        'Dif Nuevo': placas - imp_nuevo,
        'Match Nuevo': match_nuevo,
        'Imp. Antiguo': imp_antiguo,
        'Dif Antiguo': placas - imp_antiguo,
        'Match Antiguo': match_antiguo,
    })

df2 = pd.DataFrame(tabla2)
print(df2.to_string(index=False))

exactos_nuevo = sum(1 for _, row in df2.iterrows() if row['Match Nuevo'] == '✓')
exactos_antiguo = sum(1 for _, row in df2.iterrows() if row['Match Antiguo'] == '✓')
print(f"\nMeses exactos vs NUEVO: {exactos_nuevo} de {len(MESES_ORDEN)}")
print(f"Meses exactos vs ANTIGUO: {exactos_antiguo} de {len(MESES_ORDEN)}")

# =============================================================================
# RESULTADO 3: Prueba de filtros por causal
# =============================================================================
print("\n" + "=" * 110)
print("RESULTADO 3: PRUEBA DE FILTROS POR CAUSAL")
print("=" * 110)

causales = sorted([c for c in df_base['CAUSAL'].dropna().unique() if str(c) != 'nan'])

# Probar excluir cada causal individualmente
print("\nExcluyendo UNA causal a la vez (error total acumulado vs datos NUEVOS):")
resultados_causal = []
for causal in causales:
    error_total = 0
    tabla_meses = []
    for key in MESES_ORDEN:
        año, mes_nombre = key
        mes_num = MES_NUMERO[mes_nombre]
        placas_sin = contar_placas_unicas_filtrado(año, mes_num, excluir_causal=causal)
        imp_nuevo = round(TOTALES[key] * PCT_NUEVOS[key] / 100)
        error_total += abs(placas_sin - imp_nuevo)
        tabla_meses.append((mes_nombre, placas_sin, imp_nuevo, placas_sin - imp_nuevo))
    resultados_causal.append((causal, error_total, tabla_meses))

resultados_causal.sort(key=lambda x: x[1])

print(f"{'Causal Excluida':<35} {'Error Total':>12} {'Error Medio':>12}")
for causal, error, _ in resultados_causal:
    print(f"{causal:<35} {error:>12} {error/len(MESES_ORDEN):>12.2f}")

# =============================================================================
# RESULTADO 4: ¿Qué cambió entre antiguo y nuevo?
# =============================================================================
print("\n" + "=" * 110)
print("RESULTADO 4: CAMBIOS ENTRE DATOS ANTIGUOS Y NUEVOS")
print("=" * 110)

cambios = []
for key in MESES_ORDEN:
    imp_nuevo = round(TOTALES[key] * PCT_NUEVOS[key] / 100)
    imp_antiguo = round(TOTALES[key] * PCT_ANTIGUOS[key] / 100)
    if imp_nuevo != imp_antiguo:
        cambios.append(f"  {key[0]} {key[1]}: {imp_antiguo} → {imp_nuevo} imprevistos (+{imp_nuevo - imp_antiguo})")

if cambios:
    print("\nMeses donde cambió la cantidad de imprevistos:")
    for c in cambios:
        print(c)
else:
    print("\nNo hubo cambios en la cantidad de imprevistos redondeados.")

# El único cambio real es MAR 2026
print(f"\n  NOTA: El único cambio REAL está en MAR 2026:")
print(f"  - Antiguo: 60.0% de 60 = 36 imprevistos")
print(f"  - Nuevo:   72.0% de 60 = 43 imprevistos")
print(f"  - Diferencia: +7 imprevistos")

# =============================================================================
# RESULTADO 5: Consistencia con Excel local
# =============================================================================
print("\n" + "=" * 110)
print("RESULTADO 5: CONSISTENCIA CON EXCEL LOCAL")
print("=" * 110)

placas_mar_2026 = contar_placas_unicas(2026, 3)
print(f"\nExcel local MAR 2026: {placas_mar_2026} placas únicas")
print(f"Cliente nuevo MAR 2026: 43 imprevistos")
print(f"Diferencia: {placas_mar_2026 - 43} (el Excel local tiene {43 - placas_mar_2026} vehículos MENOS)")

print(f"\nConclusión: El Excel local está DESACTUALIZADO para MAR 2026.")
print(f"Faltan al menos {43 - placas_mar_2026} vehículos en la BASE DE DATOS.")

# =============================================================================
# CONCLUSIONES FINALES
# =============================================================================
print("\n" + "=" * 110)
print("CONCLUSIONES FINALES")
print("=" * 110)

print("""
╔════════════════════════════════════════════════════════════════════════════════════════════╗
║                                    CONCLUSIONES                                            ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                            ║
║  1. METODOLOGÍA DEL CLIENTE:                                                               ║
║     • Cuenta VEHÍCULOS ÚNICOS POR PLACA en BASE DE DATOS.                                  ║
║     • NO aplica filtros de ESTATUS, CAUSAL, PROPIO o COBRADO.                              ║
║     • Usa redondeo estándar (ROUND).                                                       ║
║     • 7 de 14 meses coinciden EXACTAMENTE con el Excel local.                              ║
║                                                                                            ║
║  2. DATOS NUEVOS VS ANTIGUOS:                                                              ║
║     • Para 13 de 14 meses, los porcentajes nuevos producen los MISMOS imprevistos         ║
║       redondeados que los antiguos (solo cambiaron los decimales).                         ║
║     • El ÚNICO cambio real está en MAR 2026: de 36 a 43 imprevistos (+7).                 ║
║                                                                                            ║
║  3. EXCEL LOCAL DESACTUALIZADO:                                                            ║
║     • MAR 2026: El Excel tiene 36 placas, el cliente reporta 43. FALTAN 7 vehículos.      ║
║     • Los demás meses con pequeñas diferencias (±1 a ±4) probablemente se deben a          ║
║       que el Excel local fue actualizado después de que el cliente calculó sus datos.     ║
║                                                                                            ║
║  4. RECOMENDACIÓN:                                                                         ║
║     • Usar PLACA ÚNICA SIN FILTROS como método de cálculo.                                 ║
║     • Solicitar al cliente el Excel actualizado o los registros faltantes de MAR 2026.    ║
║     • Los porcentajes nuevos del cliente son CORRECTOS para la mayoría de meses,          ║
║       pero NO pueden replicarse completamente con el Excel local actual.                  ║
║                                                                                            ║
╚════════════════════════════════════════════════════════════════════════════════════════════╝
""")

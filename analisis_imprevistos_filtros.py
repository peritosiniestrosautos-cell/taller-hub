#!/usr/bin/env python3
"""
Análisis para identificar qué filtros podría estar usando el cliente.
Nos enfocamos en los meses donde hay diferencias entre Excel y datos antiguos/nuevos.
"""

import pandas as pd
import numpy as np

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

IMP_NUEVOS = {k: round(v * PCT_NUEVOS[k] / 100) for k, v in TOTALES.items()}
IMP_ANTIGUOS = {k: round(v * PCT_ANTIGUOS[k] / 100) for k, v in TOTALES.items()}

print("=" * 100)
print("IDENTIFICACIÓN DE FILTROS POR ANÁLISIS DE DIFERENCIAS")
print("=" * 100)

# =============================================================================
# Para cada mes con diferencia, ver qué placas "sobran" en el Excel
# =============================================================================
print("\n" + "=" * 100)
print("ANÁLISIS: ¿QUÉ VEHÍCULOS 'SOBRAN' EN EL EXCEL RESPECTO A LOS DATOS ANTIGUOS?")
print("=" * 100)

# Diferencias con datos antiguos
meses_dif = []
for key in TOTALES.keys():
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placas_unicas = set(df_mes['PLACA '].unique())
    imp_antiguo = IMP_ANTIGUOS[key]
    dif = len(placas_unicas) - imp_antiguo
    if dif != 0:
        meses_dif.append((key, dif, placas_unicas, df_mes))

print(f"\nMeses con diferencias respecto a datos ANTIGUOS: {len(meses_dif)}")
for key, dif, placas, df_mes in meses_dif:
    print(f"\n{'─'*80}")
    print(f"{key[0]} {key[1]}: Excel tiene {len(placas)} placas, Cliente antiguo reporta {IMP_ANTIGUOS[key]} (dif: {dif:+d})")
    print(f"{'─'*80}")
    
    # Agrupar por placa para ver atributos
    placas_info = df_mes.groupby('PLACA ').agg({
        'ESTATUS': lambda x: list(x.unique()),
        'CAUSAL': lambda x: list(x.unique()),
        'COMPAÑÍA DE SEGUROS': 'first',
        'PROPIO': 'first',
        'COBRADO': 'first'
    }).reset_index()
    
    print(f"  Detalle por placa:")
    for _, row in placas_info.iterrows():
        print(f"    {row['PLACA ']}: ESTATUS={row['ESTATUS']}, CAUSAL={row['CAUSAL']}, CIA={row['COMPAÑÍA DE SEGUROS']}, PROPIO={row['PROPIO']}, COBRADO={row['COBRADO']}")

# =============================================================================
# Probar si excluir alguna causal específica hace coincidir los datos antiguos
# =============================================================================
print("\n" + "=" * 100)
print("PRUEBA: ¿QUÉ CAUSALES EXCLUIR PARA COINCIDIR CON DATOS ANTIGUOS?")
print("=" * 100)

causales = [c for c in df_base['CAUSAL'].dropna().unique() if str(c) != 'nan']

for key in TOTALES.keys():
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placas_total = df_mes['PLACA '].nunique()
    imp_antiguo = IMP_ANTIGUOS[key]
    
    if placas_total == imp_antiguo:
        continue
        
    print(f"\n{key[0]} {key[1]}: Excel={placas_total}, Cliente antiguo={imp_antiguo}, necesita reducir en {placas_total - imp_antiguo}")
    
    # Probar excluir cada causal individualmente
    for causal in causales:
        placas_sin = df_mes[df_mes['CAUSAL'] != causal]['PLACA '].nunique()
        if placas_sin == imp_antiguo:
            print(f"  ✓ Excluir '{causal}' coincide exactamente ({placas_sin})")
        
    # Probar excluir combinaciones de 2 causales
    from itertools import combinations
    for c1, c2 in combinations(causales, 2):
        placas_sin = df_mes[~df_mes['CAUSAL'].isin([c1, c2])]['PLACA '].nunique()
        if placas_sin == imp_antiguo:
            print(f"  ✓ Excluir '{c1}' + '{c2}' coincide exactamente ({placas_sin})")

# =============================================================================
# Verificar si el cliente podría estar usando PLACA+SINIESTRO con algún filtro
# =============================================================================
print("\n" + "=" * 100)
print("COMPARACIÓN: PLACA ÚNICA vs PLACA+SINIESTRO vs DATOS ANTIGUOS Y NUEVOS")
print("=" * 100)

print(f"\n{'AÑO':>5} {'MES':>5} {'TOTAL':>6} {'Placa':>6} {'P+S':>6} {'Antiguo':>8} {'Nuevo':>8} {'Dif Placa-Ant':>14} {'Dif P+S-Ant':>12} {'Dif Placa-Nue':>14} {'Dif P+S-Nue':>12}")
for key in TOTALES.keys():
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placa = df_mes['PLACA '].nunique()
    ps = df_mes[['PLACA ', 'SINIESTRO']].drop_duplicates().shape[0]
    ant = IMP_ANTIGUOS[key]
    nue = IMP_NUEVOS[key]
    print(f"{año:>5} {mes_nombre:>5} {TOTALES[key]:>6} {placa:>6} {ps:>6} {ant:>8} {nue:>8} {placa-ant:>14} {ps-ant:>12} {placa-nue:>14} {ps-nue:>12}")

# =============================================================================
# ¿El cliente podría estar filtrando por ESTATUS?
# =============================================================================
print("\n" + "=" * 100)
print("PRUEBA: FILTROS POR ESTATUS (PLACA ÚNICA)")
print("=" * 100)

for key in TOTALES.keys():
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    
    placas_total = df_mes['PLACA '].nunique()
    placas_aut = df_mes[df_mes['ESTATUS'] == 'AUTORIZADO']['PLACA '].nunique()
    placas_no_rech = df_mes[df_mes['ESTATUS'] != 'RECHAZADO']['PLACA '].nunique()
    placas_no_proc = df_mes[df_mes['ESTATUS'] != 'EN PROCESO']['PLACA '].nunique()
    placas_aut_proc = df_mes[df_mes['ESTATUS'].isin(['AUTORIZADO', 'EN PROCESO'])]['PLACA '].nunique()
    
    ant = IMP_ANTIGUOS[key]
    nue = IMP_NUEVOS[key]
    
    matches = []
    if placas_total == ant: matches.append("Total=Ant")
    if placas_total == nue: matches.append("Total=Nue")
    if placas_aut == ant: matches.append("Aut=Ant")
    if placas_aut == nue: matches.append("Aut=Nue")
    if placas_no_rech == ant: matches.append("NoRech=Ant")
    if placas_no_rech == nue: matches.append("NoRech=Nue")
    if placas_no_proc == ant: matches.append("NoProc=Ant")
    if placas_no_proc == nue: matches.append("NoProc=Nue")
    if placas_aut_proc == ant: matches.append("AutProc=Ant")
    if placas_aut_proc == nue: matches.append("AutProc=Nue")
    
    if matches:
        print(f"{año} {mes_nombre:>5}: {', '.join(matches)}")

# =============================================================================
# ¿El cliente podría estar filtrando por PROPIO o COBRADO?
# =============================================================================
print("\n" + "=" * 100)
print("PRUEBA: FILTROS POR PROPIO Y COBRADO (PLACA ÚNICA)")
print("=" * 100)

for key in TOTALES.keys():
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    
    placas_si = df_mes[df_mes['PROPIO'] == 'SI']['PLACA '].nunique()
    placas_no = df_mes[df_mes['PROPIO'] == 'NO']['PLACA '].nunique()
    placas_taller = df_mes[df_mes['COBRADO'] == 'en taller']['PLACA '].nunique()
    placas_fuera = df_mes[df_mes['COBRADO'] == 'fuera']['PLACA '].nunique()
    
    ant = IMP_ANTIGUOS[key]
    nue = IMP_NUEVOS[key]
    
    matches = []
    if placas_si == ant: matches.append("SI=Ant")
    if placas_si == nue: matches.append("SI=Nue")
    if placas_no == ant: matches.append("NO=Ant")
    if placas_no == nue: matches.append("NO=Nue")
    if placas_taller == ant: matches.append("Taller=Ant")
    if placas_taller == nue: matches.append("Taller=Nue")
    if placas_fuera == ant: matches.append("Fuera=Ant")
    if placas_fuera == nue: matches.append("Fuera=Nue")
    
    if matches:
        print(f"{año} {mes_nombre:>5}: {', '.join(matches)}")

# =============================================================================
# Resumen de hallazgos
# =============================================================================
print("\n" + "=" * 100)
print("RESUMEN DE HALLAZGOS")
print("=" * 100)

print("""
HALLAZGOS CLAVE:

1. PARA LOS DATOS ANTIGUOS:
   - MAR 2026 coincide EXACTAMENTE con PLACA única sin filtro (36=36).
   - Esto sugiere que los datos antiguos fueron calculados directamente
     del Excel local sin filtros adicionales.
   - Los meses con diferencias (MAR-MAY, SEPT, NOV, DIC 2025; FEB 2026)
     podrían deberse a que el Excel local fue actualizado DESPUÉS de que
     el cliente calculó los porcentajes antiguos.

2. PARA LOS DATOS NUEVOS:
   - MAR 2026 cambió de 36 a 43 imprevistos, pero el Excel local sigue
     teniendo solo 36 placas. ESTE CAMBIO NO PUEDE REPLICARSE con el
     Excel local actual.
   - Los demás meses son prácticamente idénticos a los antiguos (solo
     cambian los decimales, no los imprevistos redondeados).

3. LA METODOLOGÍA MÁS PROBABLE DEL CLIENTE:
   - Contar VEHÍCULOS ÚNICOS POR PLACA en BASE DE DATOS.
   - SIN FILTROS de ESTATUS, CAUSAL, PROPIO o COBRADO.
   - El redondeo parece ser ROUND() estándar (no TRUNC).

4. RECOMENDACIÓN FINAL:
   a) El Excel local ESTÁ DESACTUALIZADO respecto a los datos del cliente,
      ESPECIALMENTE para MAR 2026 donde faltan 7 vehículos.
   b) Para replicar los cálculos del cliente, usar:
      - Deduplicar por PLACA (no PLACA+SINIESTRO).
      - Sin filtros adicionales.
      - Redondeo estándar (ROUND).
   c) Es necesario solicitar al cliente el Excel actualizado o los
      registros faltantes de MAR 2026.
""")

print("=" * 100)

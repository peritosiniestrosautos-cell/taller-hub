#!/usr/bin/env python3
"""
Análisis detallado adicional para entender las discrepancias.
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

MESES_ORDEN = list(TOTALES.keys())

print("=" * 100)
print("ANÁLISIS DETALLADO ADICIONAL")
print("=" * 100)

# =============================================================================
# 1. Comparar "sin filtro PLACA única" vs datos antiguos y nuevos
# =============================================================================
print("\n" + "=" * 100)
print("1. COMPARACIÓN: Sin filtro, PLACA única vs Cliente Antiguo y Nuevo")
print("=" * 100)

tabla = []
for key in MESES_ORDEN:
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placas_unicas = df_mes['PLACA '].nunique()
    
    tabla.append({
        'AÑO': año, 'MES': mes_nombre, 'TOTAL': TOTALES[key],
        'Placas Únicas': placas_unicas,
        'Imp. Antiguo': IMP_ANTIGUOS[key],
        'Dif Antiguo': placas_unicas - IMP_ANTIGUOS[key],
        'Imp. Nuevo': IMP_NUEVOS[key],
        'Dif Nuevo': placas_unicas - IMP_NUEVOS[key],
    })

df_tabla = pd.DataFrame(tabla)
print(df_tabla.to_string(index=False))

print(f"\nError total vs ANTIGUO: {df_tabla['Dif Antiguo'].abs().sum()}")
print(f"Error total vs NUEVO: {df_tabla['Dif Nuevo'].abs().sum()}")
print(f"Meses exactos vs ANTIGUO: {(df_tabla['Dif Antiguo'] == 0).sum()}")
print(f"Meses exactos vs NUEVO: {(df_tabla['Dif Nuevo'] == 0).sum()}")

# =============================================================================
# 2. ¿Y si el cliente usa TRUNC en vez de ROUND?
# =============================================================================
print("\n" + "=" * 100)
print("2. ¿EL CLIENTE USA TRUNC/FLOOR EN VEZ DE ROUND?")
print("=" * 100)

tabla2 = []
for key in MESES_ORDEN:
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placas_unicas = df_mes['PLACA '].nunique()
    
    imp_trunc_nuevo = int(TOTALES[key] * PCT_NUEVOS[key] / 100)
    imp_trunc_antiguo = int(TOTALES[key] * PCT_ANTIGUOS[key] / 100)
    
    tabla2.append({
        'AÑO': año, 'MES': mes_nombre, 'TOTAL': TOTALES[key],
        'Placas Únicas': placas_unicas,
        'Trunc Nuevo': imp_trunc_nuevo,
        'Dif Trunc Nuevo': placas_unicas - imp_trunc_nuevo,
        'Trunc Antiguo': imp_trunc_antiguo,
        'Dif Trunc Antiguo': placas_unicas - imp_trunc_antiguo,
    })

df_tabla2 = pd.DataFrame(tabla2)
print(df_tabla2.to_string(index=False))

# =============================================================================
# 3. Análisis específico de MAR 2026
# =============================================================================
print("\n" + "=" * 100)
print("3. ANÁLISIS ESPECÍFICO DE MAR 2026 (DONDE HAY MAYOR DISCREPANCIA)")
print("=" * 100)

df_mar = df_base[(df_base['AÑO'] == 2026) & (df_base['MES'] == 3)]
print(f"\nTotal registros en BASE DE DATOS para MAR 2026: {len(df_mar)}")
print(f"Vehículos únicos por PLACA: {df_mar['PLACA '].nunique()}")
print(f"Vehículos únicos por PLACA+SINIESTRO: {df_mar[['PLACA ', 'SINIESTRO']].drop_duplicates().shape[0]}")
print(f"\nCliente reporta: {IMP_NUEVOS[(2026, 'MAR')]} imprevistos (72.0% de 60)")
print(f"Diferencia: {IMP_NUEVOS[(2026, 'MAR')] - df_mar['PLACA '].nunique()} vehículos FALTAN en el Excel local")

print(f"\nPor ESTATUS:")
print(df_mar['ESTATUS'].value_counts().to_string())

print(f"\nPor CAUSAL:")
print(df_mar['CAUSAL'].value_counts().to_string())

print(f"\nPor COMPAÑÍA DE SEGUROS:")
print(df_mar['COMPAÑÍA DE SEGUROS'].value_counts().to_string())

print(f"\nVehículos únicos en MAR 2026:")
placas_mar = sorted(df_mar['PLACA '].unique())
print(f"Total: {len(placas_mar)}")
print(f"Placas: {', '.join(placas_mar)}")

# =============================================================================
# 4. ¿Cuáles meses coinciden exactamente con PLACA única sin filtro?
# =============================================================================
print("\n" + "=" * 100)
print("4. COINCIDENCIAS EXACTAS CON 'PLACA ÚNICA SIN FILTRO'")
print("=" * 100)

print(f"\nVs PORCENTAJES NUEVOS:")
for key in MESES_ORDEN:
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placas = df_mes['PLACA '].nunique()
    cliente = IMP_NUEVOS[key]
    match = "✓ COINCIDE" if placas == cliente else f"✗ Dif: {placas - cliente:+d}"
    print(f"  {año} {mes_nombre:>5}: Excel={placas:>2}, Cliente={cliente:>2}  {match}")

print(f"\nVs PORCENTAJES ANTIGUOS:")
for key in MESES_ORDEN:
    año, mes_nombre = key
    mes_num = MES_NUMERO[mes_nombre]
    df_mes = df_base[(df_base['AÑO'] == año) & (df_base['MES'] == mes_num)]
    placas = df_mes['PLACA '].nunique()
    cliente = IMP_ANTIGUOS[key]
    match = "✓ COINCIDE" if placas == cliente else f"✗ Dif: {placas - cliente:+d}"
    print(f"  {año} {mes_nombre:>5}: Excel={placas:>2}, Cliente={cliente:>2}  {match}")

# =============================================================================
# 5. Verificar si el cliente usa redondeo al entero más cercano o truncamiento
# =============================================================================
print("\n" + "=" * 100)
print("5. ANÁLISIS DE MÉTODO DE REDONDEO DEL CLIENTE")
print("=" * 100)

print(f"\nPara cada mes, qué imprevistos produce cada método de redondeo:")
print(f"{'AÑO':>5} {'MES':>5} {'TOTAL':>6} {'%Nuevo':>7} {'ROUND':>6} {'TRUNC':>6} {'FLOOR':>6} {'CEIL':>6} {'Cliente':>8}")
for key in MESES_ORDEN:
    año, mes_nombre = key
    total = TOTALES[key]
    pct = PCT_NUEVOS[key]
    raw = total * pct / 100
    r = round(raw)
    t = int(raw)
    f = int(np.floor(raw))
    c = int(np.ceil(raw))
    cliente = IMP_NUEVOS[key]
    print(f"{año:>5} {mes_nombre:>5} {total:>6} {pct:>7.1f} {r:>6} {t:>6} {f:>6} {c:>6} {cliente:>8}")

# =============================================================================
# 6. ¿El Excel tiene datos hasta ABR 2026?
# =============================================================================
print("\n" + "=" * 100)
print("6. RANGO TEMPORAL DEL EXCEL LOCAL")
print("=" * 100)

print(f"\nMeses disponibles en BASE DE DATOS:")
conteos = df_base.groupby(['AÑO', 'MES']).size().reset_index(name='registros')
conteos['MES_NOMBRE'] = conteos['MES'].map(MES_NOMBRE)
for _, row in conteos.iterrows():
    print(f"  {int(row['AÑO'])} {row['MES_NOMBRE']:>5}: {row['registros']} registros")

# =============================================================================
# 7. Conclusiones finales
# =============================================================================
print("\n" + "=" * 100)
print("7. CONCLUSIONES FINALES")
print("=" * 100)

print("""
CONCLUSIONES:

1. MARZO 2026 ES EL ÚNICO MES CON CAMBIO REAL:
   - Los porcentajes nuevos vs antiguos son casi idénticos para todos los meses
     excepto MAR 2026 (60.0% → 72.0%, de 36 a 43 imprevistos).
   - El Excel local solo tiene 36 placas únicas para MAR 2026, pero el cliente
     reporta 43. Esto significa que FALTAN 7 vehículos en el Excel local.
   - El Excel local está DESACTUALIZADO para MAR 2026.

2. LA METODOLOGÍA DEL CLIENTE ES PROBABLEMENTE:
   - Contar VEHÍCULOS ÚNICOS POR PLACA con imprevistos (sin filtros adicionales).
   - Para 7 de 14 meses (FEB, JUN, JUL, AGOS, OCT 2025; ENE, FEB 2026) esto
     coincide EXACTAMENTE con los datos nuevos del cliente.
   - Las pequeñas diferencias en otros meses (±1 a ±3) pueden deberse a:
     a) Redondeo diferente (el cliente puede estar usando TRUNC o redondeo
        personalizado).
     b) El Excel local tiene ligeras diferencias con la fuente del cliente.
     c) El cliente aplica algún filtro muy sutil que no hemos detectado.

3. NO SE ENCONTRÓ NINGUNA COMBINACIÓN DE FILTROS QUE COINCIDA EXACTAMENTE
   CON TODOS LOS MESES. La mejor combinación (excluir ELIMINACIÓN CIA.)
   solo reduce el error de 25 a 21, lo cual es marginal.

4. RECOMENDACIÓN:
   - USAR "PLACA ÚNICA SIN FILTROS" como método de cálculo. Es la más simple
     y coincide con la mayoría de meses.
   - ACTUALIZAR el Excel local con los datos faltantes de MAR 2026.
   - VERIFICAR con el cliente si la metodología es simplemente contar placas
     únicas sin filtros, y confirmar de dónde sacó los datos de MAR 2026.
""")

print("=" * 100)

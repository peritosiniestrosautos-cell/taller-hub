#!/usr/bin/env python3
"""
Analizar si los porcentajes del cliente se pueden calcular desde BASE DE DATOS.
"""
import pandas as pd

file_path = "DISTRIKIA COPIA.xlsx"

# Porcentajes del cliente
client_pcts = {
    ('2025', 'FEB'): 40, ('2025', 'MAR'): 47, ('2025', 'ABR'): 60, ('2025', 'MAY'): 42,
    ('2025', 'JUN'): 33, ('2025', 'JUL'): 44, ('2025', 'AGOS'): 41, ('2025', 'SEPT'): 50,
    ('2025', 'OCT'): 44, ('2025', 'NOV'): 35, ('2025', 'DIC'): 24, ('2026', 'ENE'): 44,
    ('2026', 'FEB'): 54, ('2026', 'MAR'): 60, ('2026', 'ABR'): 42
}

print("=" * 80)
print("ANÁLISIS: ¿DE DÓNDE VIENEN LOS PORCENTAJES DEL CLIENTE?")
print("=" * 80)

df = pd.read_excel(file_path, sheet_name='BASE DE DATOS')
print("\nColumnas:", df.columns.tolist())
print("\nShape:", df.shape)
print("\nMuestra de columnas relevantes:")
print(df[['FECHA INGR', 'MES', 'AÑO', 'IMPREVISTO', 'ACCIÓN', 'CAUSAL', 'ESTATUS', 'PROPIO']].head(20))

# Asegurar tipos
df['FECHA INGR'] = pd.to_datetime(df['FECHA INGR'], errors='coerce')
df['AÑO'] = df['AÑO'].astype(str)
df['MES'] = df['MES'].astype(int)

# Mapeo de número de mes a nombre
mes_nombres = {1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
               7: 'JUL', 8: 'AGOS', 9: 'SEPT', 10: 'OCT', 11: 'NOV', 12: 'DIC'}
df['MES_NOMBRE'] = df['MES'].map(mes_nombres)

print("\n" + "=" * 80)
print("VALORES ÚNICOS EN COLUMNA 'IMPREVISTO'")
print("=" * 80)
print(df['IMPREVISTO'].value_counts(dropna=False))

print("\n" + "=" * 80)
print("VALORES ÚNICOS EN COLUMNA 'ACCIÓN'")
print("=" * 80)
print(df['ACCIÓN'].value_counts(dropna=False))

print("\n" + "=" * 80)
print("VALORES ÚNICOS EN COLUMNA 'CAUSAL'")
print("=" * 80)
print(df['CAUSAL'].value_counts(dropna=False))

print("\n" + "=" * 80)
print("VALORES ÚNICOS EN COLUMNA 'ESTATUS'")
print("=" * 80)
print(df['ESTATUS'].value_counts(dropna=False))

print("\n" + "=" * 80)
print("TOTAL REGISTROS POR MES")
print("=" * 80)
total_por_mes = df.groupby(['AÑO', 'MES_NOMBRE']).size().reset_index(name='TOTAL_REGISTROS')
print(total_por_mes.to_string(index=False))

# Contar imprevistos = SI por mes
print("\n" + "=" * 80)
print("IMPREVISTO = 'SI' POR MES")
print("=" * 80)
imprevisto_si = df[df['IMPREVISTO'] == 'SI'].groupby(['AÑO', 'MES_NOMBRE']).size().reset_index(name='IMPREVISTOS_SI')
print(imprevisto_si.to_string(index=False))

# Contar imprevistos != NO o vacíos
print("\n" + "=" * 80)
print("IMPREVISTO != 'NO' POR MES")
print("=" * 80)
imprevisto_not_no = df[df['IMPREVISTO'] != 'NO'].groupby(['AÑO', 'MES_NOMBRE']).size().reset_index(name='IMPREVISTOS_NOT_NO')
print(imprevisto_not_no.to_string(index=False))

# Contar ACCIÓN = RECUPERACIÓN
print("\n" + "=" * 80)
print("ACCIÓN = 'RECUPERACIÓN' POR MES")
print("=" * 80)
accion_rec = df[df['ACCIÓN'] == 'RECUPERACIÓN'].groupby(['AÑO', 'MES_NOMBRE']).size().reset_index(name='ACCION_RECUPERACION')
print(accion_rec.to_string(index=False))

# Contar CAUSAL específicos
print("\n" + "=" * 80)
print("CAUSALES ESPECÍFICAS POR MES")
print("=" * 80)
for causal in ['AJUSTE MANO DE OBRA', 'DAÑO EN PROCESO', 'DIGITACIÓN', 'ELIMINACIÓN CIA.', 'NO COTIZADO', 'NO ES DEL SINIESTRO', 'RECUPERACIÓN DE PIEZA', 'SIN DIAGNÓSTICO', 'TOT', 'NO VISIBLE']:
    count = df[df['CAUSAL'] == causal].groupby(['AÑO', 'MES_NOMBRE']).size().reset_index(name=f'CAUSAL_{causal.replace(" ", "_")}')
    if not count.empty:
        print(f"\n--- {causal} ---")
        print(count.to_string(index=False))

# Calcular tasas
print("\n" + "=" * 80)
print("COMPARACIÓN: TASA DE IMPREVISTOS CALCULADA VS CLIENTE")
print("=" * 80)

# Unir totales
merged = total_por_mes.merge(imprevisto_si, on=['AÑO', 'MES_NOMBRE'], how='left')
merged = merged.merge(imprevisto_not_no, on=['AÑO', 'MES_NOMBRE'], how='left')
merged = merged.merge(accion_rec, on=['AÑO', 'MES_NOMBRE'], how='left')
merged = merged.fillna(0)
merged['TASA_SI'] = (merged['IMPREVISTOS_SI'] / merged['TOTAL_REGISTROS'] * 100).round(2)
merged['TASA_NOT_NO'] = (merged['IMPREVISTOS_NOT_NO'] / merged['TOTAL_REGISTROS'] * 100).round(2)
merged['TASA_RECUPERACION'] = (merged['ACCION_RECUPERACION'] / merged['TOTAL_REGISTROS'] * 100).round(2)

# Agregar porcentaje del cliente
merged['CLIENTE_PCT'] = merged.apply(lambda row: client_pcts.get((row['AÑO'], row['MES_NOMBRE']), None), axis=1)

print(merged.to_string(index=False))

# ============================================================
# Revisar si la tasa se calcula con vehículos únicos (placas únicas)
# ============================================================
print("\n" + "=" * 80)
print("ANÁLISIS CON PLACAS ÚNICAS POR MES")
print("=" * 80)

# Placas únicas por mes
placas_unicas = df.groupby(['AÑO', 'MES_NOMBRE'])['PLACA '].nunique().reset_index(name='PLACAS_UNICAS')
print(placas_unicas.to_string(index=False))

# Imprevisto SI con placas únicas
imprevisto_si_unique = df[df['IMPREVISTO'] == 'SI'].groupby(['AÑO', 'MES_NOMBRE'])['PLACA '].nunique().reset_index(name='IMPREV_SI_UNIQUE')
print("\nImprevisto=SI (placas únicas):")
print(imprevisto_si_unique.to_string(index=False))

# Revisar la hoja TASA DE IMPREVISTOS para ver los totales
print("\n" + "=" * 80)
print("DATOS DE 'TASA DE IMPREVISTOS' (vehículos entregados por mes)")
print("=" * 80)
df_tasa = pd.read_excel(file_path, sheet_name='TASA DE IMPREVISTOS', header=1)
print(df_tasa.to_string(index=False))

# ============================================================
# Comparar totales de BASE DE DATOS con TASA DE IMPREVISTOS
# ============================================================
print("\n" + "=" * 80)
print("¿COINCIDEN LOS TOTALES DE BASE DE DATOS CON TASA DE IMPREVISTOS?")
print("=" * 80)

# Los totales en TASA DE IMPREVISTOS parecen ser suma de SURA+BOLÍVAR+ALLIANZ+MAPFRE
# Veamos si coinciden con el conteo de registros en BASE DE DATOS
print("\nComparación (BASE DE DATOS total registros vs TASA DE IMPREVISTOS TOTAL):")
for _, row in total_por_mes.iterrows():
    año = row['AÑO']
    mes = row['MES_NOMBRE']
    total_reg = row['TOTAL_REGISTROS']
    tasa_row = df_tasa[(df_tasa['AÑO'].astype(str) == año) & (df_tasa['MES'] == mes)]
    if not tasa_row.empty:
        tasa_total = tasa_row['TOTAL'].values[0]
        print(f"  {año}-{mes}: BASE DE DATOS={total_reg}, TASA DE IMPREVISTOS TOTAL={tasa_total}, diff={total_reg - tasa_total}")
    else:
        print(f"  {año}-{mes}: BASE DE DATOS={total_reg}, TASA DE IMPREVISTOS=NO ENCONTRADO")

print("\n" + "=" * 80)
print("ANÁLISIS TERMINADO")
print("=" * 80)

import pandas as pd
import numpy as np
import warnings, itertools
warnings.filterwarnings('ignore')

TARGET = 69910566

df_raw = pd.read_excel('/Users/xstaked/Downloads/RENOMOTRIZ.xlsx', sheet_name='BASE DE DATOS')
df_raw.columns = [c.strip().upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U') for c in df_raw.columns]
df_raw['PLACA'] = df_raw['PLACA'].astype(str).str.strip().str.upper()
df_raw['SINIESTRO'] = df_raw['SINIESTRO'].astype(str).str.strip()
df_raw['ESTATUS'] = df_raw['ESTATUS'].astype(str).str.strip().str.upper()
df_raw['CAUSAL'] = df_raw['CAUSAL'].astype(str).str.strip().str.upper().replace('É','E').replace('Ó','O')
df_raw['ACCION'] = df_raw['ACCION'].astype(str).str.strip().str.upper().replace('Ó','O')
df_raw['PROPIO_NORM'] = df_raw['PROPIO'].astype(str).str.strip().str.upper()

df_raw['DIF'] = df_raw['M. DE O. FINAL'] - df_raw['M. DE O. INICIAL']

results = []

def record(total, name):
    if pd.isna(total):
        return
    diff = abs(total - TARGET)
    results.append((diff, total, name))

def dedup_none(df): return df
def dedup_first_ps(df): return df.drop_duplicates(subset=['PLACA','SINIESTRO'], keep='first')
def dedup_last_ps(df): return df.drop_duplicates(subset=['PLACA','SINIESTRO'], keep='last')
def dedup_first_p(df): return df.drop_duplicates(subset=['PLACA'], keep='first')
def dedup_last_p(df): return df.drop_duplicates(subset=['PLACA'], keep='last')
def dedup_sumdif_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False)['DIF'].sum()
    return d.rename(columns={'DIF':'VAL'})
def dedup_maxdif_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False)['DIF'].max()
    return d.rename(columns={'DIF':'VAL'})
def dedup_mindif_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False)['DIF'].min()
    return d.rename(columns={'DIF':'VAL'})
def dedup_meandif_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False)['DIF'].mean()
    return d.rename(columns={'DIF':'VAL'})
def dedup_maxrec_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False)['RECUPERADO'].max()
    return d.rename(columns={'RECUPERADO':'VAL'})
def dedup_sumrec_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False)['RECUPERADO'].sum()
    return d.rename(columns={'RECUPERADO':'VAL'})
def dedup_sumini_sumfin_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False).agg({'M. DE O. INICIAL':'sum','M. DE O. FINAL':'sum'})
    d['VAL'] = d['M. DE O. FINAL'] - d['M. DE O. INICIAL']
    return d
def dedup_meanini_meanfin_ps(df):
    d = df.groupby(['PLACA','SINIESTRO'], as_index=False).agg({'M. DE O. INICIAL':'mean','M. DE O. FINAL':'mean'})
    d['VAL'] = d['M. DE O. FINAL'] - d['M. DE O. INICIAL']
    return d

dedup_fns = [
    ('none', dedup_none),
    ('first_ps', dedup_first_ps),
    ('last_ps', dedup_last_ps),
    ('first_p', dedup_first_p),
    ('last_p', dedup_last_p),
    ('sumdif_ps', dedup_sumdif_ps),
    ('maxdif_ps', dedup_maxdif_ps),
    ('mindif_ps', dedup_mindif_ps),
    ('meandif_ps', dedup_meandif_ps),
    ('maxrec_ps', dedup_maxrec_ps),
    ('sumrec_ps', dedup_sumrec_ps),
    ('sumini_sumfin_ps', dedup_sumini_sumfin_ps),
    ('meanini_meanfin_ps', dedup_meanini_meanfin_ps),
]

estatus_opts = [(None, 'all'), (['AUTORIZADO'], 'aut'), (['AUTORIZADO','EN PROCESO'], 'aut_proc')]
propio_opts = [(None, 'all'), ('SI', 'si'), ('NO', 'no')]
sin_opts = [(False, 'all_sin'), (True, 'nosin_nan')]

causales = df_raw['CAUSAL'].dropna().unique().tolist()
print('Causales unicos:', causales)

causal_exclusion_sets = [[]]
for c in causales:
    causal_exclusion_sets.append([c])
for c1, c2 in itertools.combinations(causales, 2):
    causal_exclusion_sets.append([c1, c2])

print(f'Total sets de exclusiones causales: {len(causal_exclusion_sets)}')

for est_list, est_name in estatus_opts:
    for prop_val, prop_name in propio_opts:
        for drop_sin, sin_name in sin_opts:
            for causal_excl in causal_exclusion_sets:
                d = df_raw.copy()
                if est_list is not None:
                    d = d[d['ESTATUS'].isin(est_list)]
                if prop_val is not None:
                    d = d[d['PROPIO_NORM'] == prop_val]
                if drop_sin:
                    d = d[d['SINIESTRO'].notna() & (d['SINIESTRO'] != '') & (d['SINIESTRO'] != 'NAN')]
                for c in causal_excl:
                    d = d[d['CAUSAL'] != c]
                if len(d) == 0:
                    continue
                for dedup_name, dedup_fn in dedup_fns:
                    try:
                        d2 = dedup_fn(d)
                        if 'VAL' in d2.columns:
                            total = d2['VAL'].sum()
                        else:
                            total = d2['DIF'].sum()
                        name = f"{dedup_name}|{est_name}|{prop_name}|{sin_name}|excl={','.join(causal_excl) if causal_excl else 'none'}"
                        record(total, name)
                    except Exception as e:
                        pass

results.sort()
print(f"\nTotal combinaciones probadas: {len(results)}")
print(f"\n--- Top 50 mas cercanas a {TARGET:,.0f} ---")
for diff, total, name in results[:50]:
    mark = "*** EXACTO ***" if diff == 0 else ("*** CERCANO ***" if diff < 1000 else "")
    print(f"{total:>15,.0f} | diff={diff:>12,.0f} | {name} {mark}")

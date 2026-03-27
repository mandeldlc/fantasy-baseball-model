import pandas as pd
import requests
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season, get_curr_data

print("Identificando closers confirmados...")

SEASON = get_season()
SEASON_1 = SEASON - 1
SEASON_2 = SEASON - 2

# ================================
# CARGAR DATOS
# ================================
pitcheo = pd.read_csv('data/pitcheo_historico.csv')
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

waivers_rp = pd.read_csv('data/waivers_rp.csv')
waivers_rp = waivers_rp[waivers_rp['Name'].notna()]

# Últimas 3 temporadas — automático
pit_curr = get_curr_data(pitcheo)
pit_prev1 = pitcheo[pitcheo['year'] == SEASON_1].copy()
pit_prev2 = pitcheo[pitcheo['year'] == SEASON_2].copy()

print(f"  Temporadas: {SEASON_2}, {SEASON_1}, {SEASON}")
print(f"  Pitchers {SEASON}: {len(pit_curr)}, {SEASON_1}: {len(pit_prev1)}, {SEASON_2}: {len(pit_prev2)}")

# ================================
# IDENTIFICAR CLOSERS
# ================================
def get_sv(df, nombre):
    row = df[df['Name'] == nombre]
    return row['p_save'].values[0] if len(row) > 0 else 0

def get_era(df, nombre):
    row = df[df['Name'] == nombre]
    return row['p_era'].values[0] if len(row) > 0 else 99

def get_xera(df, nombre):
    row = df[df['Name'] == nombre]
    return row['xera'].values[0] if len(row) > 0 else 99

def get_xwoba(df, nombre):
    row = df[df['Name'] == nombre]
    return row['xwoba'].values[0] if len(row) > 0 else 0.400

closers = []
for _, row in waivers_rp.iterrows():
    nombre = row['Name']

    sv_curr  = get_sv(pit_curr,  nombre)
    sv_prev1 = get_sv(pit_prev1, nombre)
    sv_prev2 = get_sv(pit_prev2, nombre)
    era_curr  = get_era(pit_curr,  nombre)
    xera_curr = get_xera(pit_curr, nombre)
    xwoba_curr = get_xwoba(pit_curr, nombre)

    closer_score = 0
    tipo = []

    # Temporada actual
    if sv_curr >= 20:
        closer_score += 5
        tipo.append(f"Closer élite {SEASON} ({sv_curr} SV)")
    elif sv_curr >= 10:
        closer_score += 3
        tipo.append(f"Closer {SEASON} ({sv_curr} SV)")
    elif sv_curr >= 5:
        closer_score += 2
        tipo.append(f"Oportunidades {SEASON} ({sv_curr} SV)")
    elif sv_curr >= 3:
        closer_score += 1
        tipo.append(f"Saves {SEASON} ({sv_curr} SV)")

    # Temporada anterior
    if sv_prev1 >= 20:
        closer_score += 3
        tipo.append(f"Élite {SEASON_1} ({sv_prev1} SV)")
    elif sv_prev1 >= 10:
        closer_score += 2
        tipo.append(f"Historial {SEASON_1} ({sv_prev1} SV)")
    elif sv_prev1 >= 5:
        closer_score += 1
        tipo.append(f"Historial {SEASON_1} ({sv_prev1} SV)")

    # Hace 2 temporadas
    if sv_prev2 >= 20:
        closer_score += 2
        tipo.append(f"Historial {SEASON_2} ({sv_prev2} SV)")
    elif sv_prev2 >= 10:
        closer_score += 1
        tipo.append(f"Historial {SEASON_2} ({sv_prev2} SV)")

    # Calidad
    if era_curr < 3.0:
        closer_score += 2
        tipo.append(f"ERA élite {era_curr:.2f}")
    elif era_curr < 3.50:
        closer_score += 1
    if xera_curr < 3.0:
        closer_score += 2
        tipo.append(f"xERA élite {xera_curr:.2f}")

    # Filtro — tiene saves reales en alguna de las 3 temporadas
    tiene_saves = sv_curr >= 3 or sv_prev1 >= 10 or sv_prev2 >= 15

    if closer_score >= 2 and tiene_saves:
        closers.append({
            'Name': nombre,
            f'SV_{SEASON}': sv_curr,
            f'SV_{SEASON_1}': sv_prev1,
            f'SV_{SEASON_2}': sv_prev2,
            'ERA': era_curr,
            'xERA': xera_curr,
            'xwOBA': xwoba_curr,
            'Closer_Score': closer_score,
            'Tipo': ' | '.join(tipo),
            'breakout_score': row.get('breakout_score', 0)
        })

df_closers = pd.DataFrame(closers).sort_values('Closer_Score', ascending=False) if closers else pd.DataFrame()

# Renombrar para compatibilidad con el dashboard
if len(df_closers) > 0:
    df_closers = df_closers.rename(columns={
        f'SV_{SEASON}': 'SV_2025',
        f'SV_{SEASON_1}': 'SV_2024',
    })

df_closers.to_csv('data/closers.csv', index=False)

print("\n" + "=" * 70)
print("🔒 CLOSERS CONFIRMADOS EN WAIVERS")
print("=" * 70)
if len(df_closers) > 0:
    for _, r in df_closers.iterrows():
        sv_curr_val = r.get('SV_2025', 0)
        sv_prev_val = r.get('SV_2024', 0)
        print(f"  🔒 {r['Name']}: SV{SEASON}={float(sv_curr_val):.0f} SV{SEASON_1}={float(sv_prev_val):.0f} ERA={float(r['ERA']):.2f} xERA={float(r['xERA']):.2f} Score={r['Closer_Score']}")
        print(f"     {r['Tipo']}")
else:
    print("  Ninguno detectado")

print(f"\n✅ {len(df_closers)} closers guardados en data/closers.csv")
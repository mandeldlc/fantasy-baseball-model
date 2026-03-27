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
pit_curr  = get_curr_data(pitcheo, min_registros=1)
pit_prev1 = pitcheo[pitcheo['year'] == SEASON_1].copy()
pit_prev2 = pitcheo[pitcheo['year'] == SEASON_2].copy()

print(f"  Temporadas: {SEASON_2}, {SEASON_1}, {SEASON}")
print(f"  Pitchers {SEASON}: {len(pit_curr)}, {SEASON_1}: {len(pit_prev1)}, {SEASON_2}: {len(pit_prev2)}")

# ================================
# FUNCIONES HELPER
# ================================
def get_stat(df, nombre, col, default=0):
    row = df[df['Name'] == nombre]
    if len(row) == 0:
        return default
    val = row[col].values[0]
    return float(val) if pd.notna(val) else default

# ================================
# IDENTIFICAR CLOSERS
# ================================
closers = []
for _, row in waivers_rp.iterrows():
    nombre = row['Name']

    sv_curr  = get_stat(pit_curr,  nombre, 'p_save')
    sv_prev1 = get_stat(pit_prev1, nombre, 'p_save')
    sv_prev2 = get_stat(pit_prev2, nombre, 'p_save')
    era_curr   = get_stat(pit_curr, nombre, 'p_era',  default=99)
    xera_curr  = get_stat(pit_curr, nombre, 'xera',   default=99)
    xwoba_curr = get_stat(pit_curr, nombre, 'xwoba',  default=0.400)

    closer_score = 0
    tipo = []

    # Temporada actual
    if sv_curr >= 20:
        closer_score += 5
        tipo.append(f"Closer élite {SEASON} ({sv_curr:.0f} SV)")
    elif sv_curr >= 10:
        closer_score += 3
        tipo.append(f"Closer {SEASON} ({sv_curr:.0f} SV)")
    elif sv_curr >= 5:
        closer_score += 2
        tipo.append(f"Oportunidades {SEASON} ({sv_curr:.0f} SV)")
    elif sv_curr >= 3:
        closer_score += 1
        tipo.append(f"Saves {SEASON} ({sv_curr:.0f} SV)")

    # Temporada anterior
    if sv_prev1 >= 20:
        closer_score += 3
        tipo.append(f"Élite {SEASON_1} ({sv_prev1:.0f} SV)")
    elif sv_prev1 >= 10:
        closer_score += 2
        tipo.append(f"Historial {SEASON_1} ({sv_prev1:.0f} SV)")
    elif sv_prev1 >= 5:
        closer_score += 1
        tipo.append(f"Historial {SEASON_1} ({sv_prev1:.0f} SV)")

    # Hace 2 temporadas
    if sv_prev2 >= 20:
        closer_score += 2
        tipo.append(f"Historial {SEASON_2} ({sv_prev2:.0f} SV)")
    elif sv_prev2 >= 10:
        closer_score += 1
        tipo.append(f"Historial {SEASON_2} ({sv_prev2:.0f} SV)")

    # Calidad
    if era_curr < 3.0:
        closer_score += 2
        tipo.append(f"ERA élite {era_curr:.2f}")
    elif era_curr < 3.50:
        closer_score += 1
    if xera_curr < 3.0:
        closer_score += 2
        tipo.append(f"xERA élite {xera_curr:.2f}")

    # Filtro
    tiene_saves = sv_curr >= 3 or sv_prev1 >= 10 or sv_prev2 >= 15

    if closer_score >= 2 and tiene_saves:
        closers.append({
            'Name': nombre,
            'SV_2025': sv_prev1,
            'SV_2024': sv_prev2,
            'ERA': era_curr,
            'xERA': xera_curr,
            'xwOBA': xwoba_curr,
            'Closer_Score': closer_score,
            'Tipo': ' | '.join(tipo),
            'breakout_score': float(row.get('breakout_score', 0))
        })

df_closers = pd.DataFrame(closers).sort_values('Closer_Score', ascending=False) if closers else pd.DataFrame()
df_closers.to_csv('data/closers.csv', index=False)

print("\n" + "=" * 70)
print("🔒 CLOSERS CONFIRMADOS EN WAIVERS")
print("=" * 70)
if len(df_closers) > 0:
    for _, r in df_closers.iterrows():
        print(f"  🔒 {r['Name']}: SV{SEASON_1}={r['SV_2025']:.0f} SV{SEASON_2}={r['SV_2024']:.0f} ERA={r['ERA']:.2f} xERA={r['xERA']:.2f} Score={r['Closer_Score']}")
        print(f"     {r['Tipo']}")
else:
    print("  Ninguno detectado")

print(f"\n✅ {len(df_closers)} closers guardados en data/closers.csv")
from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
from datetime import date

load_dotenv()

query = YahooFantasySportsQuery(
    league_id="31891",
    game_code="mlb",
    game_id=469,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    yahoo_access_token_json=None,
    env_file_location=Path("."),
    save_token_data_to_env_file=True
)

print("Calculando hot/cold streaks...")

# Cargar stats históricas
bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

bateo_2024 = bateo[bateo['year'] == 2024]
bateo_2025 = bateo[bateo['year'] == 2025]
pitcheo_2024 = pitcheo[pitcheo['year'] == 2024]
pitcheo_2025 = pitcheo[pitcheo['year'] == 2025]

# Cargar roster y waivers
mi_roster = pd.read_csv('data/roster.csv')
mis_jugadores = mi_roster['Name'].tolist()

waivers_bat = pd.read_csv('data/waivers_bateadores.csv')
waivers_sp = pd.read_csv('data/waivers_sp.csv')
waivers_rp = pd.read_csv('data/waivers_rp.csv')
jugadores_waivers_bat = waivers_bat['Name'].tolist()
jugadores_waivers_pit = pd.concat([waivers_sp, waivers_rp])['Name'].tolist()

# ================================
# FUNCION CALCULAR STREAK BATEADOR
# ================================
def calc_streak_bat(nombres, fuente):
    resultados = []
    for nombre in nombres:
        stats_2024 = bateo_2024[bateo_2024['Name'] == nombre]
        stats_2025 = bateo_2025[bateo_2025['Name'] == nombre]
        if len(stats_2024) == 0 or len(stats_2025) == 0:
            continue
        woba_2024 = stats_2024['woba'].values[0]
        woba_2025 = stats_2025['woba'].values[0]
        xwoba_2025 = stats_2025['xwoba'].values[0]
        ev_2025 = stats_2025['exit_velocity_avg'].values[0]
        barrel_2025 = stats_2025['barrel_batted_rate'].values[0]
        diff = round(woba_2025 - woba_2024, 3)
        if diff > 0.020:
            streak = '🔥 HOT'
        elif diff < -0.020:
            streak = '🥶 COLD'
        else:
            streak = '➡️ NEUTRAL'
        resultados.append({
            'Name': nombre,
            'Fuente': fuente,
            'wOBA 2024': woba_2024,
            'wOBA 2025': woba_2025,
            'xwOBA 2025': xwoba_2025,
            'EV': ev_2025,
            'Barrel%': barrel_2025,
            'Diff': diff,
            'Streak': streak
        })
    return resultados

# ================================
# FUNCION CALCULAR STREAK PITCHER
# ================================
def calc_streak_pit(nombres, fuente):
    resultados = []
    for nombre in nombres:
        stats_2024 = pitcheo_2024[pitcheo_2024['Name'] == nombre]
        stats_2025 = pitcheo_2025[pitcheo_2025['Name'] == nombre]
        if len(stats_2024) == 0 or len(stats_2025) == 0:
            continue
        era_2024 = stats_2024['p_era'].values[0]
        era_2025 = stats_2025['p_era'].values[0]
        xera_2025 = stats_2025['xera'].values[0]
        ks_2025 = stats_2025['p_strikeout'].values[0]
        diff = round(era_2025 - era_2024, 2)
        if diff < -0.50:
            streak = '🔥 HOT'
        elif diff > 0.50:
            streak = '🥶 COLD'
        else:
            streak = '➡️ NEUTRAL'
        resultados.append({
            'Name': nombre,
            'Fuente': fuente,
            'ERA 2024': era_2024,
            'ERA 2025': era_2025,
            'xERA 2025': xera_2025,
            'Ks': ks_2025,
            'Diff ERA': diff,
            'Streak': streak
        })
    return resultados

# ================================
# CALCULAR PARA ROSTER Y WAIVERS
# ================================
bat_roster = calc_streak_bat(mis_jugadores, 'Mi Roster')
bat_waivers = calc_streak_bat(jugadores_waivers_bat, 'Waiver')
pit_roster = calc_streak_pit(mis_jugadores, 'Mi Roster')
pit_waivers = calc_streak_pit(jugadores_waivers_pit, 'Waiver')

df_bat = pd.DataFrame(bat_roster + bat_waivers).sort_values('Diff', ascending=False)
df_pit = pd.DataFrame(pit_roster + pit_waivers).sort_values('Diff ERA', ascending=True)

df_bat.to_csv('data/streaks_bat.csv', index=False)
df_pit.to_csv('data/streaks_pit.csv', index=False)

print(f"\n✅ Bateadores: {len(df_bat)} ({len(bat_roster)} roster + {len(bat_waivers)} waivers)")
print(f"✅ Pitchers: {len(df_pit)} ({len(pit_roster)} roster + {len(pit_waivers)} waivers)")

print("\n🔥 BATEADORES HOT (roster):")
for r in [r for r in bat_roster if r['Streak'] == '🔥 HOT']:
    print(f"  {r['Name']}: {r['wOBA 2024']} → {r['wOBA 2025']} (+{r['Diff']})")

print("\n🔥 BATEADORES HOT (waivers):")
for r in [r for r in bat_waivers if r['Streak'] == '🔥 HOT'][:5]:
    print(f"  {r['Name']}: {r['wOBA 2024']} → {r['wOBA 2025']} (+{r['Diff']})")
from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import os
import pandas as pd

load_dotenv()

SEASON = date.today().year
SEASON_PREV = SEASON - 1

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

bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

bateo_prev = bateo[bateo['year'] == SEASON_PREV]
bateo_curr = bateo[bateo['year'] == SEASON]
pitcheo_prev = pitcheo[pitcheo['year'] == SEASON_PREV]
pitcheo_curr = pitcheo[pitcheo['year'] == SEASON]

mi_roster = pd.read_csv('data/roster.csv')
mis_jugadores = mi_roster['Name'].tolist()

waivers_bat = pd.read_csv('data/waivers_bateadores.csv')
waivers_sp = pd.read_csv('data/waivers_sp.csv')
waivers_rp = pd.read_csv('data/waivers_rp.csv')
jugadores_waivers_bat = waivers_bat['Name'].tolist()
jugadores_waivers_pit = pd.concat([waivers_sp, waivers_rp])['Name'].tolist()

def calc_streak_bat(nombres, fuente):
    resultados = []
    for nombre in nombres:
        stats_prev = bateo_prev[bateo_prev['Name'] == nombre]
        stats_curr = bateo_curr[bateo_curr['Name'] == nombre]
        if len(stats_prev) == 0 or len(stats_curr) == 0:
            continue
        woba_prev = stats_prev['woba'].values[0]
        woba_curr = stats_curr['woba'].values[0]
        xwoba_curr = stats_curr['xwoba'].values[0]
        ev_curr = stats_curr['exit_velocity_avg'].values[0]
        barrel_curr = stats_curr['barrel_batted_rate'].values[0]
        diff = round(woba_curr - woba_prev, 3)
        if diff > 0.020:
            streak = '🔥 HOT'
        elif diff < -0.020:
            streak = '🥶 COLD'
        else:
            streak = '➡️ NEUTRAL'
        resultados.append({
            'Name': nombre,
            'Fuente': fuente,
            f'wOBA {SEASON_PREV}': woba_prev,
            f'wOBA {SEASON}': woba_curr,
            f'xwOBA {SEASON}': xwoba_curr,
            'EV': ev_curr,
            'Barrel%': barrel_curr,
            'Diff': diff,
            'Streak': streak
        })
    return resultados

def calc_streak_pit(nombres, fuente):
    resultados = []
    for nombre in nombres:
        stats_prev = pitcheo_prev[pitcheo_prev['Name'] == nombre]
        stats_curr = pitcheo_curr[pitcheo_curr['Name'] == nombre]
        if len(stats_prev) == 0 or len(stats_curr) == 0:
            continue
        era_prev = stats_prev['p_era'].values[0]
        era_curr = stats_curr['p_era'].values[0]
        xera_curr = stats_curr['xera'].values[0]
        ks_curr = stats_curr['p_strikeout'].values[0]
        diff = round(era_curr - era_prev, 2)
        if diff < -0.50:
            streak = '🔥 HOT'
        elif diff > 0.50:
            streak = '🥶 COLD'
        else:
            streak = '➡️ NEUTRAL'
        resultados.append({
            'Name': nombre,
            'Fuente': fuente,
            f'ERA {SEASON_PREV}': era_prev,
            f'ERA {SEASON}': era_curr,
            f'xERA {SEASON}': xera_curr,
            'Ks': ks_curr,
            'Diff ERA': diff,
            'Streak': streak
        })
    return resultados

bat_roster = calc_streak_bat(mis_jugadores, 'Mi Roster')
bat_waivers = calc_streak_bat(jugadores_waivers_bat, 'Waiver')
pit_roster = calc_streak_pit(mis_jugadores, 'Mi Roster')
pit_waivers = calc_streak_pit(jugadores_waivers_pit, 'Waiver')

df_bat = pd.DataFrame(bat_roster + bat_waivers)
df_pit = pd.DataFrame(pit_roster + pit_waivers)
if len(df_bat) > 0 and 'Diff' in df_bat.columns:
    df_bat = df_bat.sort_values('Diff', ascending=False)
if len(df_pit) > 0 and 'Diff ERA' in df_pit.columns:
    df_pit = df_pit.sort_values('Diff ERA', ascending=True)

df_bat.to_csv('data/streaks_bat.csv', index=False)
df_pit.to_csv('data/streaks_pit.csv', index=False)

print(f"\n✅ Bateadores: {len(df_bat)} ({len(bat_roster)} roster + {len(bat_waivers)} waivers)")
print(f"✅ Pitchers: {len(df_pit)} ({len(pit_roster)} roster + {len(pit_waivers)} waivers)")

print(f"\n🔥 BATEADORES HOT (roster):")
for r in [r for r in bat_roster if r['Streak'] == '🔥 HOT']:
    print(f"  {r['Name']}: {r[f'wOBA {SEASON_PREV}']} → {r[f'wOBA {SEASON}']} (+{r['Diff']})")

print(f"\n🔥 BATEADORES HOT (waivers):")
for r in [r for r in bat_waivers if r['Streak'] == '🔥 HOT'][:5]:
    print(f"  {r['Name']}: {r[f'wOBA {SEASON_PREV}']} → {r[f'wOBA {SEASON}']} (+{r['Diff']})")
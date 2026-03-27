from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import os
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season

load_dotenv()

SEASON = get_season()
SEASON_PREV = SEASON - 1
SEASON_PREV2 = SEASON - 2

query = YahooFantasySportsQuery(
    league_id="31891", game_code="mlb", game_id=469,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    yahoo_access_token_json=None,
    env_file_location=Path("."), save_token_data_to_env_file=True
)

print("Calculando hot/cold streaks...")

bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')

bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

# Usar temporada actual si tiene datos, si no usar la anterior
bateo_curr = bateo[bateo['year'] == SEASON]
bateo_prev = bateo[bateo['year'] == SEASON_PREV]
bateo_prev2 = bateo[bateo['year'] == SEASON_PREV2]
pitcheo_curr = pitcheo[pitcheo['year'] == SEASON]
pitcheo_prev = pitcheo[pitcheo['year'] == SEASON_PREV]
pitcheo_prev2 = pitcheo[pitcheo['year'] == SEASON_PREV2]

print(f"  Data {SEASON}: {len(bateo_curr)} bateadores, {len(pitcheo_curr)} pitchers")
print(f"  Data {SEASON_PREV}: {len(bateo_prev)} bateadores, {len(pitcheo_prev)} pitchers")

mi_roster = pd.read_csv('data/roster.csv')
mis_jugadores = mi_roster['Name'].tolist()

waivers_bat = pd.read_csv('data/waivers_bateadores.csv')
waivers_sp = pd.read_csv('data/waivers_sp.csv')
waivers_rp = pd.read_csv('data/waivers_rp.csv')
jugadores_waivers_bat = waivers_bat['Name'].tolist()
jugadores_waivers_pit = pd.concat([waivers_sp, waivers_rp])['Name'].tolist()

def get_bat_stats(nombre):
    """Obtener stats actuales y anteriores con fallback inteligente"""
    curr = bateo_curr[bateo_curr['Name'] == nombre]
    prev = bateo_prev[bateo_prev['Name'] == nombre]
    prev2 = bateo_prev2[bateo_prev2['Name'] == nombre]

    if len(curr) > 0 and len(prev) > 0:
        return curr.iloc[0], prev.iloc[0], SEASON, SEASON_PREV
    elif len(prev) > 0 and len(prev2) > 0:
        return prev.iloc[0], prev2.iloc[0], SEASON_PREV, SEASON_PREV2
    return None, None, None, None

def get_pit_stats(nombre):
    curr = pitcheo_curr[pitcheo_curr['Name'] == nombre]
    prev = pitcheo_prev[pitcheo_prev['Name'] == nombre]
    prev2 = pitcheo_prev2[pitcheo_prev2['Name'] == nombre]

    if len(curr) > 0 and len(prev) > 0:
        return curr.iloc[0], prev.iloc[0], SEASON, SEASON_PREV
    elif len(prev) > 0 and len(prev2) > 0:
        return prev.iloc[0], prev2.iloc[0], SEASON_PREV, SEASON_PREV2
    return None, None, None, None

def calc_streak_bat(nombres, fuente):
    resultados = []
    for nombre in nombres:
        s_curr, s_prev, yr_curr, yr_prev = get_bat_stats(nombre)
        if s_curr is None or s_prev is None:
            continue
        woba_curr = s_curr['woba']
        woba_prev = s_prev['woba']
        xwoba_curr = s_curr['xwoba']
        ev_curr = s_curr['exit_velocity_avg']
        barrel_curr = s_curr['barrel_batted_rate']
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
            f'wOBA {yr_prev}': round(woba_prev, 3),
            f'wOBA {yr_curr}': round(woba_curr, 3),
            f'xwOBA {yr_curr}': round(xwoba_curr, 3),
            'EV': round(ev_curr, 1),
            'Barrel%': round(barrel_curr, 1),
            'Diff': diff,
            'Streak': streak,
            'Comparativo': f'{yr_prev} vs {yr_curr}'
        })
    return resultados

def calc_streak_pit(nombres, fuente):
    resultados = []
    for nombre in nombres:
        s_curr, s_prev, yr_curr, yr_prev = get_pit_stats(nombre)
        if s_curr is None or s_prev is None:
            continue
        era_curr = s_curr['p_era']
        era_prev = s_prev['p_era']
        xera_curr = s_curr['xera']
        ks_curr = s_curr['p_strikeout']
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
            f'ERA {yr_prev}': round(era_prev, 2),
            f'ERA {yr_curr}': round(era_curr, 2),
            f'xERA {yr_curr}': round(xera_curr, 2),
            'Ks': round(ks_curr, 0),
            'Diff ERA': diff,
            'Streak': streak,
            'Comparativo': f'{yr_prev} vs {yr_curr}'
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
    print(f"  {r['Name']} [{r['Comparativo']}]: Diff +{r['Diff']}")

print(f"\n🔥 BATEADORES HOT (waivers top 5):")
for r in [r for r in bat_waivers if r['Streak'] == '🔥 HOT'][:5]:
    print(f"  {r['Name']} [{r['Comparativo']}]: Diff +{r['Diff']}")
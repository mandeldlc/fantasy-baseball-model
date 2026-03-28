from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import os
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blend_utils import get_season, get_blend_weights

load_dotenv()

SEASON = get_season()
SEASON_PREV = SEASON - 1
SEASON_PREV2 = SEASON - 2
W_HIST, W_CURR = get_blend_weights()

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

bateo_curr  = bateo[bateo['year'] == SEASON].copy()
bateo_prev  = bateo[bateo['year'] == SEASON_PREV].copy()
bateo_prev2 = bateo[bateo['year'] == SEASON_PREV2].copy()
pitcheo_curr  = pitcheo[pitcheo['year'] == SEASON].copy()
pitcheo_prev  = pitcheo[pitcheo['year'] == SEASON_PREV].copy()
pitcheo_prev2 = pitcheo[pitcheo['year'] == SEASON_PREV2].copy()

print(f"  Data {SEASON}: {len(bateo_curr)} bateadores, {len(pitcheo_curr)} pitchers")
print(f"  Data {SEASON_PREV}: {len(bateo_prev)} bateadores, {len(pitcheo_prev)} pitchers")
print(f"  Blend: {int(W_HIST*100)}% hist / {int(W_CURR*100)}% actual")

mi_roster = pd.read_csv('data/roster.csv')
mis_jugadores = mi_roster['Name'].tolist()

waivers_bat = pd.read_csv('data/waivers_bateadores.csv')
waivers_sp  = pd.read_csv('data/waivers_sp.csv')
waivers_rp  = pd.read_csv('data/waivers_rp.csv')
jugadores_waivers_bat = waivers_bat['Name'].tolist()
jugadores_waivers_pit = pd.concat([waivers_sp, waivers_rp])['Name'].tolist()

def blend_woba(woba_prev, woba_curr, pa_curr):
    """Blend inteligente — más peso a 2026 cuando hay más PA"""
    if pa_curr <= 0 or woba_curr > 0.600 or woba_curr <= 0:
        return woba_prev  # datos inválidos → usar solo historial
    w = min(W_CURR * (pa_curr / 50), W_CURR) if pa_curr < 50 else W_CURR
    w_h = 1 - w
    return round(w_h * woba_prev + w * woba_curr, 3)

def blend_era(era_prev, era_curr, ip_curr):
    """Blend ERA — más peso a 2026 cuando hay más IP"""
    if ip_curr <= 0 or era_curr > 15 or era_curr <= 0:
        return era_prev
    w = min(W_CURR * (ip_curr / 20), W_CURR) if ip_curr < 20 else W_CURR
    w_h = 1 - w
    return round(w_h * era_prev + w * era_curr, 2)

def get_bat_stats(nombre):
    """Stats blended: si hay 2026 hacer blend con 2025, sino comparar 2025 vs 2024"""
    curr = bateo_curr[bateo_curr['Name'] == nombre]
    prev = bateo_prev[bateo_prev['Name'] == nombre]
    prev2 = bateo_prev2[bateo_prev2['Name'] == nombre]

    if len(prev) > 0:
        s_prev = prev.iloc[0]
        if len(curr) > 0:
            s_curr = curr.iloc[0]
            pa_curr = float(s_curr.get('pa', 0))
            # Blend wOBA y xwOBA
            woba_blended  = blend_woba(float(s_prev['woba']),  float(s_curr['woba']),  pa_curr)
            xwoba_blended = blend_woba(float(s_prev['xwoba']), float(s_curr['xwoba']), pa_curr)
            ev_blended    = blend_woba(float(s_prev.get('exit_velocity_avg', 88)),
                                       float(s_curr.get('exit_velocity_avg', 88)), pa_curr)
            barrel_blended = blend_woba(float(s_prev.get('barrel_batted_rate', 8)),
                                        float(s_curr.get('barrel_batted_rate', 8)), pa_curr)
            # Crear fila blended
            blended = s_prev.copy()
            blended['woba']  = woba_blended
            blended['xwoba'] = xwoba_blended
            blended['exit_velocity_avg']   = ev_blended
            blended['barrel_batted_rate']  = barrel_blended
            return blended, s_prev, SEASON, SEASON_PREV
        elif len(prev2) > 0:
            return s_prev, prev2.iloc[0], SEASON_PREV, SEASON_PREV2
    return None, None, None, None

def get_pit_stats(nombre):
    curr  = pitcheo_curr[pitcheo_curr['Name'] == nombre]
    prev  = pitcheo_prev[pitcheo_prev['Name'] == nombre]
    prev2 = pitcheo_prev2[pitcheo_prev2['Name'] == nombre]

    if len(prev) > 0:
        s_prev = prev.iloc[0]
        if len(curr) > 0:
            s_curr = curr.iloc[0]
            ip_curr = float(s_curr.get('p_formatted_ip', 0))
            era_blended  = blend_era(float(s_prev['p_era']), float(s_curr['p_era']), ip_curr)
            xera_blended = blend_era(float(s_prev['xera']), float(s_curr['xera']), ip_curr)
            blended = s_prev.copy()
            blended['p_era'] = era_blended
            blended['xera']  = xera_blended
            return blended, s_prev, SEASON, SEASON_PREV
        elif len(prev2) > 0:
            return s_prev, prev2.iloc[0], SEASON_PREV, SEASON_PREV2
    return None, None, None, None

def calc_streak_bat(nombres, fuente):
    resultados = []
    for nombre in nombres:
        s_curr, s_prev, yr_curr, yr_prev = get_bat_stats(nombre)
        if s_curr is None or s_prev is None:
            continue
        woba_curr  = float(s_curr['woba'])
        woba_prev  = float(s_prev['woba'])
        xwoba_curr = float(s_curr['xwoba'])
        ev_curr    = float(s_curr.get('exit_velocity_avg', 0))
        barrel_curr = float(s_curr.get('barrel_batted_rate', 0))

        # Validar valores
        if woba_curr > 0.600 or woba_prev > 0.600:
            continue

        diff = round(woba_curr - woba_prev, 3)
        streak = '🔥 HOT' if diff > 0.020 else '🥶 COLD' if diff < -0.020 else '➡️ NEUTRAL'

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
        era_curr  = float(s_curr['p_era'])
        era_prev  = float(s_prev['p_era'])
        xera_curr = float(s_curr['xera'])
        ks_curr   = float(s_curr.get('p_strikeout', 0))

        if era_curr > 15 or era_prev > 15:
            continue

        diff = round(era_curr - era_prev, 2)
        streak = '🔥 HOT' if diff < -0.50 else '🥶 COLD' if diff > 0.50 else '➡️ NEUTRAL'

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

bat_roster  = calc_streak_bat(mis_jugadores, 'Mi Roster')
bat_waivers = calc_streak_bat(jugadores_waivers_bat, 'Waiver')
pit_roster  = calc_streak_pit(mis_jugadores, 'Mi Roster')
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
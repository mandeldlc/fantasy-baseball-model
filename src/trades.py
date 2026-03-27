from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
import json

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

print("Analizando trades posibles...")

# Cargar stats
bateo = pd.read_csv('data/bateo_historico.csv')
pitcheo = pd.read_csv('data/pitcheo_historico.csv')
bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']

# Calcular WHIP
pitcheo['p_formatted_ip'] = pd.to_numeric(pitcheo['p_formatted_ip'], errors='coerce')
pitcheo['p_whip'] = ((pitcheo['p_walk'] + pitcheo['hit']) / pitcheo['p_formatted_ip']).round(3)

from datetime import date
SEASON = date.today().year
bateo_2025 = bateo[bateo['year'] == SEASON]
pitcheo_2025 = pitcheo[pitcheo['year'] == SEASON]
if len(bateo_2025) < 50:
    bateo_2025 = bateo[bateo['year'] == SEASON - 1]
if len(pitcheo_2025) < 50:
    pitcheo_2025 = pitcheo[pitcheo['year'] == SEASON - 1]

mi_roster = pd.read_csv('data/roster.csv')
mis_jugadores = mi_roster['Name'].tolist()

# Categorías de la liga
CAT_BAT = ['r_run', 'home_run', 'b_rbi', 'r_total_stolen_base', 'on_base_percent', 'slg_percent']
CAT_BAT_NOMBRES = ['R', 'HR', 'RBI', 'SB', 'OBP', 'SLG']
CAT_PIT = ['p_win', 'p_strikeout', 'p_era', 'p_whip', 'p_save']
CAT_PIT_NOMBRES = ['W', 'K', 'ERA', 'WHIP', 'NSV']
CAT_PIT_LOWER = ['p_era', 'p_whip']

def calc_valor_bat(jugadores):
    stats = bateo_2025[bateo_2025['Name'].isin(jugadores)]
    if len(stats) == 0:
        return {}
    resultado = {}
    for col, nombre in zip(CAT_BAT, CAT_BAT_NOMBRES):
        if col in stats.columns:
            val = stats[col].mean(skipna=True)
            resultado[nombre] = round(float(val), 3) if pd.notna(val) else 0.0
        else:
            resultado[nombre] = 0.0
    return resultado

def calc_valor_pit(jugadores):
    stats = pitcheo_2025[pitcheo_2025['Name'].isin(jugadores)]
    if len(stats) == 0:
        return {}
    resultado = {}
    for col, nombre in zip(CAT_PIT, CAT_PIT_NOMBRES):
        if col in stats.columns:
            val = stats[col].mean(skipna=True)
            resultado[nombre] = round(float(val), 3) if pd.notna(val) else 0.0
        else:
            resultado[nombre] = 0.0
    return resultado

def calc_valor_pit(jugadores):
    stats = pitcheo_2025[pitcheo_2025['Name'].isin(jugadores)]
    if len(stats) == 0:
        return {}
    resultado = {}
    for col, nombre in zip(CAT_PIT, CAT_PIT_NOMBRES):
        if col in stats.columns:
            val = stats[col].mean()
            if pd.notna(val):
                resultado[nombre] = round(val, 3)
    return resultado

# Stats de mi equipo
mis_bat_stats = calc_valor_bat(mis_jugadores)
mis_pit_stats = calc_valor_pit(mis_jugadores)

print(f"\n📊 Mis stats promedio:")
print(f"  Bateo: {mis_bat_stats}")
print(f"  Pitcheo: {mis_pit_stats}")

# Analizar todos los equipos
trades_sugeridos = []

for team_id in range(1, 13):
    if team_id == 6:
        continue
    try:
        team = query.get_team_info(team_id=team_id)
        roster = query.get_team_roster_by_week(team_id=team_id, chosen_week=1)
        team_name = team.name.decode('utf-8') if isinstance(team.name, bytes) else team.name
        jugadores = [p.name.full for p in roster.players]

        opp_bat = calc_valor_bat(jugadores)
        opp_pit = calc_valor_pit(jugadores)

        # Identificar mis debilidades y sus fortalezas
        for cat, col in zip(CAT_BAT_NOMBRES, CAT_BAT):
            mi_val = mis_bat_stats.get(cat, 0)
            opp_val = opp_bat.get(cat, 0)
            if opp_val > 0 and mi_val > 0 and opp_val > mi_val * 1.1:
                if col in bateo_2025.columns:
                    sus_jugadores = bateo_2025[bateo_2025['Name'].isin(jugadores)].sort_values(col, ascending=False).head(3)
                    for _, j in sus_jugadores.iterrows():
                        mis_excesos = []
                        for cat2, col2 in zip(CAT_BAT_NOMBRES, CAT_BAT):
                            mi_val2 = mis_bat_stats.get(cat2, 0)
                            opp_val2 = opp_bat.get(cat2, 0)
                            if mi_val2 > 0 and opp_val2 > 0 and mi_val2 > opp_val2 * 1.1:
                                mis_excesos.append(cat2)

                        trades_sugeridos.append({
                            'oponente': team_name,
                            'pedir': j['Name'],
                            'categoria_pedir': cat,
                            'valor_pedir': round(j[col], 3),
                            'mi_debilidad': round(mi_val, 3),
                            'mis_fortalezas': ', '.join(mis_excesos) if mis_excesos else 'N/A',
                            'tipo': 'Bateador'
                        })

        # Pitcheo
        for cat, col in zip(CAT_PIT_NOMBRES, CAT_PIT):
            mi_val = mis_pit_stats.get(cat, 0)
            opp_val = opp_pit.get(cat, 0)
            lower = col in CAT_PIT_LOWER
            if lower:
                mejora = opp_val > 0 and mi_val > 0 and opp_val < mi_val * 0.9
            else:
                mejora = opp_val > 0 and mi_val > 0 and opp_val > mi_val * 1.1
            if mejora:
                if col in pitcheo_2025.columns:
                    asc = not lower
                    sus_pit = pitcheo_2025[pitcheo_2025['Name'].isin(jugadores)].sort_values(col, ascending=asc).head(3)
                    for _, j in sus_pit.iterrows():
                        mis_excesos_pit = []
                        for cat2, col2 in zip(CAT_PIT_NOMBRES, CAT_PIT):
                            mi_val2 = mis_pit_stats.get(cat2, 0)
                            opp_val2 = opp_pit.get(cat2, 0)
                            lower2 = col2 in CAT_PIT_LOWER
                            if lower2:
                                if mi_val2 > 0 and opp_val2 > 0 and mi_val2 < opp_val2 * 0.9:
                                    mis_excesos_pit.append(cat2)
                            else:
                                if mi_val2 > 0 and opp_val2 > 0 and mi_val2 > opp_val2 * 1.1:
                                    mis_excesos_pit.append(cat2)

                        trades_sugeridos.append({
                            'oponente': team_name,
                            'pedir': j['Name'],
                            'categoria_pedir': cat,
                            'valor_pedir': round(j[col], 3) if pd.notna(j[col]) else 0,
                            'mi_debilidad': round(mi_val, 3),
                            'mis_fortalezas': ', '.join(mis_excesos_pit) if mis_excesos_pit else 'N/A',
                            'tipo': 'Pitcher'
                        })

        print(f"  ✅ {team_name} analizado")

    except Exception as e:
        print(f"  ❌ Equipo {team_id}: {e}")

df_trades = pd.DataFrame(trades_sugeridos)
if len(df_trades) > 0:
    df_trades = df_trades.sort_values('valor_pedir', ascending=False)

df_trades.to_csv('data/trades_sugeridos.csv', index=False)
print(f"\n✅ {len(df_trades)} trades analizados — guardado en data/trades_sugeridos.csv")
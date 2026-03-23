from yfpy.query import YahooFantasySportsQuery
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
import numpy as np
from datetime import date, timedelta
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

# ================================
# OBTENER MATCHUP POR FECHA
# ================================
def get_matchup_by_date(target_date):
    matchups = query.get_team_matchups(team_id=6)
    for m in matchups:
        try:
            start = date.fromisoformat(m.week_start)
            end = date.fromisoformat(m.week_end)
            if start <= target_date <= end:
                return m
        except:
            continue
    return None

def procesar_matchup(matchup):
    if matchup is None:
        return None

    teams = matchup.teams
    mi_equipo = None
    oponente = None

    for t in teams:
        if isinstance(t, dict):
            team = t.get('team', t)
        else:
            team = t
        try:
            team_id = team.team_id
        except:
            team_id = team.get('team_id')
        if team_id == 6:
            mi_equipo = team
        else:
            oponente = team

    oponente_name = oponente.name.decode('utf-8') if isinstance(oponente.name, bytes) else oponente.name
    oponente_id = oponente.team_id
    week = matchup.week
    week_start = matchup.week_start
    week_end = matchup.week_end

    print(f"\n⚔️  Semana {week}: Dando Tabla vs {oponente_name}")
    print(f"📅 {week_start} — {week_end}")

    # Roster del oponente
    print(f"Obteniendo roster de {oponente_name}...")
    roster_oponente = query.get_team_roster_by_week(team_id=oponente_id, chosen_week=week)
    jugadores_oponente = [p.name.full for p in roster_oponente.players]

    # Stats
    bateo = pd.read_csv('data/bateo_historico.csv')
    pitcheo = pd.read_csv('data/pitcheo_historico.csv')
    bateo[['last_name', 'first_name']] = bateo['last_name, first_name'].str.split(', ', expand=True)
    bateo['Name'] = bateo['first_name'] + ' ' + bateo['last_name']
    pitcheo[['last_name', 'first_name']] = pitcheo['last_name, first_name'].str.split(', ', expand=True)
    pitcheo['Name'] = pitcheo['first_name'] + ' ' + pitcheo['last_name']
    bateo_2025 = bateo[bateo['year'] == 2025]
    pitcheo_2025 = pitcheo[pitcheo['year'] == 2025]

    mi_roster = pd.read_csv('data/roster.csv')
    mis_jugadores = mi_roster['Name'].tolist()

    def calc_bat_stats(jugadores, label):
        stats = bateo_2025[bateo_2025['Name'].isin(jugadores)]
        if len(stats) == 0:
            return {}
        return {
            'equipo': label,
            'jugadores': len(stats),
            'HR_avg': round(stats['home_run'].mean(), 1),
            'OPS': round(stats['on_base_plus_slg'].mean(), 3),
            'wOBA': round(stats['woba'].mean(), 3),
            'xwOBA': round(stats['xwoba'].mean(), 3),
            'EV': round(stats['exit_velocity_avg'].mean(), 1),
            'Barrel%': round(stats['barrel_batted_rate'].mean(), 1),
        }

    def calc_pit_stats(jugadores, label):
        stats = pitcheo_2025[pitcheo_2025['Name'].isin(jugadores)]
        if len(stats) == 0:
            return {}
        return {
            'equipo': label,
            'jugadores': len(stats),
            'ERA': round(stats['p_era'].mean(), 2),
            'xERA': round(stats['xera'].mean(), 2),
            'Ks': round(stats['p_strikeout'].mean(), 1),
            'xwOBA': round(stats['xwoba'].mean(), 3),
            'EV_against': round(stats['exit_velocity_avg'].mean(), 1),
        }

    mis_bat = calc_bat_stats(mis_jugadores, 'Dando Tabla')
    opp_bat = calc_bat_stats(jugadores_oponente, oponente_name)
    mis_pit = calc_pit_stats(mis_jugadores, 'Dando Tabla')
    opp_pit = calc_pit_stats(jugadores_oponente, oponente_name)

    return {
        'semana': week,
        'oponente': oponente_name,
        'oponente_id': int(oponente_id),
        'week_start': str(week_start),
        'week_end': str(week_end),
        'mis_bat': mis_bat,
        'opp_bat': opp_bat,
        'mis_pit': mis_pit,
        'opp_pit': opp_pit
    }

# ================================
# PROCESAR SEMANA ACTUAL Y SIGUIENTE
# ================================
hoy = date.today()
semana_siguiente = hoy + timedelta(weeks=1)

print("Obteniendo matchup semana actual...")
matchup_actual = get_matchup_by_date(hoy)
resultado_actual = procesar_matchup(matchup_actual)

print("\nObteniendo matchup semana siguiente...")
matchup_siguiente = get_matchup_by_date(semana_siguiente)
resultado_siguiente = procesar_matchup(matchup_siguiente)

# Guardar
with open('data/matchup_semana.json', 'w') as f:
    json.dump(resultado_actual, f, indent=2)

if resultado_siguiente:
    with open('data/matchup_siguiente.json', 'w') as f:
        json.dump(resultado_siguiente, f, indent=2)

print("\n✅ Guardado en data/matchup_semana.json y data/matchup_siguiente.json")